# LLM-ERP 專案總控檔（CLAUDE.md）

> **本檔是專案的「北極星」**：所有開發、規劃、決策與紀錄都以此為單一真相來源。
> 任何 Claude 會話啟動時請先讀此檔，掌握當前進度與下一步。
> **語言**：所有專案內溝通與文件一律使用**繁體中文**。

> ⚡ **v3.0 戰略軸轉（2026-05-15 會話 #18）**
> 砍掉 LINE Bot / Mobile App / 外協協同三條支線，**全力做桌機對話式 ERP**。
> 詳見 §10「v3.0 戰略軸轉紀錄」。

---

## 0. 速覽（一頁式摘要）

| 項目 | 內容 |
|---|---|
| **專案名稱** | LLM-ERP |
| **目標客戶** | **50–100 人小型製造業**（明確 ICP） |
| **核心承諾** | 「給小型製造業的 **對話式 ERP**：30 萬一年，用講的就能下單、查庫存、改單、改交期、看報表」 |
| **差異化武器** | ① 自然語言操作（不用學系統）② 桌機 Chat 全 CRUD（不只查，會做）③ 即時庫存同步 + 主動推播 |
| **三大支柱** | ERP（管理）× AI 對話（智能）× IE 工業工程（適度引用，**不過度設計**） |
| **當前階段** | **Phase 0 完成** → 進入 Phase 1（**對話式 CRUD：查 / 增 / 改 / 刪 全用講的**） |
| **程式碼位置** | `D:\114-DOWN\LLM-ERP\program\opnetest\` |
| **客戶定位文件** | [docs/CUSTOMER_POSITIONING.md](./docs/CUSTOMER_POSITIONING.md)（**戰略軸心**） |
| **MVP 範圍** | [docs/MVP_DEFINITION.md](./docs/MVP_DEFINITION.md) |
| **分階藍圖** | [docs/ROADMAP.md](./docs/ROADMAP.md)（Phase 0-7，v3 桌機對話導向版） |
| **差距分析** | [docs/GAP_ANALYSIS.md](./docs/GAP_ANALYSIS.md)（v3 版） |
| **動態工作日誌** | [docs/WORKLOG.md](./docs/WORKLOG.md)（**每次工作後務必更新**） |
| **PDF ↔ 程式對映** | [docs/KNOWLEDGE_MAP.md](./docs/KNOWLEDGE_MAP.md) |
| **權限系統設計** | [docs/PERMISSION_MODEL.md](./docs/PERMISSION_MODEL.md)（**架構級基礎，2026-05-14 落地**） |
| **架構決策紀錄** | [docs/ARCHITECTURE_DECISIONS.md](./docs/ARCHITECTURE_DECISIONS.md)（含 ADR-013 v3.0 砍 mobile） |
| **資料生命週期** | [docs/DATA_LIFECYCLE.md](./docs/DATA_LIFECYCLE.md)（防 DB 膨脹） |
| **戰略地圖（學術+商業）** | [docs/STRATEGY_LANDSCAPE.md](./docs/STRATEGY_LANDSCAPE.md) |
| **系統架構拓樸圖** | [docs/ARCHITECTURE_DIAGRAM.md](./docs/ARCHITECTURE_DIAGRAM.md) ([SVG](./docs/architecture_diagram.svg)) |
| **系統流程關聯拓樸** | [中文 SYSTEM_TOPOLOGY_ZH](./docs/SYSTEM_TOPOLOGY_ZH.md) / [EN](./docs/SYSTEM_TOPOLOGY_EN.md) ([SVG](./docs/system_flow_topology.svg)) |
| **網路部署規劃** | [中文 NETWORK_DEPLOYMENT_ZH](./docs/NETWORK_DEPLOYMENT_ZH.md) / [EN](./docs/NETWORK_DEPLOYMENT_EN.md) |
| **代碼自查報告** | [docs/CODE_REVIEW_REPORT.md](./docs/CODE_REVIEW_REPORT.md) |
| **LLM 評比報告** | [中文 LLM_BENCHMARK_REPORT_ZH](./docs/LLM_BENCHMARK_REPORT_ZH.md) / [EN](./docs/LLM_BENCHMARK_REPORT_EN.md)（DeepSeek 10/10） |
| **產品說明書（給採購決策者）** | [中文 PRODUCT_OVERVIEW_ZH.md](./docs/PRODUCT_OVERVIEW_ZH.md) / [English EN](./docs/PRODUCT_OVERVIEW_EN.md) |
| **使用者操作手冊** | [中文 USER_MANUAL_ZH.md](./docs/USER_MANUAL_ZH.md) / [English EN](./docs/USER_MANUAL_EN.md)（**桌機 Chat + MESH**）|
| **🎯 對話式 ERP 北極星（必讀）** | [中文 CONVERSATIONAL_ERP_DESIGN_ZH](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md) / [English EN](./docs/CONVERSATIONAL_ERP_DESIGN_EN.md)（**6 層架構 + 7 設計原則 + 4 階段**）|
| **🎯 Phase 1 Day-1 to Day-5 Spec** | [中文 PHASE1_SPEC_ZH](./docs/CONVERSATIONAL_ERP_PHASE1_SPEC_ZH.md) / [English EN](./docs/CONVERSATIONAL_ERP_PHASE1_SPEC_EN.md) |
| **系統架構藍圖（網路架構師）** | [中文 ARCHITECTURE_BLUEPRINT_ZH](./docs/ARCHITECTURE_BLUEPRINT_ZH.md) / [English EN](./docs/ARCHITECTURE_BLUEPRINT_EN.md) |
| **Secrets 輪換 SOP** | [中文 SECRETS_ROTATION_SOP_ZH](./docs/SECRETS_ROTATION_SOP_ZH.md) / [English EN](./docs/SECRETS_ROTATION_SOP_EN.md) |
| **生產 Docker Compose** | [`docker-compose.prod.yml`](./docker-compose.prod.yml) |
| **AI 助手目錄** | [中文 AGENT_CATALOG_ZH](./docs/AGENT_CATALOG_ZH.md) / [English EN](./docs/AGENT_CATALOG_EN.md)（**10 agent + 26 tool**） |
| **台灣合規對照表** | [中文 COMPLIANCE_TW_ZH](./docs/COMPLIANCE_TW_ZH.md) / [English EN](./docs/COMPLIANCE_TW_EN.md) |
| **導入實施手冊（顧問）** | [中文 IMPLEMENTATION_PLAYBOOK_ZH](./docs/IMPLEMENTATION_PLAYBOOK_ZH.md) / [English EN](./docs/IMPLEMENTATION_PLAYBOOK_EN.md) |
| **支援運維手冊** | [中文 SUPPORT_RUNBOOK_ZH](./docs/SUPPORT_RUNBOOK_ZH.md) / [English EN](./docs/SUPPORT_RUNBOOK_EN.md) |
| **備份還原 SOP** | [中文 BACKUP_RESTORE_SOP_ZH](./docs/BACKUP_RESTORE_SOP_ZH.md) / [English EN](./docs/BACKUP_RESTORE_SOP_EN.md) |
| **安裝指南（給老闆）** | [中文 INSTALLATION_ZH.md](./docs/INSTALLATION_ZH.md) / [English EN](./docs/INSTALLATION_EN.md) |
| **一鍵安裝腳本** | `install.sh`（Mac/Linux）/ `install.bat`（Windows）/ `load_industry.sh` |
| **客戶手冊 PDF（31 份雙語）** | 跑 `build_pdfs.bat`（Win）或 `./build_pdfs.sh`（Mac/Linux）→ 輸出至 `docs/pdf/` |
| **PR 模板** | [`.github/PULL_REQUEST_TEMPLATE.md`](./.github/PULL_REQUEST_TEMPLATE.md)（**強制貼 run_gates 輸出**） |
| **🛡️ 自證閘（必跑）** | `bash scripts/run_gates.sh` — 7 道閘 ~290 秒，**綠燈才能說完成**。CI: [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) |
| **測試套件** | `backend/tests/` — **148 tests**（smoke + persona + integration 含 O2C/P2P/P2I + MESH + Tenant Isolation 4-layer + Tool Registry） |
| **AI 治理基礎** | [`app/agents/governance.py`](./backend/app/agents/governance.py)（cost tracker + prompt safety + human-in-loop） |
| **Analytics 6 KPI** | `/api/analytics/{dso,inventory-turn,gross-margin,oee,purchase-concentration,ai-cost,summary}` |
| **台灣稅務 7 endpoints** | `/api/tax/tw/{401,403,einvoice/issue,validate-tax-id,...}` |
| **快速入門 / 管理員 / API** | [QUICK_START](./docs/QUICK_START.md) / [ADMIN_GUIDE](./docs/ADMIN_GUIDE.md) / [API_REFERENCE](./docs/API_REFERENCE.md) |
| **開發 SOP** | [docs/DEVELOPMENT_SOP.md](./docs/DEVELOPMENT_SOP.md) |
| **知識體系** | `D:\114-DOWN\LLM-ERP\生產排程系統完整參考資料 (1).pdf`（14 章理論參考） |
| **阻塞中** | 無（DeepSeek API key 已交付並驗證 12/12 query 通過） |

---

## 1. 專案北極星（Project North Star）

### 1.1 願景（Vision）
> 讓 **50-100 人小型製造業**也能享有現代化 ERP 的紅利——透過 **桌機 Chat 自然語言對話**，把「ERP 導入」從半年顧問工程降為「2 週上線、2 小時上手」。
>
> 員工坐在電腦前打字（或語音），講出口的話自動變成查詢/新增/修改/刪除—— **AI 取代教育訓練**。

### 1.2 使命（Mission，兩大核心承諾）

1. **🗣️ 自然語言取代教育訓練**
   王董打字問「今天狀況」就拿到老闆儀表板；採購打字說「跟長江廠下 100 個 M6 螺絲」就出採購單（含 ConfirmCard 確認卡）。**不用學系統、不用受訓、不需 IT 顧問**。

2. **🔄 全 CRUD 對話化**
   不只「查」用講的，「**增 / 改 / 刪**」也用講的。
   - hard-write 操作出 **ConfirmCard 確認卡**，使用者點「確認」才執行
   - 缺欄位時 AI **反問**（slot-filling），不憑空生成
   - 90 秒內可 **Undo**（撤銷）
   - 同名/同義詞由 **glossary** + **disambiguation** 自動處理

### 1.3 我們做什麼 / 我們不做什麼

| 我們做 ✅ | 我們不做 ❌ |
|---|---|
| 桌機 Chat 全 CRUD | LINE Bot / 行動 App |
| 自然語言對話操作 | 複雜的多階審批 |
| ConfirmCard 高風險確認 | 無感執行 hard-write |
| Slot-filling 反問 | 假設 / 編造缺漏欄位 |
| 90 秒 Undo | 一去無回的操作 |
| 即時庫存同步 + Toast 通知 | Excel 風格的多工作表 |
| 簡化版 MPS/MRP | 完整版 APS 演算法 |
| MESH 多廠（VMI） | 集中式單一資料庫 |
| 30-50 萬/年定價 | 200 萬+授權費 |

### 1.4 北極星 KPI（v3.0 桌機對話導向）

| 維度 | KPI | 起始 | MVP 目標 |
|---|---|---|---|
| **採用率** | 50 人廠 DAU/總人數 | n/a | > 60% |
| **AI 對話比例** | 自然語言操作 / 總操作 | 22% | **> 70%** |
| **CRUD 對話完整度** | 4 種操作（查/增/改/刪）AI 可做 | 1/4 | **4/4** |
| **誤操作率** | hard-write 被 Undo 比例 | n/a | < 5% |
| **報表等待** | 老闆問→拿到答案 | 數小時 | < 10 秒 |
| **下單速度** | 採購一句話→送單 | 5-10 分鐘 | < 30 秒 |
| **導入時間** | 決定購買→上線 | 6-18 月 | < 2 週 |
| **教育訓練** | 每員工受訓時數 | 1-3 月 | < 2 小時 |
| **客單價** | 50 人廠年費 | n/a | 30-50 萬 |

---

## 2. 客戶定位摘要（詳見 [CUSTOMER_POSITIONING.md](./docs/CUSTOMER_POSITIONING.md)）

### 2.1 4 個 Persona（v3.0 全桌機）

| Persona | 角色 | 主要需求 | 主要裝置 |
|---|---|---|---|
| **王董** | 老闆 | 隨時看公司表現、用講的問就回 | 辦公室桌機 Chrome |
| **小陳** | 業務 | 客戶面前 3 秒答題、報價單 30 秒成型 | 筆電（外出帶 Chrome 連 VPN） |
| **林廠長** | 生產主管 | 看哪裡卡關、用講的釋放/調整工單 | 辦公室桌機 + 廠房大屏 |
| **阿玲** | 採購兼倉管 | 不要重 Key、用講的下單 + USB 條碼槍盤點 | 桌機 + USB 條碼槍 |

> ⚠️ v2 的「老吳（外協廠 / LINE）」persona **於 v3.0 移除**。外協協同延後到「等客戶反饋」。

### 2.2 核心痛點 vs 解法

| 痛點 | 我們的解法 |
|---|---|
| 太貴（SAP 200 萬+） | 開源 + 30 萬/年 + Docker 一鍵 |
| 太難用 | 自然語言：用講的、不用學 |
| 介面點來點去 | **Chat 一句話直達**（含 hard-write 確認卡） |
| 庫存不同步 | 即時 DB + SSE 推播 |
| 老闆要看大數字 | Chat 一句話就拿到老闆儀表板 |
| 缺料才發現 | 自動警示 + Toast 即時通知 |
| 員工沒空受訓 | AI 取代教育訓練（< 2 小時上手） |

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
| L6 MES/SFC | 🟡 簡化（桌機報工 + USB 條碼槍） |

> **重要**：原 v1 規劃要求「七層全做才完整」，**v2/v3 改為「客戶痛點解決就 OK」**。

---

## 4. 模組進度看板（Module Dashboard）

> **每次完成工作後請更新此看板**——這是專案的儀表板。

### 4.1 MVP 6 大核心功能進度（v3.0 收斂）

```
1. AI 自然語言查詢          🟢 [████████  ]  80%   ✅ 12/12 query 實機 PASS
2. AI 自然語言寫入（CRUD）  🟡 [████      ]  42%   🔄 Phase 1 重點（11/26 tools 入 registry）
3. 即時庫存同步             🟢 [██████████] 100%   ✅ Phase 0 已備
4. AI 主動推播（Toast/Email）🟡 [█████     ]  50%   EventBus 有，缺 Toast/Email 整合
5. 基礎訂單到出貨閉環       🟢 [█████████ ]  95%   ✅ O2C/P2P/P2I 全測過
6. USB 條碼槍盤點/報工      ❌ [          ]   0%   Phase 2
```

**MVP 整體進度**：**~62%**（Phase 1-3 完成後達 100%）

### 4.2 桌機對話 ERP 進度（v3.0 新看板，取代舊「行動化 & LINE」）

```
Tool registry framework  🟢 [████████  ]  80%  ✅ @register_tool + RiskTier + Slot
Tool 入 registry         🟡 [████      ]  42%  ✅ 11/26（inventory ×3 + sales ×1 + purchase ×3 + production ×4）
ConfirmCard schema       ❌ [          ]   0%  Phase 1 Day 2
ConfirmCard 前端         ❌ [          ]   0%  Phase 1 Day 2
Slot-filling 反問        ❌ [          ]   0%  Phase 1 Day 4
第一個 hard-write tool   ❌ [          ]   0%  Phase 1 Day 3（create_purchase_order_with_confirm）
Glossary（同義詞表）     ❌ [          ]   0%  Phase 2
Disambiguation（消歧）   ❌ [          ]   0%  Phase 2
Workflow guide           ❌ [          ]   0%  Phase 2
Undo（90s 撤銷）         ❌ [          ]   0%  Phase 2
Chat UX（Markdown / 歷史）🟢 [█████████ ]  90%  ✅ 會話 #17 升級
桌面 Toast 通知          ❌ [          ]   0%  Phase 3
Email 摘要               ❌ [          ]   0%  Phase 3
USB 條碼槍輸入           ❌ [          ]   0%  Phase 3
語音輸入（Whisper）      ❌ [          ]   0%  Phase 4
```

### 4.3 後端核心進度

```
12 Domain 模型          🟢 [██████████] 100%
12 Domain API           🟢 [██████████] 100%
Multi-Agent (10 個)     🟢 [██████████] 100%
Tools (26 個)           🟢 [████████  ]  80%  待擴充寫入類（11/26 已入新 registry）
Constraint Rules (16)   🟢 [████████  ]  80%  待擴充寫入規則
SSE Event Stream        🟢 [██████████] 100%
Audit + Auth            🟢 [██████████] 100%
RBAC                    🟢 [██████████] 100%  ✅ 87 endpoints 全套保護完成
Row-Level Security      🟢 [████████  ]  80%
Tenant 多租戶基礎       🟢 [█████████ ]  95%  ✅ 19 表已加 tenant_id（with_loader_criteria 自動過濾）
前端權限管理頁          🟢 [█████████ ]  90%  ✅ 角色管理 + 我的權限 2 頁完成
```

### 4.4 部署 & DevOps

```
Docker Compose          🟢 [██████████] 100%
Healthcheck             🟢 [██████████] 100%
Alembic Async           🟢 [██████████] 100%
Seed Script             🟢 [██████████] 100%
CI/CD (GitHub Actions)  🟢 [████████  ]  80%   ✅ ci.yml + run_gates.sh
測試套件 (pytest)       🟢 [████████  ]  80%   ✅ 148 tests
自證閘 (Self-Verify)    🟢 [██████████] 100%   ✅ 7 gates 全綠
MESH 真實可用           🟢 [████████  ]  80%
```

### 4.5 PDF 理論模組（延後）

```
MPS 簡化版              🟡 [███       ]  30%  Phase 3 處理
MRP 簡化版              🟡 [███▌      ]  35%  Phase 3 處理
APS / 演算法引擎        ❌ [          ]   0%   P5+ 待客戶反饋
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

4. 執行工作（遵守 SOP，先問「這對 MVP 6 大功能有貢獻嗎？」）

5. 必做收尾動作 ★★★ 重要 ★★★
   ┌─→ 更新 docs/WORKLOG.md（追加新條目，倒序）
   ├─→ 更新 CLAUDE.md §4 模組進度看板的百分比
   ├─→ 若解鎖某 G-XXX，更新 docs/GAP_ANALYSIS.md
   └─→ 若有架構變化，更新 docs/KNOWLEDGE_MAP.md
```

### 5.2 黃金原則（每行程式碼前的「五問」v3.0）

1. **這對 MVP 6 大功能有貢獻嗎？**（沒有就不寫）
2. **這 50-100 人廠用得到嗎？**（用不到就降級）
3. **這能用一句話對 AI 講出來嗎？**（不能就補 tool / slot 描述）
4. **這是 hard-write 嗎？有 ConfirmCard 嗎？**（沒有就加）
5. **這超過 3 步操作嗎？**（是就簡化 / 改成單一句話） |

### 5.3 開發 SOP（詳見 [docs/DEVELOPMENT_SOP.md](./docs/DEVELOPMENT_SOP.md)）

- 新增 domain / tool / constraint / 演算法 各有標準步驟
- 新增 tool 一律走 `@register_tool` decorator（含 RiskTier 與 required_permission）
- 每次收尾必做 5 步（跑 smoke test → 進度看板 → WORKLOG → GAP → KNOWLEDGE_MAP）

---

## 6. Roadmap 速覽（v3.0，詳見 [docs/ROADMAP.md](./docs/ROADMAP.md)）

| Phase | 名稱 | 主交付物 | 預估工時 | 狀態 |
|---|---|---|---|---|
| **P0** | ERP 基礎 + Multi-Agent | 12 domain + 10 agent + SSE | – | ✅ **已完成** |
| **P1** | 🔥 **對話式 CRUD** | 26/26 tools 入 registry + ConfirmCard + slot-filling + 3 hard-write tool | 2 週 | 🔄 進行中（42%） |
| **P2** | 💬 **對話智能** | Glossary + Disambiguation + Workflow guide + Undo | 2 週 | 待開始 |
| **P3** | 🔔 **桌機體驗補完** | Toast 通知 + Email 摘要 + USB 條碼槍 + Chat 語音 | 1 週 | 待開始 |
| **P4** | 🌐 MESH 多廠 | Factory Node + 結構化查詢 + 聚合（既有 80%，補完） | 1 週 | 部分完成 |
| — | **🎯 MVP 上線、開始接客戶** | – | – | ~ 2026-08 月 |
| P5+ | ⏸️ 進階功能 | APS / 演算法 / OEE / S&OP / 外協 Web 入口（如客戶要） | TBD | **等客戶反饋** |

---

## 7. 已知風險與阻塞（v3.0）

| 編號 | 風險/阻塞 | 影響 | 應對 | 狀態 |
|---|---|---|---|---|
| R-01 | LLM 成本失控 | DeepSeek/Claude 一個月燒太多 | governance.py 有 cost tracker，> 閾值自動 fallback 廉價模型 | ✅ 已落地 |
| R-02 | hard-write 誤操作 | AI 幻覺 + 客戶生氣 | ConfirmCard 強制人類點確認 + 90 秒 Undo | 🔄 Phase 1 Day 2-3 |
| R-03 | Slot-filling 反問迴圈 | AI 反問 5 次還對不到答 | 3 次內必 fallback 到「請改用表單頁面」 | 🔄 Phase 1 Day 4 |
| R-04 | 同義詞炸表 | 「鋼釘 = 螺絲 = M6-BOLT」要對齊 | Glossary 表 + LLM-pre-translation 兩段機制 | 🔄 Phase 2 |
| R-05 | MinIO 儲存 | 附件 / 對話 log 累積 | docker-compose 內建 MinIO + DATA_LIFECYCLE.md 30 天輪轉 | ✅ 已規劃 |

---

## 8. 名詞解釋（Glossary）

| 縮寫 | 全名 | 中文 |
|---|---|---|
| ATP | Available-to-Promise | 可供承諾量 |
| BOM | Bill of Materials | 物料清單 |
| ConfirmCard | – | 確認卡（hard-write 前的人類點確認） |
| CRUD | Create / Read / Update / Delete | 增/查/改/刪 |
| ICP | Ideal Customer Profile | 理想客戶輪廓 |
| JTBD | Jobs-to-be-Done | 待辦工作（產品設計法） |
| MPS | Master Production Schedule | 主生產排程 |
| MRP | Material Requirements Planning | 物料需求規劃 |
| MVP | Minimum Viable Product | 最小可行產品 |
| OEE | Overall Equipment Effectiveness | 設備總效率 |
| persona | – | 人物誌（設計用戶代表） |
| RiskTier | – | 工具風險級（read / soft-write / hard-write） |
| Slot-filling | – | 槽位填充：AI 反問缺欄位 |
| SSE | Server-Sent Events | 伺服器主動推送 |
| STT | Speech-to-Text | 語音轉文字（Whisper） |
| VMI | Vendor Managed Inventory | 供應商管理庫存 |

---

## 9. 給未來 Claude 會話的指引（IMPORTANT）

> 任何後續會話開始時請依此順序執行：

1. **讀此 CLAUDE.md 全文**，掌握願景與當前進度。
2. **讀 §10「v3.0 戰略軸轉紀錄」**，理解為什麼砍 mobile。
3. **讀 [docs/WORKLOG.md](./docs/WORKLOG.md) 最新 5 條紀錄**，理解最近發生了什麼。
4. **若使用者請求新功能**：
   - 先查 [docs/GAP_ANALYSIS.md](./docs/GAP_ANALYSIS.md) 看是否有對應 G-XXX
   - 確認屬於當前 Phase（P1/P2/P3/P4）
   - 若屬 Phase 5+（暫緩）：先和使用者確認是否真的需要
   - **若涉及 mobile / LINE / 外協**：先說「v3.0 已砍此功能，要做請改回 v2 規劃」
5. **執行工作時遵守 SOP**：[docs/DEVELOPMENT_SOP.md](./docs/DEVELOPMENT_SOP.md)。
6. **完成後必定更新**：
   - 在 `docs/WORKLOG.md` 頂部追加新條目
   - 更新本檔 §4 模組進度看板
7. **所有對使用者回覆**：使用繁體中文，技術名詞可保留英文。
8. **設計爭議時的仲裁**（v3.0 更新）：
   - 易用 vs 完整 → **易用**
   - 介面 vs 對話 → **對話**
   - 即時 vs 精準 → **即時**
   - 客戶要的 vs 我們覺得酷的 → **客戶要的**
   - 加功能 vs 砍功能 → **砍**（v3.0 教訓：mediocre × 3 不如 excellent × 1）

---

## 10. v3.0 戰略軸轉紀錄（2026-05-15 會話 #18）

### 10.1 為什麼砍

v1/v2 兩條 DNA 同時並存，互相消耗能量：
- 舊 DNA：「LINE 原生 ERP」（手機 + LINE Bot + 外協 QR）
- 新 DNA：「對話式 ERP」（桌機 Chat + ConfirmCard + Slot-filling）

桌機 Chat 還在 1.5/8 完成度時，再分散精力做 mobile/LINE 等於三線都做不好。
**收斂到單一 DNA 後，工程能量集中、產品故事乾淨、客戶簡報不分心。**

### 10.2 砍了什麼

- `frontend-mobile/` 整個資料夾（Expo 5 tab，16 檔 git rm -r）
- LINE Bot Webhook 規劃（roadmap 全段）
- 外協廠 persona「老吳」、外協 QR token、外協 LINE 回報
- mobile-evidence 證據資料夾
- 「行動化 & LINE 整合進度」整段看板
- KPI：手機使用比例、LINE Bot 互動、外協回報率
- 風險 R-02 LINE Channel、R-03 Apple/Google、R-05 外協 LINE 識別
- 32 份 PDF → 31 份（Mobile App 使用指南 PDF 移除）
- CI 的 mobile tsc 步驟、PR 模板的 mobile 勾選

### 10.3 補了什麼

- Phase 1 對話式 CRUD（ConfirmCard / Slot-filling / Undo）
- Phase 2 對話智能（Glossary / Disambiguation / Workflow guide）
- Phase 3 桌機體驗（Toast / Email / USB 條碼槍 / Whisper）
- KPI 改成 CRUD 對話完整度 + 誤操作率 + 下單速度
- 5 問改成「能對 AI 一句話講出來嗎」「有 ConfirmCard 嗎」

### 10.4 時間表

- **修正到好（demo-ready）**：~7 個工作天（1.5 週）
- **完善（production-grade）**：~5-6 週

詳見 §6 Roadmap。

---

**最後更新**：2026-05-15（會話 #18：v3.0 戰略軸轉——砍 mobile + 重定對話式 ERP DNA）
**維護者**：使用者 + Claude
**版本**：3.0
