# Commercial Licensing / 商業授權

erpilot 採 **三軌授權（tri-license）**：

| 軌道 | 條款 | 適用對象 | 費用 |
|---|---|---|---|
| 🟢 **開源軌** | [AGPL-3.0](./LICENSE) | 願意揭露 source 的所有人、社群協作 | **免費** |
| 🌱 **小小企業軌** | Small Business License | **≤ 20 concurrent users** 的單一公司，非 ISV / SaaS / SI | **完全免費**（含閉源 connector）|
| 🔵 **商業軌** | 個別協商 | > 20 concurrent users、ISV / OEM、SaaS provider、大企業 | 個別報價 |

> 🌱 **「20 以內全免費」戰略**：對齊 erpilot 的承諾「**讓中小和小小企業可以快速上手**」。
> Taiwan SMB 有海量 1-20 人廠，我們把整套（含鼎新/正航/SAP connector）給你白用，
> 等你長到 21 人並且離不開 erpilot，再聊商業合約。

---

## 🤔 我需要哪一軌？決策樹

```
你打算把 erpilot...

├─ 純自家公司內部用，不對外發行？
│    │
│    ├─ 同時在線使用者 ≤ 20 人？
│    │    └→ 🌱 小小企業軌（完全免費，含所有 connector）
│    │
│    └─ 同時在線使用者 > 20 人？
│         ├─ 願意公開所有改動 source？
│         │    └→ ✅ AGPL-3.0 即可（免費）
│         └─ 不想公開改動？
│              └→ 🔵 需要商業授權
│
├─ 改動後做成 SaaS 對外提供服務？（hosting 給多客戶）
│    ├─ 願意公開所有改動 source？
│    │    └→ ✅ AGPL-3.0 即可（免費，必須公開 source）
│    └─ 不想公開？
│         └→ 🔵 需要商業授權（小小企業軌**不適用** SaaS）
│
├─ 嵌入自家產品閉源轉售（ISV / OEM）？
│    └→ 🔵 需要商業授權（小小企業軌**不適用** ISV / OEM）
│
├─ 你是 SI / 顧問，幫多家客戶部署？
│    ├─ 你只幫部署，每個客戶各自適用其軌？
│    │    └→ 每個客戶獨立判斷（多半可走 🌱 小小企業軌）
│    └─ 你做改動然後散布給多家客戶？
│         └→ 🔵 需要商業授權
│
├─ 公司政策不准用 GPL/AGPL 系列？
│    └→ 🔵 需要商業授權（小小企業軌也是非 AGPL）
│
└─ 純個人開發 / 學習 / 研究？
     └→ ✅ AGPL-3.0 或 🌱 小小企業軌都可
```

---

## 🌱 小小企業軌（Small Business License）

**目標**：讓 Taiwan 1-20 人廠 / 新創 / 工作室**完全免費**用 erpilot，
**含閉源 connector**（鼎新 / 正航 / SAP / Oracle），無 AGPL source 揭露義務。

### 適格條件（**全部**都要成立）

1. ✅ **同時在線使用者 ≤ 20**（24 小時內任一時刻峰值）
2. ✅ **單一法人公司**內部使用（不能跨子公司、跨集團）
3. ✅ **不嵌入給第三方的產品 / 服務**（不能 ISV / OEM 包裝賣）
4. ✅ **不是 SI / 顧問**對外做專案賣
5. ✅ **不對外提供 SaaS / hosted service**

### 包含什麼

| 項目 | 小小企業軌 |
|---|---|
| 核心 ERP 功能（多代理 LLM、ConfirmCard、CRUD）| ✅ 全部 |
| Schema Mapping AI | ✅ |
| 開源 connector（CSV / Excel / SQLite / Postgres / MySQL）| ✅ |
| **閉源 connector（鼎新 / 正航 / SAP / Oracle）** | ✅ **含**（v3.0 戰略：全 connector 對小小企業免費）|
| 多廠 MESH | ✅（單一法人下不限廠數）|
| AGPL source 揭露義務 | ❌ **免除** |
| 商業授權費 | ❌ **NT$0** |

### 不包含什麼（要付費升級）

| 項目 | 商業軌 |
|---|---|
| 多公司 / 多租戶 hosting | 🔵 商業軌 |
| 嵌入自家產品轉售（ISV/OEM）| 🔵 商業軌 |
| SLA 技術支援（4 / 8 / 24h 應答）| 🔵 商業軌 |
| 移除「Powered by erpilot Community」標示 | 🔵 商業軌 |
| 智財侵權賠償條款（IP indemnification）| 🔵 商業軌 |
| 早期 access（新功能比社群早拿）| 🔵 商業軌 |
| 客製化 schema mapping 顧問 | 🔵 商業軌（或自助）|

### 升級觸發

- **同時在線突破 21 人**（24 小時峰值）→ 自動 30 天 grace period → 必須申請商業授權或回退 AGPL-3.0
- **情境改變**（變 SaaS / ISV / SI）→ 立即需要商業授權

### 如何使用 / 怎麼 enforce？

**Honor system**（榮譽制）+ 技術 hook：

- erpilot 內建 [Analytics dashboard](./README.md#try-the-event-stream) 會記錄 peak concurrent users
- 突破 20 時自動跳出 toast：「您的同時在線使用者已達 X 人，請確認授權軌」
- 沒有 hard gate（不會強制 disable 功能）—— 我們相信小廠老闆
- 維護者保留**抽查權**（極端情況下要求看 analytics record）



---

## 🔵 商業軌包含什麼

**A. 規模 + 使用情境授權**
- 同時在線 > 20 人（小小企業軌不適用）
- ISV / OEM 嵌入閉源產品
- SaaS 多租戶 hosting
- 多公司 / 多集團跨用

**B. 加值服務（依方案）**
- 📞 **技術支援 SLA**：4 / 8 / 24 小時應答層級可選
- 🎓 **導入顧問**：2 週上線 + 員工訓練 + 客製 schema mapping
- 🔐 **私有部署協助**：on-premise / 客戶 VPC / 多廠 MESH 規模化
- 🆕 **早期 access**：新功能比社群早 1-2 個 release 拿到
- 🏷️ **品牌權**：可移除 "Powered by erpilot Community" 標示

**C. 智財保護**
- 智慧財產侵權賠償條款（IP indemnification）
- 明確的責任歸屬

> ⚠️ 注意：閉源 connector（鼎新 / 正航 / SAP / Oracle）對所有軌道都開放——
> 小小企業軌**免費含**，AGPL 軌也可用（但要按 AGPL 揭露你自己的改動），
> 商業軌包含在合約裡。

---

## 定價結構（範圍指引）

> 確切報價 case by case，看你的部署規模 + 使用情境

| 客戶類型 | 推薦方案 | 範圍（NT$） |
|---|---|---|
| 🌱 **小小企業（≤20 concurrent）** | 小小企業軌 | **NT$ 0**（含 connector）|
| **50-100 人小型製造廠**（>20 concurrent） | Per-seat 年費 | 30-50 万 / 年 |
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
