**繁體中文** | [English](./README.en.md)

# Ouvoca — 用講的就能操作的工廠 ERP

> 打一句話：**「跟長江廠下 100 個 M6 螺絲，交期下週五」**
> → AI 幫你把採購單開好，跳出確認卡讓你按「確認」才真的送出。
>
> 給 **50–100 人的台灣中小製造廠**。不用學系統、不用教育訓練、雙擊安裝。
> **同時在線 20 人以內，整套完全免費。**

[![CI](https://github.com/fanchanyu/ouvoca/actions/workflows/ci.yml/badge.svg)](https://github.com/fanchanyu/ouvoca/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-880%20passed-brightgreen)](./docs/CHANGELOG_ZH.md)
[![Version](https://img.shields.io/badge/version-3.70-blueviolet)](./docs/CHANGELOG_ZH.md)
[![API](https://img.shields.io/badge/API-242%20endpoints-informational)](./docs/ARCHITECTURE_DIAGRAM.md)
[![Tables](https://img.shields.io/badge/tables-107-informational)](./docs/ARCHITECTURE_DIAGRAM.md)
[![AI tools](https://img.shields.io/badge/AI%20tools-201-orange)](./docs/FEATURES_ZH.md)
[![License](https://img.shields.io/badge/license-AGPL--3.0%20%2B%20SBL%20%2B%20Commercial-blue)](./LICENSE)

| 你是誰 | 你要的 | 點這裡 |
|---|---|---|
| 👔 **老闆 / 採購 / 業務 / 倉管** | 我要裝起來用，不會寫程式 | 👉 [**5 分鐘安裝**](#-5-分鐘安裝電腦小白模式) |
| 🧐 **還在評估要不要用** | 這東西能幹嘛、要多少錢 | 👉 [**功能總覽**](#-功能總覽) · [**三軌授權**](#️-三軌授權20-人以內免費) |
| 🆘 **裝失敗了** | 錯誤訊息怎麼解 | 👉 [**安裝排錯指南**](./docs/INSTALL_TROUBLESHOOTING_ZH.md) |
| 👨‍💻 **工程師 / IT** | 看程式碼、跑測試、送 PR | 👉 [**開發者快速上手**](#-開發者快速上手) |

---

## ⚡ 30 秒看懂 Ouvoca

**Ouvoca 是台灣中小製造業的「對話式 ERP」。**
員工坐在電腦前打一句中文，AI 就把它變成完整的單據；任何會**寫入資料**的動作都會先跳出
**確認卡（ConfirmCard）**，把要寫的內容列清楚，人按了「確認」才執行——確認卡 30 分鐘內有效，
做錯了 90 秒內還能跟 AI 說「撤銷」救回來。

| 工廠的老問題 | Ouvoca 的解法 |
|---|---|
| SAP / Oracle 太貴 | 20 人以內 **NT$0**；超過再談（同級系統一般 NT$30–50 萬 / 年） |
| 員工不愛學系統 | 用講的就會用，AI 取代教育訓練 |
| 改個規則要等 IT 顧問一個月 | 「家規」把公司規矩存成資料，改規則不用改程式、不用重新部署 |
| 老闆想看數字要等會計 | Chat 一句話拿到應收帳齡、庫存週轉、毛利率 |
| 怕 AI 亂操作 | 確認卡強制人工確認 + 90 秒撤銷 + 逐筆稽核日誌 |
| 舊系統（鼎新 / 正航）不想丟 | Schema Mapping AI 自助接外部資料庫<sup>※</sup> |

> ⚠️ <sup>※</sup> connector 為「**技術連線元件**」，不含原 ERP（如 Workflow / ChengHang / SAP B1 等廠商之產品）的使用授權；各廠商之授權合約規定可能不同，請依貴司與該廠商之合約為準。建議客戶於啟用前先和原 ERP 廠商書面確認授權範圍。Ouvoca **不參與、不代理**此類合約事務；於適用法律所允許之最大範圍內不承擔相關責任。詳見 [`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md) / [EN](./docs/EXTERNAL_DB_LICENSING_NOTICE_EN.md)。<br>The connector is a **technical connectivity component** and does NOT include the licensing of your incumbent ERP; each vendor's terms may differ. Ouvoca **does not participate in or represent the customer in** such contractual matters.

### 🏛️ 招牌差異化：「家規（House Rules）」

每家公司都有自己的規矩：「採購超過 10 萬要老闆批」「工單沒做法不能開工」「折扣超過 5% 要主管審」。
鼎新 / SAP 把這些規則**寫死在程式裡**，要改就得等顧問。

**Ouvoca 把規則變成資料**——每條家規是資料庫裡的一筆記錄（觸發點 + 條件 + 動作 + 例外），
不是程式碼。內建 **23 條**台灣工廠常見規矩，一鍵載入即可使用；要加、要改、要停用，
都只是改資料，**不用改程式、不用重新部署、不用等顧問**。

| 對手 | 改規則的方式 | 缺點 |
|---|---|---|
| SAP B1 | 顧問改程式 | 等 1 個月 + 5–20 萬 |
| 鼎新 / 正航 | 設定畫面 | 條件死板 |
| NetSuite | SuiteScript（JS） | 要會寫程式 |
| Odoo | Python eval | 危險 |
| **Ouvoca** ⭐ | **改資料庫裡的規則**（一鍵載入 23 條預設 + 9 支管理 API） | **不用改程式、不用重新部署** |

> ⚠️ **現況誠實說明**：家規引擎與 23 條預設規則已經在跑（會實際擋下違規單據），
> 管理方式目前是 **9 支 REST API**（`/api/policies/*`）。
> **設定畫面**與**「跟 AI 講一句就新增規則」尚未實作**，列在 roadmap。

📖 [家規完整使用指南](./docs/HOUSE_RULES_GUIDE_ZH.md)（含 23 條預設規則清單）

---

## 🔒 我的資料放在哪？會不會被送到 AI 公司？

老闆看 AI ERP 的第一個問題。以下**照程式碼實際行為**寫，不美化也不恐嚇。

### 📁 資料存在哪台機器？

**存在你自己的電腦／伺服器裡。Ouvoca 沒有雲端，程式裡沒有任何「把資料庫上傳出去」的路徑。**

| 安裝方式 | 資料庫在哪 |
|---|---|
| 一鍵安裝（`install_easy.bat` / `.sh`） | `backend\erp.db` — 就在你解壓的資料夾裡（例如 `C:\Ouvoca\backend\erp.db`），SQLite 單一檔案 |
| Docker（`install.bat` / `docker compose`） | Docker volume `backend-data`，容器內 `/app/data/erp.db` |
| 正式上線換 PostgreSQL | 你自己指定的資料庫伺服器（`backend/.env` 的 `DATABASE_URL_PROD`） |

上傳的附件在 `backend\uploads\`、系統備份在 `backend\backups\backup-*.db`——一樣都在你的機器上。
要異地備份就自己複製這幾個檔案 → [`BACKUP_RESTORE_SOP_ZH.md`](./docs/BACKUP_RESTORE_SOP_ZH.md)

### 🤖 開了 AI 對話，到底哪些內容會送出去？

**只有你按下送出的那一句話、以及為了回答它所查到的資料**，會走到你選的 LLM 供應商（預設 DeepSeek）。逐項列清楚：

| 會送出去 | 說明 |
|---|---|
| ✅ 你打的那句話 | 例如「跟長江廠下 100 個 M6 螺絲」 |
| ✅ 同一個對話視窗最近 **10 則**訊息 | `backend/app/api/chat.py` 只撈 10 筆當上下文 |
| ✅ 你的帳號、員工編號、角色、權限碼清單 | 寫在系統提示詞裡，讓 AI 不會叫你做沒權限的事 |
| ✅ 該領域可用的工具定義（名稱／說明／欄位） | 只是欄位規格，不含任何你的營運資料 |
| ⚠️ **AI 為了回答你而查到的那筆資料** | 最關鍵的一項。你問「列出庫存低於安全庫存的零件」，那份清單就會被送回供應商，AI 才有辦法用中文講給你聽 |

| 不會送出去 | 為什麼 |
|---|---|
| ❌ 資料庫檔案本身 | 程式沒有上傳資料庫的功能 |
| ❌ 資料庫帳號密碼 | LLM 拿不到連線資訊，也不會產生 SQL。它只能從**已註冊的工具**挑一個、把欄位填好，實際查詢由後端執行（`backend/app/agents/engine.py` 的 `execute_tool`） |
| ❌ 你這次沒問到的資料 | 沒被工具查到的東西，不會出現在送出的內容裡 |

> 📌 **一句話總結**：AI 看得到的，就是它為了回答你這一句話而查到的那些資料——不多也不少。
> 反過來說，**你問了什麼，就等於把什麼交給了供應商**。
> 客戶名單、成本結構這類敏感資料，如果不想讓它出公司，就別用 AI 去問，或改用下面的離線模式。

預設供應商是 DeepSeek（`https://api.deepseek.com/v1`），可在設定頁改成 OpenAI / Anthropic / Ollama。
⚠️ **DeepSeek、OpenAI、Anthropic 的伺服器都在國外，用這三家等於資料會出境**，
有個資或客戶保密要求的公司請先評估 → [`COMPLIANCE_TW_ZH.md`](./docs/COMPLIANCE_TW_ZH.md)（個資法對照）

### 🚫 不開 AI 對話，系統還能不能用？

**能，而且是完整的 ERP。** 沒設 API Key 時 AI 助手會回一張「還沒啟用」的提示卡，其他東西照跑——
17 個前端頁面、242 支 REST API、家規、審批、權限、備份、PDF 列印全都不需要 LLM。
整套系統可以在**完全沒有對外網路**的區網裡運作（只有安裝當下需要網路）。

> ⚠️ 唯一例外：[功能總覽](#-功能總覽)裡**只標 💬**、沒有 🖥 也沒有 🔌 的模組（目前是 **💰 金流付款／收款**），
> 只做了 AI 工具、沒有畫面也沒有 REST API，不開 AI 就用不到。

### 🏠 完全離線：Ollama

想要「一個位元組都不出公司」，把供應商改成 **Ollama**——模型跑在你自己的機器上
（預設 `http://localhost:11434`），API Key 留空，對話內容完全不出區網。
安裝步驟見 [`HOW_TO_GET_LLM_API_KEY_ZH.md`](./docs/HOW_TO_GET_LLM_API_KEY_ZH.md) 的 Ollama 段落。

> ⚠️ **誠實揭露（v3.70 現況）**：Ollama 這條路**目前只能聊天問答，不能真的開單**。
> `backend/app/agents/engine.py` 的 `_ollama_chat()` 沒有把工具定義傳給模型，回傳的 `tool_calls` 永遠是空的——
> 所以「跟長江廠下 100 個螺絲」在 Ollama 模式下**不會**跳確認卡、**不會**建單。
> 要用對話開單，目前必須用 DeepSeek / OpenAI / Anthropic。

📖 資料分類、保留與清理策略（工程向）→ [`docs/DATA_LIFECYCLE.md`](./docs/DATA_LIFECYCLE.md) ·
🔐 漏洞回報 → [`SECURITY.md`](./SECURITY.md)

---

## 🎯 設計優先順序 — 能上線才是王道 / Deployability first

功能再強，裝不起來就等於零。所以每個技術決策都照這個順序取捨，**衝突時一律讓上位者贏**：

| 優先 | 原則 | 實際意思 |
|:---:|---|---|
| **1** | **電腦小白裝得起來** | 雙擊就會裝，不需要 Docker / Python / Node 背景知識。任何 PR 都不能讓這件事變難 |
| **2** | 資料不能弄丟 | 升級自動備份、還原前先存救援檔、破壞性操作一律要確認 |
| **3** | 做錯了救得回來 | 90 秒 Undo、稽核軌跡、ConfirmCard 先看再送出 |
| **4** | 台灣工廠真的用得到 | 統一發票、401/405 報稅、批號追溯優先於通用型花俏功能 |
| **5** | 程式好看 | 最後才考慮 |

這條原則由專案主於 2026-05-22 凍結，並由 `tests/smoke/test_v349_deployability_first.py`
跨四份文件同步驗證——任何人在某一份文件刪掉它，測試就會紅燈。

📖 完整取捨理由 → [`ARCHITECTURE_DECISIONS.md`](./docs/ARCHITECTURE_DECISIONS.md)

---

## 🚀 5 分鐘安裝（電腦小白模式）

**不需要 IT 背景、不需要先裝 Docker / Python / Node。** 會雙擊滑鼠 + 開瀏覽器就會裝。

```text
Step 1️⃣  下載 ZIP（GitHub 綠色 [< > Code] 按鈕 → Download ZIP）
Step 2️⃣  解壓到 C:\Ouvoca，雙擊 install_easy.bat（Mac / Linux：bash install_easy.sh）
Step 3️⃣  等 10–20 分鐘 → 瀏覽器自動打開 → 登入 admin / admin123
```

腳本會自動把 **Python 3.11.9** 與 **Node.js 20.11.1** 下載到專案內的 `tools\` 資料夾，
**不需要管理員權限、不會動到你系統原本的 Python**。

| 日常操作 | 怎麼做 |
|---|---|
| ▶️ 開機啟動 | 雙擊 `start.bat`（Mac / Linux：`bash start.sh`） |
| 🆙 更新到新版 | 雙擊 `update.bat` — 自動備份資料 → 拉新版 → 升級資料庫 → 補權限碼 → 重啟 |
| 🗑 完全移除 | 雙擊 `uninstall_easy.bat` — 會一併清掉 Windows 註冊表殘留，並先問你要不要保留資料 |
| 🐳 **Docker 模式**（給 IT / 工程師） | 改雙擊 `install.bat`（需先裝 Docker Desktop），或 `docker compose up -d` |

### 系統需求

| 項目 | 最低 | 建議 |
|---|---|---|
| 作業系統 | Windows 10 / macOS 11 / Ubuntu 20 | Windows 11 / macOS 13 |
| 記憶體 | 4 GB | 8 GB 以上 |
| 硬碟空間 | 5 GB | 20 GB 以上 |
| CPU | 任何 x86_64 / ARM64 | 4 核以上 |
| 顯示卡 | ❌ 不需要 | ❌ 不需要（AI 走雲端 API） |
| 網路 | 安裝時需要 | 日常使用**不需要**（除非開 AI 對話） |

下載量約 **556MB**（Python ~26MB + Node ~30MB + 套件 ~500MB）；解壓安裝後磁碟佔用約 **750MB**，全部在專案資料夾內。
10 Mbps 的網路大約 10 分鐘裝完。

📋 **安裝程式到底從哪裡下載了什麼、各自是什麼授權** → [`THIRD_PARTY_DOWNLOADS_ZH.md`](./docs/THIRD_PARTY_DOWNLOADS_ZH.md)
（逐項列出來源網址、版本、授權條款，方便你的 IT 或法務審核）

> ⚠️ **防毒軟體可能誤判** Python 安裝程式，請暫時停用或把本資料夾加入白名單。
> 🐍 **想自己建 venv 的工程師**：安裝腳本內建 Python 3.11.9；自建環境支援 3.11 與 3.12
> （見 `backend/pyproject.toml` 的 `requires-python = ">=3.11,<3.13"`，專案 CI 跑在 3.12），3.13 尚未支援。

### 🎯 裝好後第一件事（全部用「講的」）

```text
1️⃣ 改密碼      → 在 AI 助手講：「改密碼，我的新密碼是 MyN3wP@ss」
2️⃣ 設公司資料  → 「公司叫 長江精密股份有限公司 統編 12345678 地址 台北市…」（PDF 上會印）
3️⃣ 載示範資料  → 「載入示範資料」（3 客戶 / 3 供應商 / 5 料件 + 1 訂單 + 1 採購單，玩完可一鍵清除）
4️⃣ 試一句業務  → 「印 SO-001」「匯出客戶清單 Excel」「今天有什麼要注意的？」
```

🔑 **想開 AI 對話功能？** 登入 → ⚙️ 設定 → 🤖 AI 助手設定 → 貼上 API Key → 測試 → 儲存（即時生效不用重啟）。
申請教學（DeepSeek / OpenAI / Anthropic / Ollama 比較）→ [`HOW_TO_GET_LLM_API_KEY_ZH.md`](./docs/HOW_TO_GET_LLM_API_KEY_ZH.md)

📘 給老闆看的圖文版安裝手冊 → [`INSTALLATION_ZH.md`](./docs/INSTALLATION_ZH.md) · [📕 PDF](./docs/pdf/01_安裝指南_中文.pdf)
🆘 裝失敗？→ [安裝排錯指南](./docs/INSTALL_TROUBLESHOOTING_ZH.md)（症狀對解法 + 14 題安裝 FAQ）

---

## 🎯 功能總覽

> 🖥 = 畫面點得到 ｜ 💬 = 只能跟 AI 講 ｜ 🔌 = 有 API 可串接
> 完整清單（每個功能對到哪支 API、哪一頁）→ **[`docs/FEATURES_ZH.md`](./docs/FEATURES_ZH.md)**

| 模組 | 做得到什麼 | 入口 |
|---|---|---|
| 📦 **庫存** | 料件建檔、即時庫存、安全庫存警示、異動紀錄、倉間調撥、盤點單全套、庫存月報 Excel（無財務權限者看不到成本欄） | 🖥 🔌 💬 |
| 📷 **條碼與追溯** `v3.64` | 條碼槍掃料號 / 批號 / 序號、料件 QR 標籤列印、**批號正反向追溯**（這批料從哪來、被哪些單吃掉）、序號追溯 | 🖥 🔌 |
| 🛒 **採購** | 供應商建檔、採購單、審核、收貨入庫、採購單 PDF、補貨建議、供應商歷史報價、採購集中度分析 | 🖥 🔌 💬 |
| 📝 **請購 / 收料** `v3.63` | **請購單 PR**（現場提需求 → 主管核准 → 轉採購單）、**收料單 GRN**（不可超收） | 🔌 💬 |
| 💱 **詢價比價** `v3.64` | **RFQ**：發詢價給多家 → 登錄報價 → 比價標出最低價 → 決標一鍵轉採購單 | 🖥 🔌 💬 |
| 💼 **銷售** | 客戶建檔、銷售訂單、確認、**出貨一鍵連動**（扣庫存 + 出貨單 + 發票 + 傳票 + 應收，同一交易內完成）、報價單全套、訂單跟單、客戶毛利率、接單決策評估 | 🖥 🔌 💬 |
| ↩️ **退貨** `v3.63` | **退貨單 RMA**：建單 → 主管核准 → 退貨入庫 | 🔌 💬 |
| 🏭 **生產** | 產品、做法（BOM）、工單釋放 / 完工、工作中心、製程工序、派工紀錄 | 🖥 🔌 💬 |
| 📤 **領料 / 成本** `v3.61` `v3.63` | **領料單 MI**（扣料 + 成本快照）、**工單成本彙總**（材料 + 人工 + 製造費用） | 🔌 💬 |
| 📅 **MPS / MRP / 規劃** | 主生產排程、物料需求計算、瓶頸辨識、DBR 排產、產能 What-if、需求預測、反查用途 | 🔌 💬 |
| 🔬 **品質** | 檢驗單、不良品 NCR、矯正措施 CAPA、檢驗報告 PDF | 🖥 🔌 💬 |
| 📒 **會計基礎** | 86 科台灣科目表開機即用、傳票、過帳、應收帳款、月結、應收帳齡 Excel、應收週轉天數 | 🖥 🔌 💬 |
| 📊 **財務三大報表** `v3.61` | **試算表 / 損益表 / 資產負債表**、401/405 營業稅申報、**3-Way Match**（採購↔收貨↔發票勾稽）、票據管理、固定資產與折舊、銷貨成本結轉 | 🔌 💬 |
| 💰 **金流** `v3.60` | 銀行帳戶、應付帳款、記錄付款 / 收款（自動記傳票並沖銷應付 / 應收） | 💬 |
| 🧾 **台灣電子發票** | B2B / B2C 開立、24 小時內作廢、5 年查詢保存、發票 PDF、多國統編驗證 | 🖥 🔌 💬 |
| 🏬 **倉儲** | 倉區 / 儲位、揀貨任務、循環盤點、批號清單、庫存週轉率 | 🔌 💬 |
| 🤝 **CRM** | 🌱 新苗（Lead）→ 🎯 追單（Opportunity）→ 客戶，互動歷程自動產生、客戶 360 度 | 🖥 🔌 💬 |
| ✅ **審批流程** | 「超過 X 元要主管審」多階規則、待我審、批准 / 拒絕（須填原因）、審批歷史 | 🖥 🔌 💬 |
| 🏛️ **家規** | 23 條預設規則開機即用（會實際擋下違規單據），可新增 / 修改 / 停用 / 試跑，附稽核紀錄 | 🔌 |
| 🔐 **資安** `v3.62` `v3.64` | **MFA 雙重驗證（TOTP）**、登入失敗鎖定、改密碼即撤銷舊登入、上傳檔案 magic bytes 驗證、病毒掃描掛鉤 | 🖥 🔌 |
| 💾 **備份還原** `v3.62` | 立即備份 / 列表 / 還原 / 刪除 + 保留策略 + 每日排程（預設 03:00） | 🖥 🔌 💬 |
| ⚙️ **系統設定** `v3.60` | 14 項系統組態（抬頭 / 統編 / 稅率 / 時區 / 備份 / 鎖定閾值…）、AI 供應商設定、檔案上傳、示範資料、5 種行業種子 | 🖥 🔌 💬 |
| 🔗 **外部資料庫** `v3.60` | 接鼎新 / 正航 / SQL / CSV，帳密 **AES-256-GCM 加密**儲存，Schema 對映帶信心分數 | 🔌 💬 |
| 👥 **權限** | 231 個權限碼 × 10 個預設角色，可複製改權限、個別例外、多租戶自動隔離 | 🖥 🔌 💬 |
| 📈 **報表與提醒** | KPI 總覽、DSO / 庫存週轉 / 毛利率、OEE、AI 成本、每日摘要 Email、主動提醒 | 🖥 🔌 💬 |

> ⚠️ **誠實揭露**：標了 💬 而沒有 🖥 的功能，**畫面上找不到入口**，只能在 AI 助手打字操作。
> 主要是財務三大報表（v3.61）、四張表單 PR / GRN / MI / RT（v3.63）、金流付款收款（v3.60）。
> 說明見 [`FEATURES_ZH.md`](./docs/FEATURES_ZH.md) 開頭。

### 📦 出貨按一次，五件事一起完成

工廠最怕的是「出貨單、發票、傳票、應收帳款四本帳對不起來」。Ouvoca 把它們綁在同一個交易內：

```text
銷售訂單 ──出貨──▶ 出貨單 ──自動──▶ 電子發票 ──自動──▶ 會計傳票 ──自動──▶ 應收帳款
                      │                                                    │
                      └────────────── 全部回連到銷售訂單 ──────────────────┘
```

中間任何一步失敗就整批復原，不會留下半成品；客戶沒有統編（B2C）則跳過開票，其餘照做。

### 🤖 對話式操作長什麼樣

| 想做的事 | 你打的字 | 系統的反應 |
|---|---|---|
| **查** | 「列出庫存低於安全庫存的零件」 | 直接回表格 |
| **建** | 「跟長江廠下 100 個 M6 螺絲，交期下週五」 | 出**確認卡** → 按確認才下單 |
| **改** | 「把 SO-2025-0042 的交期改到 6/10」 | 出確認卡 |
| **刪** | 「取消 PO-2025-0099」 | 出確認卡 + 90 秒內可撤銷 |

缺欄位時 AI 會**反問**（例如沒講單價就問你單價），不會憑空編造。
🎬 真實 DeepSeek 跑 9/9 情境全通（50 秒、21 次工具呼叫）→ [`demos/deepseek_e2e_latest.md`](./docs/demos/deepseek_e2e_latest.md)
📐 設計原理（6 層架構 + 7 條原則）→ [`CONVERSATIONAL_ERP_DESIGN_ZH.md`](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md)

---

## ⚖️ 三軌授權（20 人以內免費）

| 軌道 | 條款 | 適用對象 | 費用 |
|---|---|---|---|
| 🟢 **開源軌** | [AGPL-3.0](./LICENSE) | 願意揭露原始碼的所有人 | **免費** |
| 🌱 **小小企業軌** | [小小企業授權](./LICENSE-SMALL-BUSINESS.md) | **同時在線 ≤ 20 人**的單一公司，非軟體商 / 非 SaaS | **完全免費**（含閉源 connector） |
| 🔵 **商業軌** | 個別協商 | 超過 20 人、軟體商 / OEM、SaaS 業者、大企業 | 個別報價 |

> 🌱 **怎麼算 20 人？** 看**同時在線人數**（24 小時內任一時刻的峰值，閒置 15 分鐘算下線）。
> 例：公司 100 人有帳號，但同時最多 18 人在用 → ✅ 免費。
>
> ⚠️ connector「免費」指的是 **Ouvoca 不收技術授權費**；要把 connector 接到您**現有商用 ERP**
> （如 Workflow / ChengHang / SAP B1 等廠商之產品），各廠商授權規定可能不同，建議先與原廠書面確認範圍。
> Ouvoca 不參與此類第三方合約事務。

不確定走哪一軌？看 [`LICENSE-COMMERCIAL.md`](./LICENSE-COMMERCIAL.md) 的決策樹，
或 [商業授權 FAQ](./docs/COMMERCIAL_LICENSING_FAQ_ZH.md)。

---

## 📅 導入要多久？誰來教員工？

自己裝來玩，[5 分鐘安裝](#-5-分鐘安裝電腦小白模式) 就夠了。
但要讓**整間工廠真的改用它**——舊資料搬進來、員工會操作、老闆看得懂報表——
那是另一件事。我們把它整理成一份 **14 天 Day-by-Day 的導入 SOP**：

| 階段 | 天數 | 做什麼 |
|---|---|---|
| 📋 需求訪談 | Day 1–2 | 現場 4 小時訪談，把現有流程、單據、規矩問清楚 |
| 🖥 環境準備 | Day 3–5 | 決定裝在單機還是伺服器、部署清單、開客戶帳號 |
| 📦 安裝 + 行業範例 | Day 6–7 | 標準安裝（2 小時內）、載入 5 套行業種子其中一套 |
| 📥 客戶資料匯入 | Day 8–9 | 依優先順序搬料件 / 供應商 / 客戶 / BOM，跑資料品質檢核抓孤兒記錄與重複 |
| 🧑‍💼 超管訓練 | Day 10 | **2 小時**：帳號權限、備份、看 log、升級、緊急重啟 |
| 👥 部門主管訓練 | Day 11–12 | **5 場 × 1 小時**，含老闆專屬的 60 分鐘 |
| 🧪 內部試營運 | Day 13 | 真單真跑，異常追蹤表逐條收斂 |
| 🚀 正式上線 | Day 14 | 上線儀式，老闆必須出席 |
| 🩺 上線後追蹤 | 30 天 | Week 1 每日看使用量、bug 24 小時內修；Day 30 帶回顧報告給老闆 |

**成敗指標**：上線後 30 天內「每天有用的人 ÷ 總人數」≥ 60%。
手冊最後還列了**常見導入陷阱**與對應的預防作法（客戶不交資料、員工抗拒、
防火牆擋掉 LLM API、老闆上線當天沒出席…）。

📖 完整 Day-by-Day 手冊 → [`docs/IMPLEMENTATION_PLAYBOOK_ZH.md`](./docs/IMPLEMENTATION_PLAYBOOK_ZH.md)
（訪談清單、訓練大綱、匯入指令、驗收 checklist 全都有）

> ⚠️ 這份手冊是寫給**導入顧問 / 整合商 / 內部 IT** 看的，預設走 Docker 部署，
> 內容停在 2026-05 尚未完全跟上 v3.70（在 [`docs/README.md`](./docs/README.md) 標為 🟡）。
> 天數與訓練排程仍然適用；指令請以 [`INSTALLATION_ZH.md`](./docs/INSTALLATION_ZH.md) 為準。
>
> 🌱 **小小企業軌（20 人以內）不含導入服務**——授權條款 §3.4 寫明只有社群支援、沒有 SLA。
> 但這份手冊是公開的，你可以自己照著做，或請你熟識的 IT 顧問照著走。
> 需要我們協助導入請走[商業軌](./LICENSE-COMMERCIAL.md)。

---

## 📚 文件導覽

| 你想知道 | 看這份 |
|---|---|
| 🗂 **先看這份：全部文件的總索引** | **[`docs/README.md`](./docs/README.md)** — `docs/` 底下 100 份說明文件一次列完，每份標 🟢🟡🔴 告訴你「這份還能不能信」，並依**老闆 / 現場員工 / IT / 開發者 / English** 五種身分各給一條閱讀路線。不知道該看哪一份就從這裡開始 |
| 📖 **這套系統有哪些功能** | [`docs/FEATURES_ZH.md`](./docs/FEATURES_ZH.md) — 每個功能對到哪支 API / 哪一頁 |
| 📜 **每一版改了什麼** | [`docs/CHANGELOG_ZH.md`](./docs/CHANGELOG_ZH.md) — 白話版版本紀錄（v3.49 → v3.70） |
| 🆘 **裝不起來 / 常見問題** | [`docs/INSTALL_TROUBLESHOOTING_ZH.md`](./docs/INSTALL_TROUBLESHOOTING_ZH.md) — 症狀對解法 + 14 題 FAQ |
| 📕 **74 份雙語 PDF** | [`docs/DOCUMENT_INDEX.md`](./docs/DOCUMENT_INDEX.md) — 產品說明書 / 操作手冊 / 學術論文 / 法律聲明 |
| 🏛️ **家規怎麼用** | [`docs/HOUSE_RULES_GUIDE_ZH.md`](./docs/HOUSE_RULES_GUIDE_ZH.md) |
| 🏗 **架構圖與領域對照** | [`docs/ARCHITECTURE_DIAGRAM.md`](./docs/ARCHITECTURE_DIAGRAM.md) · [`ARCHITECTURE_BLUEPRINT_ZH.md`](./docs/ARCHITECTURE_BLUEPRINT_ZH.md) |
| 🔌 **API 清單** | [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md) · 或跑起來直接看 http://localhost:8000/docs |
| 🚢 **正式上線 / 換 PostgreSQL** | [`DEPLOYMENT.md`](./DEPLOYMENT.md) |
| 🔒 **資安政策 / 漏洞回報** | [`SECURITY.md`](./SECURITY.md) |
| 🧭 **為什麼這樣設計** | [`docs/ARCHITECTURE_DECISIONS.md`](./docs/ARCHITECTURE_DECISIONS.md) — 含「能上線才是王道」設計優先順序 |
| 🗝 **申請 AI API Key** | [`docs/HOW_TO_GET_LLM_API_KEY_ZH.md`](./docs/HOW_TO_GET_LLM_API_KEY_ZH.md) |

---

## 🛠 開發者快速上手

```bash
git clone https://github.com/fanchanyu/ouvoca && cd ouvoca

# 1) 必跑一次：安裝 secret-scanning hook（防 API key / .env 誤推）
bash scripts/git-hooks/install_hooks.sh        # Windows：scripts\git-hooks\install_hooks.bat

# 2) 開發模式（熱重載）。Windows 直接雙擊 start_dev.bat：
#    檢查 Python 3.11 / Node 20 → seed admin/admin123 → 釋放 :8000 / :5173 → 自動開瀏覽器
#    停止：雙擊 stop_dev.bat（精準 PID kill，不誤殺其他 Python / Node）

# 3) 跑測試
cd backend && python -m pytest                 # 883 收集 / 880 通過 / 2 skipped
python -m pytest tests/smoke/ -v               # 只跑 smoke
python -m pytest -k test_update_part            # 跑特定測試

# 4) 自證閘（4 道 gate：編譯 / 行為 / 文件 / 治理），pre-push hook 會自動跑
bash scripts/run_gates.sh
```

| 服務 | 網址 | 備註 |
|---|---|---|
| 桌機 UI | http://localhost:5173 | 登入 `admin / admin123` |
| API 文件 | http://localhost:8000/docs | OpenAPI / Swagger |
| War Room | http://localhost:8080 | 即時事件儀表板（SSE） |
| 分廠節點 | http://localhost:8001/api/health | MESH 節點健康檢查（`/api/factory/*` 只有 register/list/aggregate） |

**技術堆疊**：FastAPI + SQLAlchemy 2 async + Alembic ｜ React 18 + Vite + Tailwind ｜
SQLite（開發）/ PostgreSQL（正式）｜ LLM 預設 DeepSeek，可換 OpenAI / Anthropic / Ollama。

**開 AI 對話**：`backend/.env` 設 `LLM_API_KEY=...`；Windows 開發環境遇到 DeepSeek 憑證問題可加 `LLM_VERIFY_SSL=false`。

工程文件：[開發 SOP](./docs/DEVELOPMENT_SOP.md) · [Gap 分析](./docs/GAP_ANALYSIS.md) ·
[對話式 ERP 6 層架構（必讀）](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md) · [架構決策 ADR](./docs/ARCHITECTURE_DECISIONS.md)

---

## 📊 專案數據

> 全部是 **2026-08-04 的程式碼實測值**（載入 `app.main` 統計路由、用 `Base.metadata` 統計資料表、
> 實際跑 `pytest`），不是估算。

| 項目 | 數值 |
|---|---|
| 後端測試 | **883 收集 / 880 通過 / 2 skipped**（約 41 秒） |
| REST API endpoint | **242**（31 個 router） |
| 資料表 | **107**（30 支模型檔） |
| AI 對話工具 | **201**（106 查詢 / 94 寫入 / 1 軟寫入），跨 **19 個領域**、**17 個 agent** |
| 前端頁面 | **17**（含登入頁） |
| 資料庫版本 | Alembic `001` → `016` |
| 權限碼 / 角色 | **231** 個權限碼 / **10** 個系統角色 |
| 開機即用種子 | 86 科會計科目 · 23 條家規 · 14 項系統組態 · 5 種行業 |
| 雙語 PDF 文件 | **74** 份（37 中文 + 36 英文 + 1 雙語合刊） |
| 程式碼行數 | 約 **10.9 萬行**（Python 6.4 萬 + TypeScript 1.2 萬 + 文件 3.4 萬） |
| 自證閘 | **4 道 gate**（編譯 / 行為 / 文件 / 治理），全綠才能 push |
| 版本 | git tag `v3.70` = `APP_VERSION` `3.70.0` = `package.json` `3.70.0` |
| Repo 建立 / 公開 | 2026-04 / 2026-05-16 |

---

## 📢 最近三版

| 版本 | 重點 |
|---|---|
| **v3.70**（2026-08-04） | 全新安裝也自動建效能索引（300 個）· 版本號三處統一 · CI 新增治理閘 · 補上 `SECURITY.md` |
| **v3.69**（2026-08-04） | 效能健檢：181 個外鍵欄位補複合索引（實測 2 萬筆明細快約 1,030 倍）· 消滅 N+1 · 稽核只記寫入動作 |
| **v3.68**（2026-08-04） | Turnkey 開機即用六套件補完：23 條家規 · 檢驗報告 / 盤點表 PDF · 86 科科目表 · 5 行業種子 |

📜 **完整版本紀錄（v3.49 → v3.70，白話版）→ [`docs/CHANGELOG_ZH.md`](./docs/CHANGELOG_ZH.md)**

---

## 🤝 貢獻

歡迎 PR！第一次貢獻請先看 [`CONTRIBUTING.md`](./CONTRIBUTING.md) 並簽 [`CLA.md`](./CLA.md)
（DCO 形式，`git commit -s` 即可）· 社群守則見 [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md)。

> CLA 第 2(b) 條是雙軌授權的命脈：你的貢獻授權維護者以任何條款（含商業）再授權。
> 沒有這一條，整條商業軌就不成立。

---

<sub>by [Peter](https://github.com/fanchanyu) · [回報問題](https://github.com/fanchanyu/ouvoca/issues) ·
[商業授權](./LICENSE-COMMERCIAL.md) · 2026-05-22 因商標衝突由 erpilot 更名為 Ouvoca（[公告](./docs/RENAME_NOTICE_ZH.md)）</sub>
