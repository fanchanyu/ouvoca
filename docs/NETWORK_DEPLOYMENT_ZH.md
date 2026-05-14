# 網路部署規劃手冊（繁體中文）

> **這份文件兼顧兩種讀者**：
> - 🧑‍💼 **老闆 / 一般使用者**：看圖、看比喻、看「我的資料安全嗎」
> - 🧑‍💻 **技術工程師 / IT**：看 config、看 port、看 nginx / VPN 範例
>
> **核心承諾呼應**：本系統是 **LINE-Native 小型製造業 ERP**——主廠資料留在主廠、外協廠用 LINE 不註冊、業務手機隨身查、老闆用 LINE 一句話問狀況。所有網路設計都圍繞這個核心。

---

## 🎯 給老闆看的 30 秒摘要

```
┌──────────────────────────────────────────────────────┐
│   我的工廠數據去哪裡了？                              │
├──────────────────────────────────────────────────────┤
│                                                      │
│   1. 主機放在「您的廠內」一台便宜的電腦上             │
│      → 資料 100% 不出廠房                             │
│                                                      │
│   2. 員工手機 / 桌機在「廠內 WiFi」就能用              │
│      → 速度快、不怕斷網                               │
│                                                      │
│   3. 業務在外用 4G/5G 連回廠內                        │
│      → 一條加密通道，沒人偷得到                       │
│                                                      │
│   4. 老闆用 LINE 問問題                              │
│      → LINE 訊息走 Cloudflare 加密通道進廠            │
│      → 工廠回答後，加密通道送回 LINE                  │
│                                                      │
│   5. 外協廠（如鍍鋅老吳）用 LINE 回報完工             │
│      → 不用註冊系統、不用裝 App                       │
│      → 掃 QR 即可，主廠立刻知道                       │
│                                                      │
│   ✅ 全程沒有把資料上傳到雲端                          │
│   ✅ 全程加密                                          │
│   ✅ 您可以隨時拔網路線「斷外」                        │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 📐 三種典型部署情境

### 情境 A：單一工廠（10-50 人）— 最常見

```
                  ☁ 公網
                  │
       ┌──────────┼──────────┐
       │          │          │
   👔老闆     👨‍💼業務     👨‍🏭工廠
   LINE      4G/5G       (在外)
   (在家)    手機         手機
       │          │          │
       │          │          │
       └────┐  ┌──┘          │
            ▼  ▼              │
       Cloudflare Tunnel       │
       (加密通道、免費)         │
            │                  │
═══════════════════════════════════════════ 工廠網路邊界
            ▼                  │
       廠內 NAS / 電腦 1 台      │
       ┌───────────────────┐    │
       │  Docker            │    │
       │   ├─ backend       │    │
       │   ├─ frontend      │    │
       │   └─ war-room      │    │
       │  Port 80 / 443     │    │
       └───────────────────┘    │
            ▲                  │
            │                  │
       ┌────┴──────┐  ┌────────┘
   👩‍💻採購阿玲    👴老吳外協
   廠內桌機       (LINE)
   (廠內 WiFi)
```

**特色**：
- ✅ 一台機器搞定（最低 i5 / 8GB RAM / 100GB SSD）
- ✅ 月成本：電費 + Cloudflare 免費
- ✅ 資料 100% 在廠內
- ⚠️ 工廠停電就停服務（建議 UPS）

---

### 情境 B：多廠 MESH（總部 + 分廠 + 外協廠）

```
                ☁ 公網（Cloudflare Tunnel）
                │
                ▼
         ┌──────────────┐
         │   👔 老闆     │
         │  LINE Bot    │
         └──────┬───────┘
                │
═══════════════════════════════════════════ 公司 VPN 邊界
                ▼
       ┌────────────────┐
       │  HQ 總部 server  │ ← 主資料庫（聚合視圖）
       │  :8000          │
       └────────┬───────┘
                │ WireGuard VPN
        ┌───────┼────────┬───────────┐
        ▼       ▼        ▼           ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │ 主廠 A  │ │ 外協 B │ │ 外協 C │ │ 外協 D │
   │ :8001  │ │ :8002  │ │ :8003  │ │ :8004  │
   │本地 LLM│ │本地 LLM│ │本地 LLM│ │本地 LLM│
   │本地 DB │ │本地 DB │ │本地 DB │ │本地 DB │
   └────────┘ └────────┘ └────────┘ └────────┘
   (Ollama)   (Ollama)   (Ollama)   (Ollama)

       ★ 各廠資料留在自己廠裡 ★
       ★ HQ 只取聚合結果（VMI 友善）★
```

**特色**：
- ✅ 各廠資料主權（不離廠）
- ✅ HQ 統一視角看全鏈
- ✅ 即使工廠斷網，本地仍能運作（離線優先）
- ⚠️ 需要 VPN 配置（WireGuard 簡單）

---

### 情境 C：雲端託管（沒有 IT 的小廠）

```
              ☁ AWS / Azure / GCP
              │
              ▼
        ┌──────────────┐
        │ Cloud Server │  ← 由我們代管 / 客戶自管
        │  Docker      │
        │  HTTPS       │
        └──────┬───────┘
               │
       ┌───────┼───────┬─────────┐
       ▼       ▼       ▼         ▼
    LINE    Mobile  Desktop   Outsource
    Bot     App     UI        QR Bot
```

**特色**：
- ✅ 完全不用維護
- ✅ 自動備份
- ✅ 隨時擴容
- ⚠️ 資料在雲端（信任服務商）
- ⚠️ 訂閱費較高

---

## 🔌 完整 Port 對照表

| Port | 服務 | 對外開放 | 用途 |
|---|---|---|---|
| **80** | Frontend (nginx) | ✅ 公網 / 內網 | Desktop UI + 反向代理 API |
| **443** | Frontend (HTTPS) | ✅ 公網 | SSL 加密版 |
| **8000** | Backend (FastAPI) | ❌ 僅內部 | REST API + SSE |
| **8001-8003** | Factory Nodes | ❌ VPN 內 | MESH 工廠節點 |
| **8080** | War-Room | 🟡 內部 / 主管 | 即時看板（純展示） |
| **5432** | PostgreSQL | ❌ 僅 backend | 資料庫 |
| **6379** | Redis (Phase 5) | ❌ 僅 backend | Cache / Queue |
| **9000-9001** | MinIO (Phase 2) | ❌ 僅 backend | 圖片儲存 |
| **11434** | Ollama (本地 LLM) | ❌ 僅 factory node | 隱私 LLM |

**防火牆規則建議**（ufw 範例）：

```bash
# Production 防火牆設定
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH（限定來源 IP 更佳）
sudo ufw allow 80/tcp    # HTTP（自動跳 HTTPS）
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## 🧑‍💻 給技術人員：完整反向代理設定

### nginx 完整 production 設定

```nginx
# /etc/nginx/sites-available/llm-erp
upstream backend {
    server localhost:8000;
    keepalive 32;
}

# HTTP → HTTPS 強制跳轉
server {
    listen 80;
    server_name erp.your-company.com;
    return 301 https://$host$request_uri;
}

# HTTPS 主服務
server {
    listen 443 ssl http2;
    server_name erp.your-company.com;

    ssl_certificate     /etc/letsencrypt/live/erp.your-company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/erp.your-company.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # 安全頭
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options          "SAMEORIGIN" always;
    add_header X-Content-Type-Options   "nosniff" always;

    # 上傳限制
    client_max_body_size 20m;

    # ─── SSE 專用（必須優先匹配）───
    location = /api/events/stream {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering    off;
        proxy_cache        off;
        proxy_read_timeout 86400s;
        proxy_set_header   X-Accel-Buffering "no";
    }

    # ─── 一般 API ───
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout    90s;  # 給 LLM 留空間

        # Rate limiting（防暴力登入）
        limit_req zone=api burst=20 nodelay;
    }

    # ─── LINE Bot webhook（公網需可達）───
    location = /api/line/webhook {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        # LINE 要求嚴格驗證 SSL 簽章
    }

    # ─── SPA frontend ───
    location / {
        root /var/www/llm-erp;
        try_files $uri $uri/ /index.html;
    }
}

# Rate limit 區設定（放在 http {} 區塊）
# limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
```

### Let's Encrypt 免費 SSL

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d erp.your-company.com
# 自動申請 + 自動續約
```

---

## 🌐 LINE Bot Webhook：讓 LINE 找到您

### 問題
LINE Bot 要求**您的 server 必須有公網 URL**。但小廠通常沒固定 IP、不想開防火牆。

### 三種解法（推薦由上到下）

#### 解法 A：Cloudflare Tunnel（推薦 ⭐⭐⭐⭐⭐）

**優點**：免費、不開防火牆、自動 HTTPS、無流量限制

```bash
# 1. 安裝 cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cf.deb
sudo dpkg -i cf.deb

# 2. 登入 Cloudflare（瀏覽器跳出）
cloudflared tunnel login

# 3. 建立 tunnel
cloudflared tunnel create llm-erp

# 4. 設定路由（在 Cloudflare DNS 加 CNAME）
# erp.your-company.com → <tunnel-id>.cfargotunnel.com

# 5. 啟動 tunnel
cloudflared tunnel route dns llm-erp erp.your-company.com
cloudflared tunnel --url http://localhost:8000 run llm-erp
```

設成 systemd service 開機自啟。

#### 解法 B：ngrok（測試用）

```bash
ngrok http 8000
# 拿到 https://xxxxx.ngrok.io
# 在 LINE 後台填這個 URL
```

> ⚠️ 免費版每次重啟換 URL，正式使用建議付費或改用 Cloudflare。

#### 解法 C：自己有固定 IP

申請固定 IP（中華電信約 1500/月），開放 port 443。
**不建議**——維護負擔大。

---

## 🔐 MESH 多廠 VPN 設定（WireGuard）

### 為什麼用 WireGuard
- **簡單**：設定檔比 OpenVPN 短 80%
- **快速**：核心級實作，效能佳
- **安全**：現代加密協議

### HQ server 設定

```bash
# /etc/wireguard/wg0.conf (HQ)
[Interface]
PrivateKey = <HQ_PRIVATE_KEY>
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
# Factory A
PublicKey = <FACTORY_A_PUBLIC_KEY>
AllowedIPs = 10.0.0.2/32

[Peer]
# Factory B (outsource)
PublicKey = <FACTORY_B_PUBLIC_KEY>
AllowedIPs = 10.0.0.3/32
```

### Factory 端設定

```bash
# /etc/wireguard/wg0.conf (Factory A)
[Interface]
PrivateKey = <FACTORY_A_PRIVATE_KEY>
Address = 10.0.0.2/24

[Peer]
PublicKey = <HQ_PUBLIC_KEY>
Endpoint = hq.your-company.com:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
```

### 啟動

```bash
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

### 工廠節點 docker-compose 設定

```yaml
factory-a:
  command: ["python", "factory_node.py"]
  environment:
    FACTORY_ID: factory-a
    HQ_URL: http://10.0.0.1:8000   # 走 VPN 內網 IP
    PORT: 8001
  network_mode: host  # 直接用 host 網路，吃 WireGuard
```

---

## 👴 給工廠老闆看的「資料安全圖」

```
        我的廠內                         網路另一頭
   ┌─────────────────┐
   │  我的伺服器       │
   │  ┌───────────┐   │              ┌──────────────┐
   │  │ 客戶資料  │   │              │              │
   │  │ 訂單     │   │  ← 加密 →    │   LINE      │
   │  │ 庫存     │   │  ════════>   │   業務手機   │
   │  │ 工單     │   │              │   外協 LINE  │
   │  │ 員工資料 │   │              │              │
   │  └───────────┘   │              └──────────────┘
   │       ▲          │
   │       │          │                    ⚠️
   │   只有我授權的   │              如果中間有人偷看
   │   使用者能看      │              他只能看到亂碼
   │                  │
   └─────────────────┘

   ✓ 資料儲存在我廠內，不上雲
   ✓ 進出都加密（HTTPS / VPN）
   ✓ 我可以隨時拔網路線「斷外」
   ✓ 我控制誰能進來看（RBAC）
```

---

## 🛠️ 快速設定檢查表（給自己 IT）

部署到 production **必做**：

- [ ] `JWT_SECRET` 改隨機 64 字元（`openssl rand -hex 32`）
- [ ] `DEBUG=false`
- [ ] `LOG_JSON=true`（給 ELK / Loki 用）
- [ ] `CORS_ORIGINS` 改成真實 domain（不要 `*`）
- [ ] Demo 帳號 admin 改強密碼
- [ ] 防火牆只開 80/443（內部 5432）
- [ ] HTTPS 設好（Let's Encrypt）
- [ ] 備份策略：每日 + 每週
- [ ] 監控告警（Phase 7）
- [ ] LINE Bot webhook URL 設好

---

## 🚀 一鍵啟動腳本（給沒有 IT 的小廠）

把這個存成 `start.sh`：

```bash
#!/bin/bash
# LLM-ERP 一鍵啟動腳本

set -e

echo "🚀 LLM-ERP 一鍵啟動..."

# 1. 檢查 Docker
if ! command -v docker &> /dev/null; then
  echo "❌ 請先安裝 Docker：https://docs.docker.com/get-docker/"
  exit 1
fi

# 2. 第一次設定
if [ ! -f backend/.env ]; then
  echo "📝 第一次執行，建立設定檔..."
  cp backend/.env.example backend/.env
  # 自動產生 JWT_SECRET
  SECRET=$(openssl rand -hex 32)
  sed -i.bak "s|change-me-in-production-please-use-openssl-rand-hex-32|$SECRET|" backend/.env
  rm -f backend/.env.bak
  echo "✅ JWT_SECRET 已自動產生"
fi

# 3. 啟動
echo "🐳 啟動容器..."
docker compose up -d --build

# 4. 等 backend 健康
echo "⏳ 等 backend 啟動（最多 60 秒）..."
for i in {1..30}; do
  if curl -fsS http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Backend 啟動完成"
    break
  fi
  sleep 2
done

# 5. 首次 seed
if [ ! -f backend/.seeded ]; then
  echo "🌱 第一次執行，載入示範資料..."
  docker compose exec -T backend python -m scripts.seed
  touch backend/.seeded
fi

echo ""
echo "🎉 完成！請打開瀏覽器："
echo ""
echo "   桌面 UI:    http://localhost:5173"
echo "   War Room:   http://localhost:8080"
echo "   API 文件:   http://localhost:8000/docs"
echo ""
echo "   登入：admin / admin123"
```

執行：`chmod +x start.sh && ./start.sh`

---

## 📞 遇到問題？

| 症狀 | 可能原因 | 解法 |
|---|---|---|
| 看不到 Dashboard | backend 還沒起 | 等 30 秒 / 看 `docker compose logs backend` |
| LINE Bot 不回 | webhook URL 不對 | 檢查 Cloudflare Tunnel 是否在跑 |
| 工廠連不上 HQ | VPN 沒連 | `sudo wg show` 確認 peer 狀態 |
| 手機看不到 | 跨網域問題 | 確認 nginx 代理 + CORS_ORIGINS |
| SSE 事件不來 | nginx buffer 沒關 | 用我們提供的 nginx.conf |

---

## 📚 進階閱讀

- [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md) - 系統架構拓樸圖
- [ADMIN_GUIDE.md](./ADMIN_GUIDE.md) - 管理員指南
- [DEPLOYMENT.md](./DEPLOYMENT.md) - 完整部署指南
- [USER_MANUAL_ZH.md](./USER_MANUAL_ZH.md) - 使用者操作手冊

---

**最後更新**：2026-05-14
**對應英文版**：[NETWORK_DEPLOYMENT_EN.md](./NETWORK_DEPLOYMENT_EN.md)
