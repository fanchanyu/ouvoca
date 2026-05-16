# 商業授權 FAQ（繁體中文）

> 這份 FAQ 不是法律意見，只是常見問題的「**直觀答案**」。
> 真正下決定前請和你的法務 / 律師確認，或開 [Commercial License Inquiry issue](https://github.com/fanchanyu/erpilot/issues/new?template=commercial-license-inquiry.yml) 給維護者。

---

## 🟢 一般使用問題

### Q1: 我只是自己一個人想玩 erpilot，要付錢嗎？

**完全免費。** AGPL-3.0 不限制「使用」（use），只限制「散布」（distribute）。
你個人安裝、跑、改、學習，都 OK，不用通知任何人。

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
