# LLM-ERP 專案總控檔（CLAUDE.md）

> **本檔是專案的「北極星」**：所有開發、規劃、決策與紀錄都以此為單一真相來源。
> 任何 Claude 會話啟動時請先讀此檔，掌握當前進度與下一步。
> **語言**：所有專案內溝通與文件一律使用**繁體中文**。

---

## 0. 速覽（一頁式摘要）

| 項目 | 內容 |
|---|---|
| **專案名稱** | LLM-ERP |
| **目標客戶** | **50–100 人小型製造業**（明確 ICP） |
| **核心承諾** | 「給小型製造業的 **LINE 原生 ERP**：30 萬一年，老闆用 LINE 就能管整個工廠」 |
| **差異化武器** | ① 自然語言操作（不用學系統）② 行動優先（手機/LINE）③ 外協協同（QR + LINE Bot） |
| **三大支柱** | ERP（管理）× AI（智能）× IE 工業工程（適度引用，**不過度設計**） |
| **當前階段** | **Phase 0 完成** → 進入 Phase 1（**LINE-Native + 行動化**） |
| **程式碼位置** | `D:\114-DOWN\LLM-ERP\program\opnetest\` |
| **客戶定位文件** | [docs/CUSTOMER_POSITIONING.md](./docs/CUSTOMER_POSITIONING.md)（**戰略軸心**） |
| **MVP 範圍** | [docs/MVP_DEFINITION.md](./docs/MVP_DEFINITION.md) |
| **分階藍圖** | [docs/ROADMAP.md](./docs/ROADMAP.md)（Phase 0-7，v2 客戶導向版） |
| **差距分析** | [docs/GAP_ANALYSIS.md](./docs/GAP_ANALYSIS.md)（v2 版） |
| **動態工作日誌** | [docs/WORKLOG.md](./docs/WORKLOG.md)（**每次工作後務必更新**） |
| **PDF ↔ 程式對映** | [docs/KNOWLEDGE_MAP.md](./docs/KNOWLEDGE_MAP.md) |
| **權限系統設計** | [docs/PERMISSION_MODEL.md](./docs/PERMISSION_MODEL.md)（**架構級基礎，2026-05-14 落地**） |
| **架構決策紀錄** | [docs/ARCHITECTURE_DECISIONS.md](./docs/ARCHITECTURE_DECISIONS.md)（12 個 ADR） |
| **資料生命週期** | [docs/DATA_LIFECYCLE.md](./docs/DATA_LIFECYCLE.md)（防 DB 膨脹） |
| **戰略地圖（學術+商業）** | [docs/STRATEGY_LANDSCAPE.md](./docs/STRATEGY_LANDSCAPE.md) |
| **系統架構拓樸圖** | [docs/ARCHITECTURE_DIAGRAM.md](./docs/ARCHITECTURE_DIAGRAM.md) ([SVG](./docs/architecture_diagram.svg)) |
| **系統流程關聯拓樸** | [中文 SYSTEM_TOPOLOGY_ZH](./docs/SYSTEM_TOPOLOGY_ZH.md) / [EN](./docs/SYSTEM_TOPOLOGY_EN.md) ([SVG](./docs/system_flow_topology.svg))（6 視角 + Mermaid）|
| **網路部署規劃** | [中文 NETWORK_DEPLOYMENT_ZH](./docs/NETWORK_DEPLOYMENT_ZH.md) / [EN](./docs/NETWORK_DEPLOYMENT_EN.md) |
| **代碼自查報告** | [docs/CODE_REVIEW_REPORT.md](./docs/CODE_REVIEW_REPORT.md)（19 問題、Critical/High 已清零） |
| **LLM 評比報告** | [中文 LLM_BENCHMARK_REPORT_ZH](./docs/LLM_BENCHMARK_REPORT_ZH.md) / [EN](./docs/LLM_BENCHMARK_REPORT_EN.md)（DeepSeek 10/10 + 開源閉源比較） |
| **產品說明書（給採購決策者）** | [中文 PRODUCT_OVERVIEW_ZH.md](./docs/PRODUCT_OVERVIEW_ZH.md) / [English EN](./docs/PRODUCT_OVERVIEW_EN.md)（**13 章選購指南**） |
| **使用者操作手冊** | [中文 USER_MANUAL_ZH.md](./docs/USER_MANUAL_ZH.md) / [English EN](./docs/USER_MANUAL_EN.md)（**含 Mobile / MESH / PDF**）|
| **🎯 對話式 ERP 北極星（必讀）** | [中文 CONVERSATIONAL_ERP_DESIGN_ZH](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md) / [English EN](./docs/CONVERSATIONAL_ERP_DESIGN_EN.md)（**6 層架構 + 7 設計原則 + 4 階段**）|
| **🎯 Phase 1 Day-1 to Day-5 Spec** | [中文 PHASE1_SPEC_ZH](./docs/CONVERSATIONAL_ERP_PHASE1_SPEC_ZH.md) / [English EN](./docs/CONVERSATIONAL_ERP_PHASE1_SPEC_EN.md)（**動工 spec / 介面契約 / 驗收標準**）|
| **系統架構藍圖（網路架構師）** | [中文 ARCHITECTURE_BLUEPRINT_ZH](./docs/ARCHITECTURE_BLUEPRINT_ZH.md) / [English EN](./docs/ARCHITECTURE_BLUEPRINT_EN.md)（**7 層防禦 + Port Matrix + HA + DR + Cost**）|
| **Secrets 輪換 SOP** | [中文 SECRETS_ROTATION_SOP_ZH](./docs/SECRETS_ROTATION_SOP_ZH.md) / [English EN](./docs/SECRETS_ROTATION_SOP_EN.md)（**6 種 secret + 15 分鐘緊急應變**）|
| **生產 Docker Compose** | [`docker-compose.prod.yml`](./docker-compose.prod.yml)（**healthcheck + 資源限制 + non-root + read-only**）|
| **AI 助手目錄** | [中文 AGENT_CATALOG_ZH](./docs/AGENT_CATALOG_ZH.md) / [English EN](./docs/AGENT_CATALOG_EN.md)（**10 agent + 26 tool + 4 道安全防線**） |
| **台灣合規對照表** | [中文 COMPLIANCE_TW_ZH](./docs/COMPLIANCE_TW_ZH.md) / [English EN](./docs/COMPLIANCE_TW_EN.md)（**401/403 + 電子發票 + 個資法**） |
| **導入實施手冊（顧問）** | [中文 IMPLEMENTATION_PLAYBOOK_ZH](./docs/IMPLEMENTATION_PLAYBOOK_ZH.md) / [English EN](./docs/IMPLEMENTATION_PLAYBOOK_EN.md)（**Day 1-14 SOP**） |
| **支援運維手冊** | [中文 SUPPORT_RUNBOOK_ZH](./docs/SUPPORT_RUNBOOK_ZH.md) / [English EN](./docs/SUPPORT_RUNBOOK_EN.md)（**8 故障情境**） |
| **備份還原 SOP** | [中文 BACKUP_RESTORE_SOP_ZH](./docs/BACKUP_RESTORE_SOP_ZH.md) / [English EN](./docs/BACKUP_RESTORE_SOP_EN.md)（**3-2-1 + DRP**） |
| **安裝指南（給老闆）** | [中文 INSTALLATION_ZH.md](./docs/INSTALLATION_ZH.md) / [English EN](./docs/INSTALLATION_EN.md)（**3 分鐘消費者立場**） |
| **一鍵安裝腳本** | `install.sh`（Mac/Linux）/ `install.bat`（Windows）/ `load_industry.sh` |
| **客戶手冊 PDF（32 份雙語）** | 跑 `build_pdfs.bat`（Win）或 `./build_pdfs.sh`（Mac/Linux）→ 輸出至 `docs/pdf/`。詳見 [scripts/build-pdfs/README.md](./scripts/build-pdfs/README.md) |
| **PR 模板** | [`.github/PULL_REQUEST_TEMPLATE.md`](./.github/PULL_REQUEST_TEMPLATE.md)（**強制貼 run_gates 輸出**） |
| **Mobile App（Expo）** | [`frontend-mobile/README.md`](./frontend-mobile/README.md) + [`VERIFY_MOBILE.md`](./frontend-mobile/VERIFY_MOBILE.md)（**Phase 1 重點**，5 tab 骨架完成） |
| **🛡️ 自證閘（必跑）** | `bash scripts/run_gates.sh` — 8 道閘 ~271 秒，**綠燈才能說完成**。CI: [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) |
| **測試套件** | `backend/tests/` — **126 tests**（103 smoke + 6 persona + 17 integration 含 O2C/P2P/P2I + MESH + Tenant Isolation 4-layer） |
| **AI 治理基礎** | [`app/agents/governance.py`](./backend/app/agents/governance.py)（cost tracker + prompt safety + human-in-loop） |
| **Analytics 6 KPI** | `/api/analytics/{dso,inventory-turn,gross-margin,oee,purchase-concentration,ai-cost,summary}` |
| **台灣稅務 7 endpoints** | `/api/tax/tw/{401,403,einvoice/issue,validate-tax-id,...}` |
| **快速入門 / 管理員 / API** | [QUICK_START](./docs/QUICK_START.md) / [ADMIN_GUIDE](./docs/ADMIN_GUIDE.md) / [API_REFERENCE](./docs/API_REFERENCE.md) |
| **開發 SOP** | [docs/DEVELOPMENT_SOP.md](./docs/DEVELOPMENT_SOP.md) |
| **知識體系** | `D:\114-DOWN\LLM-ERP\生產排程系統完整參考資料 (1).pdf`（14 章理論參考） |
| **阻塞中** | LLM_API_KEY 待提供（架構完成後由使用者交付） |

---

## 1. 專案北極星（Project North Star）

### 1.1 願景（Vision）
> 讓 **50-100 人小型製造業**也能享有現代化 ERP 的紅利——透過 **LINE + 手機 + 自然語言**，把「ERP 導入」從半年顧問工程降為「2 週上線、2 小時上手」。

### 1.2 使命（Mission，三大核心承諾）

1. **🗣️ 自然語言解決導入難題**
   王董用 LINE 問一句「今天狀況」就拿到老闆儀表板；不用學系統、不用受訓、不需 IT 顧問。

2. **📱 手機隨身同步**
   業務在客戶端 3 秒查到庫存/價格/交期；廠長在現場手機就能釋放工單、看推播警示。

3. **🤝 庫存與外協廠即時同步**
   主廠庫存 SSE 即時推送；外協廠用 LINE 掃 QR 就能回報進度，不需註冊、不需學新軟體。

### 1.3 我們做什麼 / 我們不做什麼

| 我們做 ✅ | 我們不做 ❌ |
|---|---|
| 自然語言操作 | 複雜的多階審批 |
| 手機/LINE 原生體驗 | 桌機優先設計 |
| 即時庫存同步 | Excel 風格的多工作表 |
| 外協 LINE 回報 | 要求外協廠註冊新系統 |
| 簡化版 MPS/MRP | 完整版 APS 演算法 |
| MESH 多廠（VMI） | 集中式單一資料庫 |
| AI 主動推播決策 | 月底才出報表 |
| 30-50 萬/年定價 | 200 萬+授權費 |

### 1.4 北極星 KPI（客戶導向版）

| 維度 | KPI | 起始 | MVP 目標 |
|---|---|---|---|
| **採用率** | 50 人廠 DAU/總人數 | n/a | > 60% |
| **AI 對話比例** | 自然語言操作 / 總操作 | < 5% | > 50% |
| **手機使用比例** | 手機請求 / 總請求 | < 10% | > 70% |
| **LINE Bot 互動** | 每日 Bot 訊息數 / 廠 | 0 | > 50 |
| **外協回報率** | 外協工單按時回報 | 0% | > 90% |
| **盤點效率** | 掃碼 vs 紙本 | – | 縮短 80% |
| **報表等待** | 老闆問→拿到答案 | 數小時 | < 10 秒 |
| **導入時間** | 決定購買→上線 | 6-18 月 | < 2 週 |
| **教育訓練** | 每員工受訓時數 | 1-3 月 | < 2 小時 |
| **客單價** | 50 人廠年費 | n/a | 30-50 萬 |

---

## 2. 客戶定位摘要（詳見 [CUSTOMER_POSITIONING.md](./docs/CUSTOMER_POSITIONING.md)）

### 2.1 5 個 Persona

| Persona | 角色 | 主要需求 | 主要裝置 |
|---|---|---|---|
| **王董** | 老闆 | 隨時看公司表現 | LINE |
| **小陳** | 業務 | 客戶面前 3 秒答題 | 手機 |
| **林廠長** | 生產主管 | 看到哪裡卡關 | 手機 + LINE |
| **阿玲** | 採購兼倉管 | 不要重 Key 系統 | 手機（掃碼） |
| **老吳** | 外協廠/作業員 | 不註冊就能回報 | LINE |

### 2.2 核心痛點 vs 解法

| 痛點 | 我們的解法 |
|---|---|
| 太貴（SAP 200 萬+） | 開源 + 30 萬/年 + Docker 一鍵 |
| 太難用 | 自然語言：用講的、用 LINE 問 |
| 行動端弱 | **行動優先**設計 |
| 庫存不同步 | 即時 DB + SSE 推播 |
| 外協看不到 | **外協 QR + LINE Bot** |
| 老闆要看大數字 | LINE Bot 即時儀表板 |
| 缺料才發現 | 自動警示 + 推播 |
| 老師傅不會用 | LINE Bot 跳過所有註冊 |

---

## 3. 知識體系基準（適度引用）

### 3.1 主要參考文件

| 文件 | 用途 |
|---|---|
| `生產排程系統完整參考資料.pdf` | **理論參考**（14 章）。**不需 100% 實作**，只取對小廠有用的部分 |
| `Precision_Manufacturing_Systems_Blueprint.pdf` | 業界實務參照 |

### 3.2 PDF 七層規劃模型對小廠的態度

| 層級 | 對小廠的態度 |
|---|---|
| L0 Strategic | ❌ 不做（老闆自己想） |
| L1 S&OP | ❌ 不做（一週開會就夠） |
| L2 MPS | 🟡 簡化版（不做時間柵欄） |
| L3 MRP | 🟡 簡化版（只做 2 階） |
| L4 RCCP/CRP | ❌ 不做（機台少、目視管理） |
| L5 APS/FCS | ❌ 不做（老師傅憑經驗排得快） |
| L6 MES/SFC | 🟡 簡化（手機報工為主） |

> **重要**：原 v1 規劃要求「七層全做才完整」，**v2 改為「客戶痛點解決就 OK」**。
> 細節請見 [docs/MVP_DEFINITION.md](./docs/MVP_DEFINITION.md)。

---

## 4. 模組進度看板（Module Dashboard）

> **每次完成工作後請更新此看板**——這是專案的儀表板。

### 4.1 MVP 8 大核心功能進度

```
1. LINE Bot 老闆儀表板    ❌ [          ]   0%   Phase 1 重點
2. 手機 App（業務+廠長）  🟢 [███████   ]  70%   ✅ Expo 5 tab 骨架完成，缺推播+報工
3. AI 自然語言查詢        🟢 [████████  ]  80%   ✅ Phase 0 已備（待加寫入工具）
4. 即時庫存同步           🟢 [██████████] 100%   ✅ Phase 0 已備
5. 外協工序追蹤           ❌ [          ]   0%   Phase 1 重點
6. 掃碼盤點/報工          🟡 [████      ]  40%   ✅ 掃描 UI 完成，待接報工 API
7. AI 主動推播            🟡 [█████     ]  50%   EventBus 有，缺 LINE/FCM 整合
8. 基礎訂單到出貨流程     🟢 [█████████ ]  95%   ✅ Phase 0 已備
```

**MVP 整體進度**：**~70%**（Phase 1-4 完成後達 100%）

### 4.2 行動化 & LINE 整合進度

```
LINE Bot Webhook        ❌ [          ]   0%
LINE Bot 自然語言       ❌ [          ]   0%
LINE Bot 推播           ❌ [          ]   0%
LINE Bot 外協回報       ❌ [          ]   0%
Mobile App 骨架         🟢 [████████  ]  80%   ✅ 5 tab + Login + 共用 store/api
Mobile Dashboard        🟢 [█████████ ]  90%   ✅ AI 摘要 + 統計卡 + 低庫存
Mobile 庫存查詢         🟢 [█████████ ]  90%   ✅ 搜尋列表
Mobile QR 掃碼          🟢 [██████    ]  60%   ✅ 掃描 UI，待接報工/盤點 API
Mobile AI 助手          🟢 [█████████ ]  90%   ✅ 對話介面 + 建議
Mobile 報工/盤點        ❌ [          ]   0%   Phase 2
Push Notification       ❌ [          ]   0%
語音輸入                ❌ [          ]   0%
```

### 4.3 後端核心進度

```
12 Domain 模型          🟢 [██████████] 100%
12 Domain API           🟢 [██████████] 100%
Multi-Agent (10 個)     🟢 [██████████] 100%
Tools (26 個)           🟢 [████████  ]  80%  待擴充寫入類
Constraint Rules (16)   🟢 [████████  ]  80%  待擴充寫入規則
SSE Event Stream        🟢 [██████████] 100%
Audit + Auth            🟢 [██████████] 100%
RBAC (8 表/109 權限/11 角色) 🟢 [██████████] 100%  ✅ 87 endpoints 全套保護完成
Row-Level Security      🟢 [████████  ]  80%  apply_row_filter 已有，list endpoints 套用待補
Tenant 多租戶基礎       🟢 [█████████ ]  95%  ✅ 19 表已加 tenant_id（mixin 共用）
前端權限管理頁          🟢 [█████████ ]  90%  ✅ 角色管理 + 我的權限 2 頁完成
```

### 4.4 部署 & DevOps（Phase 0 已備）

```
Docker Compose          🟢 [██████████] 100%
Healthcheck             🟢 [██████████] 100%
Alembic Async           🟢 [██████████] 100%
Seed Script             🟢 [██████████] 100%
CI/CD (GitHub Actions)  🟢 [████████  ]  80%   ✅ ci.yml + run_gates.sh
測試套件 (pytest)       🟢 [███████   ]  70%   ✅ 30 tests (smoke+persona+integration)
自證閘 (Self-Verify)    🟢 [██████████] 100%   ✅ 8 gates 全綠 121s
MESH 真實可用           🟢 [████████  ]  80%   ✅ register/list/aggregate + 5 整合測試
```

### 4.5 PDF 理論模組（延後）

```
MPS 簡化版              🟡 [███       ]  30%  Phase 3 處理
MRP 簡化版              🟡 [███▌      ]  35%  Phase 3 處理
APS / 演算法引擎        ❌ [          ]   0%   P5+ 待客戶反饋
三元排程（人/機/料）    🟡 [████      ]  40%  料完整、人機暫緩
RCCP/CRP                ❌ [          ]   0%   P5+ 待客戶反饋
OEE                     ❌ [          ]   0%   P5+ 待客戶反饋
```

---

## 5. 開發節奏與 SOP

### 5.1 每次工作會話的標準流程

```
1. 啟動 Claude 會話
   └→ Claude 自動讀取此 CLAUDE.md

2. 讀取 docs/WORKLOG.md
   └→ 知道上次做了什麼、下次該做什麼

3. 與使用者確認本次目標（明確對應某個 G-XXX）

4. 執行工作（遵守 SOP，先問「這對 MVP 有貢獻嗎？」）

5. 必做收尾動作 ★★★ 重要 ★★★
   ┌─→ 更新 docs/WORKLOG.md（追加新條目，倒序）
   ├─→ 更新 CLAUDE.md §4 模組進度看板的百分比
   ├─→ 若解鎖某 G-XXX，更新 docs/GAP_ANALYSIS.md
   └─→ 若有架構變化，更新 docs/KNOWLEDGE_MAP.md
```

### 5.2 黃金原則（每行程式碼前的「五問」）

1. **這對 MVP 8 大功能有貢獻嗎？**（沒有就不寫）
2. **這 50-100 人廠用得到嗎？**（用不到就降級）
3. **這能在手機上操作嗎？**（不能就改設計）
4. **這能用自然語言觸發嗎？**（不能就補 tool）
5. **這超過 3 步操作嗎？**（是就簡化）

### 5.3 開發 SOP（詳見 [docs/DEVELOPMENT_SOP.md](./docs/DEVELOPMENT_SOP.md)）

- 新增 domain / tool / constraint / 演算法 各有標準步驟
- 每次收尾必做 5 步（跑 smoke test → 進度看板 → WORKLOG → GAP → KNOWLEDGE_MAP）

---

## 6. Roadmap 速覽（詳見 [docs/ROADMAP.md](./docs/ROADMAP.md)）

| Phase | 名稱 | 主交付物 | 預估工時 | 狀態 |
|---|---|---|---|---|
| **P0** | ERP 基礎 + Multi-Agent | 12 domain + 10 agent + SSE | – | ✅ **已完成** |
| **P1** | 🔥 **LINE-Native + 行動化** | LINE Bot + Mobile App + 外協 QR | 3 週 | 🔄 待啟動 |
| **P2** | 📱 行動化深化 | 掃碼盤點/報工 + 推播 + LLM 寫入 | 2 週 | 待開始 |
| **P3** | 📋 規劃層精簡 | 簡化 MPS/MRP + 補貨建議 | 2 週 | 待開始 |
| **P4** | 🌐 MESH 多廠 | Factory Node + 結構化查詢 + 聚合 | 2 週 | 待開始 |
| — | **🎯 MVP 上線、開始接客戶** | – | – | ~ 2026-09 月 |
| P5+ | ⏸️ 進階功能 | APS / 演算法 / OEE / S&OP | TBD | **等客戶反饋** |

---

## 7. 已知風險與阻塞

| 編號 | 風險/阻塞 | 影響 | 應對 | 狀態 |
|---|---|---|---|---|
| R-01 | LLM_API_KEY 未提供 | LINE Bot 自然語言無法測試 | 等使用者交付，先做不需 API Key 的項目（model/UI/外協） | ⏳ 等待 |
| R-02 | LINE Channel 申請 | 需 LINE 官方帳號 | 提供申請 SOP，使用者自行申請（或先用 ngrok + 個人帳號測試） | ⏳ 待 Phase 1 |
| R-03 | Apple Developer / Google Play 帳號 | iOS/Android 上架需要 | Expo 開發階段不需要，正式上架前申請 | ⏳ 待 Phase 2 |
| R-04 | MinIO 儲存 | Phase 2 圖片上傳需要 | docker-compose 內建 MinIO | ✅ 已規劃 |
| R-05 | 外協廠 LINE 識別 | 不註冊如何識別？ | QR token 內含一次性綁定碼 | ✅ 已設計 |

---

## 8. 名詞解釋（Glossary）

| 縮寫 | 全名 | 中文 |
|---|---|---|
| ATP | Available-to-Promise | 可供承諾量 |
| BOM | Bill of Materials | 物料清單 |
| ICP | Ideal Customer Profile | 理想客戶輪廓 |
| JTBD | Jobs-to-be-Done | 待辦工作（產品設計法） |
| LINE Bot | LINE Messaging API | LINE 官方帳號自動回應 |
| MPS | Master Production Schedule | 主生產排程 |
| MRP | Material Requirements Planning | 物料需求規劃 |
| MVP | Minimum Viable Product | 最小可行產品 |
| OEE | Overall Equipment Effectiveness | 設備總效率 |
| persona | – | 人物誌（設計用戶代表） |
| Push Notification | – | 推播通知（FCM/APNs） |
| QR | Quick Response code | 二維條碼 |
| SSE | Server-Sent Events | 伺服器主動推送 |
| STT | Speech-to-Text | 語音轉文字 |
| VMI | Vendor Managed Inventory | 供應商管理庫存 |

---

## 9. 給未來 Claude 會話的指引（IMPORTANT）

> 任何後續會話開始時請依此順序執行：

1. **讀此 CLAUDE.md 全文**，掌握願景與當前進度。
2. **讀 [docs/CUSTOMER_POSITIONING.md](./docs/CUSTOMER_POSITIONING.md)**，掌握客戶定位（最重要！）。
3. **讀 [docs/WORKLOG.md](./docs/WORKLOG.md) 最新 5 條紀錄**，理解最近發生了什麼。
4. **若使用者請求新功能**：
   - 先查 [docs/GAP_ANALYSIS.md](./docs/GAP_ANALYSIS.md) 看是否有對應 G-XXX
   - 確認屬於當前 Phase（P1/P2/P3/P4）
   - 若屬 Phase 5+（暫緩）：先和使用者確認是否真的需要
5. **執行工作時遵守 SOP**：[docs/DEVELOPMENT_SOP.md](./docs/DEVELOPMENT_SOP.md)。
6. **完成後必定更新**：
   - 在 `docs/WORKLOG.md` 頂部追加新條目
   - 更新本檔 §4 模組進度看板
   - 若解鎖 G-XXX，更新 `docs/GAP_ANALYSIS.md`
7. **所有對使用者回覆**：使用繁體中文，技術名詞可保留英文。
8. **設計爭議時的仲裁**：
   - 易用 vs 完整 → **易用**
   - 手機 vs 桌機 → **手機**
   - 對話 vs 介面 → **對話**
   - 即時 vs 精準 → **即時**
   - 客戶要的 vs 我們覺得酷的 → **客戶要的**

---

**最後更新**：2026-05-15（會話 #17：2hr 並行衝刺 / Phase 1 Day 1 框架 30% / AI demo / Chat UX / 技術債）
**維護者**：使用者 + Claude
**版本**：2.9
