# Commercial Licensing / 商業授權

erpilot 採 **dual-license（雙軌授權）**：

| 軌道 | 條款 | 適用對象 | 費用 |
|---|---|---|---|
| 🟢 **開源軌** | [AGPL-3.0](./LICENSE) | 內部自用、個人開發、不在意 source disclosure 的客戶 | **免費** |
| 🔵 **商業軌** | 個別協商 | 需閉源整合、ISV 包裝轉售、SaaS 不想公開修改 | 個別報價 |

---

## 🤔 我需要商業授權嗎？決策樹

```
你打算把 erpilot...

├─ 純粹自家公司用，不對外發行？
│    └→ ✅ AGPL-3.0 即可（免費）
│
├─ 改動後內部用，不打算對外發行？
│    └→ ✅ AGPL-3.0 即可（免費，但內部使用者可向你索取改動 source）
│
├─ 改動後做成 SaaS 對外提供服務？（含 hosting 給多客戶）
│    ├─ 願意公開所有改動 source？
│    │    └→ ✅ AGPL-3.0 即可（免費，必須公開 source）
│    └─ 不想公開？
│         └→ 🔵 需要商業授權
│
├─ 嵌入自家產品閉源轉售（ISV / OEM）？
│    └→ 🔵 需要商業授權
│
├─ 公司政策不准用 GPL/AGPL 系列？
│    └→ 🔵 需要商業授權
│
└─ 賣 erpilot 給客戶但客戶要求閉源？
     └→ 🔵 需要商業授權
```

---

## 商業授權包含什麼

**A. 免於 AGPL-3.0 義務**
- 不需要公開 source code
- 不需要把改動回饋給社群
- 可以閉源整合 / 閉源轉售

**B. 加值服務（依方案）**
- 🛠️ **閉源 connector**：鼎新 / 正航 / SAP / Oracle 等 ERP 系統的接入模組
- 📞 **技術支援 SLA**：4 / 8 / 24 小時應答層級可選
- 🎓 **導入顧問**：2 週上線 + 員工訓練 + 客製 schema mapping
- 🔐 **私有部署協助**：on-premise / 客戶 VPC / 多廠 MESH 配置
- 🆕 **早期 access**：新功能比社群早 1-2 個 release 拿到

**C. 智財保護**
- 智慧財產侵權賠償條款（IP indemnification）
- 明確的責任歸屬

---

## 定價結構（範圍指引）

> 確切報價 case by case，看你的部署規模 + 使用情境

| 客戶類型 | 推薦方案 | 範圍（NT$） |
|---|---|---|
| **50-100 人小型製造廠**（直接 end user） | Per-seat 年費 | 30-50 万 / 年 |
| **ISV / SI / 軟體商**（包裝給多客戶） | Per-tenant 年費 | 5-10 万 / 租戶 / 年 |
| **大企業內部 IT**（單一公司多廠） | 站點授權（site license） | 100-300 万 / 年 |
| **要買斷的保守企業**（不愛年費） | Perpetual + maintenance | 一次性 + 20%/年 |

包含：技術支援 SLA、閉源整合權、IP indemnification。

**OEM 條款**：若你拿 erpilot 包成自家產品，請在產品 about 頁 / 文件
明顯處標示 "Powered by erpilot"。

---

## 📨 如何申請

請開一個 [Commercial License Inquiry issue](https://github.com/fanchanyu/erpilot/issues/new?template=commercial-license-inquiry.yml)，
填完表單，維護者會在 5 個工作天內聯絡你。

或寄信至：*(email 待填)*

請在信中提供：
- 公司 / 個人名稱、所在國家
- 預計使用情境（哪個情境 → 上面決策樹哪一支）
- 員工 / 終端使用者規模
- 期望上線時程
- 預算範圍（可選，幫加速報價）

---

## FAQ

詳見 [`docs/COMMERCIAL_LICENSING_FAQ_ZH.md`](./docs/COMMERCIAL_LICENSING_FAQ_ZH.md)。

常見問題：
- ❓ 我只是公司內部用，要不要付錢？→ **不用**（AGPL-3.0 內部使用免費）
- ❓ 用 AGPL 版做 SaaS 但只服務自家集團，要付嗎？→ **要看「對外提供」的定義**
- ❓ 改了 source 但只給內部員工用，要公開嗎？→ **AGPL 不強制，但內部員工可索取**
- ❓ 商業授權可以撤銷嗎？→ **依合約期間，年費到期不續就終止；perpetual 不會被撤銷**

---

## 為什麼選 AGPL-3.0？

不是為了「強迫客戶付錢」，而是因為 AGPL-3.0 是**最強的 copyleft 防護**：

- ✅ 防大廠（Amazon / Google / Microsoft）把 erpilot 拿去包 SaaS 服務閉源轉賣，
  把社群價值收割掉
- ✅ 對「自己用」「研究」「不擔心 source disclosure 的部署」**完全免費**
- ✅ 給「真的有商業需求 + 不能 disclose source」的客戶一個合法管道

我們不做「open core」（核心免費，加值功能要付錢）那一套——
**所有核心功能都在 AGPL 版**。商業授權買的是「不揭露 source 的權利」+
「需要服務 / 整合的 contract」，不是「解鎖隱藏功能」。

---

*This document is informational only. The legally binding terms are in the
respective LICENSE files and individually negotiated commercial agreements.*

*本文件僅供參考。法律效力以各 LICENSE 檔案和個別協商之商業合約為準。*
