# 商業授權 FAQ（繁體中文）

> 這份 FAQ 不是法律意見，只是常見問題的「**直觀答案**」。
> 真正下決定前請和你的法務 / 律師確認，或開 [Commercial License Inquiry issue](https://github.com/fanchanyu/erpilot/issues/new?template=commercial-license-inquiry.yml) 給維護者。

---

## 🌱 小小企業軌專屬 FAQ（最常見）

### SB1: 我是 5 人新創 / 10 人工作室 / 18 人小工廠，可以白用嗎？

**可以，完全免費**，而且**含所有 connector**（包含我們的閉源鼎新 / 正航 /
SAP / Oracle 整合模組）。

只要符合 [Small Business License](../LICENSE-SMALL-BUSINESS.md) 的條件：
- ≤ 20 人同時在線（24 小時峰值）
- 單一法人內部用
- 不對外提供 SaaS / 不嵌入產品轉售 / 不是 SI 散布

這是 erpilot 對 Taiwan SMB 的戰略差異化承諾。

> ⚠️ **重要**：免費「含 connector」指的是 **erpilot 不收技術授權費**。要把
> connector 接到您**現有商用 ERP**（鼎新 / 正航 / SAP B1 等），**仍須客戶
> 自行向原 ERP 廠商取得書面授權**（多數採每位具名使用者授權，禁止以共用 /
> 服務帳號連線）。erpilot **不協助、不代理、不承擔**與第三方 ERP 廠商之
> 合約 / 授權事務。詳見 [`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./EXTERNAL_DB_LICENSING_NOTICE_ZH.md) /
> [EN](./EXTERNAL_DB_LICENSING_NOTICE_EN.md)。

### SB2: 「同時在線」怎麼算？

定義：**在過去 15 分鐘內**有任一經驗證行為（API 請求 / 頁面載入 /
WebSocket / SSE event）的 logged-in user。

舉例：
- 公司 30 人有 erpilot 帳號，但只有 18 人**正在用**（過去 15 分鐘有動作）→ ✅ 適格
- 公司 15 人有帳號，全部都在 dashboard 上看著（即使沒點任何東西）→ ✅ 適格（15 ≤ 20）
- 公司 50 人帳號，平常都用，但峰值（如午休前 11:45）有 25 人同時動作 → ❌ 不適格

實務上：用 erpilot 內建 analytics dashboard 看「peak concurrent users」就知道。

### SB3: 20 人怎麼這麼少？我們公司 50 人但只有少數人用 ERP 也可以嗎？

可以，**重點是「同時在線」不是「公司員工數」**。

很多製造廠模式是：
- 廠長 1 人天天用
- 業務 5 人偶爾下單
- 採購 2 人查庫存
- 老闆 1 人看 dashboard
- 倉管 3 人盤點

→ 公司可能 80 人，但同時在線多半 ≤ 10。**完全適格**。

### SB4: 我是 21 人廠，會不會有 1 人的差距很尷尬？

技術上會。我們的態度：
- **沒有 hard gate** — 系統不會自動 disable，只會 toast 提醒「您已達 20 人」
- **Grace period 30 天**讓你決定升級或調整
- **誠信制** — 我們不主動 audit，相信 SMB 老闆

如果你公司是 21-25 人，這個 tier 不適合你。但商業授權**沒有官方最低門檻**——
可以開 issue 跟維護者聊「我們 23 人，能不能用比較合理的價錢」。

### SB5: 我們可以分拆成兩家公司各 18 人，都用小小企業軌嗎？

**技術上可以，但有自然摩擦**：
- 兩家公司 = 不同法人 = 不能跨用同一個 erpilot 部署
- 你要架兩套 erpilot，資料是分開的
- 真要查跨公司資料，得手動匯整

而且如果**實質**上是同一個經營體（同老闆 / 同地址 / 共用人員），稅務 /
營業登記面已經有相關認定。Section 1.2「單一法人」在法律上有 substance over
form 原則。

實務上：真分拆會自然產生足夠摩擦，讓多數人想升級而不是規避。

### SB6: 我是 SI / 顧問，可以用小小企業軌幫客戶部署嗎？

**看誰是 license 持有人**：

- 客戶名下部署、你只是顧問 → 客戶獨立判斷其軌（多數客戶可走 🌱）
- 你**修改**了 erpilot 然後**散布給多個客戶** → 不適格，需要商業授權

簡單說：SI 角色不影響客戶適格性，但 SI 自己不能拿來當 freemium ISV 工具。

### SB7: 小小企業軌會被收回嗎？

**不會**。Small Business License 本身是永久條款 — 只要你符合條件就一直適用。

但**版本鎖定**：你使用某個版本（如 v3.12）的權利不會被撤銷；未來新版本
（如 v5.0）的條款可能調整，你可選擇升級或繼續用舊版。

### SB8: 我用 AGPL-3.0 軌也免費，為什麼要選小小企業軌？

**選 AGPL** 如果：
- 你樂於開源你的改動回饋社群
- 你內部員工不怕看到 source
- 你做的東西本來就會公開

**選小小企業軌** 如果：
- 你不想揭露任何修改 / 配置 / 客製 logic
- 你的客製化是商業秘密（如：採購談判規則、定價公式）
- 你想白用閉源 connector（鼎新等）但**不公開**你串接的細節

兩條都免費，差別在「**source disclosure 義務**」。

---

## 🟢 一般使用問題

### Q1: 我只是自己一個人想玩 erpilot，要付錢嗎？

**完全免費。** AGPL-3.0 不限制「使用」（use），只限制「散布」（distribute）。
你個人安裝、跑、改、學習，都 OK，不用通知任何人。

也可以選 🌱 小小企業軌（1 人 ≤ 20 同時在線）— 不用揭露你的學習筆記 modifications。

### Q2: 我們公司想內部用 erpilot，要付錢嗎？

**不用。** 公司內部使用 = AGPL-3.0 沒有觸發「散布」條款。

⚠️ **但有兩個邊界**：
1. **多公司集團**：如果 erpilot 改動後給「**法律上不同的公司**」用（即使同集團），
   按嚴格解釋可能算「散布」，要公開 source。實務上同集團視為內部多半 OK，
   但建議和法務確認。
2. **內部員工有權索取 source**：AGPL-3.0 規定**接觸過程式的人**（包含員工）
   可以要求拿到改動後的 source。如果你的改動是商業敏感的（例如：客製化的
   採購談判邏輯），就要小心。

### Q3: 改了 source code 但只內部用，要公開嗎？

**AGPL-3.0 不強制把改動傳到 GitHub 給全世界看**。但內部使用者 / 員工有權
向你索取改動後的 source（你必須提供）。

如果你不想連內部都揭露 → 需要商業授權。

### Q4: 我們是 SI（系統整合商），幫客戶導入 erpilot，要付錢嗎？

**看你和客戶的關係**：

- 你只是**幫客戶部署 + 設定**，所有改動是客戶名下、客戶內部用？
  → AGPL-3.0 即可，客戶身分如 Q2。
- 你**改了程式**然後**把改動版交付**給客戶（多個客戶都收到你的版本）？
  → 這算「散布」。AGPL-3.0 要求你連同改動 source 給客戶。
  - 如果客戶接受 → AGPL-3.0 即可
  - 如果客戶不要拿到 source（要黑盒子）→ 需要商業授權

### Q5: 我把 erpilot 包成 SaaS，給好幾家客戶用，要付錢嗎？

**這就是 AGPL 設計來保護的情境**：

- 願意公開你的改動（包含 hosting/scaling 用的程式）→ AGPL-3.0 即可，**免費**
- **不想公開**改動 → **需要商業授權**

AGPL-3.0 的特殊 §13 條款：「使用者透過網路存取你的修改版時，你必須提供
source 取得方式」——這就是「**A**ffero GPL」的精髓，**堵 SaaS 規避 GPL** 漏洞。

---

## 🔵 商業授權細節問題

### Q6: 商業授權怎麼買？流程多久？

1. 開 [Commercial License Inquiry issue](https://github.com/fanchanyu/erpilot/issues/new?template=commercial-license-inquiry.yml) 或寄 email
2. 維護者 5 個工作天內聯絡你做 scoping call
3. 報價（依規模 + 服務組合）
4. 合約用印（一般 1-2 週）
5. 發 license key + 開帳號（1 個工作天）

總計：**2-4 週**從詢價到上線。

### Q7: 商業授權有 license key 嗎？

**有**。商業版用 JWT-signed license key 啟動以下能力：

- 解鎖閉源 connector（鼎新 / 正航 / SAP 等）
- 啟動商業 SLA 支援 channel
- 顯示「Powered by erpilot Enterprise」品牌
- 多租戶 hosting 配額（按合約規模）

⚠️ **核心 ERP 功能（CRUD、Multi-Agent、ConfirmCard）AGPL 版就有**。
license key 不會解鎖「藏起來的核心功能」——我們不做 open core。

### Q8: 年費到期不續，會發生什麼事？

License key 到期日 + 30 天 grace period 後失效：

- **閉源 connector 模組**：停止運作（你會 fallback 到 AGPL 版的 CSV/Excel 匯入）
- **多租戶配額**：自動降到單租戶
- **SLA 支援**：終止
- **品牌標示**：你必須在 30 天內移除「Powered by erpilot Enterprise」字樣
- **既有資料**：完全你的，不會被鎖

不會回頭追溯任何過去的合規問題。

### Q9: 我們公司想要永久授權（perpetual），可以嗎？

**可以**。一次性買斷 + 20%/年 maintenance（拿新版 + 支援）。
適合：
- 政府單位 / 學校 / 公營事業（會計分類偏好 capex）
- 高度保守的法務文化
- 不想每年走採購流程的中大型企業

報價會比年費模式高（通常是年費 × 3-5 倍）。

### Q10: 我們有自己的法務、想用我們的合約模板可以嗎？

**可以**。給維護者你們的 master service agreement 模板，我們審後通常
2-3 輪修改就能定案。

但**這會明顯拉長時程**（4-8 週）和產生審稿費用。建議你先看我們的標準模板。

---

## ⚖️ AGPL-3.0 細節

### Q11: 「Network use is distribution」是什麼意思？

AGPL-3.0 §13 規定：
> 如果你修改了程式，且讓**其他人透過網路**和這個修改版互動，**那些人**
> 有權向你索取修改後的 source。

實務上：
- 你架了一個 erpilot SaaS 給客戶用 → 客戶有權向你索取 source
- 你內網架了 erpilot 給員工用 → 員工有權向你索取 source
- 你只是後端服務、不對人提供互動 → 此條不適用（但其他 GPL 條款仍適用）

### Q12: 「Compatible License」清單裡有什麼？

AGPL-3.0 可以和以下授權混用（**注意最終發行版要按 AGPL-3.0**）：
- GPL-3.0、LGPL-3.0
- Apache-2.0（單向：可以吃 Apache，反之不行）
- MIT、BSD-2/3
- 大部分寬鬆授權的單向相容

不相容：
- GPL-2.0（沒寫 "or later"）
- AGPL-3.0 **單向**不能和 GPL-2.0 only / EPL / MPL 純混用

不確定就問律師或開 issue。

### Q13: erpilot 的 LICENSE 檔可以放進我的商業產品嗎？

只放 LICENSE 檔 = 沒用。AGPL-3.0 的義務不會因為你保留 license 檔就消失。
你還是要：
- 揭露使用 erpilot
- 提供 erpilot 原始碼取得方式
- 你的 derivative work（基於 erpilot 改動的部分）也要 AGPL-3.0

如果你想保有「改動的部分不公開」的權利 → 走商業授權。

---

## 🛠️ 技術整合問題

### Q14: 我可以寫 plugin 接 erpilot 嗎？plugin 要不要 AGPL？

看 plugin 的「**結合方式**」：

- **API 呼叫**（HTTP / REST）：你的 plugin **不一定**要 AGPL，可以是任何授權。
  這是 AGPL 對「程式」邊界的解讀。
- **import / link**（Python `from erpilot import ...`、frontend `import 'erpilot/...'`）：
  你的 plugin 必須 AGPL-3.0（或相容授權）。

實務上：
- 寫 connector 用 HTTP/SSE 呼叫 erpilot → 可以閉源
- 寫 Python module 直接 import erpilot internals → 必須 AGPL

如果你想 import 但保有閉源權 → 商業授權。

### Q15: 我可以基於 erpilot fork 一份做自己的產品嗎？

**可以，但 AGPL-3.0 條款還是適用整個 fork**：

- 你的 fork 仍是 AGPL-3.0
- 任何客戶 / 使用者都可以向你索取 source
- 你要保留 erpilot 的 copyright notice
- 你**不能**改授權成 MIT / Apache（單向授權移轉，這方向不行）

如果你想 fork 後改授權成商業 → 需要和維護者另議「源碼授權」契約
（這比一般商業授權貴，因為涉及智財轉讓）。

---

## 📞 還有問題？

開 issue 標 `legal/cla` 或 `legal/commercial-license`，或寄 email 至
*(email 待填)*。

⚠️ **再次提醒**：本 FAQ 不是法律意見。重要決策請和你的法務 / 律師確認。
