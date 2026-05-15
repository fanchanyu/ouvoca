# LLM-ERP 導入實施手冊（顧問用 · 繁體中文）— v3.0

> **2 週上線、Day-by-Day SOP**
> 適用：導入顧問 / 整合商 / 內部 IT

> ⚡ **v3.0 戰略軸轉通知**：Day 1-14 中所有「Mobile App / LINE Bot / 外協 QR」步驟在 v3.0 跳過。
> v3.0 只需部署：backend + frontend-desktop + PostgreSQL + Redis + MinIO（無 Expo、無 LINE Channel 申請）。

---

## 📑 目錄

1. [導入流程速覽](#1-導入流程速覽)
2. [Pre-Sales 階段](#2-pre-sales-階段)
3. [Day 1-2 合約簽訂 + 需求訪談](#3-day-1-2)
4. [Day 3-5 環境準備](#4-day-3-5)
5. [Day 6-7 Docker 安裝 + 行業範例](#5-day-6-7)
6. [Day 8-9 客戶資料匯入](#6-day-8-9)
7. [Day 10 超管教育訓練](#7-day-10)
8. [Day 11-12 部門主管教育訓練](#8-day-11-12)
9. [Day 13 內部試營運](#9-day-13)
10. [Day 14 正式上線](#10-day-14)
11. [上線後 30 天追蹤](#11-上線後-30-天追蹤)
12. [常見導入陷阱](#12-常見導入陷阱)

---

## 1. 導入流程速覽

```
Pre-Sales        Implementation (2 週)              Hyper-care (30 天)
─────────  ────────────────────────────────────  ──────────────────
需求訪談      Day 1-2 簽約 + 需求                每週回訪
PoC 試用      Day 3-5 環境準備                   日誌監控
報價          Day 6-7 安裝 + Demo data           小問題即時修
簽約          Day 8-9 客戶資料匯入                月底回顧會議
              Day 10  超管訓練 (2h)
              Day 11-12 部門訓練 (5×1h)
              Day 13 試營運
              Day 14 正式上線
```

**核心 KPI**：上線後 30 天內 DAU/總人數 ≥ 60%。

---

## 2. Pre-Sales 階段

### 2.1 需求訪談清單

進客戶之前先填這 12 題：

```
公司資料
─ 員工人數：____ 人
─ 主要產業：金屬 / 塑膠 / PCB / 食品 / 紡織 / 其他____
─ 年營收：____ 億 NT$
─ 客戶數：____ 家   主要客戶：________________
─ 供應商數：____ 家  主要供應商：________________
─ 是否多廠：是 / 否   廠數：____

現況痛點（複選）
□ ERP 太貴買不起
□ 庫存不同步
□ 老闆要看數字要等
□ 外協廠協同困難
□ 業務拿不到即時庫存
□ 員工不會用現有系統
□ 其他：____

數位現況
─ 目前用什麼：Excel / SAP / 自製 / 無
─ 月 IT 預算：____ 萬 NT$
─ 是否有 IT 人員：是 / 否
─ 是否使用 LINE 群組：是 / 否
─ 是否願意導入 LINE Bot：是 / 否
```

### 2.2 PoC 14 天試用

- 寄安裝包 + INSTALLATION_ZH.pdf
- 客戶自行 `install.bat` → Demo Mode 進入
- 顧問每 3 天 LINE 群組詢問狀況
- 第 12 天約 30 分鐘 review 通話

---

## 3. Day 1-2 簽約 + 需求訪談

### 簽約 Checklist

- [ ] 合約版本：v_____
- [ ] 訂閱方案：Basic / Pro / Enterprise
- [ ] 年費已確認
- [ ] 一次性導入費已確認
- [ ] 付款條件：50% 預付 / 50% 上線
- [ ] SLA 等級：8h / 2h / 1h
- [ ] 加值服務：客製 / 教育訓練加開 / etc.

### 需求訪談（Day 2，現場 4 小時）

帶完整 12 題問卷 + 訪談以下角色：

| 角色 | 訪談時長 | 重點問題 |
|---|---|---|
| 老闆 | 30 分鐘 | 最在意哪 3 個數字？最常 LINE 問什麼？ |
| 業務主管 | 30 分鐘 | 客戶面前最尷尬的時刻？ |
| 生產主管 | 30 分鐘 | 卡單最常發生在哪？ |
| 採購主管 | 30 分鐘 | 進料延遲怎麼追？ |
| 倉管 | 30 分鐘 | 盤點怎麼做？多久一次？ |
| IT（若有）| 60 分鐘 | 機器 / 網路 / 備份現況 |
| 會計 | 30 分鐘 | 月結幾號完成？發票怎麼開？ |

訪談**錄音**（取得同意），結束 24 小時內整理出**需求確認書**。

---

## 4. Day 3-5 環境準備

### 4.1 硬體 / 雲端決策樹

```
Q1: 有沒有自己的伺服器？
  → 有 → Q2
  → 沒有 → 雲端託管模式（GCP/AWS/Azure）
  
Q2: 規格夠嗎？(4-core / 8GB / 100GB SSD)
  → 夠 → 自架模式 → Q3
  → 不夠 → 升級或雲端
  
Q3: 是否有 IT 人員？
  → 有 → 完全交給客戶 IT
  → 沒有 → 我們的工程師遠端協作
```

### 4.2 部署清單

- [ ] 硬體 / VM 規格符合要求
- [ ] OS：Linux Server (推 Ubuntu 22.04+)
- [ ] Docker 24+ 已裝
- [ ] 防火牆 port 5173/8000 對內網開放
- [ ] 公網 access（若要 LINE Bot）：Cloudflare Tunnel 設好
- [ ] 域名（若有自有 SaaS）：DNS A 紀錄指好

### 4.3 客戶帳號開通

- [ ] 預設 admin 帳號（onboarding 完換密碼）
- [ ] 為老闆 / 業務主管 / 生產主管 / 採購 / 倉管 開帳號
- [ ] 確認 LINE 群組已加我們的客服機器人

---

## 5. Day 6-7 Docker 安裝 + 行業範例

### Day 6 標準安裝（< 2 小時）

```bash
cd /opt/llm-erp
git clone https://github.com/your-org/llm-erp.git
cd llm-erp
cp backend/.env.example backend/.env
# 編輯 .env：JWT_SECRET、LLM_API_KEY、DATABASE_URL（若不是 SQLite）
docker compose up -d --build
```

完成後跑健康檢查：

```bash
curl http://localhost:8000/api/health | jq
# 應該看到 status=ok, db=ok
```

### Day 7 載入行業範例

按客戶行業選一個：

```bash
docker compose exec backend python -m scripts.seed_industries metal
# 或 plastic / pcb / food / textile / all
```

帶客戶**現場 demo**：
- 登入桌機 UI
- 看 Dashboard 4 統計卡
- 點「庫存」看示範零件
- 試用 AI 對話：「今天工廠狀況」

---

## 6. Day 8-9 客戶資料匯入

### 匯入優先順序

```
🟢 必匯（影響上線）
  1. 員工 + 部門 + 角色（含 RBAC）
  2. 客戶（至少 top 20）
  3. 供應商（至少 top 20）
  4. 零件 + BOM（核心 30 項）

🟡 可延後（上線後補）
  5. 完整客戶清單
  6. 完整零件清單
  7. 歷史訂單（最近 3 個月）
  8. 歷史庫存交易
```

### 匯入工具

提供 Excel 範本（位於 `templates/`）：
- `import_employees.xlsx`
- `import_customers.xlsx`
- `import_suppliers.xlsx`
- `import_parts.xlsx`
- `import_bom.xlsx`

執行：

```bash
docker compose exec backend python -m scripts.import_excel employees.xlsx
```

### 資料品質檢核

匯入後一定要跑：

```bash
docker compose exec backend python -m scripts.data_quality_check
# 輸出：孤兒記錄 / 重複 master data / 異常 BOM
```

---

## 7. Day 10 超管教育訓練（2 小時）

對象：客戶 IT 主管 / 系統管理員

### 大綱

| 時間 | 內容 |
|---|---|
| 30 分 | 系統架構 30 秒看懂（SYSTEM_TOPOLOGY） |
| 30 分 | RBAC 5 層 + 帳號權限管理 |
| 30 分 | 監控 / 備份 / 升級 SOP |
| 30 分 | Q&A + 故障排除演練 |

### 必教 5 件事

1. **帳號管理** — 新增 / 停用 / 改權限
2. **資料備份** — `docker compose exec backend cp /app/erp.db /tmp/backup.db`
3. **看 log** — `docker compose logs -f backend | grep ERROR`
4. **升級** — `git pull && docker compose up -d --build`
5. **緊急重啟** — `docker compose restart`

### 教材

- `docs/ADMIN_GUIDE.md`（完整管理員指南）
- `docs/SUPPORT_RUNBOOK_ZH.md`（出狀況怎麼辦）

---

## 8. Day 11-12 部門主管教育訓練（5 × 1 小時）

### 排程建議

| 時段 | 對象 | 重點 |
|---|---|---|
| Day 11 09:00 | 老闆 | LINE Bot + Dashboard 看數字 |
| Day 11 14:00 | 業務主管 | 手機查庫存 + 開報價 + AI 對話 |
| Day 11 16:00 | 生產主管 | 手機看工單 + 推播設定 |
| Day 12 09:00 | 採購主管 | 桌機建 PO + 手機掃 QR 進料 |
| Day 12 14:00 | 倉管 | 手機盤點 + 移轉 |

### 老闆訓練（最關鍵 60 分鐘）

```
00:00  LINE 加官方帳號 + 綁定（10 分）
00:10  問「今天狀況」實際體驗（5 分）
00:15  看 Dashboard 4 個數字代表什麼（15 分）
00:30  紅色警示介紹（5 分）
00:35  示範 5 個常問問題（15 分）
00:50  Q&A + 加 line 群組（10 分）
```

---

## 9. Day 13 內部試營運

### 試營運清單

- [ ] 所有員工帳號可登入
- [ ] 各部門至少完成 1 筆真實業務操作
- [ ] AI 助手至少 5 次成功互動
- [ ] 手機 App 至少 3 人安裝
- [ ] 老闆 LINE Bot 互動 ≥ 5 次
- [ ] 任何 bug / 不順手立即記錄

### 異常追蹤表

| 時間 | 報告人 | 問題 | 處理人 | 狀態 |
|---|---|---|---|---|
| | | | | |

---

## 10. Day 14 正式上線

### 上線 Ceremony

09:00 全員集合（影音會議或現場）：
- 老闆致詞 1 分鐘
- 顧問演示「今天問了什麼 AI」5 分鐘
- 立刻啟動使用（不再用舊系統 / Excel）

### 上線當天必做

- [ ] 跑 `bash scripts/run_gates.sh` 確認全綠
- [ ] 確認所有員工已通知正式上線
- [ ] 客戶 IT 確認備份排程已啟動
- [ ] 顧問 standby 4 小時待命處理問題
- [ ] 收尾款 50%

---

## 11. 上線後 30 天追蹤

### Week 1（高關注期）

- 每日 LINE 群組詢問
- 每日看 `GET /api/analytics/summary` 確認使用量
- 任何 bug 24 小時內 patch

### Week 2-3（過渡期）

- 每 3 天詢問
- 個別員工訪談 3 人，問「最不順手是什麼」
- 微調 RBAC 權限

### Day 30 回顧會議

帶這份報告給老闆：

```
┌─────────────────────────────────────┐
│ LLM-ERP 上線 30 天回顧               │
├─────────────────────────────────────┤
│ • 總使用者 _____ / 啟用 _____        │
│ • DAU 平均 _____ (目標 60%)         │
│ • AI 對話次數 _____ 次              │
│ • Mobile 安裝率 _____ %             │
│ • 抓到並修的 bug _____ 個            │
│ • 客戶滿意度（10 分制）_____        │
│ • 下個月優先做的 3 件事：             │
│   1. _________                      │
│   2. _________                      │
│   3. _________                      │
└─────────────────────────────────────┘
```

---

## 12. 常見導入陷阱

| 陷阱 | 預防 |
|---|---|
| 客戶不交資料 | 簽約時就排好「Day 8 之前必須交」 |
| 老闆沒興趣用 LINE | Day 11 老闆親自體驗 + 顧問陪坐 |
| 員工抗拒 | 預先發 USER_MANUAL_ZH.pdf + 教材影片 |
| 網路不通 | Day 5 之前先測 `curl from phone` |
| 防火牆檔 LLM API | Day 3 之前測過 `/api/chat-v2` |
| 試營運出 bug | Day 13 試營運務必充分 |
| 上線後沒人用 | Day 14 老闆出席必須 |

---

**對應英文版**：[`IMPLEMENTATION_PLAYBOOK_EN.md`](./IMPLEMENTATION_PLAYBOOK_EN.md)
**最後更新**：2026-05-14 · v2.5
