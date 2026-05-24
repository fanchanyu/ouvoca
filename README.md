# Ouvoca — 給小工廠的 AI ERP / AI ERP for Small Factories

> 🇹🇼 **用講的就能下單、查庫存、做報表** — 給 50-100 人小工廠的免費 AI ERP，不需懂程式，雙擊安裝。
>
> 🇺🇸 **Talk to your ERP like a person** — Buy, ship, check stock, generate reports with one sentence. Free for SMB factories ≤20 concurrent users.

---

## 🚀 我要快速開始 / Quick Start

| 想做什麼 / What you want | 點這裡 / Click here |
|---|---|
| 🇹🇼 **我要裝起來用看看**（雙擊就會裝，不用懂程式）| 👉 [**5 分鐘安裝指南**](#-5-分鐘安裝指南--5-minute-install-for-non-developers) |
| 🇹🇼 **我要看它長什麼樣**（30 秒了解 + 範例對話）| 👉 [**30 秒看懂 Ouvoca**](#-30-秒看懂-ouvoca--30-second-pitch) |
| 🇹🇼 **裝失敗了怎麼辦** | 👉 [**安裝排錯指南**](./docs/INSTALL_TROUBLESHOOTING_ZH.md) |
| 🇹🇼 **我想知道費用 / 授權** | 👉 [**三軌授權**](#️-三軌授權--tri-license-model) — 20 人以下免費 |
| 👨‍💻 **我是工程師，要看 code** | 👉 [**開發者指南**](#-開發者指南--developer-guide) |

---

[![Tests](https://img.shields.io/badge/tests-701%20passing-brightgreen)]()
[![Gates](https://img.shields.io/badge/self--verify-7%2F7%20green-brightgreen)]()
[![Docs](https://img.shields.io/badge/PDFs-76%20bilingual-blue)]()
[![License](https://img.shields.io/badge/license-AGPL--3.0%20%2B%20SBL%20%2B%20Commercial-blue)](./LICENSE)
[![Version](https://img.shields.io/badge/version-3.50-blueviolet)]()
[![Author](https://img.shields.io/badge/by-Peter-lightgrey)](https://github.com/fanchanyu)

---

## 📢 最近修了什麼？（電腦小白版）/ What's Fixed Recently?

> 🇹🇼 **不講工程術語，只說「你能用到什麼」**。每條修復都按「你會看到什麼差別」描述。
> 🇺🇸 **No tech jargon — only what you'll notice as a user.**

### 🆕 v3.50（2026-05-24）— 嚴苛標準六大修復

| 修了什麼 / What was fixed | 你會看到的差別 / What you'll notice |
|---|---|
| 🐍 **Python 版本不再打架** | 你電腦不論已裝 Python 3.12 / 3.13 / 完全沒裝，安裝都不會衝突。`install_easy.bat` 用獨立的 3.11，**完全不污染你系統的 Python**。 |
| 🔒 **裝錯版本會被擋下** | 以前 pip / npm 會默默裝壞，runtime 才炸。現在裝錯版本立刻紅燈，告訴你「用 install_easy.bat」。 |
| 📄 **電子發票可下載完整 PDF** | 以前點「列印發票」只開瀏覽器列印視窗，現在多了「📥 下載 PDF 發票」按鈕，**伺服器產生完整 A4 PDF**（含品項表格 + 中文字型）。 |
| 📋 **採購單 / 銷售單 / 出貨單 PDF 變完整** | 以前列印只印摘要寫「完整品項請至系統查詢」，現在每張單子加「📥 PDF」按鈕，**伺服器直接給你完整品項 + 簽核欄位 + 公司 LOGO** 的正式 PDF。 |
| 👤 **管理員（admin）可以新增帳戶 / 角色** | 以前 admin 點「新增使用者」會收到 403 Forbidden，現在權限系統補了 22 個缺失的權限碼，**admin 真的能管帳號了**。 |
| 🚨 **權限漏洞修補** | 內部找到一個 bug：建立使用者用的權限碼竟然是「讀使用者」（複製貼上錯誤）。已修正為「建立使用者」，**避免有人靠讀取權限偷建帳號**。 |

### 🆕 v3.49（2026-05-22）— 電腦小白安裝路徑

| 修了什麼 | 你會看到的差別 |
|---|---|
| 🚀 **不需 Docker、不需先裝任何東西** | 雙擊 `install_easy.bat` → 腳本自動下載 Python 3.11 + Node.js 20 到專案內 `tools\`，**全程無需管理員權限、不修改你系統**。 |
| ⚖️ **下載前先告知 + 5 秒倒數** | 執行前畫面會顯示「即將下載 Python (PSF License) / Node (MIT License)」，給你 Ctrl+C 取消機會。 |
| 🆘 **裝失敗有救援指引** | 開 [`docs/INSTALL_TROUBLESHOOTING_ZH.md`](./docs/INSTALL_TROUBLESHOOTING_ZH.md)，按「症狀」對「解法」，常見錯誤（防毒擋住、防火牆、埠口被占）一查就會。 |
| 🗑️ **卸載 = 刪資料夾** | 整個 Ouvoca 都在這個資料夾內，不會在註冊表、系統服務、`Program Files` 留東西。 |

[👉 詳細版本紀錄請點開下方 `📜 版本更新紀錄`](#-版本更新紀錄)

---

<details>
<summary>📜 <strong>版本更新紀錄 / Changelog</strong>（點開展開，最新在上）</summary>

> 🇹🇼 **2026-05-22 — 因商標衝突更名為 Ouvoca** — 詳見 [RENAME_NOTICE_ZH.md](./docs/RENAME_NOTICE_ZH.md) · [EN](./docs/RENAME_NOTICE_EN.md)

- **v3.50** (2026-05-24) — 🛠 嚴苛標準三維修復：Python 版本全 codebase 鎖到 3.11 + PDF 雙系統合一（E-invoice/PO/SO/出貨單可下完整 PDF）+ RBAC 補 22 缺失權限碼 + 修一個權限升級 bug
- **v3.49** (2026-05-22) — 🚀 **電腦小白零依賴安裝**（雙擊 `install_easy.bat` 自動下載 Python/Node，不需 Docker）+ 法律揭露 + 排錯指南
- **v3.48** (2026-05-22) — 全模組六維二次審計修復 + 12 model 補 TenantMixin + 法律精簡
- **v3.47** (2026-05-22) — 6 維審計：安裝 / 安全 / 資料 / UX 四維修補
- **v3.46** (2026-05-22) — Glossary DB 持久化 + datetime fixes
- **v3.42** (2026-05-22) — 使用者帳號管理 / 全域跨表搜尋 / AI 每日上限 / 台灣工作天 / 時區設定 · [法律 ZH](./docs/pdf/37_第六輪卡關修補法律聲明_中文.pdf) · [EN](./docs/pdf/37_Polish_V342_Legal_EN.pdf) — 使用前由 IT + 法律 + HR 主管覆核
- **v3.41** (2026-05-22) — 客戶毛利率 / 訂單跟單 / 寄 PDF Email / 資料健康檢查 · [法律 ZH](./docs/pdf/36_第五輪卡關修補法律聲明_中文.pdf) · [EN](./docs/pdf/36_Polish_V341_Legal_EN.pdf) — 使用前由 CPA + 法律 + 業務主管覆核
- **v3.40** (2026-05-21) — 凍結 hard-write 安全模式 / Audit log 跨人搜尋 / 中文相對日期解析 · [法律 ZH](./docs/pdf/35_第四輪卡關修補法律聲明_中文.pdf) · [EN](./docs/pdf/35_Polish_V340_Legal_EN.pdf) — 使用前由 CPA + 法律 + 內控覆核
- **v3.39** (2026-05-21) — PDF 印公司 LOGO / Delete 三件套 / LLM 工具分頁 · [法律 ZH](./docs/pdf/34_第三輪卡關修補法律聲明_中文.pdf) · [EN](./docs/pdf/34_Polish_V339_Legal_EN.pdf)
- **v3.38** (2026-05-21) — ConfirmCard TTL 30 分 / 一鍵備份 / 客戶 disambiguation · [法律 ZH](./docs/pdf/33_第二輪卡關修補法律聲明_中文.pdf) · [EN](./docs/pdf/33_Polish_Legal_EN.pdf)
- **v3.37** (2026-05-21) — 電腦小白卡關 14 條全修：Docker 中文字型、預設密碼提示、OnboardingWizard、Chat 歡迎 · [法律 ZH](./docs/pdf/32_安裝精靈法律聲明_中文.pdf) · [EN](./docs/pdf/32_Setup_Wizard_Legal_EN.pdf)
- **v3.0** (2026-05-15) — ⚡ 戰略軸轉：砍 LINE Bot / Mobile App / 外協協同三線 · [ADR](./docs/ARCHITECTURE_DECISIONS.md)

完整 changelog 見 [`docs/WORKLOG.md`](./docs/WORKLOG.md)（內部）。

</details>

---

## 🙋 你是誰？/ Who Are You?

🇹🇼 Ouvoca 有 3 種讀者，**請點下面的連結直接跳到你需要的章節**：
🇺🇸 Ouvoca has 3 audiences. **Jump to your section**:

| 我是... / I am... | 我需要... / I need... | 跳到 / Jump to |
|---|---|---|
| 👔 **老闆 / 採購 / 業務 / 倉管**<br>Boss / Buyer / Sales / Warehouse | 我要**用** Ouvoca，不會寫程式<br>I want to **use** Ouvoca, no coding | 👉 [**5 分鐘安裝指南**](#-5-分鐘安裝指南--5-minute-install-for-non-developers) |
| 📚 **採購決策者 / 顧問**<br>Buyer decider / Consultant | 我要看**文件 / 報價 / 規格書**<br>I need **docs / quotes / specs** | 👉 [**76 份雙語 PDF**](#-76-份雙語客戶文件--76-bilingual-customer-pdfs) |
| 👨‍💻 **工程師 / IT / 想貢獻者**<br>Developer / IT / Contributor | 我要看**程式碼 / 開發環境 / PR**<br>I want **code / dev setup / PR** | 👉 [**開發者指南**](#-開發者指南--developer-guide) |

---

## 📑 目錄 / Table of Contents

- [⚡ 30 秒看懂 Ouvoca / 30-Second Pitch](#-30-秒看懂-ouvoca--30-second-pitch)
- [🚀 5 分鐘安裝指南 / 5-Minute Install](#-5-分鐘安裝指南--5-minute-install-for-non-developers)
- [❓ 安裝常見問題 / Install FAQ](#-安裝常見問題--install-faq)
- [📚 76 份雙語客戶文件 / 76 Bilingual PDFs](#-76-份雙語客戶文件--76-bilingual-customer-pdfs)
- [🎯 內含什麼 / What's Inside](#-內含什麼--whats-inside)
- [🏗 架構 / Architecture](#-架構--architecture)
- [🗺 領域對照 / Domain Map](#-領域對照--domain-map)
- [🤖 對話式 CRUD 範例 / Try the Conversational CRUD](#-對話式-crud-範例--try-the-conversational-crud)
- [📡 即時事件流 / Try the Event Stream](#-即時事件流--try-the-event-stream)
- [🐘 Production 切換 PostgreSQL / Production Switch-over](#-production-切換-postgresql--production-switch-over)
- [📂 檔案結構 / File Layout](#-檔案結構--file-layout)
- [⚖️ 三軌授權 / Tri-License Model](#️-三軌授權--tri-license-model)
- [🛠 開發者指南 / Developer Guide](#-開發者指南--developer-guide)
- [🤝 貢獻 / Contributing](#-貢獻--contributing)

---

## 🏛️ 新功能聚焦：「家規 (House Rules)」⭐ Ouvoca 招牌差異化

🇹🇼 **不抄 SAP「Business Rule」/ 鼎新「業務規則」/ Odoo「Server Action」**，Ouvoca 自創「家規」概念：
🇺🇸 **Not copying SAP "Business Rule" / 鼎新 "Business Rules" / Odoo "Server Actions"** — Ouvoca's original concept "House Rules":

> 🇹🇼 像家庭家規一樣，**每家公司有自己的規矩**（PO > 10 萬要老闆批 / WO 沒做法不能釋放 / 折扣 > 5% 要主管審…）。
> 鼎新 / SAP 把規則寫死，改要等顧問 1 個月、花 5-20 萬。
> Ouvoca 把規則**資料化**，你可以：
>
> 1. 🖱 **UI 點一點** 開關 / 改條件 / 新增（不用改 code）
> 2. 💬 **對 AI 講話**「我們公司 SO 折扣超 5% 應該主管審」→ AI 回 ConfirmCard 確認 → 規矩立即上線
> 3. 🔌 **Plugin 新條件**（給工程師擴充特殊國家 / 行業 logic）

> 🇺🇸 Like household rules, **every company has their own** (PO > 100k needs boss approval / WO without Recipe can't release / discount > 5% needs manager review…).
> SAP/鼎新 hardcodes rules — to change them, wait 1 month + pay $5k-20k for consultants.
> Ouvoca **data-fies** rules. You can:
>
> 1. 🖱 **Click in UI** to toggle / edit / add (no code change)
> 2. 💬 **Tell AI**: "SO discount > 5% needs manager approval" → AI returns ConfirmCard → rule goes live
> 3. 🔌 **Plug-in new conditions** (engineers can extend for special countries / industries)

| 對手 / Competitor | 改家規方式 / How to change | 缺點 / Drawback |
|---|---|---|
| SAP B1 | 顧問改 code | 等 1 個月 + 5-20 萬 / 1 month + $5-20k |
| 鼎新 / 正航 | 設定畫面 | 條件死板 / Rigid |
| NetSuite | SuiteScript (JS) | 要會寫程式 / Coding required |
| Odoo | Python eval | 危險 / Unsafe |
| **Ouvoca** ⭐ | **UI 點 / AI 講 / Plugin** | **小白能改、立刻生效** / **Anyone can edit, instant** |

📖 **完整使用指南（給電腦小白）**：
- 🇹🇼 中文 → [`docs/HOUSE_RULES_GUIDE_ZH.md`](./docs/HOUSE_RULES_GUIDE_ZH.md)
- 🇺🇸 English → [`docs/HOUSE_RULES_GUIDE_EN.md`](./docs/HOUSE_RULES_GUIDE_EN.md)

> 🎯 **這是 Ouvoca 真正能贏鼎新/SAP 的關鍵差異化**——他們做不到「使用者自己改規矩」。
> 🎯 **This is Ouvoca's real edge over SAP/鼎新** — they can't let end users customize their own business rules.

---

## ⚡ 30 秒看懂 Ouvoca / 30-Second Pitch

🇹🇼 **Ouvoca 是台灣中小製造業的對話式 ERP**：員工坐在電腦前打一句話（「跟長江廠下 100 個 M6 螺絲，交期下週五」），AI 就把它變成完整的採購單，跳出 ConfirmCard 確認卡讓你按確認才執行。**不用學系統、不用教育訓練、2 小時上手**。20 人以內的小公司**完全免費**用整套（含鼎新 / 正航 connector<sup>※</sup>）。

🇺🇸 **Ouvoca is a conversational ERP for Taiwan SMB manufacturers.** Your staff types one sentence ("Order 100 M6 bolts from ChangJiang, delivery next Friday") and the AI turns it into a full purchase order, presenting a ConfirmCard for human approval before executing. **No training required, ready in 2 hours**. **Completely free for organizations with ≤20 concurrent users**, including closed-source connectors for 鼎新 / 正航 / SAP<sup>※</sup>.

> ⚠️ <sup>※</sup> connector 為「**技術連線元件**」，不含原 ERP（如 Workflow / ChengHang / SAP B1 等廠商之產品）的使用授權；各廠商之授權合約規定可能不同，請依貴司與該廠商之合約為準。建議客戶於啟用前先和原 ERP 廠商書面確認授權範圍。Ouvoca **不參與、不代理**此類合約事務；於適用法律所允許之最大範圍內不承擔相關責任。詳見 [`docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md) / [EN](./docs/EXTERNAL_DB_LICENSING_NOTICE_EN.md)。<br>The connector is a **technical connectivity component** and does NOT include the licensing of your incumbent ERP (e.g., products from vendors such as Workflow / ChengHang / SAP B1); each vendor's license terms may differ — please refer to your contract with that vendor. We recommend the customer confirm authorization scope in writing with the incumbent ERP vendor before enabling. Ouvoca **does not participate in or represent the customer in** such contractual matters; to the maximum extent permitted by applicable law, Ouvoca assumes no related liability.

| 為什麼選 Ouvoca? / Why Ouvoca? | 我們的解法 / Our Answer |
|---|---|
| 🇹🇼 SAP / Oracle 太貴 / Too expensive | NT$30-50 万/年（小小企業 ≤20 人 NT$0）|
| 🇹🇼 員工不愛學系統 / No one wants training | 用講的就會用，AI 取代訓練 |
| 🇹🇼 改個欄位要等 IT 顧問 / IT bottleneck | Schema Mapping AI 自助接外部 DB |
| 🇹🇼 老闆要看數字 / Boss wants real-time data | Chat 一句話拿到老闆儀表板 |
| 🇹🇼 怕 AI 亂操作 / AI hallucination fear | ConfirmCard 強制人工確認 + 90 秒 Undo |

---

## 🎯 設計優先順序 / Design Priorities

> **能上線才是王道。**用戶裝不起來，所有功能都等於零。
> **Deployability first.** If the user can't install it, every feature you built is worth zero.

Ouvoca 的設計決策按以下優先順序排（衝突時上位永遠贏）：

| # | 原則 / Principle | 體現 / Embodiment |
|---|------------------|-------------------|
| **1** | **🚀 電腦小白裝得起來** > 工程師方便 | `install_easy.bat` 自動下載 Python/Node — 王董（70 歲）雙擊就裝 |
| **2** | **🛡️ 不掉資料** > 速度 / 美觀 | ConfirmCard 強制確認 + 90 秒 Undo + tenant 自動隔離 |
| **3** | **🗣️ 自然語言** > 表單操作 | 70%+ 操作走 Chat，少數高頻表單保留 |
| **4** | **🎯 解決客戶痛點** > 我們覺得酷的功能 | v3.0 砍 LINE Bot / 行動 App 戰略軸轉 |
| **5** | **➖ 砍功能** > 加功能 | 「mediocre × 3 不如 excellent × 1」|

**為什麼上線優先?**
- 開發 100 個 feature × 0 個用戶上線 = 0 價值
- 開發 10 個 feature × 50 家用戶實際在用 = 巨大價值
- 安裝失敗的客戶不會回頭，**第一印象只有一次**

**這個原則如何影響開發排序：**
新功能進 backlog 前先問 → 「裝這個東西需要先裝什麼？電腦小白裝得起來嗎？」
答不出來就降優先；先把現有的東西的安裝體驗修到「雙擊即可」再加新東西。

---

## 🚀 5 分鐘安裝指南 / 5-Minute Install (for non-developers)

🇹🇼 **不需要 IT 背景、不需要懂程式**。會雙擊滑鼠 + 開瀏覽器就會裝。
🇺🇸 **No IT skills required.** If you can double-click and open a browser, you can install this.

---

### 🌟 推薦：**電腦小白模式**（不需 Docker、不需先裝 Python）

#### 📋 三種路徑的 Python / Node 版本對照

| 路徑 | Python | Node | 你要做什麼 |
|------|--------|------|-----------|
| ✨ `install_easy.bat`（推薦） | **3.11.9（自動下載）** | **20.11.1（自動下載）** | 什麼都不用，雙擊即可 |
| 🐳 `install.bat`（Docker） | 容器內 3.11-slim | 容器內 20-alpine | 先裝 Docker Desktop |
| ⚙️ `start_dev.bat`（工程師） | 3.11.x（手動裝） | 20 LTS（手動裝）| 自己 venv + npm install |

⚠️ **務必使用 Python 3.11**（不是 3.12 也不是 3.13）。requirements.txt 已用 `requires-python = ">=3.11,<3.13"` 鎖定。

**只要會雙擊就會裝**。腳本會自動下載所需的 Python 和 Node.js。

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│    Step 1️⃣ 下載 ZIP                                            │
│    Step 2️⃣ 雙擊 install_easy.bat（Win）or install_easy.sh (Mac) │
│    Step 3️⃣ 等 10-20 分鐘 → 自動開瀏覽器 → 登入 admin/admin123 │
│                                                                │
│    完全不需安裝 Docker、Python、Node。腳本自動下載至 tools\    │
│    刪除整個資料夾即完全解除安裝。                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**首次安裝**：雙擊 `install_easy.bat`（Windows）或執行 `bash install_easy.sh`（Mac/Linux）
**後續啟動**：雙擊 `start.bat` 或 `bash start.sh`

下載大小：Python ~26MB + Node ~30MB + 套件 ~500MB（首次） ≒ **約 750MB 磁碟**，全部在本資料夾內。
網路速度：10 Mbps 約 **10 分鐘** 內裝完。

> ⚠️ **防毒軟體可能誤判** Python silent installer，請暫時停用或將本資料夾加入白名單。
> ⚠️ **Antivirus may flag** the silent Python installer — temporarily disable or whitelist this folder.

#### 📚 重要法律 / 排錯文件 / Important Docs

| 想知道 | 看這份 |
|--------|--------|
| `install_easy` 會下載什麼？合法嗎？ | [`docs/THIRD_PARTY_DOWNLOADS_ZH.md`](./docs/THIRD_PARTY_DOWNLOADS_ZH.md) / [EN](./docs/THIRD_PARTY_DOWNLOADS_EN.md) |
| 裝失敗了，錯誤怎麼解？ | [`docs/INSTALL_TROUBLESHOOTING_ZH.md`](./docs/INSTALL_TROUBLESHOOTING_ZH.md) / [EN](./docs/INSTALL_TROUBLESHOOTING_EN.md) |
| 離線環境怎麼裝？ | [THIRD_PARTY_DOWNLOADS §4](./docs/THIRD_PARTY_DOWNLOADS_ZH.md#4-離線安裝不想連網下載) |

---

### 🛠 進階：Docker 模式（給有 IT 背景的人）

如果你已經會用 Docker，這條路 image 更穩定、隔離性更好：

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│    Step 1️⃣          Step 2️⃣          Step 3️⃣                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                │
│  │ 📥 下載   │ →  │ 🐳 裝     │ →  │ ▶️ 雙擊  │ → http://...   │
│  │ Ouvoca  │    │  Docker   │    │ install  │   localhost    │
│  │  zip 檔  │    │ Desktop   │    │   .bat   │   :5173        │
│  └──────────┘    └──────────┘    └──────────┘                │
│   2 分鐘 / 2min   5-10 分鐘     2-5 分鐘     登入 admin/admin123 │
│                  (一次性 once)                                 │
└────────────────────────────────────────────────────────────────┘
```

### Step 1️⃣ · 下載 Ouvoca / Download Ouvoca（2 分鐘）

🇹🇼 **方法 A（最簡單，不用裝 git）**：
1. 用瀏覽器打開 https://github.com/fanchanyu/ouvoca
2. 點頁面上方綠色按鈕 **[`< > Code`]** → 選 **[Download ZIP]**
3. 把 zip 解壓到任何資料夾（建議 `C:\Ouvoca` 或 `D:\Ouvoca`）

🇺🇸 **Method A (easiest, no git needed)**: Open https://github.com/fanchanyu/ouvoca → click green **[`< > Code`]** button → **[Download ZIP]** → unzip anywhere (e.g. `C:\Ouvoca`).

🇹🇼 方法 B（會用 git）：`git clone https://github.com/fanchanyu/ouvoca`
🇺🇸 Method B (if you have git): `git clone https://github.com/fanchanyu/ouvoca`

### Step 2️⃣ · 安裝 Docker Desktop（一次性，5-10 分鐘）

🇹🇼 **Docker 是什麼？** 就像一個「保護箱」，把 Ouvoca 包起來不影響你電腦其他軟體。
🇺🇸 **What's Docker?** A "container" that bundles Ouvoca so it doesn't mess with your other software.

| 系統 / OS | 下載連結 / Download | 安裝步驟 / Steps |
|---|---|---|
| 🪟 **Windows 10/11** | [Download Docker Desktop](https://www.docker.com/products/docker-desktop/) → 選 `Download for Windows` | 雙擊 `.exe` → 一路按 Next → **重開機** → 雙擊桌面 🐳 圖示 → 等出現 `Engine running` |
| 🍎 **Mac (M1/M2/Intel)** | [Download Docker Desktop](https://www.docker.com/products/docker-desktop/) → 選對應晶片版本 | 雙擊 `.dmg` → 拖 Docker 到 Applications → 啟動 → 按「允許」權限 |
| 🐧 **Linux** | 命令列 / Terminal | `curl -fsSL https://get.docker.com \| sudo sh && sudo usermod -aG docker $USER` → 登出再登入 |

🇹🇼 ⚠️ Windows 10 家庭版需要先在「Windows 功能」啟用 WSL2，Docker 安裝精靈會提示你。
🇺🇸 ⚠️ Windows 10 Home requires WSL2 (Docker installer will prompt you).

### Step 3️⃣ · 跑 install 腳本 / Run installer（2-5 分鐘）

| 系統 / OS | 怎麼跑 / How to run |
|---|---|
| 🪟 Windows | 在你解壓的資料夾裡 **雙擊 `install.bat`** |
| 🍎 Mac | 在 Terminal 跑：`cd ~/ouvoca && ./install.sh` |
| 🐧 Linux | 同 Mac |

🇹🇼 你會看到視窗自動跑這 5 步：
🇺🇸 The script will automatically run these 5 steps:

```
[Step 1/5] 檢查 Docker / Checking Docker..............OK ✓
[Step 2/5] 設定環境變數（自動產生 JWT_SECRET）..........OK ✓
[Step 3/5] 啟動服務（首次需 2-5 分鐘下載 image）.........OK ✓
[Step 4/5] 等後端就緒.....................................OK ✓ (15s)
[Step 5/5] 載入示範資料（5 客戶 / 3 供應商 / 10 料件）...OK ✓

           ============================================
                     安裝完成 / Installation Done
           ============================================

           請打開瀏覽器訪問 / Open your browser:
              http://localhost:5173

           登入 / Login:
              帳號 / Username:  admin
              密碼 / Password:  admin123

           *** 重要 / IMPORTANT (v3.37) ***
           登入後請立即在 Chat 講「改密碼」更換預設密碼
           After login, say "change password" in Chat immediately
```

🇹🇼 **完成！** 瀏覽器會自動打開登入畫面。輸入 `admin` / `admin123` 進去。
🇺🇸 **Done!** Browser will auto-open the login page. Use `admin` / `admin123`.

### 🎯 第一次進去做這 4 件事（v3.37 — 全用「講的」即可）/ First-Login Checklist

> ⚠️ **電腦小白也會做** — 不用點選單、不用學系統，全部對 AI 打字就好。
> Beginners-friendly — just type to the AI; no menus, no training needed.

```
1️⃣ 立即改密碼（資安基本盤）
    在 AI 助手講：「改密碼，我的新密碼是 MyN3wP@ss」
    → AI 出 ConfirmCard → 點確認 → 下次用新密碼登入

2️⃣ 設定公司資料（PDF 上要印的）
    講：「公司叫 長江精密股份有限公司 統編 12345678 地址 台北市信義區...」
    → AI 出 ConfirmCard → 點確認 → 之後所有 PDF 都印你公司名

3️⃣ 載入示範資料（要不要玩玩看？）
    講：「載入示範資料」
    → 3 客戶 + 3 供應商 + 5 料件，可以開始玩

4️⃣ 試講一句業務
    講：「印 SO-001」「匯出客戶清單 Excel」「今天有什麼要注意的？」
    → AI 自動產 PDF / Excel，瀏覽器直接彈出下載
```

🇺🇸 **First 4 things to do (v3.37 — all conversational)**:

```
1️⃣ Change password immediately:
    Tell AI: "change password to MyN3wP@ss"
2️⃣ Set company info (printed on PDFs):
    Tell AI: "company name is Acme Inc., tax id 12345678"
3️⃣ Load demo data (optional):
    Tell AI: "load demo data"
4️⃣ Try a business action:
    Tell AI: "print SO-001" / "export customer list" / "what should I watch today?"
```

### 後續想做的事

| 我想... / I want to... | 怎麼做 / How |
|---|---|
| 啟動 AI 對話功能 / Enable AI chat | 登入 → ⚙️ 設定 → 🤖 AI 助手設定 → 貼 API Key + 測試 + 儲存（**即時生效不需重啟**）。詳見 [`HOW_TO_GET_LLM_API_KEY_ZH.md`](./docs/HOW_TO_GET_LLM_API_KEY_ZH.md)（含 3 個 provider 比較 + 5 分鐘申請步驟） |
| 上傳我的舊報價單 / 發票 PDF | 登入 → ⚙️ 設定 → 📁 上傳業務文件 → 拖檔案進去 |
| 清掉示範資料 / Clear demo data | 登入 → ⚙️ 設定 → 📦 示範資料 → 🗑 清除 |
| 停止 Ouvoca / Stop | `docker compose down`（在解壓目錄裡）或關掉 Docker Desktop |
| 完全移除 / Uninstall | `docker compose down -v` → 刪 Ouvoca 資料夾 |
| 連現有鼎新 / 正航 DB | 看 [`docs/EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md`](./docs/EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md)<br>⚠️ **建議閱讀**：[`docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md) — 商用 ERP 之授權條款依各廠商而異，建議客戶於啟用前先和原 ERP 廠商書面確認授權範圍；Ouvoca 不參與此類合約事務 |

📘 **更詳細的「給老闆看的版本」（純圖文、零技術術語）**：
- 中文 → [`docs/INSTALLATION_ZH.md`](./docs/INSTALLATION_ZH.md)
- English → [`docs/INSTALLATION_EN.md`](./docs/INSTALLATION_EN.md)
- 或直接下載 PDF → [`📕 01_安裝指南_中文.pdf`](./docs/pdf/01_安裝指南_中文.pdf)

---

## ❓ 安裝常見問題 / Install FAQ

🇹🇼 安裝前先看這 13 題能省 90% 麻煩。
🇺🇸 Reading these 13 questions before installing saves 90% of headaches.

<details>
<summary><strong>Q1. 我的電腦跑得動嗎？/ Will my computer run this?</strong></summary>

| 項目 | 最低 / Min | 建議 / Recommended |
|---|---|---|
| 作業系統 | Win 10 / macOS 11 / Ubuntu 20 | Win 11 / macOS 13 |
| RAM | 4 GB | 8 GB+ |
| 硬碟空間 | 5 GB | 20 GB+（含 Docker images）|
| CPU | 任何 x86_64 / ARM64 | 4 核以上 |
| GPU | ❌ 不需要 | ❌ 不需要（LLM 用雲端 API）|
| 網路 | 安裝時需要 | 日常使用**不需要**（除非開 AI 對話）|

</details>

<details>
<summary><strong>Q2. install.bat 提示「找不到 Docker」/ "Docker not found"</strong></summary>

你還沒裝 Docker Desktop。回 Step 2️⃣ 完成安裝、**重開機**、桌面看到 🐳 圖示再來。

如果裝了 Docker 但還是這個錯：開 Docker Desktop（雙擊桌面 🐳）→ 等左下角出現 `Engine running` 綠燈 → 再跑 install.bat。

</details>

<details>
<summary><strong>Q3. install.bat 卡在「啟動服務」很久 / Stuck at "Starting services"</strong></summary>

首次下載 Docker images（~2 GB）需要 2-5 分鐘，**請耐心等**。
網速慢可能要 10-20 分鐘。

確認方法：另開一個 terminal/cmd 跑 `docker ps`，看到 ouvoca-backend / ouvoca-frontend 在 Up 狀態 = 進度正常。

</details>

<details>
<summary><strong>Q4. 瀏覽器打開只看到「Cannot connect / 無法連線」</strong></summary>

最常見：等服務完全啟動需要 1-2 分鐘，**等一下再重新整理 (F5)**。

還不行的話：
1. 確認 install.bat 沒報錯（看到「安裝完成」）
2. `docker compose ps` 看服務狀態都是 `Up`
3. `docker compose logs backend` 看後端錯誤訊息
4. 試試 http://127.0.0.1:5173（換 localhost）

</details>

<details>
<summary><strong>Q5. 提示「Port 5173 / 8000 被占用」/ "Port in use"</strong></summary>

你的電腦已經有其他程式用了同樣的 port（最常見是 Vite dev server 或別的 web 服務）。

**最簡單**：重開機，再跑 install.bat。

**進階**：
- Windows: `netstat -ano | findstr :5173` 找到 PID → 用工作管理員關掉
- Mac/Linux: `lsof -i :5173` 找到 PID → `kill -9 <PID>`

</details>

<details>
<summary><strong>Q6. Windows Defender / 防毒軟體擋住了 install.bat</strong></summary>

第一次跑批次檔常見現象。Ouvoca 是開源 (AGPL-3.0)，可以在 GitHub 完整檢視程式碼。

按「**更多資訊 → 仍要執行 (Run anyway)**」就好。

不放心可以先閱讀 `install.bat` 的內容（用記事本打開）— 只做 5 件事：檢查 Docker、設定 .env、跑 docker compose、等就緒、執行 seed。

</details>

<details>
<summary><strong>Q7. 預設帳號 admin / admin123 安全嗎？要改嗎？</strong></summary>

**內部使用**（公司內網、沒對外開放）：可以不改，方便試用。

**對外發行**（exposed to internet 或多人共用）：**一定要改！**

改密碼方法：
1. 登入 → 點右上角頭像 → 「我的權限」
2. 點「修改密碼」（功能待補，下個 sprint）
3. 暫時方法：`docker compose exec backend python -m scripts.create_admin <newuser> <newpass>`

對外發行時也要把 `backend/.env` 的 `JWT_SECRET` 換成 64 字元亂數（install.bat 已經自動產生過了）。

</details>

<details>
<summary><strong>Q8. 我可以匯入舊的 Excel / 報價單 / 鼎新 DB 嗎？</strong></summary>

**3 種匯入方式**：

| 方式 | 場景 | 怎麼做 |
|---|---|---|
| 📁 直接上傳 | 報價單 / 發票 / 合約 / 規格書 PDF | 登入 → ⚙️ 設定 → 上傳業務文件 → 拖檔案 → 選分類 |
| 📊 Excel CSV 匯入 | 你的料件清單、客戶清單 | 用 Schema Mapping AI 接 connector（自動對欄位）|
| 🔗 直連現有 ERP | 鼎新 / 正航 / SAP 主檔 | 設定 connector，AI 自動 mapping 欄位（見 [外部 DB 串接指南](./docs/EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md)）|

**🌱 小小企業軌（≤20 人）免費含閉源 connector！**

> ⚠️ **直連現有商用 ERP 前的合規提醒**：商用 ERP（例如 Workflow / ChengHang / SAP B1 / Vitals 等）之授權合約對「以共用 / 服務帳號連線」之規定可能不同；具體請依貴司與該廠商之合約為準。建議客戶於啟用前先和原 ERP 廠商書面確認授權範圍，必要時購買相應之整合授權。Ouvoca **不參與、不代理**與第三方 ERP 廠商之合約 / 授權事務；於適用法律所允許之最大範圍內不承擔相關責任。完整提醒：[`docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md) / [EN](./docs/EXTERNAL_DB_LICENSING_NOTICE_EN.md)。

</details>

<details>
<summary><strong>Q9. 我的資料安全嗎？會不會傳到雲端？</strong></summary>

**完全本地**，除非你自己開啟 AI 對話：

| 項目 | 在哪 | 會傳出去嗎？ |
|---|---|---|
| 業務資料（料件、訂單、庫存）| 你的電腦 `backend/erp.db`（SQLite）或你設的 PostgreSQL | ❌ 永不離開你的電腦 |
| 上傳的檔案（報價單、發票）| 你的電腦 `backend/uploads/` | ❌ 永不離開 |
| **AI 對話**（如果你開啟） | 只有「**你打的問題文字**」會傳給 LLM 供應商（DeepSeek / OpenAI 等）| ⚠️ **問題文字**會出去，但 DB 資料不會 |

如果連 LLM 都不想連網 → 用本地 Ollama（離線模式，見 docs）。

</details>

<details>
<summary><strong>Q10. 一定要連網嗎？/ Do I need internet?</strong></summary>

| 階段 | 需要網路嗎？ |
|---|---|
| 第一次安裝（下載 Docker images） | ✅ 需要 |
| 日常使用（CRUD、查報表） | ❌ 不需要 |
| AI 對話（如果有開啟）| ⚠️ 需要（除非用 Ollama 離線 LLM） |
| 更新到新版 | ✅ 需要 |

</details>

<details>
<summary><strong>Q11. 我忘了密碼怎麼辦？/ Forgot password?</strong></summary>

```bash
docker compose exec backend python -c "
import asyncio
from app.database import async_session
from app.models.organization import User
from app.core.security import hash_password
from sqlalchemy import select

async def reset():
    async with async_session() as db:
        u = (await db.execute(select(User).where(User.username=='admin'))).scalar_one()
        u.password_hash = hash_password('newpass123')
        await db.commit()
        print('✓ admin 密碼已重設為 newpass123')

asyncio.run(reset())
"
```

（一個更友善的 reset_password.bat 待下個 sprint 補）

</details>

<details>
<summary><strong>Q12. 小小企業免費門檻怎麼算？/ How is the ≤20 free tier counted?</strong></summary>

看 **同時在線使用者數**（24 小時內任一時刻的峰值，15 分鐘 idle 算下線）。

舉例：
- 公司 50 人有 Ouvoca 帳號，但同時在線最多 18 人 → ✅ 適格（白用）
- 公司 25 人，同時在線常 22 人 → ❌ 不適格（需商業授權）
- 公司 100 人但只 5 個業務在用 → ✅ 適格

完整條款：[`LICENSE-SMALL-BUSINESS.md`](./LICENSE-SMALL-BUSINESS.md)

</details>

<details>
<summary><strong>Q13. 升級到新版怎麼弄？/ How to upgrade?</strong></summary>

```bash
cd Ouvoca
git pull origin main          # 或重下載 ZIP 覆蓋
docker compose down
docker compose up -d --build  # 重 build 新版
docker compose exec backend alembic upgrade head  # 跑 DB migration（如果有）
```

你的資料（DB + uploads/）會**完整保留**。

</details>

### Q14. 我電腦已有其他版本的 Python（3.12 / 3.13）/ 沒裝 Python，會衝突嗎？

**完全不會。** `install_easy.bat` 會把 Python 3.11.9 安裝到專案內的 `tools\python\` 資料夾，**不修改你系統的 PATH、不污染你現有的 Python**。

- 如果你系統有 Python 3.12 / 3.13 → 它們繼續存在，`install_easy` 用自己的 3.11
- 如果你系統沒 Python → `install_easy` 直接下載 3.11.9 silent install 進 `tools\python\`
- 卸載：刪除整個專案資料夾即可，沒有任何系統設定被改

`start.bat` 啟動時會**優先**使用 `tools\python\` 的 Python，而不是系統的。

⚠️ **還沒解的問題？** 開 [GitHub Issue](https://github.com/fanchanyu/ouvoca/issues/new) 我們處理。

---

## 📚 76 份雙語客戶文件 / 76 Bilingual Customer PDFs

🇹🇼 點下面任一個直接下載 PDF（全部繁中 + English）：
🇺🇸 Click any to download (all bilingual ZH + EN):

| # | 文件 / Document | 🇹🇼 中文 | 🇺🇸 English |
|---|---|---|---|
| 00 | 產品說明書 / Product Overview | [📕 中文 PDF](./docs/pdf/00_產品說明書_中文.pdf) | [📘 EN PDF](./docs/pdf/00_Product_Overview_EN.pdf) |
| 01 | 安裝指南 / Installation Guide | [📕 中文 PDF](./docs/pdf/01_安裝指南_中文.pdf) | [📘 EN PDF](./docs/pdf/01_Installation_Guide_EN.pdf) |
| 02 | 快速入門 / Quick Start | [📕 雙語 PDF（單檔）](./docs/pdf/02_快速入門_Quick_Start.pdf) | (內含 EN 段落) |
| 03 | 使用者操作手冊 / User Manual | [📕 中文 PDF](./docs/pdf/03_使用者操作手冊_中文.pdf) | [📘 EN PDF](./docs/pdf/03_User_Manual_EN.pdf) |
| 05 | 網路部署規劃 / Network Deployment | [📕 中文 PDF](./docs/pdf/05_網路部署規劃_中文.pdf) | [📘 EN PDF](./docs/pdf/05_Network_Deployment_EN.pdf) |
| 06 | 系統架構流程拓樸 / System Architecture | [📕 中文 PDF](./docs/pdf/06_系統架構流程拓樸_中文.pdf) | [📘 EN PDF](./docs/pdf/06_System_Architecture_Topology_EN.pdf) |
| 07 | LLM 評比報告 / LLM Benchmark Report | [📕 中文 PDF](./docs/pdf/07_LLM評比報告_中文.pdf) | [📘 EN PDF](./docs/pdf/07_LLM_Benchmark_Report_EN.pdf) |
| 08 | AI 助手目錄 / AI Agent Catalog | [📕 中文 PDF](./docs/pdf/08_AI助手目錄_中文.pdf) | [📘 EN PDF](./docs/pdf/08_AI_Agent_Catalog_EN.pdf) |
| 09 | 台灣合規對照表 / Taiwan Compliance | [📕 中文 PDF](./docs/pdf/09_台灣合規對照表_中文.pdf) | [📘 EN PDF](./docs/pdf/09_Taiwan_Compliance_EN.pdf) |
| 10 | 導入實施手冊 / Implementation Playbook | [📕 中文 PDF](./docs/pdf/10_導入實施手冊_中文.pdf) | [📘 EN PDF](./docs/pdf/10_Implementation_Playbook_EN.pdf) |
| 11 | 支援運維手冊 / Support Runbook | [📕 中文 PDF](./docs/pdf/11_支援運維手冊_中文.pdf) | [📘 EN PDF](./docs/pdf/11_Support_Runbook_EN.pdf) |
| 12 | 備份還原 SOP / Backup & Restore | [📕 中文 PDF](./docs/pdf/12_備份還原SOP_中文.pdf) | [📘 EN PDF](./docs/pdf/12_Backup_Restore_SOP_EN.pdf) |
| 13 | 系統架構藍圖 / Architecture Blueprint | [📕 中文 PDF](./docs/pdf/13_系統架構藍圖_中文.pdf) | [📘 EN PDF](./docs/pdf/13_Architecture_Blueprint_EN.pdf) |
| 14 | Secrets 輪換 SOP / Secrets Rotation | [📕 中文 PDF](./docs/pdf/14_Secrets輪換SOP_中文.pdf) | [📘 EN PDF](./docs/pdf/14_Secrets_Rotation_SOP_EN.pdf) |
| 15 | 對話式 ERP 架構 / Conversational ERP | [📕 中文 PDF](./docs/pdf/15_對話式ERP架構_中文.pdf) | [📘 EN PDF](./docs/pdf/15_Conversational_ERP_Architecture_EN.pdf) |
| 16 | Phase 1 實作 Spec | [📕 中文 PDF](./docs/pdf/16_Phase1_實作Spec_中文.pdf) | [📘 EN PDF](./docs/pdf/16_Phase1_Implementation_Spec_EN.pdf) |
| 17 | 外部 DB 串接設計 / External DB Integration | [📕 中文 PDF](./docs/pdf/17_外部DB串接設計_中文.pdf) | [📘 EN PDF](./docs/pdf/17_External_DB_Integration_Design_EN.pdf) |
| 18 | 業務 demo 一頁紙 / Sales Killer Moments | [📕 中文 PDF](./docs/pdf/18_業務demo一頁紙_中文.pdf) | [📘 EN PDF](./docs/pdf/18_Sales_Killer_Moments_EN.pdf) |
| 19 | LLM API Key 申請指南（小白版）/ How to Get LLM API Key | [📕 中文 PDF](./docs/pdf/19_LLM_API_Key申請指南_中文.pdf) | [📘 EN PDF](./docs/pdf/19_How_to_Get_LLM_API_Key_EN.pdf) |
| **20** | 🏛️ **家規完整使用指南** ⭐招牌 / **House Rules — Complete Guide** | [📕 **中文 PDF**](./docs/pdf/20_家規完整使用指南_中文.pdf) | [📘 **EN PDF**](./docs/pdf/20_House_Rules_Guide_EN.pdf) |
| 21 | 商業授權 FAQ（含 ≤20 人免費條款） | [📕 中文 PDF](./docs/pdf/21_商業授權FAQ_中文.pdf) | — |
| **22** | ⚠️ **第三方 ERP 授權合規提醒**（接舊系統前建議閱讀）/ **External ERP Licensing Compliance Reminder** | [📕 **中文 PDF**](./docs/pdf/22_第三方ERP授權合規通知_中文.pdf) | [📘 **EN PDF**](./docs/pdf/22_External_ERP_Licensing_Notice_EN.pdf) |
| **23** | 📐 **MRP-II 演算法設計（學術論文）** ⭐ Orlicky + Wagner-Whitin + Silver-Meal / **Multi-Echelon Time-Phased MRP-II Design** | [📕 **中文 PDF**](./docs/pdf/23_MRP演算法設計_中文.pdf) | [📘 **EN PDF**](./docs/pdf/23_MRP_Algorithm_Design_EN.pdf) |
| **24** | 🏭 **產能感知 MRP 設計（學術論文）** ⭐ Dixon-Silver CLSP heuristic + Routing / **Capacity-Aware MRP** | [📕 **中文 PDF**](./docs/pdf/24_產能感知MRP設計_中文.pdf) | [📘 **EN PDF**](./docs/pdf/24_Capacity_Aware_MRP_Design_EN.pdf) |
| **25** | 🔍 **可解釋規劃 + TOC 瓶頸（學術論文）** ⭐ Goldratt + Cheney + Saltelli — IE/Algo/ERP/AI 四域交集 / **Explainable Planning** | [📕 **中文 PDF**](./docs/pdf/25_可解釋規劃與TOC瓶頸_中文.pdf) | [📘 **EN PDF**](./docs/pdf/25_Explainable_Planning_TOC_EN.pdf) |
| **26** | 💰 **Throughput Accounting + 訂單接受決策（學術論文）** ⭐ 完成 Goldratt TOC 三部曲 — 「該不該接這張單？」最佳解 / **TA + DBR + Order Acceptance** | [📕 **中文 PDF**](./docs/pdf/26_Throughput會計與訂單決策_中文.pdf) | [📘 **EN PDF**](./docs/pdf/26_Throughput_Accounting_DBR_EN.pdf) |
| **27** | 📈 **AI 增強需求預測（學術論文）** ⭐ Hyndman + Croston + Makridakis M4/M5 — 自動 MPS 上游補完 / **Demand Forecasting** | [📕 **中文 PDF**](./docs/pdf/27_需求預測引擎_中文.pdf) | [📘 **EN PDF**](./docs/pdf/27_Demand_Forecasting_EN.pdf) |
| **28** | 🤖 **對話式規劃顧問** ⭐⭐ 把 v3.25.9-v3.29 全部演算法包成 LLM tools + Daily Briefing — Ouvoca 北極星補完 / **Conversational Planning Agent** | [📕 **中文 PDF**](./docs/pdf/28_對話式規劃顧問_中文.pdf) | [📘 **EN PDF**](./docs/pdf/28_Conversational_Planning_EN.pdf) |
| **29** | ⚖️ **進銷存模組法律聲明**（v3.32/v3.33）/ **Inventory/Sales Module Legal Notice** | [📕 **中文 PDF**](./docs/pdf/29_進銷存法律聲明_中文.pdf) | [📘 **EN PDF**](./docs/pdf/29_Inventory_Sales_Legal_EN.pdf) |
| **30** | ⚖️ **稅務/會計/審批模組法律與合規警告**（v3.34）/ **Tax/Accounting/Approval Compliance Notice** | [📕 **中文 PDF**](./docs/pdf/30_稅務會計法律聲明_中文.pdf) | [📘 **EN PDF**](./docs/pdf/30_Tax_Accounting_Legal_EN.pdf) |
| **31** | ⚖️ **列印/匯出模組法律與合規警告**（v3.36）/ **Print/Export Compliance Notice** | [📕 **中文 PDF**](./docs/pdf/31_列印匯出法律聲明_中文.pdf) | [📘 **EN PDF**](./docs/pdf/31_Print_Export_Legal_EN.pdf) |
| **32** | ⚖️ **安裝精靈 / Day 0-7 卡關修補法律聲明**（v3.37）/ **Setup Wizard & Beginner-Fix Notice** | [📕 **中文 PDF**](./docs/pdf/32_安裝精靈法律聲明_中文.pdf) | [📘 **EN PDF**](./docs/pdf/32_Setup_Wizard_Legal_EN.pdf) |
| **33** | ⚖️ **第二輪小白卡關修補法律聲明**（v3.38 — TTL / Undo / 備份 / AI 成本）/ **Second-Round Beginner-Fix Notice** | [📕 **中文 PDF**](./docs/pdf/33_第二輪卡關修補法律聲明_中文.pdf) | [📘 **EN PDF**](./docs/pdf/33_Polish_Legal_EN.pdf) |
| **34** | ⚖️ **第三輪小白卡關修補法律聲明**（v3.39 — LOGO / 刪除 / 批次 / 分頁）/ **Third-Round Beginner-Fix Notice** | [📕 **中文 PDF**](./docs/pdf/34_第三輪卡關修補法律聲明_中文.pdf) | [📘 **EN PDF**](./docs/pdf/34_Polish_V339_Legal_EN.pdf) |
| **35** | ⚖️ **第四輪小白卡關修補法律聲明 — 高敏感**（v3.40 — 凍結 hard-write / Delete Undo / 跨人 Audit / 應收帳齡）/ **Fourth-Round Beginner-Fix Notice — HIGH SENSITIVITY** | [📕 **中文 PDF**](./docs/pdf/35_第四輪卡關修補法律聲明_中文.pdf) | [📘 **EN PDF**](./docs/pdf/35_Polish_V340_Legal_EN.pdf) |
| **36** | ⚖️ **第五輪小白卡關修補法律聲明 — 對外最敏感**（v3.41 — 寄 PDF Email / 客戶毛利率 / 訂單跟單）/ **Fifth-Round Beginner-Fix Notice — OUTBOUND-SENSITIVE** | [📕 **中文 PDF**](./docs/pdf/36_第五輪卡關修補法律聲明_中文.pdf) | [📘 **EN PDF**](./docs/pdf/36_Polish_V341_Legal_EN.pdf) |
| **37** | ⚖️ **第六輪小白卡關修補法律聲明 — 帳號管理最敏感**（v3.42 — 使用者帳號 / 全域搜尋 / AI 每日限額 / 工作天 / 時區）/ **Sixth-Round Beginner-Fix Notice — ACCOUNT-MGMT-SENSITIVE** | [📕 **中文 PDF**](./docs/pdf/37_第六輪卡關修補法律聲明_中文.pdf) | [📘 **EN PDF**](./docs/pdf/37_Polish_V342_Legal_EN.pdf) |
| **38** | ⚖️ **Ouvoca 商標合規 / Trademark Compliance** | [📕 **中文 PDF**](./docs/pdf/38_重命名公告_中文.pdf) | [📘 **EN PDF**](./docs/pdf/38_Rename_Notice_EN.pdf) |

📌 **特別文件**：
- [**`HOW_TO_GET_LLM_API_KEY_ZH.md`**](./docs/HOW_TO_GET_LLM_API_KEY_ZH.md) · [EN](./docs/HOW_TO_GET_LLM_API_KEY_EN.md) — 5-10 分鐘申請 API Key 完整教學（DeepSeek/OpenAI/Anthropic/Ollama 比較）
- [**`HOUSE_RULES_GUIDE_ZH.md`**](./docs/HOUSE_RULES_GUIDE_ZH.md) · [EN](./docs/HOUSE_RULES_GUIDE_EN.md) — ⭐ Ouvoca 招牌差異化「家規」完整指南
- ⚠️ [**`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`**](./docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md) · [EN](./docs/EXTERNAL_DB_LICENSING_NOTICE_EN.md) — **接舊 ERP 前建議閱讀**：第三方 ERP 授權合規提醒（商用 ERP 之授權條款依各廠商而異；本文件非法律意見）

🇹🇼 **電腦小白優先讀**：00（產品說明書）→ 01（安裝指南）→ 02（快速入門）→ 03（使用者操作手冊）
🇺🇸 **Beginners read first**: 00 → 01 → 02 → 03

📦 全部 PDF 在 [`docs/pdf/`](./docs/pdf/) 目錄。要全部下載？clone repo 或 [download ZIP](https://github.com/fanchanyu/ouvoca/archive/refs/heads/main.zip)。

---

## 🎯 內含什麼 / What's Inside

| 模組 / Module | 中文 | English |
|---|---|---|
| **FastAPI backend** | 12 個業務領域（庫存/採購/生產/MPS/MRP/品質/銷售/會計/倉儲/CRM/HR/AI 治理）| 12 business domains (Inventory, Purchase, Production, MPS/MRP, Quality, Sales, Accounting, Warehouse, CRM, HR, AI Governance) |
| **Multi-Agent LLM Engine** | 10 agents、**40 tools**（22 read / 4 soft-write / 14 hard-write），DeepSeek 為預設供應商 | 10 agents, **40 tools** (22 read / 4 soft-write / 14 hard-write), DeepSeek as default LLM provider |
| **ConfirmCard 確認卡** | hard-write 操作出卡，使用者點「確認」才執行（5 分鐘 TTL + Slot-filling 反問 + 90 秒 Undo）| Hard-write actions issue confirmation cards; user must click "confirm" to execute (5-min TTL + slot-filling reverse-ask + 90s undo) |
| **💡 AskAI 浮球**（Ouvoca 獨家 v3.16）| 每頁右下角的「現場 AI 教練」，問「這頁怎麼用」AI 直接答（取代別家的 onboarding tour / help bubble） | "Live AI coach" on every page — ask "how do I use this page?" and AI answers (replaces traditional tours / tooltips) |
| **🤖 Auto CrmEvent**（Ouvoca 獨家 v3.16）| 訂單成立 / Lead 轉換 / 商機推進時自動產 CrmEvent 進 Customer timeline（業務不必手動加 activity log）| Orders / lead conversions / opportunity stage changes auto-create CRM events (no manual activity logging) |
| **🤝 CRM 完整 UI**（v3.15）| Lead 漏斗 / 商機 Kanban / Customer 360 三 tab | Lead pipeline / Opportunity Kanban / Customer 360 (3 tabs) |
| **⚙️ Settings 頁**（v3.13）| 自助 AI key 設定（測試 + 即時生效）/ 載入清除示範資料 / 檔案上傳 drag-and-drop | Self-service AI key setup (test + live apply) / demo data / file upload drag-and-drop |
| **📒 會計 + 🧾 電子發票**（v3.18-19）| 傳票 / AR / 科目表 / 台灣 MIG 標準電子發票開立查詢作廢 | Journals / AR / Chart of Accounts / Taiwan MIG e-invoice issue/lookup/void |
| **📈 報表中心**（v3.19）| KPI 即時（DSO/週轉/毛利率）+ AR aging xlsx + 月度庫存 xlsx + 401 報表 HTML | Live KPI + AR aging xlsx + monthly inventory xlsx + Taiwan 401 tax HTML |
| **🌍 多國統編驗證**（v3.20）| 6 國內建（TW/CN/US/JP/EU+GENERIC）+ `register_validator()` 客戶可 plug-in 任何國家 | 6 built-in (TW/CN/US/JP/EU+GENERIC) + plug-in for any country |
| **🔍 Cmd+K 全系統搜尋**（v3.21）| 8 種 entity + 10 快速命令，鍵盤導航（SAP B1 / Linear / Notion / Raycast 風） | Fuzzy search 8 entities + 10 quick commands; SAP/Linear-style |
| **🖨 單據列印 PDF**（v3.21）| PO / SO / 出貨單 / 發票 一鍵印給供應商 / 客戶（標準台頭 + 簽章區）| PO / SO / Delivery Note / Invoice one-click PDF (standard header + signature blocks) |
| **✅ 多階審批工作流**（v3.22）| 規則設定 + 待我審 + 歷史，EventBus 自動觸發（鼎新 / SAP 招牌功能）| Rules + pending / history; auto-trigger via EventBus (鼎新/SAP signature feature) |
| **📊 流程鏈視覺化**（v3.22）| 每張 PO/SO/WO 點 📊 看流程鏈狀態（SAP B1 Process Flow Chart 風）| Each PO/SO/WO has 📊 showing chain status (SAP B1 Process Flow style) |
| **📝 單據備註**（v3.22）| 每張 PO/SO/WO 可留 internal remarks（不會印給客戶）| Internal remarks on every PO/SO/WO (not printed to customer) |
| **📋 Dashboard 待辦中心**（v3.23）| 登入第一眼看「待我審 / 缺貨 / 草稿 PO / 草稿 WO」+ 點即跳轉（鼎新 / SAP Cockpit 風）| Personalized Todo Center on dashboard (鼎新/SAP Cockpit style) |
| **🧬 BOM 物料表編輯器**（v3.23）| Production 加「管理 BOM」按鈕，視覺化編輯 + unblock WO release | Visual BOM editor — unblocks WO release |
| **📜 庫存異動歷史**（v3.23）| Inventory 加 tab，列每筆 inbound/outbound/工單完工/盤點調整 | New tab on Inventory listing every txn (inbound/outbound/WO complete/adjust) |
| **🎨 Ouvoca 原創語彙**（v3.24）| 🌱 新苗 (Sprout) = Lead / 🎯 追單 (Chase) = Opportunity / 📖 做法 (Recipe) = BOM — 不抄鼎新/Salesforce，給小白好記 | 🌱 Sprout = Lead / 🎯 Chase = Opportunity / 📖 Recipe = BOM — original vocabulary, memorable for beginners |
| **🏛️ 家規 (House Rules) 引擎**（v3.25 Ouvoca 原創）| 規則資料化（trigger / condition / action / override）不寫死 code；客戶可 UI 開關 / LLM 對話建；4 內建 condition + plugin 機制；WO release「需做法」已從寫死改用引擎 | Data-driven rule engine (vs SAP/Odoo hardcoded). Toggle/edit via UI; LLM can author rules. WO-release-needs-recipe rule migrated to engine |
| **Schema Mapping AI** | exact/alias/partial 3 級 confidence，把外部 DB（鼎新/正航/Excel）一鍵接進來 | 3-tier confidence mapping (exact/alias/partial) — one-click external DB integration (鼎新/正航/Excel) |
| **Event Engine** | EventBus + 16+ ConstraintChecker 規則 + SSE 廣播 | EventBus + 16+ ConstraintChecker rules + SSE broadcasting |
| **React + Vite + Tailwind** | 桌機前端，完整 CRUD UI（EntityRowActions + EntityFormModal）| Desktop frontend with full CRUD UI (reusable EntityRowActions + EntityFormModal components) |
| **War-room dashboard** | HTML + SSE 即時事件儀表板 | HTML + SSE live event dashboard |
| **MESH factory nodes** | VMI 友善：原始資料不離廠 | VMI-friendly: raw data never leaves the factory |
| **5-layer RBAC** | 多租戶隔離（TenantMixin + with_loader_criteria 自動過濾）| Multi-tenant isolation (TenantMixin + auto-filter via with_loader_criteria) |
| **7-gate Self-Verification** | ~290s 全綠才能 commit / push | ~290s suite, must be green before commit/push |
| **Pre-commit secret-scan** | sk-/ghp_/xoxb-/JWT_SECRET 模式自動攔截 | Auto-blocks commits with sk-/ghp_/xoxb-/JWT_SECRET patterns |
| **Docker Compose + Alembic** | 健康檢查 + async migration + seed 腳本 | Health checks + async migrations + seed script |

---

## 🏗 架構 / Architecture

```
┌──────────────────┐  ┌─────────────┐
│  Desktop UI      │  │  War Room   │
│  (Vite/React +   │  │  (HTML+SSE) │
│   Chat + Confirm)│  │             │
└──────┬───────────┘  └──────┬──────┘
       │                     │
       └─────────────────────┘
                         │ HTTPS + Bearer JWT
              ┌──────────▼───────────┐
              │   FastAPI Backend     │
              │ ┌───────────────────┐ │
              │ │  Auth/Audit MW    │ │
              │ │  Exception MW     │ │
              │ └─────────┬─────────┘ │
              │           │           │
              │  ┌────────▼────────┐  │
              │  │ 12 Domain APIs  │  │
              │  │ + Multi-Agent   │  │
              │  │ + Event Engine  │  │
              │  │ + SSE stream    │  │
              │  └────────┬────────┘  │
              │           │           │
              │  SQLAlchemy Async + Alembic │
              │  SQLite(dev) / Postgres(prod)│
              └──────────┬───────────┘
                         │ VPN / structured queries
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
  Factory A          Factory B         Factory C
  (FastAPI:8001)    (FastAPI:8002)    (FastAPI:8003)
  Local DB / LLM    Local DB / LLM    Local DB / LLM
  ★ 原始資料不離廠 / Raw data stays local; only aggregates returned (VMI-friendly)
```

🇹🇼 **VMI 友善設計**：每個工廠跑自己的本地 Ouvoca 節點（factory_node.py），中央只拿聚合資料、不直接存取原始細目，符合代工廠對「客戶資料保密」的硬性要求。
🇺🇸 **VMI-friendly design**: Each factory runs its own local Ouvoca node (factory_node.py); the central instance only receives aggregates, never raw details — meeting the strict data confidentiality requirements of contract manufacturers.

---

## 🗺 領域對照 / Domain Map

| 領域 / Domain   | API 路徑 / Prefix    | 模型 / Models                       | Agent           |
|-----------------|----------------------|-------------------------------------|-----------------|
| Auth & Org      | `/api/auth`, `/api/organization` | Department, Employee, User, Role | (none)          |
| Inventory 庫存   | `/api/inventory`     | Part, Inventory, InventoryTransaction | InventoryAgent |
| Purchase 採購    | `/api/purchase`      | Supplier, PurchaseOrder, POItem     | PurchaseAgent   |
| Production 生產  | `/api/production`    | Product, BOMItem, ProductionOrder, Operation | ProductionAgent |
| MPS / MRP       | `/api/mps-mrp`       | MpsMaster, MpsEntry, MrpMaster, MrpItem | MpsMrpAgent  |
| Quality 品質     | `/api/quality`       | InspectionOrder, NonConformance, CAPA | QualityAgent  |
| Sales 銷售       | `/api/sales`         | Customer, SalesOrder, SalesOrderItem | SalesAgent     |
| Accounting 會計  | `/api/accounting`    | Account, JournalEntry, AR, MonthEndClose | AccountingAgent |
| Warehouse 倉儲   | `/api/warehouse`     | Zone, BinLocation, PickTask, CycleCount | WarehouseAgent |
| CRM             | `/api/crm`           | Lead, Opportunity, CrmEvent         | CrmAgent        |
| Events / SSE    | `/api/events`        | (in-memory ring buffer)             | —               |
| Chat            | `/api/chat-v2`       | ConversationLog                     | GeneralAgent    |

---

## 🤖 對話式 CRUD 範例 / Try the Conversational CRUD

🇹🇼 對 AI 助手講以下任一句話：
🇺🇸 Talk to the AI Assistant with any of these:

| 操作 / Action | 範例 / Example |
|---|---|
| **查 / Read** | 「列出庫存低於安全庫存的零件」 / "List parts below safety stock" |
| **增 / Create** | 「跟長江廠下 100 個 M6 螺絲，交期下週五」→ **ConfirmCard** 出卡，點確認才下單<br>"Order 100 M6 bolts from ChangJiang, delivery next Friday" → **ConfirmCard** appears |
| **改 / Update** | 「把 SO-2025-0042 的交期改到 6/10」→ ConfirmCard 出卡<br>"Change SO-2025-0042 delivery date to 6/10" → ConfirmCard appears |
| **刪 / Delete** | 「取消 PO-2025-0099」→ ConfirmCard + 90 秒內可 Undo<br>"Cancel PO-2025-0099" → ConfirmCard + 90s undo window |

🇹🇼 缺欄位時 AI 會**反問**（slot-filling），不會憑空編造。
🇺🇸 When fields are missing, the AI **asks back** (slot-filling) instead of hallucinating.

詳見 / See:
- 🇹🇼 [`docs/CONVERSATIONAL_ERP_DESIGN_ZH.md`](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md) — 6 層架構 + 7 設計原則
- 🇺🇸 [`docs/CONVERSATIONAL_ERP_DESIGN_EN.md`](./docs/CONVERSATIONAL_ERP_DESIGN_EN.md) — 6-layer architecture + 7 design principles
- 🎬 [`docs/demos/deepseek_e2e_latest.md`](./docs/demos/deepseek_e2e_latest.md) — 真實 DeepSeek 跑 9/9 killer moments 全通（50 秒、21 tool calls）/ Real DeepSeek run: 9/9 killer moments passed in 50s with 21 tool calls

---

## 📡 即時事件流 / Try the Event Stream

🇹🇼 同時打開兩個視窗：
🇺🇸 Open two windows:

1. **/events** in the desktop UI (http://localhost:5173/events)
2. **War Room** at http://localhost:8080

🇹🇼 從第三個視窗觸發事件（例：`/inventory` 新增料件），兩個 dashboard 都會即時收到 `part.created` 事件。
🇺🇸 Trigger an event from a third window (e.g., create a Part in `/inventory`); both dashboards receive `part.created` in real time.

或用 curl / Or via curl:
```bash
curl -N http://localhost:8000/api/events/stream
```

---

## 🐘 Production 切換 PostgreSQL / Production Switch-over

🇹🇼 開發用 SQLite，正式上線改 PostgreSQL：
🇺🇸 Dev uses SQLite; production switches to PostgreSQL:

1. 編輯 `.env` / Edit `.env`:
   ```
   DATABASE_DRIVER=postgresql
   DATABASE_URL_PROD=postgresql+asyncpg://user:pass@host:5432/erp
   JWT_SECRET=<openssl rand -hex 32>    # disables demo bypass automatically
   ```

2. 取消 `docker-compose.yml` 中 `postgres` 服務的註解 / Uncomment the `postgres` service in `docker-compose.yml`.

3. 跑 migration / Run migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

詳見 / See [`DEPLOYMENT.md`](./DEPLOYMENT.md).

---

## 📂 檔案結構 / File Layout

```
opnetest/
├── backend/                    ← FastAPI 後端 / Backend
│   ├── app/
│   │   ├── core/              ← Base, logging, exceptions, deps
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── middleware/        ← auth, audit
│   │   ├── models/            ← 12 領域模型 / 12 domain models (60+ tables)
│   │   ├── schemas/           ← Pydantic schemas
│   │   ├── services/          ← 商業邏輯 / Business logic per domain
│   │   ├── api/               ← FastAPI routers per domain
│   │   ├── events/            ← EventBus, 16+ constraint rules
│   │   └── agents/            ← engine + 10 domain tool/agent modules
│   ├── scripts/seed.py        ← seed parts/products/customers/admin
│   ├── alembic/               ← migrations
│   ├── factory_node.py        ← MESH 節點 / MESH node
│   ├── Dockerfile
│   └── requirements.txt
├── frontend-desktop/           ← React 桌機 UI / Desktop frontend
│   ├── src/
│   │   ├── lib/api.ts         ← typed API client
│   │   ├── store/auth.ts      ← Zustand auth + persist
│   │   ├── i18n/              ← 中英雙語 / EN+ZH translations
│   │   ├── pages/             ← 8 pages
│   │   └── components/Layout.tsx
│   ├── Dockerfile
│   └── nginx.conf
├── war-room/                   ← 即時事件儀表板 / Live SSE dashboard
│   ├── index.html
│   └── Dockerfile
├── docs/                       ← 76 份雙語文件 / 76 bilingual docs
│   ├── CONVERSATIONAL_ERP_DESIGN_ZH.md / _EN.md
│   ├── COMMERCIAL_LICENSING_FAQ_ZH.md
│   └── ... (32 more)
├── LICENSE                     ← AGPL-3.0
├── LICENSE-SMALL-BUSINESS.md   ← 🌱 ≤20 人完全免費 / Free tier license
├── LICENSE-COMMERCIAL.md       ← 🔵 商業授權說明 / Commercial license info
├── CLA.md                      ← Contributor License Agreement (bilingual)
├── CONTRIBUTING.md
└── docker-compose.yml
```

---

## ⚖️ 三軌授權 / Tri-License Model

🇹🇼 Ouvoca 同時提供三種授權，依你的情境選擇：
🇺🇸 Ouvoca offers three license tracks — choose based on your scenario:

| 軌道 / Track | 條款 / Terms | 適用 / For | 費用 / Cost |
|---|---|---|---|
| 🟢 **AGPL 開源軌 / Open-source** | [AGPL-3.0](./LICENSE) | 🇹🇼 願意揭露 source 的所有人<br>🇺🇸 Anyone willing to disclose source | **免費 / Free** |
| 🌱 **小小企業軌 / Small Business** | [Small Business License](./LICENSE-SMALL-BUSINESS.md) | 🇹🇼 **≤ 20 concurrent users** 的單一公司，非 ISV / SaaS<br>🇺🇸 Single company with ≤20 concurrent users; non-ISV, non-SaaS | **完全免費（含閉源 connector）/ Fully free (incl. closed-source connectors)** |
| 🔵 **商業軌 / Commercial** | 個別協商 / Individually negotiated | 🇹🇼 > 20 users、ISV / OEM、SaaS provider、大企業<br>🇺🇸 >20 users, ISV/OEM, SaaS provider, enterprise | 🇹🇼 個別報價<br>🇺🇸 Custom pricing |

> 🌱 **「20 人以內全免費」戰略 / "Free for ≤20 users" strategy**
>
> 🇹🇼 對齊 Ouvoca「**讓小小企業也快速上手**」承諾。Taiwan SMB 1-20 人廠把整套（含鼎新 / 正航 / SAP connector）拿去白用，等你長到 21 人並離不開 Ouvoca 再聊商業合約。
>
> 🇺🇸 Aligned with Ouvoca's promise to help small businesses get started fast. Taiwan SMBs (1-20 employees) get the full suite — including 鼎新 / 正航 / SAP connectors — for free. Talk commercial contract only when you grow past 20 and can't live without it.
>
> ⚠️ **建議閱讀 / Recommended reading**：connector「免費」指的是 **Ouvoca 不收技術授權費**；要把 connector 接到您**現有商用 ERP**（如 Workflow / ChengHang / SAP B1 等廠商之產品），各廠商之授權合約規定可能不同，建議客戶於啟用前先和原 ERP 廠商書面確認授權範圍。Ouvoca 不參與此類第三方合約事務。詳見 [`docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md) / [EN](./docs/EXTERNAL_DB_LICENSING_NOTICE_EN.md) — "Free" here means **Ouvoca charges no technical license fee**; connecting to your incumbent ERP still calls for **the customer to confirm authorization scope in writing with the incumbent ERP vendor**. Ouvoca does not participate in such third-party contractual matters.

🇹🇼 不確定哪一軌？看 [`LICENSE-COMMERCIAL.md`](./LICENSE-COMMERCIAL.md) 決策樹。
🇺🇸 Not sure which track? See the decision tree in [`LICENSE-COMMERCIAL.md`](./LICENSE-COMMERCIAL.md).

詳細 FAQ / Detailed FAQ: [`docs/COMMERCIAL_LICENSING_FAQ_ZH.md`](./docs/COMMERCIAL_LICENSING_FAQ_ZH.md)

---

## 🛠 開發者指南 / Developer Guide

🇹🇼 想看程式碼、改功能、貢獻 PR？這節是你的入口。
🇺🇸 Want to read code, modify features, or contribute PRs? This section is for you.

### 🔐 首次設定 secret-scanning hook（強制 / Mandatory）

🇹🇼 第一次 clone repo 後**必跑**，避免 API key / .env 被誤推：
🇺🇸 **Must run after first clone** — prevents accidental commit of API keys / .env files:

```bash
# Mac / Linux / Git Bash
bash scripts/git-hooks/install_hooks.sh

# Windows
scripts\git-hooks\install_hooks.bat
```

🇹🇼 之後每次 `git commit` 自動掃 `sk-` / `ghp_` / `xoxb-` / hardcoded password 等樣式。
🇺🇸 Every `git commit` now auto-scans for `sk-` / `ghp_` / `xoxb-` / hardcoded password patterns.

### 🚀 開發環境（不用 Docker，熱重載 / hot reload）

🇹🇼 Windows 雙擊 `start_dev.bat`，會自動完成：
🇺🇸 On Windows, double-click `start_dev.bat`:

```
[1/5] 檢查 Python 3.11 / Node 20+               Verify Python 3.11 / Node 20+
[2/5] 自動 seed admin/admin123 + sample data    Auto-seed admin + sample data
[3/5] 釋放占用的 :8000 / :5173 port            Free up ports :8000 / :5173
[4/5] 等 backend healthcheck 綠燈              Wait for backend healthcheck
[5/5] 自動打開 http://localhost:5173           Auto-open browser
```

🇹🇼 **停止**：雙擊 `stop_dev.bat`（精準 PID kill 不誤殺其他 Python/Node）。
🇺🇸 **Stop**: double-click `stop_dev.bat` (precise PID kill).

### 🐳 Docker 模式（與 ERP 使用者裝法相同 / Same as user install）

```bash
cd Ouvoca
cp backend/.env.example backend/.env    # optionally set LLM_API_KEY
docker compose up -d --build
docker compose exec backend python -m scripts.seed
```

### 🧪 跑測試 / Run Tests

```bash
cd backend
python -m pytest                       # 298 tests (~12s)
python -m pytest tests/smoke/ -v       # 只跑 smoke
python -m pytest -k test_update_part   # 跑特定 test
```

### 🛡 自證閘 / Self-Verification Gates

```bash
bash scripts/run_gates.sh              # 跑 7 道 gate (~290s)
```

🇹🇼 7 道全綠才能 commit / push。pre-push hook 自動跑。
🇺🇸 All 7 gates must pass before commit / push. Auto-run by pre-push hook.

### 🤖 啟用 AI 對話 / Enable AI Chat

```bash
# backend/.env
LLM_API_KEY=<YOUR_KEY_FROM_DEEPSEEK_OR_ANTHROPIC_OR_OPENAI>

# Windows 開發環境 SSL 證書問題（DeepSeek 常見）
# Windows SSL cert issue with DeepSeek
LLM_VERIFY_SSL=false
```

🇹🇼 改完跑 `stop_dev.bat` → `start_dev.bat` 重啟。
🇺🇸 Restart with `stop_dev.bat` → `start_dev.bat`.

### 🔍 主要服務 URL / Main Service URLs

| 服務 / Service  | URL                              | 說明 / Notes                            |
|----------------|----------------------------------|----------------------------------------|
| Desktop UI     | http://localhost:5173            | 登入 / Login: `admin / admin123`        |
| API docs       | http://localhost:8000/docs       | OpenAPI / Swagger                      |
| War Room       | http://localhost:8080            | 即時事件儀表板 / Real-time dashboard     |
| Factory A      | http://localhost:8001/api/factory/health | MESH 節點健康 / Node health      |
| Factory B      | http://localhost:8002/api/factory/health |                                |

### 📖 工程文件 / Engineering Docs

| 文件 / Doc | 用途 / Purpose |
|---|---|
| [`docs/DEVELOPMENT_SOP.md`](./docs/DEVELOPMENT_SOP.md) | 開發 SOP、新增 domain/tool/constraint 步驟 |
| [`docs/GAP_ANALYSIS.md`](./docs/GAP_ANALYSIS.md) | Gap 分析（找事做的好地方） |
| [`docs/CONVERSATIONAL_ERP_DESIGN_ZH.md`](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md) | 對話式 ERP 6 層架構（必讀）|
| [`docs/ARCHITECTURE_DECISIONS.md`](./docs/ARCHITECTURE_DECISIONS.md) | ADR 架構決策紀錄 |
| 📝 Sprint 紀錄 / 動態工作日誌 | （內部 AI 工作檔，不公開）|

---

## 🤝 貢獻 / Contributing

🇹🇼 歡迎 PR！第一次貢獻請先看 [`CONTRIBUTING.md`](./CONTRIBUTING.md) + 簽 [`CLA.md`](./CLA.md)（DCO-style，`git commit -s` 即可）。
🇺🇸 PRs welcome! First-time contributors please read [`CONTRIBUTING.md`](./CONTRIBUTING.md) and sign the [`CLA.md`](./CLA.md) (DCO-style — just use `git commit -s`).

CLA Section 2(b) 是 dual-license 模式的命脈：你的 contribution 授權 maintainer 用任何條款（含商業）再授權。沒這條，整條商業軌作廢。
CLA Section 2(b) is the lifeline of the dual-license model: your contributions grant the maintainer the right to relicense under any terms (including commercial). Without it, the commercial track collapses.

---

## 📊 專案數據 / Project Stats

| 維度 / Metric | 數值 / Value |
|---|---|
| Backend tests | 287 passing |
| Self-verification gates | 7/7 green (~290s) |
| Bilingual PDFs | 35 |
| Domain models | 60+ tables across 12 domains |
| Multi-Agent tools | 40 (22 read / 4 soft-write / 14 hard-write) |
| Frontend pages | 10 (含 Permissions 管理) |
| Lines of code | ~50,000 (Python + TypeScript + docs) |
| Repo created | 2026-04 |
| Public since | 2026-05-16 |

---

<sub>by [Peter](https://github.com/fanchanyu) · [Issues](https://github.com/fanchanyu/ouvoca/issues) · [Commercial License](./LICENSE-COMMERCIAL.md)</sub>
