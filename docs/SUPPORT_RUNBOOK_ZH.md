# LLM-ERP 支援運維手冊（繁體中文）— v3.0

> **出狀況怎麼辦 — 給客戶 IT 或我們客服**
> 設計：照著做就能 90% 自救，剩下 10% 才需要找原廠。

> ⚡ **v3.0 戰略軸轉通知**：§6.3「LINE Bot Webhook 收不到」於 v3.0 下架（LINE Bot 不再是產品功能）。

---

## 📑 目錄

1. [緊急程度分級](#1-緊急程度分級)
2. [常見問題快查表](#2-常見問題快查表)
3. [系統無法啟動](#3-系統無法啟動)
4. [API 變慢 / 超時](#4-api-變慢--超時)
5. [LLM 連不上](#5-llm-連不上)
6. [SSE 推播沒收到](#6-sse-推播沒收到)
7. [資料庫鎖死](#7-資料庫鎖死)
8. [被攻擊](#8-被攻擊)
9. [日常監控 SOP](#9-日常監控-sop)
10. [緊急升級 vs 回滾](#10-緊急升級-vs-回滾)

---

## 1. 緊急程度分級

| 等級 | 描述 | 回應時間 | 處理人 |
|---|---|---|---|
| **🔴 P0** | 系統完全停擺 / 資料毀損 | 即時 | 廠商 + 客戶 IT 同時 |
| **🟠 P1** | 核心功能不可用（不能登入 / 不能下單）| 1 小時內 | 廠商 |
| **🟡 P2** | 某功能異常但有 workaround | 8 小時內 | 廠商 |
| **🟢 P3** | UI bug / 文字錯字 | 1 週內 | 廠商 |

---

## 2. 常見問題快查表

| 現象 | 立刻試 | 詳見 |
|---|---|---|
| 整個瀏覽器打不開 | `docker compose ps`，看哪個 container down | §3 |
| 登入後一片空白 | F12 看 Console 錯誤，可能是 JWT_SECRET 變了 | §3.4 |
| 庫存查詢轉圈不回 | 看 backend log，可能 N+1 query | §4 |
| AI 對話「連線錯誤」 | 看 `/api/health` 的 llm_provider 狀態 | §5 |
| 老闆 LINE Bot 沒回應 | 檢查 Cloudflare Tunnel + LINE Channel webhook URL | §6 |
| 「Database is locked」 | SQLite 寫入競爭 | §7 |
| 突然 429 Too Many Requests | Rate limit 觸發，可能被攻擊 | §8 |

---

## 3. 系統無法啟動

### 3.1 檢查 container 狀態

```bash
docker compose ps
```

看到 `Exit X` → 該服務掛了。

### 3.2 backend 啟動失敗

```bash
docker compose logs backend | tail -50
```

常見錯誤對應：

| Log 訊息 | 原因 | 修法 |
|---|---|---|
| `JWT_SECRET still default` | 沒設密鑰 | 編 `.env` 設 `JWT_SECRET=$(openssl rand -hex 32)` |
| `OperationalError: no such table` | 沒跑 migration | `docker compose exec backend alembic upgrade head` |
| `Connection refused: postgres` | DB 沒起 | `docker compose up -d db` |
| `ImportError` | 升版檔案不全 | `git status` 看遺漏 |

### 3.3 frontend 跑不起來

```bash
docker compose logs frontend | tail -30
```

常見：nginx config 錯誤 → 看 `nginx.conf` 是否被改壞。

### 3.4 登入後一片空白

90% 是「JWT_SECRET 改過 → 舊 token 失效但前端 cache 還在用」。

修：
1. 開瀏覽器 DevTools → Application → Clear site data
2. 重新登入

---

## 4. API 變慢 / 超時

### 4.1 確認哪個 endpoint 慢

```bash
docker compose logs backend | grep "took" | sort -k 9 -nr | head -10
```

### 4.2 常見原因

| 原因 | 證據 | 修法 |
|---|---|---|
| N+1 query | log 有大量「SELECT」連續 | 在對應 service 加 `selectinload` |
| LLM 響應慢 | 只有 chat endpoint 慢 | §5 |
| DB 滿了 | 「disk full」warning | 清舊資料 / 加碟 |
| Index 缺失 | 大表 + slow query | `EXPLAIN` 看 + 加 index |

### 4.3 快速降載

如果某 endpoint 被狂打：

```bash
# Rate limit 已內建，加嚴：編 .env
RATE_LIMIT_ENABLED=true
# Restart
docker compose restart backend
```

---

## 5. LLM 連不上

### 5.1 確認 health

```bash
curl http://localhost:8000/api/health | jq .llm_provider
# 應該回："deepseek" / "claude" 等，不應該回 null
```

### 5.2 測試 API Key

```bash
docker compose exec backend python -c "
from app.config import settings
print('Provider:', settings.LLM_PROVIDER)
print('API key set:', bool(settings.LLM_API_KEY))
print('Model:', settings.LLM_MODEL)
"
```

### 5.3 對應 provider 的故障

| Provider | 503 解法 |
|---|---|
| Claude | 等 5 分鐘 / 切換到 DeepSeek 暫用 |
| OpenAI | 同上 |
| DeepSeek | 中國機房有時不穩，切 Ollama 本地暫用 |
| Ollama | 確認 Ollama service 還活著：`curl http://ollama:11434/api/tags` |

### 5.4 緊急降級到 Demo Mode

```bash
# .env
LLM_PROVIDER=disabled
docker compose restart backend
# 所有 chat endpoint 回 demo 訊息（不會錯），其餘功能正常
```

---

## 6. SSE 推播沒收到

### 6.1 檢查 nginx config

```bash
docker compose exec frontend cat /etc/nginx/conf.d/default.conf | grep -A 5 "/api/events"
```

必須有：
```
proxy_buffering off;
proxy_cache off;
chunked_transfer_encoding off;
```

### 6.2 測試 SSE 通道

```bash
curl -N http://localhost:8000/api/events/stream
# 應該每 10 秒看到一筆 heartbeat
```

如果一直沒輸出 → nginx buffering 沒關。

### 6.3 LINE Bot Webhook 收不到

- Cloudflare Tunnel 起來嗎？`cloudflared tunnel list`
- LINE Channel 後台 Webhook URL 設對嗎？
- Signature 驗證有沒有過？看 backend log。

---

## 7. 資料庫鎖死

「Database is locked」幾乎都是 SQLite 寫入競爭。

### 7.1 立即解法

```bash
docker compose restart backend
```

### 7.2 長期解法

升級到 PostgreSQL：

```bash
# .env
DATABASE_URL=postgresql+asyncpg://erp:password@db:5432/erp
# 同時改 docker-compose.yml 加 PostgreSQL service
```

詳見 `docs/ADMIN_GUIDE.md` 「升級到 PostgreSQL」章節。

---

## 8. 被攻擊

### 8.1 偵測

每日跑：

```bash
docker compose logs backend | grep -E "429|risk_flagged|injection" | wc -l
```

數量陡增 → 可能被攻擊。

### 8.2 立即措施

1. **加嚴 rate limit**（編 `.env`）：
   ```
   RATE_LIMIT_LLM_CHAT=5/minute  # 從 30 降到 5
   ```
2. **暫時關 LLM**（如果是針對 LLM cost 攻擊）：`LLM_PROVIDER=disabled`
3. **設防火牆規則**：在 nginx 加 `deny` 黑名單 IP
4. **看 audit log** 抓出攻擊源頭：
   ```bash
   docker compose exec backend python -m scripts.audit_query \
       --period 1h --filter "status_code=429"
   ```

### 8.3 報告 + 加白名單

確定攻擊源 IP 後：
- nginx 加白名單（只開放客戶辦公室 IP）
- 通知客戶 IT 換 VPN

---

## 9. 日常監控 SOP

### 9.1 每日（自動）

加進 crontab：

```cron
# 每天 09:00 跑健康檢查 + LINE 通知
0 9 * * * /opt/llm-erp/scripts/daily_health_check.sh
```

`daily_health_check.sh`：

```bash
#!/bin/bash
cd /opt/llm-erp
HEALTH=$(curl -s http://localhost:8000/api/health)
LINE_TOKEN=$YOUR_LINE_NOTIFY_TOKEN

if [ "$(echo $HEALTH | jq -r .status)" != "ok" ]; then
    curl -X POST https://notify-api.line.me/api/notify \
         -H "Authorization: Bearer $LINE_TOKEN" \
         -d "message=⚠️ LLM-ERP 健康檢查失敗：$HEALTH"
fi
```

### 9.2 每週

- 看 `GET /api/analytics/ai-cost` 確認沒超量
- 看 `docker compose logs backend | grep ERROR | wc -l`，異常數要 < 10
- 跑 `bash scripts/run_gates.sh` 確認 8 道閘都綠

### 9.3 每月

- 跑 backup script
- 跑 `scripts/data_quality_check`
- 與客戶月度回顧

---

## 10. 緊急升級 vs 回滾

### 10.1 標準升級

```bash
cd /opt/llm-erp
git fetch && git checkout v2.5  # 指定版本，不要直接 main
docker compose pull
docker compose up -d --build
# 跑 migration
docker compose exec backend alembic upgrade head
# 驗證
bash scripts/run_gates.sh
```

### 10.2 升級壞了要回滾

```bash
cd /opt/llm-erp
# 先停服務
docker compose down
# 還原資料
cp /opt/backup/erp-pre-upgrade.db erp.db
# 回到舊版
git checkout v2.4
docker compose up -d --build
```

**事前準備**：升級前必跑 `docker compose exec backend cp /app/erp.db /tmp/erp-$(date +%F).db`。

---

## 📞 升級不順 / 撞牆找我們

| 等級 | 聯絡方式 |
|---|---|
| P0 系統停擺 | 24/7 phone（Pro+）/ LINE @llmerp |
| P1 核心壞 | 工作日 office hours |
| P2/P3 | support@llm-erp.example |

---

**對應英文版**：[`SUPPORT_RUNBOOK_EN.md`](./SUPPORT_RUNBOOK_EN.md)
**最後更新**：2026-05-14 · v2.5
