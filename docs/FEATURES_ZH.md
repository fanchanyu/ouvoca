# 🎯 Ouvoca 功能完整清單

> ⬅️ 回到 [README](../README.md) · 相關：[版本紀錄](./CHANGELOG_ZH.md) · [API 對照](./API_REFERENCE.md) · [架構](./ARCHITECTURE_DIAGRAM.md)
>
> 本清單依**實際程式碼**盤點（`backend/app/api/` 30 支、`frontend-desktop/src/pages/` 17 頁、
> `backend/app/agents/domains/` 35 支），非依文件描述。

## 三種操作入口，看懂這張圖再往下讀

| 標記 | 意思 |
|---|---|
| 🖥 **畫面** | 側欄選單點得到，滑鼠操作 |
| 💬 **對話** | 只能在 AI 助手打字操作（畫面上沒有入口） |
| 🔌 **API** | 有 REST endpoint，給程式或 Excel 巨集串接 |

> ⚠️ **請先看這裡**：v3.61 財務三大報表、v3.63 四張表單（請購 / 收料 / 領料 / 退貨）、
> v3.60 金流（付款 / 收款 / 銀行帳戶）目前**畫面上沒有入口**，只能用 💬 對話或 🔌 API 操作。
> 這是實測 `frontend-desktop/src/lib/api.ts` 的結果，不是規劃中的功能。

---

## 1. 📦 庫存管理

| 功能 | 說明 | 入口 |
|---|---|---|
| 建立 / 修改 / 刪除料件 | 料號、品名、類別、安全庫存、單位成本、前置天數 | 🖥 🔌 💬 |
| 料件清單與查詢 | 依類別（原料 / 半成品 / 零組件 / 耗材 / 包裝）瀏覽 | 🖥 🔌 💬 |
| 查即時庫存 | 在手量、可用量、已配置量對比安全庫存 | 🖥 🔌 💬 |
| 低於安全庫存警示 | 一次列出快沒料的品項與短缺量 | 🖥 🔌 💬 |
| 庫存異動紀錄 | 進貨 / 出貨 / 工單完工自動留痕，可回查來源單據 | 🖥 🔌 |
| 手動進出料 / 盤點調整 | 人工登錄 | 🔌 💬 |
| 倉間調撥 | 料件從一個庫位搬到另一個 | 🔌 |
| 條碼槍掃描 `v3.64` | 掃料號 / 批號 / 序號，立刻顯示庫存與可做的動作 | 🖥 🔌 |
| 料件 QR 標籤列印 `v3.64` | 60×40mm QR 標籤貼料架 | 🖥 🔌 💬 |
| 盤點單全套 | 建盤點單 → 批次輸入實盤數 → 看進度 → 主管覆核沖銷差異 | 💬 |
| 盤點表 PDF `v3.68` | 印空白盤點表給倉管拿去現場填 | 🔌 |
| 庫存月報 Excel | 低於安全庫存自動黃底高亮；**無財務權限者不輸出成本欄** | 🖥 🔌 |

## 2. 🛒 採購管理

| 功能 | 說明 | 入口 |
|---|---|---|
| 供應商建檔 / 修改 / 刪除 | 有採購單者不可刪 | 🖥 🔌 💬 |
| 開採購單 | 選供應商、料件、數量、單價、交期 | 🖥 🔌 💬 |
| 採購單審核 | 主管核准後才能發出 | 🖥 🔌 💬 |
| 採購收貨入庫 | 收到貨按一下，數量直接進庫存（原子更新） | 🖥 🔌 💬 |
| 取消 / 備註採購單 | | 🖥 🔌 💬 |
| 採購單 PDF | 正式採購單寄供應商 | 🖥 🔌 💬 |
| **請購單 PR** `v3.63` | 現場提需求 → 主管核准 → 轉正式採購單 | 🔌 💬 |
| **收料單 GRN** `v3.63` | 對採購單開正式收料單，更新收貨量並入庫，不可超收 | 🔌 💬 |
| **RFQ 詢價** `v3.64` | 針對料件發詢價給多家供應商 | 🖥 🔌 💬 |
| **登錄供應商報價** `v3.64` | 把各家回報價格打進系統 | 🖥 🔌 💬 |
| **比價** `v3.64` | 並排看各家報價，標出每個料件的最低價 | 🖥 🔌 💬 |
| **決標轉採購單** `v3.64` | 選定得標廠商，一鍵轉 PO | 🖥 🔌 💬 |
| 補貨建議 | 低於再訂購點的料件與建議下單量；智慧版含前置期與供應商分組 | 💬 |
| 供應商歷史報價 | 某零件過去各家報價、MOQ、交期 | 💬 |
| 採購集中度分析 | 前 N 大供應商佔總採購金額比例（風險評估） | 🔌 |

## 3. 💼 銷售管理

| 功能 | 說明 | 入口 |
|---|---|---|
| 客戶建檔 / 修改 / 刪除 | 編號、名稱、分級、信用額度 | 🖥 🔌 💬 |
| 開銷售訂單 | 選客戶、產品、數量、單價、交期 | 🖥 🔌 💬 |
| 訂單確認 | 客戶確認後鎖定，才可出貨 | 🖥 🔌 💬 |
| **出貨（全鏈原子化）** `v3.55` | 按一次出貨：扣成品庫存 + 產出貨單 + 開發票 + 記傳票 + 產生應收，全在同一個交易內 | 🖥 🔌 💬 |
| 出貨單清單 / 明細 | 查出貨紀錄與連動的發票、傳票 | 🔌 💬 |
| 取消 / 備註訂單 | 已出貨不可取消 | 🖥 🔌 💬 |
| **退貨單 RMA** `v3.63` | 客戶退貨 → 建單 → 主管核准 → 退貨入庫 | 🔌 💬 |
| 報價單全套 | 建報價、查明細、改狀態、作廢、複製舊報價、Email 寄客戶、轉銷售訂單 | 💬 🔌 |
| 報價單 / 銷售單 / 出貨單 PDF | 正式單據列印 | 🖥 🔌 💬 |
| 訂單跟單 | 追 報價 → 訂單 → 出貨 → 應收 → 收款 的完整生命週期 | 💬 |
| 客戶毛利率 | 某客戶賺不賺錢、誰最賺 | 🔌 💬 |
| 接單決策評估 | 依限制理論算單位瓶頸產出，建議接單 / 拒單 / 議價 | 💬 |

## 4. 🏭 生產管理

| 功能 | 說明 | 入口 |
|---|---|---|
| 產品建檔 | 成品編號、名稱、售價、標準成本 | 🖥 🔌 💬 |
| 做法 / Recipe（BOM） | 「這個產品由哪些料、各用幾個」；UI 刻意不叫 BOM | 🖥 🔌 💬 |
| 開生產工單 | 指定產品與數量 | 🖥 🔌 💬 |
| 工單釋放 | 放行到現場（會檢查做法是否完整） | 🖥 🔌 💬 |
| 工單報完工 | 回報完工量與不良量，達訂單量自動結案並入庫 | 🖥 🔌 💬 |
| 取消 / 備註工單 | | 🖥 🔌 💬 |
| **工單成本彙總** `v3.61` | 材料 + 人工 + 製造費用，這張單是賺是賠 | 🔌 💬 |
| **領料單 MI** `v3.63` | 工單從倉庫扣料，記錄成本快照 | 🔌 💬 |
| 工作中心 / 機台 | 機台、日產能、效率 | 🔌 💬 |
| 製程工序 / 派工紀錄 | 定義作業步驟；記錄誰在哪台機做了什麼 | 🔌 |
| 主生產排程 MPS | 各期計畫產量 | 🔌 💬 |
| 物料需求計算 MRP | 依 MPS 展開做法，算出該買什麼、該做什麼 | 🔌 💬 |
| 瓶頸辨識 | 找出目前產能最吃緊的機台並給改善建議 | 💬 |
| DBR 排產建議 | 依瓶頸節奏規劃投料時程 | 💬 |
| 產能 What-if 模擬 | 「加 20% 沖床產能會怎樣」 | 💬 |
| 需求預測 | 自動選演算法預測料件未來需求，可寫回 MPS | 💬 |
| 反查用途 | 這個料件被用在哪些產品的做法裡 | 💬 |
| 設備綜合效率 OEE | 可用率 × 效能 × 良率 | 🔌 |

## 5. 🔬 品質管理

| 功能 | 說明 | 入口 |
|---|---|---|
| 建立 / 完成檢驗單 | 進料 / 製程 / 出貨 QC；不合格自動觸發不良品紀錄 | 🖥 🔌 💬 |
| 不良品 NC / NCR | 嚴重度、說明、影響數量 | 🖥 🔌 💬 |
| 矯正預防措施 CAPA | 針對不良開改善對策並追蹤 | 🔌 💬 |
| 檢驗報告 PDF `v3.68` | 正式檢驗報告 | 🔌 |
| 未結案 NCR 查詢 | 依嚴重度列出還沒結的不合格 | 💬 |

## 6. 📒 會計與財務

### 6.1 基礎帳務

| 功能 | 說明 | 入口 |
|---|---|---|
| 會計科目表 | **86 科台灣科目表開機即用**，可增修停用（系統科目有保護） | 🖥 🔌 |
| 建立 / 過帳傳票 | 簡化版借貸輸入；過帳後鎖定不可改 | 🖥 🔌 💬 |
| 應收帳款 | 建立與列出 AR，看未收 / 逾期 | 🖥 🔌 💬 |
| 月結 | 關帳鎖定期間 | 🔌 💬 |
| 應收帳齡 Excel | 誰欠錢、欠多久、欠多少 | 🖥 🔌 💬 |
| 應收週轉天數 DSO | 錢平均多久收得回來 | 🖥 🔌 |

### 6.2 財務閉環 M2 `v3.61`（**沒有畫面，只能對話或 API**）

| 功能 | 說明 | 入口 |
|---|---|---|
| 試算表 | 檢查借貸平不平衡 | 🔌 💬 |
| 損益表 | 某期間賺多少賠多少 | 🔌 💬 |
| 資產負債表 | 公司家底一覽（累計餘額） | 🔌 💬 |
| 401 / 405 營業稅申報 | 銷項、進項、應納稅額 | 🔌 💬 |
| 進銷項明細表（403） | 銷項或進項明細 | 🔌 |
| 401 申報書 HTML | 瀏覽器列印存 PDF 交檔 | 🖥 🔌 |
| 供應商發票 + 3-Way Match | 採購單 ↔ 收貨 ↔ 發票三方勾稽，抓數量 / 價格差異 | 🔌 💬 |
| 票據管理 | 應收 / 應付票據與到期提示 | 🔌 💬 |
| 固定資產 + 提列折舊 | 直線折舊，過帳折舊傳票（借 折舊費用 / 貸 累計折舊） | 🔌 💬 |
| 銷貨成本結轉 | 月結：期間出貨 × 成本 → 傳票（借 銷貨成本 / 貸 製成品） | 🔌 💬 |

### 6.3 金流閉環 `v3.60`（**只有對話，連 REST 都沒有**）

| 功能 | 說明 | 入口 |
|---|---|---|
| 銀行帳戶主檔 | 新增銀行帳戶、查餘額 | 💬 |
| 應付帳款查詢 | 我們欠供應商多少、下週要付多少 | 💬 |
| 記錄付款 | 付供應商，自動記傳票（借 應付 / 貸 銀行），沖銷應付 | 💬 |
| 記錄收款 | 客戶付款，自動記傳票（借 銀行 / 貸 應收），沖銷應收 | 💬 |
| 收付款查詢 | 上個月付了哪些、收了哪些 | 💬 |

### 6.4 台灣電子發票

| 功能 | 說明 | 入口 |
|---|---|---|
| 開立電子發票 | B2B 三聯式 / B2C 二聯式 | 🖥 🔌 💬 |
| 作廢發票 | 24 小時內可作廢，需填原因 | 🖥 🔌 💬 |
| 發票查詢 / 清單 | 合規 5 年保存與查詢 | 🖥 🔌 💬 |
| 發票 PDF | 列印電子發票 | 🖥 🔌 |
| 統編驗證 | 台灣 8 碼 checksum，另支援 CN / US / JP / EU / GENERIC，可 plug-in 任何國家 | 🖥 🔌 💬 |

## 7. 🏬 倉儲管理

| 功能 | 說明 | 入口 |
|---|---|---|
| 倉區 / 儲位設定 | 建立倉庫分區與貨架儲位 | 🔌 💬 |
| 揀貨任務 | 為銷售單建揀貨單、指派倉管、回報完成 | 🔌 💬 |
| 循環盤點 | 建立循環盤點紀錄 | 🔌 💬 |
| **批號清單** `v3.64` | 每個批號的數量與效期 | 🖥 🔌 |
| **批號正反向追溯** `v3.64` | 這批料從哪進來、被哪些單據吃掉 | 🖥 🔌 💬 |
| **序號追溯** `v3.64` | 單一序號的狀態與相關文件 | 🖥 🔌 💬 |
| 批號 / 序號建檔 | 建批號主檔、批量登記序號 | 💬 |
| 庫存週轉率 | 銷貨成本 ÷ 平均庫存 | 🖥 🔌 |

## 8. 🤝 客戶關係 CRM

| 功能 | 說明 | 入口 |
|---|---|---|
| 潛在客戶（🌱 新苗 / Lead） | 登錄與列出名單，可依狀態篩選 | 🖥 🔌 💬 |
| 名單轉客戶 | Lead 談成後轉正式客戶 | 🖥 🔌 |
| 商機（🎯 追單 / Opportunity） | 建立商機並看 pipeline，依預計成交日排序 | 🖥 🔌 💬 |
| 推進商機階段 | 把商機往下一階段拖 | 🖥 🔌 |
| 互動歷程 | 通話 / 拜訪 / Email 紀錄；訂單成立、Lead 轉換、商機推進會**自動**產生 | 🖥 🔌 💬 |
| 客戶 360 度 | 基本資料 + 所有訂單 + 信用額度 + 最近活動一次看完 | 💬 |
| 客戶名稱消歧 | 講「ABC」有多個匹配時列候選讓人選 | 💬 |

## 9. ⚙️ 系統管理

### 9.1 登入與帳號

| 功能 | 說明 | 入口 |
|---|---|---|
| 登入 | 帳密登入取得 token | 🖥 🔌 |
| **登入失敗鎖定** `v3.62` | 預設連錯 5 次鎖 15 分鐘；鎖定期間不揭露帳號是否存在 | 內建 |
| **改密碼即撤銷舊登入** `v3.62` | 其他裝置的舊 token 立刻失效 | 內建 |
| **MFA 雙重驗證（TOTP）** `v3.64` | 綁定 Authenticator App，登入需輸入 6 位驗證碼 | 🖥 🔌 |
| 註冊使用者 / 停用帳號 | 給新員工開帳號；離職員工封存不刪除 | 🖥 🔌 💬 |
| 部門與員工 | 建立部門、員工並列出 | 🔌 |

### 9.2 權限 RBAC

| 功能 | 說明 | 入口 |
|---|---|---|
| 權限碼清單 | **231 個權限碼**，含中文名、敏感標記、風險等級 | 🖥 🔌 |
| 角色管理 | **10 個預設角色**：系統管理員 / 老闆 / 廠長 / 業務主管 / 業務員 / 採購 / 倉管 / 會計 / 品檢員 / 作業員，可新增、複製、改權限 | 🖥 🔌 |
| 指派 / 撤銷角色 | 給某員工角色或拿掉 | 🖥 🔌 💬 |
| 個別權限例外 | 針對單一使用者加開權限 | 🔌 |
| 查有效權限 / 我的權限 | 角色 + 例外 + scope 實際生效的結果 | 🖥 🔌 |
| 多租戶 | 建立與列出 tenant，資料自動隔離 | 🔌 |

### 9.3 審批流程

| 功能 | 說明 | 入口 |
|---|---|---|
| 審批規則設定 | 「採購單超過 X 元要主管審」，可多階 | 🖥 🔌 |
| 待我審清單 | 依角色看待審單據 | 🖥 🔌 💬 |
| 批准 / 拒絕 | 核准推進下一階，拒絕必須填原因 | 🖥 🔌 💬 |
| 審批歷史 | 依狀態與類型查歷史決議 | 🖥 🔌 |

> ⚠️ **已知限制**：`/api/approvals/*` 目前只檢查「有沒有登入」，沒有再檢查權限碼，
> 與其他模組採用 `require_permission` 的做法不同。多人環境請自行評估風險。

### 9.4 🏛️ 家規（House Rules）

| 功能 | 說明 | 入口 |
|---|---|---|
| 家規清單 / 新增 / 修改 / 刪除 | 規則存成資料（觸發點 + 條件 + 動作 + 例外），可隨時停用 | 🔌 |
| 一鍵載入 **23 條**預設家規 | 工單釋放需做法、採購高額審批、傳票借貸需平衡、收料不可超收… | 🔌 |
| 可用觸發點 / 條件清單 | 給設定畫面下拉選單用（公開端點） | 🔌 |
| 手動試跑規則 | 測試某條規則會不會擋 | 🔌 |
| 家規稽核紀錄 | 看哪些單被規則擋下 | 🔌 |

> ⚠️ **現況誠實說明**：家規引擎已在跑（違規單據會實際被擋），但管理入口目前**只有 9 支 REST API**
> （`/api/policies/*`）。實測 `frontend-desktop/src/` 沒有任何 policy 相關程式碼，
> AI 工具註冊表也沒有 policy 領域——**設定畫面與「跟 AI 講就能新增規則」尚未實作**。

### 9.5 系統設定與維運

| 功能 | 說明 | 入口 |
|---|---|---|
| **系統組態 14 項** `v3.60` | 公司名稱、統編、地址、電話、幣別、稅率、信用額度檢查、時區、語系、備份開關 / 排程 / 保留天數、登入鎖定次數、AI 每日用量上限。優先序：**環境變數 > 資料庫 > 預設值** | 🖥 🔌 |
| **資料庫備份** `v3.62` | 立即備份、列出（時間 / 大小）、刪除 | 🖥 🔌 💬 |
| **備份還原** `v3.62` | 從備份還原（破壞性，需 `confirm=true`；還原前先存救援檔） | 🔌 💬 |
| **外部資料庫連線** `v3.60` | 接鼎新 / 正航 / SQL / CSV，帳密以 **AES-256-GCM 加密**儲存 | 🔌 💬 |
| **集中式單據編號** `v3.60` | 單號原子計數器，多人同時開單不會撞號 | 內建 |
| AI 供應商設定 | DeepSeek / OpenAI / Anthropic / Ollama，貼 API key 即時生效不需重啟 | 🖥 🔌 |
| 檔案上傳 / 下載 / 刪除 | 上傳業務文件並分類，連結到單據 | 🖥 🔌 |
| **上傳檔案內容驗證** `v3.62` | magic bytes 檢查，防「.txt 改名 .pdf」 | 內建 |
| **病毒掃描掛鉤** `v3.64` | 設定 `AV_SCAN_URL` 後啟用上傳掃毒 | 內建 |
| 示範資料 | 一鍵載入 **5 客戶 / 3 供應商 / 10 料件**，試完一鍵清除 | 🖥 🔌 💬 |
| 5 行業種子 | 金屬加工 / 塑膠射出 / PCB / 食品 / 紡織，各含料件、成品 + 做法、供應商、客戶、工作中心、示範工單 | CLI `python -m scripts.seed_industries <industry>` |
| 即時事件流 SSE | 推播看系統即時發生什麼事 + 桌面通知 | 🖥 🔌 |
| 多廠聯網 MESH | 分廠註冊到總部，總部跨廠聚合查詢（原始資料不離廠） | 🔌 |
| 系統健康檢查 | 資料庫 / LLM / 服務狀態 | 🔌 💬 |
| 資料健康檢查 | 抓 BOM 循環依賴、重複客戶、重複料件、孤兒資料 | 💬 |

> ⚠️ **已知限制**：`POST /api/factory/aggregate`（跨廠聚合查詢）目前沒有認證依賴，
> 未登入即可呼叫。多廠部署請放在內網或 VPN 之後，不要直接對外開放。

### 9.6 全域 UI 功能（跨頁）

| 功能 | 說明 |
|---|---|
| 快速搜尋 | `Ctrl+K` / `Cmd+K` 模糊搜尋客戶 / 供應商 / 料件 / 產品 / 訂單 / 工單，鍵盤導航 |
| 💡 AI 浮球現場教練 | 右下角球，帶當前頁面情境問 AI「這頁怎麼做」 |
| 首次登入引導 | 歡迎卡 + 一鍵載入示範資料 + 申請 API key 引導 |
| 流程鏈視覺化 | 一眼看出單據在流程哪一步、後面會發生什麼 |
| 中英文切換 | 側欄國旗切換 zh-TW / en |
| 權限化選單 | 沒權限的模組不出現在側欄（不只後端 403） |
| 桌面通知 | 瀏覽器 Toast + SSE 推播 |
| 單據備註編輯 | 在訂單 / 採購單 / 工單上留內部備註（不會印給客戶） |

## 10. 🤖 AI 對話（201 個工具 / 19 個領域 / 17 個 agent）

### 10.1 對話機制

| 功能 | 說明 |
|---|---|
| 對話式操作 | 用中文講話就能查詢與建單（`POST /api/chat-v2`） |
| **ConfirmCard 確認卡** | 任何會寫入資料的動作先出確認卡，列出要寫什麼，按確認才真的寫。**TTL 30 分鐘** |
| 缺欄位反問（slot-filling） | 缺資料時 AI 會問回來，不會憑空編造 |
| 90 秒撤銷 | 剛剛做錯可以講「撤銷」救回來（限 90 秒內、一次） |
| 對話歷史 / 回饋評分 | 回查同 session 問答；對 AI 回答按讚 / 倒讚 |
| 直接執行工具 | 前端動態表單直接叫某個工具（不經對話） |
| 全系統寫入凍結 | 老闆出國把所有寫入操作鎖住，查詢照常 |
| 工具級 RBAC `v3.60` | 每個工具都掛權限碼，對話管線一樣要過權限檢查 |

### 10.2 各領域工具數（實測 `@register_tool` 註冊結果）

| 領域 | 工具數 | 代表性能力 |
|---|---:|---|
| `system` | 34 | 我是誰 / 我能做什麼、FAQ、全域搜尋、稽核日誌搜尋、對話匯出、AI 成本、備份還原、公司資料與 LOGO、時區、改密碼、開帳號 / 停用、示範資料、資料健檢、相對日期解析、台灣工作天、主動提醒、Excel 匯入引導 |
| `sales` | 25 | 建客戶 / 訂單、出貨、取消、改行項與交期、報價全套、訂單跟單、客戶毛利率、客戶分頁列表 |
| `accounting` | 25 | 三大報表、應收帳齡、應付 / 待收款、記付款 / 收款、銀行帳戶、票據、固定資產與折舊、3-Way Match、銷貨成本結轉、401/405、傳票過帳、月結狀態 |
| `purchase` | 23 | 建供應商 / 採購單、審核、收貨、取消、加刪改行項、改交期、請購單、收料單、RFQ 詢價比價決標、補貨建議、歷史報價 |
| `inventory` | 18 | 建料件、改安全庫存、庫存查詢、低於安全庫存、進出料、盤點單全套、批號建檔、序號登記、追溯、QR 標籤 |
| `production` | 13 | 產品清單、做法增刪改查、工單查詢 / 釋放 / 完工 / 取消、領料、工單成本、工作中心 |
| `planning` | 10 | 需求預測、寫入 MPS、瓶頸辨識、DBR 排產、產能 What-if、接單決策、議價曲線、計畫訂單溯源、反查用途、每日簡報 |
| `quality` | 7 | 完成檢驗、開 NCR、開 CAPA、清單查詢、未結 NCR |
| `external_db` | 7 | 列 / 新增 / 刪除外部連線、列外部資料表、Schema 對映預覽（帶信心分數）、跨庫查詢、一次性匯入 |
| `warehouse` | 6 | 建 / 完成揀貨任務、待揀清單、倉區清單、循環盤點 |
| `export` | 6 | 客戶 / 料件 / 庫存 / 供應商 / 採購單 / 銷售單匯出 Excel 或 CSV |
| `crm` | 5 | 客戶 360、名稱消歧、Lead 清單、商機 pipeline、互動歷程 |
| `tax` | 5 | 開立 / 作廢電子發票、查訂單發票、月營業稅概況、統編驗證 |
| `print` | 5 | 報價單 / 採購單 / 銷售單 / 出貨單 PDF、批次列印打包 ZIP |
| `approval` | 3 | 待我審、批准、拒絕（須填原因） |
| `glossary` | 3 | 教 AI 同義詞（「以後我說鋼釘就是 M6-BOLT-20」）、查詞、列出 |
| `analytics` | 2 | 老闆儀表板摘要預覽、寄每日摘要 Email |
| `mps_mrp` | 2 | MPS 清單、MRP 結果與建議計畫訂單 |
| `permission` | 2 | 給某員工角色、拿掉某員工角色 |
| **合計** | **201** | 106 read / 94 hard-write / 1 soft-write |

### 10.3 報表與摘要

| 功能 | 說明 | 入口 |
|---|---|---|
| KPI 總覽 | 一次拿全部 KPI | 🖥 🔌 |
| 老闆三個關鍵數字 | DSO、庫存週轉、毛利率 | 🖥 🔌 💬 |
| AI 成本追蹤 | LLM 用了多少 token、花多少錢 | 🔌 💬 |
| 每日摘要 Email | 預覽（JSON / HTML）與寄送；未設 SMTP 則 dry-run | 🔌 💬 |
| 主動提醒 | 應收逾期 / 低於安全庫存 / 待簽核三件事 | 💬 |

---

## 附錄 A · 原 README「🎯 內含什麼 / What's Inside」表（原文保留）

> 以下為 2026-05 版 README 的原始表格，**逐字保留**以免歷史敘述遺失。
> 其中的數量（40 tools / 12 domains / 5 分鐘 TTL / 7-gate）已被本文件上半部的實測值取代，
> 實測值為準：**201 tools / 19 domains / 30 分鐘 TTL / 4 道 gate**。

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

**最後更新**：v3.70（2026-08-04）· 盤點方式：直接讀程式碼
