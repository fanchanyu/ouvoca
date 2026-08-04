# 📚 Ouvoca 文件總索引 / Documentation Index

> **版本基準**：發布版 **v3.70**（git tag）／程式版 **3.70.0**（`backend/app/config.py` 與 `frontend-desktop/package.json`）
> 兩個數字並存是刻意的，原因見 [`CHANGELOG_ZH.md`](./CHANGELOG_ZH.md)。
> **本索引校對日期**：2026-08-04
> **這裡有什麼**：`docs/` 底下 **99 份說明文件**（不含本索引）+ 74 份 PDF + 4 張架構圖 + 實測逐字稿

**不知道要看哪一份？** 直接跳到 👉 [我想做 X，要看哪一份？](#-我想做-x要看哪一份)

---

## 🚦 怎麼看懂狀態標記

每份文件旁邊都有一個燈號，告訴你「這份還能不能信」：

| 標記 | 意思 | 你該怎麼做 |
|:---:|---|---|
| 🟢 | 內容與現在的系統一致 | 放心照做 |
| 🟡 | 大方向對，但有些細節停在舊版本 | 可以看，遇到對不上就以畫面實際為準 |
| 🔴 | 有明確過時的內容（數字、章節缺漏） | 只當參考，重要事情請問我們或看系統實際畫面 |
| 📦 | 歷史存檔，只供回頭查 | 不用讀，除非你在追歷史 |

<details>
<summary>⚠️ <b>老實說：哪些文件現在對不上？（點開看）</b></summary>

我們在 2026-08-04 用程式碼實際核對過，以下差異是**已知的**，正在修：

| 文件 | 文件上寫的 | 程式實際 | 影響 |
|---|---|---|---|
| `API_REFERENCE.md` | 102 個 API 端點 | **242 個**（FastAPI 啟動後實際註冊的 `/api` 路由數） | 開發者會漏掉一半以上功能 |
| `AGENT_CATALOG_ZH/EN.md` | 26 個 AI 工具 | **201 個**（`app.agents.registry._REGISTRY` 實際註冊數） | 低估 AI 能做的事 |
| `PERMISSION_MODEL.md` | 約 95 個權限碼 | **231 個**（182 + 49 補充碼），角色 10 個正確 | 權限設定會找不到項目 |

**已於 2026-08-04 修正完畢的問題**（列出來讓你知道不必再擔心）：

| 原問題 | 現況 |
|---|---|
| `INSTALLATION_*` `QUICK_START` `ADMIN_GUIDE` `THIRD_PARTY_DOWNLOADS_*` 指令寫 `cd opnetest`（資料夾其實叫 `ouvoca`），會直接卡住安裝 | ✅ 全部改為 `ouvoca` |
| 35 份文件與 4 張架構圖仍用舊產品名 `LLM-ERP`（2026-05-22 已更名為 Ouvoca） | ✅ 全部更新為 Ouvoca；`docs/demos/` 的實測逐字稿與 `architecture/TOPOLOGY_AUDIT_v3.7.md` 刻意保留原文，因為那是有時間戳的歷史紀錄 |
| `USER_MANUAL_ZH/EN.md` 缺 v3.61 之後的財務報表、報稅、備份、批號追溯、MFA 等章節 | ✅ 中英文版都已補齊 |

**遇到文件跟畫面不一樣時，一律以系統實際畫面為準。**
API 的權威來源是後端啟動後的 <http://localhost:8000/docs>（自動產生，永遠正確）。

</details>

---

## 🎯 我想做 X，要看哪一份？

| 我想做的事 | 看這份 | 備註 |
|---|---|---|
| 📜 **我想知道最近改了什麼、修了什麼** | [`CHANGELOG_ZH.md`](./CHANGELOG_ZH.md) | 白話版更新紀錄，不講工程術語 |
| 🖨 **我要印成紙本 / 帶去沒網路的現場看** | [`DOCUMENT_INDEX.md`](./DOCUMENT_INDEX.md) | 74 份中英 PDF 逐份下載 |
| 🔧 **我要把系統裝起來** | [`INSTALLATION_ZH.md`](./INSTALLATION_ZH.md) | 雙擊安裝，不需 IT 背景 |
| 😰 **我裝了但失敗 / 打不開** | [`INSTALL_TROUBLESHOOTING_ZH.md`](./INSTALL_TROUBLESHOOTING_ZH.md) | 按「症狀」分類，前 3 條解決 90% 問題 |
| 👀 **我想先花 5 分鐘看看長怎樣** | [`QUICK_START.md`](./QUICK_START.md) | 中英文都在同一份 |
| 🤖 **我要讓 AI 真的會講話（申請 API Key）** | [`HOW_TO_GET_LLM_API_KEY_ZH.md`](./HOW_TO_GET_LLM_API_KEY_ZH.md) | 5-10 分鐘，圖文步驟 |
| 🔑 **我要改密碼 / 第一次登入** | [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md) §2 | 頭像 → 個人設定 → 修改密碼 |
| 👷 **我要教員工怎麼操作** | [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md) | 30 分鐘上手，含 4 個角色實戰 |
| 🏛️ **我要設公司規矩（誰能簽多少錢）** | [`HOUSE_RULES_GUIDE_ZH.md`](./HOUSE_RULES_GUIDE_ZH.md) | 家規功能，不用寫程式 |
| 👥 **我要加人員、分配權限** | [`ADMIN_GUIDE.md`](./ADMIN_GUIDE.md) §3 → [`PERMISSION_MODEL.md`](./PERMISSION_MODEL.md) | 10 個內建角色可直接套用 |
| 💾 **我要備份 / 資料要救回來** | [`BACKUP_RESTORE_SOP_ZH.md`](./BACKUP_RESTORE_SOP_ZH.md) | 3-2-1 備份原則 + 還原步驟 |
| 🧾 **我要開電子發票** | [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md) §3.9 → [`COMPLIANCE_TW_ZH.md`](./COMPLIANCE_TW_ZH.md) §2 | 開立 / 查詢 / 作廢，財政部 MIG 標準 |
| 💰 **我要報營業稅（401 / 405）** | [`COMPLIANCE_TW_ZH.md`](./COMPLIANCE_TW_ZH.md) §1 → [`TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md`](./TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md) | ⚠️ 系統產出僅供內部參考，正式申報請記帳士覆核 |
| 🔌 **我要接舊 ERP / 外部資料庫（鼎新、正航）** | [`EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md`](./EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md) | ⚠️ 動手前務必先讀 [`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./EXTERNAL_DB_LICENSING_NOTICE_ZH.md)（授權風險） |
| 🌐 **我要讓辦公室多台電腦一起連** | [`NETWORK_DEPLOYMENT_ZH.md`](./NETWORK_DEPLOYMENT_ZH.md) | 三種部署情境 + 給老闆看的資料安全圖 |
| 🚨 **系統掛了 / 突然變很慢** | [`SUPPORT_RUNBOOK_ZH.md`](./SUPPORT_RUNBOOK_ZH.md) | 照著做 90% 能自救 |
| 💵 **我想知道要付多少錢 / 能不能免費用** | [`COMMERCIAL_LICENSING_FAQ_ZH.md`](./COMMERCIAL_LICENSING_FAQ_ZH.md) | 20 人以下免費軌的完整問答 |
| 🎬 **我要 demo 給老闆 / 客戶看** | [`SALES_KILLER_MOMENTS_ZH.md`](./SALES_KILLER_MOMENTS_ZH.md) | 30 分鐘走完 9 個畫面 |
| 📅 **我要規劃導入時程** | [`IMPLEMENTATION_PLAYBOOK_ZH.md`](./IMPLEMENTATION_PLAYBOOK_ZH.md) | 2 週上線的 Day-by-Day SOP |
| 🧠 **我想知道 AI 會不會亂做事、花多少錢** | [`AGENT_CATALOG_ZH.md`](./AGENT_CATALOG_ZH.md) | 成本透明度 + 4 道安全防線 + AI 拒答清單 |
| 👨‍💻 **我要用程式接 API** | <http://localhost:8000/docs>（權威）→ [`API_REFERENCE.md`](./API_REFERENCE.md) | 文件版數字已過時，以 `/docs` 為準 |
| 🔐 **我要換密鑰 / 做資安稽核** | [`SECRETS_ROTATION_SOP_ZH.md`](./SECRETS_ROTATION_SOP_ZH.md) → [`../SECURITY.md`](../SECURITY.md) | 密鑰輪換週期與步驟 |
| 🐌 **資料越積越多，系統變慢** | [`DATA_LIFECYCLE.md`](./DATA_LIFECYCLE.md) | 資料分層、清理、索引策略 |
| 🚀 **我要部署到正式生產環境** | [`../DEPLOYMENT.md`](../DEPLOYMENT.md) | 從 compose up 到安全加固 |

---

## 👤 我是誰？30 秒找到你的路

### 🏭 工廠老闆 / 決策者

> 你想知道：這能幹嘛？要多少錢？合不合法？多久能上線？

| 順序 | 先看這份 | 為什麼 |
|:---:|---|---|
| 1️⃣ | [`PRODUCT_OVERVIEW_ZH.md`](./PRODUCT_OVERVIEW_ZH.md) | 12 大功能、競品比較、採購 FAQ 一次看完 |
| 2️⃣ | [`COMMERCIAL_LICENSING_FAQ_ZH.md`](./COMMERCIAL_LICENSING_FAQ_ZH.md) | 20 人以下能不能白用？商業授權怎麼算？ |
| 3️⃣ | [`COMPLIANCE_TW_ZH.md`](./COMPLIANCE_TW_ZH.md) | 台灣稅務、電子發票、個資法對照，給你的會計師看 |

**接下來**：導入規劃看 [`IMPLEMENTATION_PLAYBOOK_ZH.md`](./IMPLEMENTATION_PLAYBOOK_ZH.md)；
要說服股東 / 幹部看 [`SALES_KILLER_MOMENTS_ZH.md`](./SALES_KILLER_MOMENTS_ZH.md)；
法律風險整包看 [§07 法務與合規](#07-法務與合規-legal--compliance)。

---

### 👷 現場員工 / 文書會計

> 你想知道：這台東西怎麼用？我按錯了怎麼辦？

| 順序 | 先看這份 | 為什麼 |
|:---:|---|---|
| 1️⃣ | [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md) | 從登入到下單，30 分鐘上手；§8 有 4 個角色的實戰範例 |
| 2️⃣ | [`HOUSE_RULES_GUIDE_ZH.md`](./HOUSE_RULES_GUIDE_ZH.md) | 「超過 10 萬要老闆簽」這種規矩怎麼設 |
| 3️⃣ | [`AGENT_CATALOG_ZH.md`](./AGENT_CATALOG_ZH.md) | AI 能幫你做什麼、什麼時候它會停下來問你 |

**卡住了**：翻 [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md) **§11 疑難排解**。
**打錯單**：手冊 §7 有 90 秒 Undo（講一句「取消剛剛那張」就好）。

> 🟢 **已補齊**：使用手冊中英文版都已補上 v3.61 之後的新功能章節——
> **財務三大報表、營業稅 401/405 申報、備份與還原、批號序號追溯、RFQ 詢價比價、請購/收料/領料/退貨、雙重驗證（MFA）** 都有教學。

---

### 🧑‍💼 IT / 系統管理員

> 你想知道：怎麼裝、怎麼顧、怎麼備份、出事怎麼救。

| 順序 | 先看這份 | 為什麼 |
|:---:|---|---|
| 1️⃣ | [`INSTALLATION_ZH.md`](./INSTALLATION_ZH.md) | 三條安裝路線：一鍵 / 標準 / Docker |
| 2️⃣ | [`ADMIN_GUIDE.md`](./ADMIN_GUIDE.md) | 部署、帳號權限、多廠 MESH、監控、升級、安全檢查清單 |
| 3️⃣ | [`NETWORK_DEPLOYMENT_ZH.md`](./NETWORK_DEPLOYMENT_ZH.md) | Port 對照表、反向代理、VPN 設定 |

**出事時的三本急救手冊**：
[`SUPPORT_RUNBOOK_ZH.md`](./SUPPORT_RUNBOOK_ZH.md)（系統掛了）·
[`BACKUP_RESTORE_SOP_ZH.md`](./BACKUP_RESTORE_SOP_ZH.md)（資料要救）·
[`INSTALL_TROUBLESHOOTING_ZH.md`](./INSTALL_TROUBLESHOOTING_ZH.md)（裝不起來）

**定期要做的**：[`SECRETS_ROTATION_SOP_ZH.md`](./SECRETS_ROTATION_SOP_ZH.md)（換密鑰）·
[`DATA_LIFECYCLE.md`](./DATA_LIFECYCLE.md)（清資料）·
[`PERMISSION_MODEL.md`](./PERMISSION_MODEL.md)（權限盤點）

---

### 👨‍💻 開發者 / 貢獻者

> 你想知道：架構長怎樣、API 怎麼接、怎麼發 PR。

| 順序 | 先看這份 | 為什麼 |
|:---:|---|---|
| 1️⃣ | [`ARCHITECTURE_BLUEPRINT_ZH.md`](./ARCHITECTURE_BLUEPRINT_ZH.md) | 防禦縱深、HA、災備、可觀測性全攤開 |
| 2️⃣ | <http://localhost:8000/docs> | **API 的權威來源**（自動產生）；概覽再看 [`API_REFERENCE.md`](./API_REFERENCE.md) |
| 3️⃣ | [`DEVELOPMENT_SOP.md`](./DEVELOPMENT_SOP.md) | 「新增一個 domain / tool / API」的標準步驟 |

**想懂為什麼這樣設計**：[`ARCHITECTURE_DECISIONS.md`](./ARCHITECTURE_DECISIONS.md)（13 條 ADR，記錄取捨理由）
**想懂演算法**：[§05 設計規格](#05-設計規格-design-specs)（MRP、TOC、需求預測、Throughput Accounting 全套方法論）
**要發 PR**：[`../CONTRIBUTING.md`](../CONTRIBUTING.md) → [`../CLA.md`](../CLA.md) → [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md)

---

### 🌏 English Readers

Ouvoca is developed in Taiwan; Traditional Chinese is the primary language.
**Every document in the table below has a full English twin** (`*_EN.md`).

| Topic | English document |
|---|---|
| **Getting started** | [`QUICK_START.md`](./QUICK_START.md) (bilingual, single file) · [`INSTALLATION_EN.md`](./INSTALLATION_EN.md) · [`INSTALL_TROUBLESHOOTING_EN.md`](./INSTALL_TROUBLESHOOTING_EN.md) · [`HOW_TO_GET_LLM_API_KEY_EN.md`](./HOW_TO_GET_LLM_API_KEY_EN.md) · [`THIRD_PARTY_DOWNLOADS_EN.md`](./THIRD_PARTY_DOWNLOADS_EN.md) |
| **Daily use** | [`USER_MANUAL_EN.md`](./USER_MANUAL_EN.md) · [`HOUSE_RULES_GUIDE_EN.md`](./HOUSE_RULES_GUIDE_EN.md) · [`AGENT_CATALOG_EN.md`](./AGENT_CATALOG_EN.md) · [`SALES_KILLER_MOMENTS_EN.md`](./SALES_KILLER_MOMENTS_EN.md) |
| **Operations** | [`NETWORK_DEPLOYMENT_EN.md`](./NETWORK_DEPLOYMENT_EN.md) · [`BACKUP_RESTORE_SOP_EN.md`](./BACKUP_RESTORE_SOP_EN.md) · [`SECRETS_ROTATION_SOP_EN.md`](./SECRETS_ROTATION_SOP_EN.md) · [`SUPPORT_RUNBOOK_EN.md`](./SUPPORT_RUNBOOK_EN.md) |
| **Architecture** | [`ARCHITECTURE_BLUEPRINT_EN.md`](./ARCHITECTURE_BLUEPRINT_EN.md) · [`SYSTEM_TOPOLOGY_EN.md`](./SYSTEM_TOPOLOGY_EN.md) |
| **Design specs** | 9 documents, all `*_DESIGN_EN.md` / `*_SPEC_EN.md` — see [§05](#05-設計規格-design-specs) |
| **Product** | [`PRODUCT_OVERVIEW_EN.md`](./PRODUCT_OVERVIEW_EN.md) · [`IMPLEMENTATION_PLAYBOOK_EN.md`](./IMPLEMENTATION_PLAYBOOK_EN.md) |
| **Legal** | [`COMPLIANCE_TW_EN.md`](./COMPLIANCE_TW_EN.md) · [`EXTERNAL_DB_LICENSING_NOTICE_EN.md`](./EXTERNAL_DB_LICENSING_NOTICE_EN.md) · plus 10 more — see [§07](#07-法務與合規-legal--compliance) |
| **Reports** | [`LLM_BENCHMARK_REPORT_EN.md`](./LLM_BENCHMARK_REPORT_EN.md) |

#### ⚠️ Chinese only — no English version (21 documents)

These have **no English twin at all**. Use machine translation, or ask us.

> Note: `QUICK_START.md` carries no language suffix but **is bilingual inside one file** — it is not in this list.

| Document | What it is | Priority for translation |
|---|---|---|
| [`ADMIN_GUIDE.md`](./ADMIN_GUIDE.md) | System administration handbook | 🔴 High — customer-facing |
| [`API_REFERENCE.md`](./API_REFERENCE.md) | REST API overview and examples | 🔴 High — integrator-facing |
| [`PERMISSION_MODEL.md`](./PERMISSION_MODEL.md) | RBAC + row-level permission design | 🔴 High — customer-facing |
| [`DATA_LIFECYCLE.md`](./DATA_LIFECYCLE.md) | Data retention, tiering, cleanup strategy | 🔴 High — IT-facing |
| [`COMMERCIAL_LICENSING_FAQ_ZH.md`](./COMMERCIAL_LICENSING_FAQ_ZH.md) | Commercial licensing Q&A | 🔴 High — prospect-facing |
| [`CHANGELOG_ZH.md`](./CHANGELOG_ZH.md) | Plain-language release notes | 🔴 High — every user reads this |
| [`ARCHITECTURE_DECISIONS.md`](./ARCHITECTURE_DECISIONS.md) | 13 ADRs with rationale | 🟡 Medium — abstract would suffice |
| [`ARCHITECTURE_DIAGRAM.md`](./ARCHITECTURE_DIAGRAM.md) | Mermaid + SVG topology | 🟡 Medium |
| [`DEVELOPMENT_SOP.md`](./DEVELOPMENT_SOP.md) | Standard procedures for adding modules | 🟡 Medium |
| [`KNOWLEDGE_MAP.md`](./KNOWLEDGE_MAP.md) | Scheduling theory ↔ source code map | 🟡 Medium |
| [`ROADMAP.md`](./ROADMAP.md) | Phased roadmap | 🟡 Medium |
| `CUSTOMER_POSITIONING.md` · `STRATEGY_LANDSCAPE.md` · `MVP_DEFINITION.md` · `GAP_ANALYSIS.md` · `CODE_REVIEW_REPORT.md` · `V360_DELIVERY_REPORT_ZH.md` · 4 × `TURNKEY_*.md` | Internal planning / strategy / engineering specs | ⚪ Not planned — internal only |

---

## 📖 完整文件清單

> 這一區收錄 `docs/` 底下**全部 99 份文件**，每份只列一次。上面的讀者導覽只是捷徑。

### 01. 安裝與上手 Install & Onboarding

| 這份在講什麼 | 什麼時候看 | 中文 | English | 狀態 |
|---|---|---|---|:---:|
| **快速開始** — Docker 一鍵啟動、載示範資料、登入 | 想先花 5 分鐘試玩 | [`QUICK_START.md`](./QUICK_START.md) | 同一份（含 🇺🇸 English 章節） | 🟡 |
| **安裝指南** — 給老闆看的三步驟版，不需 IT 背景 | 正式要裝的時候 | [`INSTALLATION_ZH.md`](./INSTALLATION_ZH.md) | [`INSTALLATION_EN.md`](./INSTALLATION_EN.md) | 🟡 |
| **安裝排錯** — 按症狀分類，前 3 條解決 90% | 裝到一半卡住 | [`INSTALL_TROUBLESHOOTING_ZH.md`](./INSTALL_TROUBLESHOOTING_ZH.md) | [`INSTALL_TROUBLESHOOTING_EN.md`](./INSTALL_TROUBLESHOOTING_EN.md) | 🟢 |
| **申請 LLM API Key** — 讓 AI 真的會回話的最後一步 | 裝完但 AI 沒反應 | [`HOW_TO_GET_LLM_API_KEY_ZH.md`](./HOW_TO_GET_LLM_API_KEY_ZH.md) | [`HOW_TO_GET_LLM_API_KEY_EN.md`](./HOW_TO_GET_LLM_API_KEY_EN.md) | 🟢 |
| **第三方下載揭露** — 安裝腳本會從哪裡下載什麼、各自授權 | 資安要求要盤點來源 | [`THIRD_PARTY_DOWNLOADS_ZH.md`](./THIRD_PARTY_DOWNLOADS_ZH.md) | [`THIRD_PARTY_DOWNLOADS_EN.md`](./THIRD_PARTY_DOWNLOADS_EN.md) | 🟢 |

> ⚠️ `QUICK_START` / `INSTALLATION_*` / `THIRD_PARTY_DOWNLOADS_*` 內的指令仍寫舊資料夾名 `opnetest`，**請自行改成 `ouvoca`**。

### 02. 日常使用 Daily Use

| 這份在講什麼 | 什麼時候看 | 中文 | English | 狀態 |
|---|---|---|---|:---:|
| **使用者操作手冊** — 登入、介面導覽、對 AI 講話做 CRUD、確認卡、90 秒 Undo、4 角色實戰、疑難排解 | 教員工、自己卡住 | [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md) | [`USER_MANUAL_EN.md`](./USER_MANUAL_EN.md) | 🔴 |
| **家規完整指南** — 把公司規矩（簽核金額、必填欄位）教給 AI 管 | 要設審批門檻、防呆規則 | [`HOUSE_RULES_GUIDE_ZH.md`](./HOUSE_RULES_GUIDE_ZH.md) | [`HOUSE_RULES_GUIDE_EN.md`](./HOUSE_RULES_GUIDE_EN.md) | 🟡 |
| **AI 助手與工具目錄** — AI 能做什麼、不能做什麼、花多少錢、4 道安全防線、拒答清單 | 老闆問「AI 會不會亂搞」 | [`AGENT_CATALOG_ZH.md`](./AGENT_CATALOG_ZH.md) | [`AGENT_CATALOG_EN.md`](./AGENT_CATALOG_EN.md) | 🔴 |
| **業務 demo 一頁紙** — 30 分鐘走完 9 個 killer moment | 要 demo 給客戶或股東 | [`SALES_KILLER_MOMENTS_ZH.md`](./SALES_KILLER_MOMENTS_ZH.md) | [`SALES_KILLER_MOMENTS_EN.md`](./SALES_KILLER_MOMENTS_EN.md) | 🟡 |

### 03. IT 維運 SOP Operations

| 這份在講什麼 | 什麼時候看 | 中文 | English | 狀態 |
|---|---|---|---|:---:|
| **系統管理指南** — 部署、帳號權限、多廠 MESH、監控、升級、安全清單、診斷指令 | IT 接手系統的第一天 | [`ADMIN_GUIDE.md`](./ADMIN_GUIDE.md) | ❌ 無英文版 | 🟡 |
| **網路部署規劃** — Port 對照表、反向代理、VPN、資料安全圖 | 要多台電腦連、要開外網 | [`NETWORK_DEPLOYMENT_ZH.md`](./NETWORK_DEPLOYMENT_ZH.md) | [`NETWORK_DEPLOYMENT_EN.md`](./NETWORK_DEPLOYMENT_EN.md) | 🟡 |
| **備份還原 SOP** — 3-2-1 備份原則、還原演練、災難情境 | **每個客戶上線前必讀** | [`BACKUP_RESTORE_SOP_ZH.md`](./BACKUP_RESTORE_SOP_ZH.md) | [`BACKUP_RESTORE_SOP_EN.md`](./BACKUP_RESTORE_SOP_EN.md) | 🔴 |
| **Secrets 輪換 SOP** — 密鑰清單、輪換週期、外洩處理 | 定期資安作業、人員離職 | [`SECRETS_ROTATION_SOP_ZH.md`](./SECRETS_ROTATION_SOP_ZH.md) | [`SECRETS_ROTATION_SOP_EN.md`](./SECRETS_ROTATION_SOP_EN.md) | 🟡 |
| **支援運維手冊** — 系統起不來、API 變慢、LLM 連不上、DB 鎖死、被攻擊 | 出事的當下 | [`SUPPORT_RUNBOOK_ZH.md`](./SUPPORT_RUNBOOK_ZH.md) | [`SUPPORT_RUNBOOK_EN.md`](./SUPPORT_RUNBOOK_EN.md) | 🟡 |
| **資料生命週期** — 資料分類、冷熱分層、清理、索引、災難復原 | 用了兩年開始變慢 | [`DATA_LIFECYCLE.md`](./DATA_LIFECYCLE.md) | ❌ 無英文版 | 🟡 |
| **權限模型** — 五層權限、10 個內建角色、權限碼命名規範 | 要加人、要分權 | [`PERMISSION_MODEL.md`](./PERMISSION_MODEL.md) | ❌ 無英文版 | 🔴 |

> 🔴 `BACKUP_RESTORE_SOP_*` 寫於 v3.62 備份管理功能（建立／列出／還原／刪除／排程）上線之前，尚未涵蓋新的備份介面。

### 04. 架構與技術 Architecture

| 這份在講什麼 | 什麼時候看 | 中文 | English | 狀態 |
|---|---|---|---|:---:|
| **系統架構藍圖** — 從 1 個客戶長到 1000 個客戶、防禦縱深、HA、災備 | IT 主管 / 資安顧問評估 | [`ARCHITECTURE_BLUEPRINT_ZH.md`](./ARCHITECTURE_BLUEPRINT_ZH.md) | [`ARCHITECTURE_BLUEPRINT_EN.md`](./ARCHITECTURE_BLUEPRINT_EN.md) | 🟡 |
| **系統流程拓樸** — 六種視角，由淺入深看懂整個系統 | 想搞懂資料怎麼流 | [`SYSTEM_TOPOLOGY_ZH.md`](./SYSTEM_TOPOLOGY_ZH.md) | [`SYSTEM_TOPOLOGY_EN.md`](./SYSTEM_TOPOLOGY_EN.md) | 🟡 |
| **架構圖** — SVG 精美版 + Mermaid 技術版 | 要貼簡報、印 A3 | [`ARCHITECTURE_DIAGRAM.md`](./ARCHITECTURE_DIAGRAM.md) | ❌ 無英文版 | 🔴 |
| **架構決策紀錄（ADR）** — 13 條「為什麼這樣選」的紀錄 | 想改架構之前 | [`ARCHITECTURE_DECISIONS.md`](./ARCHITECTURE_DECISIONS.md) | ❌ 無英文版 | 🟡 |
| **API 參考** — 認證、庫存、採購、生產、銷售、AI、權限、MRP 端點與範例 | 要寫程式接系統 | [`API_REFERENCE.md`](./API_REFERENCE.md) | ❌ 無英文版 | 🔴 |
| **開發 SOP** — 新增 domain / model / API / tool 的標準步驟 | 要動手改 code | [`DEVELOPMENT_SOP.md`](./DEVELOPMENT_SOP.md) | ❌ 無英文版 | 🟢 |
| **知識地圖** — 生產排程理論 14 章 ↔ 程式模組對映 | 想知道理論落在哪支程式 | [`KNOWLEDGE_MAP.md`](./KNOWLEDGE_MAP.md) | ❌ 無英文版 | 🟡 |
| **拓樸稽核 v3.7** — 當時的 tool / event / domain 盤點 | 追歷史才需要 | [`architecture/TOPOLOGY_AUDIT_v3.7.md`](./architecture/TOPOLOGY_AUDIT_v3.7.md) | — | 📦 |

> 🔴 三份架構文件都自帶「圖裡還有 LINE Bot / Expo 等已下架節點」的免責說明，SVG 尚未重畫。文字描述以各檔開頭 banner 為準。

### 05. 設計規格 Design Specs

> 給**開發者與研究者**看的方法論文件，寫作採學術論文格式。**9 組全部中英齊全。**
> 一般使用者不需要讀這區。

| 主題 | 一句話 | 中文 | English |
|---|---|---|---|
| 對話式 ERP 架構 | 用 AI 取代教育訓練、自然語言全 CRUD 的北極星文件 | [`CONVERSATIONAL_ERP_DESIGN_ZH.md`](./CONVERSATIONAL_ERP_DESIGN_ZH.md) | [`_EN`](./CONVERSATIONAL_ERP_DESIGN_EN.md) |
| Phase 1 實作 Spec | Day 1-5 基建週的逐日實作規格 | [`CONVERSATIONAL_ERP_PHASE1_SPEC_ZH.md`](./CONVERSATIONAL_ERP_PHASE1_SPEC_ZH.md) | [`_EN`](./CONVERSATIONAL_ERP_PHASE1_SPEC_EN.md) |
| 對話式規劃顧問 | 把 IE/OR 演算法包成 LLM 可呼叫的工具 | [`CONVERSATIONAL_PLANNING_DESIGN_ZH.md`](./CONVERSATIONAL_PLANNING_DESIGN_ZH.md) | [`_EN`](./CONVERSATIONAL_PLANNING_DESIGN_EN.md) |
| MRP-II 演算法 | 多階時序化物料需求規劃引擎 | [`MRP_ALGORITHM_DESIGN_ZH.md`](./MRP_ALGORITHM_DESIGN_ZH.md) | [`_EN`](./MRP_ALGORITHM_DESIGN_EN.md) |
| 產能感知 MRP | 加上工作中心產能限制（Dixon-Silver 啟發法） | [`MRP_CAPACITY_AWARE_DESIGN_ZH.md`](./MRP_CAPACITY_AWARE_DESIGN_ZH.md) | [`_EN`](./MRP_CAPACITY_AWARE_DESIGN_EN.md) |
| 可解釋規劃 + TOC | 排程結果講得出理由 + 瓶頸分析 | [`PLANNING_EXPLAINABILITY_DESIGN_ZH.md`](./PLANNING_EXPLAINABILITY_DESIGN_ZH.md) | [`_EN`](./PLANNING_EXPLAINABILITY_DESIGN_EN.md) |
| 需求預測 | 從歷史銷售自動預測 + LLM 增強，取代人工填 MPS | [`DEMAND_FORECASTING_DESIGN_ZH.md`](./DEMAND_FORECASTING_DESIGN_ZH.md) | [`_EN`](./DEMAND_FORECASTING_DESIGN_EN.md) |
| Throughput Accounting | TA + DBR 排程 + 訂單接受決策 | [`THROUGHPUT_ACCOUNTING_DESIGN_ZH.md`](./THROUGHPUT_ACCOUNTING_DESIGN_ZH.md) | [`_EN`](./THROUGHPUT_ACCOUNTING_DESIGN_EN.md) |
| 外部資料庫串接 | 讀取鼎新 / 正航 / Excel 舊資料的設計 | [`EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md`](./EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md) | [`_EN`](./EXTERNAL_DB_INTEGRATION_DESIGN_EN.md) |

### 06. 產品與商務 Product & Strategy

| 這份在講什麼 | 什麼時候看 | 中文 | English | 狀態 |
|---|---|---|---|:---:|
| **產品說明書** — 12 大功能、差異化、技術規格、採購 FAQ、競品比較 | 評估要不要買 | [`PRODUCT_OVERVIEW_ZH.md`](./PRODUCT_OVERVIEW_ZH.md) | [`PRODUCT_OVERVIEW_EN.md`](./PRODUCT_OVERVIEW_EN.md) | 🟡 |
| **導入實施手冊** — 2 週上線 Day-by-Day SOP、教育訓練排程 | 決定導入後排時程 | [`IMPLEMENTATION_PLAYBOOK_ZH.md`](./IMPLEMENTATION_PLAYBOOK_ZH.md) | [`IMPLEMENTATION_PLAYBOOK_EN.md`](./IMPLEMENTATION_PLAYBOOK_EN.md) | 🟡 |
| **商業授權 FAQ** — 20 人以下免費軌、AGPL 細節、整合問題 | 搞不清楚要不要付錢 | [`COMMERCIAL_LICENSING_FAQ_ZH.md`](./COMMERCIAL_LICENSING_FAQ_ZH.md) | ❌ 無英文版 | 🟢 |
| **客戶定位** — 為什麼只做 50-100 人廠（內部戰略） | 內部 / 顧問 | [`CUSTOMER_POSITIONING.md`](./CUSTOMER_POSITIONING.md) | ❌ 無英文版 | 🟡 |
| **競品地景** — 學術與商業視角的市場分析（內部） | 內部 / 業務備課 | [`STRATEGY_LANDSCAPE.md`](./STRATEGY_LANDSCAPE.md) | ❌ 無英文版 | 🟡 |
| **MVP 範圍定義** — 做什麼、不做什麼的界線 | 內部 | [`MVP_DEFINITION.md`](./MVP_DEFINITION.md) | ❌ 無英文版 | 📦 |
| **分階藍圖 ROADMAP** — Phase 規劃 | 想知道之後會有什麼 | [`ROADMAP.md`](./ROADMAP.md) | ❌ 無英文版 | 🔴 |
| **差距分析** — 理論與實務的缺口盤點 | 內部 | [`GAP_ANALYSIS.md`](./GAP_ANALYSIS.md) | ❌ 無英文版 | 🔴 |

> 🔴 `ROADMAP.md` 與 `GAP_ANALYSIS.md` 標題都還寫「v3.0 對話式 ERP 版」，內容停在 2026-05-15，未涵蓋 v3.60 之後的財務閉環、表單工程、開機即用套件。

### 07. 法務與合規 Legal & Compliance

> ⚠️ **本區所有文件皆為「合規提醒」，不構成法律、稅務或會計意見。**
> 正式上線前，請務必由您的**記帳士 / 會計師 / 法律顧問**覆核。

| 這份在講什麼 | 什麼時候看 | 中文 | English | 狀態 |
|---|---|---|---|:---:|
| **台灣合規對照表** — 營業稅、電子發票、個資法、勞動法、產業特規、自行設定清單 | 給會計師 / 法務確認 | [`COMPLIANCE_TW_ZH.md`](./COMPLIANCE_TW_ZH.md) | [`COMPLIANCE_TW_EN.md`](./COMPLIANCE_TW_EN.md) | 🟡 |
| **進銷存法律聲明**（v3.32 / v3.33） | 上線進銷存模組前 | [`INVENTORY_SALES_LEGAL_NOTICE_ZH.md`](./INVENTORY_SALES_LEGAL_NOTICE_ZH.md) | [`_EN`](./INVENTORY_SALES_LEGAL_NOTICE_EN.md) | 🟡 |
| **稅務 / 會計 / 審批法律聲明**（v3.34） | 開始用會計與審批功能前 | [`TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md`](./TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md) | [`_EN`](./TAX_ACCOUNTING_LEGAL_NOTICE_EN.md) | 🔴 |
| **列印 / 匯出法律聲明**（v3.36） | 要把單據 PDF 給外部 | [`PRINT_EXPORT_LEGAL_NOTICE_ZH.md`](./PRINT_EXPORT_LEGAL_NOTICE_ZH.md) | [`_EN`](./PRINT_EXPORT_LEGAL_NOTICE_EN.md) | 🟡 |
| **安裝精靈法律聲明**（v3.37）— 預設密碼、自動下載、主動推播 | 用一鍵安裝腳本前 | [`SETUP_WIZARD_LEGAL_NOTICE_ZH.md`](./SETUP_WIZARD_LEGAL_NOTICE_ZH.md) | [`_EN`](./SETUP_WIZARD_LEGAL_NOTICE_EN.md) | 🟡 |
| **第三方 ERP 授權提醒** — 讀取鼎新 / 正航等舊系統資料的授權風險 | **接外部資料庫前必讀** | [`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./EXTERNAL_DB_LICENSING_NOTICE_ZH.md) | [`_EN`](./EXTERNAL_DB_LICENSING_NOTICE_EN.md) | 🟢 |
| **專案重命名公告** — erpilot → Ouvoca（2026-05-22） | 看到舊名稱時 | [`RENAME_NOTICE_ZH.md`](./RENAME_NOTICE_ZH.md) | [`_EN`](./RENAME_NOTICE_EN.md) | 🟢 |

<details>
<summary>📦 <b>卡關修補法律聲明 v3.38 → v3.42（5 組 10 份，累積適用）</b></summary>

這 5 份格式相同、逐版累積，讀者要理解完整範圍必須依序讀完。**建議未來合併成單一 changelog。**

| 版本 | 該輪涵蓋哪些功能 | 中文 | English |
|---|---|---|---|
| v3.38（第二輪） | 確認卡 TTL 延長、AI 成本入口、備份還原、Undo、客戶消歧 | [`POLISH_LEGAL_NOTICE_ZH.md`](./POLISH_LEGAL_NOTICE_ZH.md) | [`_EN`](./POLISH_LEGAL_NOTICE_EN.md) |
| v3.39（第三輪） | LOGO 上傳、刪除三件套、批次列印、分頁、開機自啟 | [`POLISH_V339_LEGAL_NOTICE_ZH.md`](./POLISH_V339_LEGAL_NOTICE_ZH.md) | [`_EN`](./POLISH_V339_LEGAL_NOTICE_EN.md) |
| v3.40（第四輪） | 相對日期解析、應收帳齡、資料凍結、稽核跨人搜尋、刪除還原 | [`POLISH_V340_LEGAL_NOTICE_ZH.md`](./POLISH_V340_LEGAL_NOTICE_ZH.md) | [`_EN`](./POLISH_V340_LEGAL_NOTICE_EN.md) |
| v3.41（第五輪） | 客戶毛利率、訂單跟單、寄 PDF email、資料健康檢查 | [`POLISH_V341_LEGAL_NOTICE_ZH.md`](./POLISH_V341_LEGAL_NOTICE_ZH.md) | [`_EN`](./POLISH_V341_LEGAL_NOTICE_EN.md) |
| v3.42（第六輪） | 使用者帳號管理、全域搜尋、附件、每人限額、工作天、時區 | [`POLISH_V342_LEGAL_NOTICE_ZH.md`](./POLISH_V342_LEGAL_NOTICE_ZH.md) | [`_EN`](./POLISH_V342_LEGAL_NOTICE_EN.md) |

</details>

> 🚨 **合規缺口（已知，優先補件中）**
> 法律聲明鏈目前**停在 v3.42**。v3.61 之後上線的**三大財務報表、401/405 營業稅申報、3-Way Match 發票勾稽、固定資產與折舊、銷貨成本結轉**，以及 v3.62 的**備份還原**、v3.64 的 **MFA 雙重驗證與病毒掃描**，目前**尚無對應的法律聲明文件**。
> 在補件完成前，請把系統產出的**所有稅務與財務報表視為內部管理參考**，正式申報一律由記帳士 / 會計師覆核。

**授權條款本體**（在 repo 根目錄）：
[`../LICENSE`](../LICENSE)（AGPL-3.0）·
[`../LICENSE-SMALL-BUSINESS.md`](../LICENSE-SMALL-BUSINESS.md)（20 人以下免費軌）·
[`../LICENSE-COMMERCIAL.md`](../LICENSE-COMMERCIAL.md)（商業軌）

### 08. 報告與實測紀錄 Reports & Evidence

| 這份在講什麼 | 什麼時候看 | 中文 | English | 狀態 |
|---|---|---|---|:---:|
| **版本更新紀錄（白話版）** — 每個版本「你會看到什麼差別」，含版本號怎麼看 | 升級後想知道多了什麼 | [`CHANGELOG_ZH.md`](./CHANGELOG_ZH.md) | ❌ 無英文版 | 🟢 |
| **LLM 評比報告** — 主流 LLM 在 ERP 場景的實測比較 | 選要用哪家 AI | [`LLM_BENCHMARK_REPORT_ZH.md`](./LLM_BENCHMARK_REPORT_ZH.md) | [`LLM_BENCHMARK_REPORT_EN.md`](./LLM_BENCHMARK_REPORT_EN.md) | 🟡 |
| **v3.60 交付報告** — P0 資安缺陷修復、外部 DB、系統組態的落地紀錄 | 想知道 v3.60 做了什麼 | [`V360_DELIVERY_REPORT_ZH.md`](./V360_DELIVERY_REPORT_ZH.md) | ❌ 無英文版 | 🟢 |
| **程式碼自查報告** — 2026-05-14 的跨檔案靜態審查 | 追歷史 | [`CODE_REVIEW_REPORT.md`](./CODE_REVIEW_REPORT.md) | ❌ 無英文版 | 📦 |
| **實測逐字稿** — AI 對話 demo、CRUD 全流程、DeepSeek E2E 九大場景 | 想看真實對話長什麼樣 | [`demos/`](./demos/) 共 4 份 | — | 📦 |

> 📦 `CODE_REVIEW_REPORT.md` 的範圍仍寫舊專案名 `opnetest/`，統計數字與 v3.65 之後的健檢修復無法對應，僅作歷史快照。
> 📦 `demos/deepseek_e2e_latest.md` 與 `demos/deepseek_e2e_20260515_1939.md` 內容完全相同（同一份存兩次）。

### 09. 內部工程文件 Internal（客戶不需閱讀）

> 這 4 份是**給工程師的施工規格**，含工時估算與實作細節，不適合直接給客戶。全部僅有中文。

| 文件 | 內容 |
|---|---|
| [`TURNKEY_PHASE0_SEED_SPEC.md`](./TURNKEY_PHASE0_SEED_SPEC.md) | 「開機即用」預置內容總規格（科目表、角色、家規、表單、行業種子） |
| [`TURNKEY_M1_PLAN.md`](./TURNKEY_M1_PLAN.md) | M1 里程碑細部規劃：科目表 + 角色矩陣 + 系統組態 |
| [`TURNKEY_M1-1_ACCOUNTS_DETAIL.md`](./TURNKEY_M1-1_ACCOUNTS_DETAIL.md) | 會計科目表逐科目設計 |
| [`TURNKEY_M1-1_3_SEEDACCOUNTS_DETAIL.md`](./TURNKEY_M1-1_3_SEEDACCOUNTS_DETAIL.md) | 科目 seed 腳本實作細節 |

> `docs/mobile-evidence/` 是 v3.0 之前的手機驗收截圖資料夾，指向已移除的 `frontend-mobile/`，**目前是空殼，可忽略**。

---

## 🗂 repo 根目錄的其他文件

| 文件 | 這份在講什麼 |
|---|---|
| [`../README.md`](../README.md) | 專案首頁：30 秒看懂 Ouvoca、5 分鐘安裝、三軌授權 |
| [`../DEPLOYMENT.md`](../DEPLOYMENT.md) | 正式生產環境部署與安全加固（英文） |
| [`../SECURITY.md`](../SECURITY.md) | 資安政策與漏洞回報管道 |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 想貢獻程式碼？從這裡開始 |
| [`../CLA.md`](../CLA.md) | 貢獻者授權協議（中英雙語） |
| [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) | 社群行為準則 |
| [`../AGENTS.md`](../AGENTS.md) | 常用開發指令速查表 |

---

## 📄 PDF 成品與圖檔

> 🖨 **要印出來、或帶去沒網路的現場看？** PDF 逐份下載連結在 👉 [**`DOCUMENT_INDEX.md`**](./DOCUMENT_INDEX.md)

- **PDF**：[`pdf/`](./pdf/) 共 **74 份**（37 份中文 + 36 份英文 + 1 份雙語合刊，編號 00–38），
  由 [`../scripts/build-pdfs/build.mjs`](../scripts/build-pdfs/) 產生。
  重新產生：在 repo 根目錄執行 `./build_pdfs.sh`（Linux/macOS）或 `build_pdfs.bat`（Windows）。
- **架構圖**：`architecture_diagram.svg`（分層圖）· `system_flow_topology.svg` / `_zh.svg` / `_en.svg`（流程拓樸，可印 A3）

> ⚠️ 現有 PDF 都是 2026-05 那批產出，**內容停在 v3.42 之前**，且不含
> `INSTALL_TROUBLESHOOTING_*`、`THIRD_PARTY_DOWNLOADS_*`、`ADMIN_GUIDE`、`PERMISSION_MODEL`、`DATA_LIFECYCLE` 等 23 份文件。
> **PDF 與 .md 不一致時，一律以 .md 為準。**

---

## 🧰 給文件維護者

<details>
<summary>命名規範、每次改版必更清單、已知斷鏈（點開）</summary>

### 命名規範

- **客戶會看的文件**：一律成對 `NAME_ZH.md` + `NAME_EN.md`
- **純內部文件**：不加語言後綴，並應收進 `docs/internal/`（尚未建立）
- 目前有 **21 份文件沒有英文版**，清單見 [English readers 區](#-english-readers)

### 每次 release 必須同步更新

| 文件 | 為什麼 |
|---|---|
| `API_REFERENCE.md` | 端點數量與清單會變（建議改為由 OpenAPI 自動產生，別再手寫數字） |
| `AGENT_CATALOG_ZH/EN.md` | AI 工具數量會變（建議由 tool registry dump 產生） |
| `PERMISSION_MODEL.md` | 權限碼會變（`backend/scripts/seed_permissions.py` 是唯一真相） |
| `USER_MANUAL_ZH/EN.md` | 有新畫面就要有新章節 |
| `ROADMAP.md` | 完成的項目要打勾 |
| **本索引的狀態欄** | 每次 release 至少把燈號調對 |

**只要動到金流、稅務、個資、資安**，就必須新增或更新對應的法律聲明。

### 已知斷鏈（尚未修復）

| 位置 | 問題 | 應改為 |
|---|---|---|
| `ADMIN_GUIDE.md` · `NETWORK_DEPLOYMENT_ZH/EN.md` · `QUICK_START.md` | 連到 `./DEPLOYMENT.md`（檔案其實在 repo 根目錄） | `../DEPLOYMENT.md` |
| `API_REFERENCE.md` · 根 `README.md` | 連到 `docs/WORKLOG.md`，但該檔已列入 `.gitignore`（GitHub 上不存在，讀者一點就 404） | 改指 [`CHANGELOG_ZH.md`](./CHANGELOG_ZH.md) |
| `CONVERSATIONAL_PLANNING_DESIGN_ZH.md` | 連到 `./CLAUDE.md`（repo 內不存在） | 移除該連結 |
| `QUICK_START.md` | 錨點寫 `#9-疑難排解`，但疑難排解其實是 §11 | `#11-疑難排解` / `#11-troubleshooting` |
| `mobile-evidence/README.md` | 指向已移除的 `frontend-mobile/` | 刪除該資料夾 |

建議在 `.github/workflows/` 加一支 Markdown 連結檢查，避免重複發生。

</details>

---

<div align="center">

**找不到你要的？** 開一個 [GitHub issue](https://github.com/fanchanyu/ouvoca/issues) 告訴我們。

*本索引所有數字均逐項核對程式碼與檔案後寫成 · 校對日期 2026-08-04 · 發布版 v3.70／程式版 3.70.0*

</div>
