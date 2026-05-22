# 專案重命名公告 — erpilot → Ouvoca

> **生效日期**：2026-05-22
> **舊名**：erpilot
> **新名**：Ouvoca
> **新倉庫**：https://github.com/fanchanyu/ouvoca
>
> **English version**: [`RENAME_NOTICE_EN.md`](./RENAME_NOTICE_EN.md)

---

## 致過往讀者、貢獻者與潛在客戶

本專案原以「**erpilot**」名稱於 GitHub 對外發布。經事後查證，我們發現
「**erpilot / ERPilot**」名稱於 ERP / SaaS / 顧問服務領域**已有多家機構先行註冊或使用**，
包含但不限於：

- **ERPilot LLC**（美國）— 商業實體 / 商標申請紀錄
- **ERPilot.in**（印度）— ERP 顧問服務
- 以及其他類似拼字（ER Pilot / e-RPilot 等）之 ERP / 顧問服務組織

為**尊重既有商標權人之權益**，避免造成市場混淆、商標爭議或法律糾紛，
本專案自 **2026-05-22** 起正式更名為「**Ouvoca**」。

---

## 我們的立場與承諾

1. ❌ 我們**不主張**對「erpilot / ERPilot」字樣之任何商標權
2. ❌ 我們**不暗示**本專案與前述機構有任何商業 / 技術 / 法律關聯
3. ✅ 我們承認對先行使用者之**商標檢索不周**，特此致歉
4. ✅ 我們在更名前已透過 **4 管道驗證**「Ouvoca」之原創性：
   - USPTO / TIPO 商標資料庫搜尋（無撞名紀錄）
   - 域名 WHOIS 查詢（ouvoca.com / ouvoca.ai 均未註冊）
   - GitHub handle 檢索（無使用者佔用）
   - Google / 公司資料庫綜合搜尋（無顯著競爭品牌）

### 📌 關於相近名稱之主動澄清

| 相近品牌 | 領域 | 與 Ouvoca 之區隔 |
|---|---|---|
| **Avoca AI** (avoca.ai, 2026) | 美國 NYC 之 AI 語音代理（給水電工等行業） | **不同領域**（語音對話 → 預約系統）+ **不同 ICP**（藍領 trades vs 製造業 ERP）+ **不同字首**（A vs O） |
| **Ouva** (SF, healthcare AI) | 醫療 AI | 不同領域 + 不同拼字 |
| **Ouvéa** (法屬太平洋島嶼) | 地名 | 非商業品牌 |

Ouvoca 之**核心定位**：「**對話式 AI-Native ERP for SMB Manufacturers**」/「50-100 人小型製造業之桌機對話式 ERP」— 與上述任一品牌**領域與 ICP 皆無重疊**。

---

## 對既有使用者之具體影響

### 🧑‍💻 對於曾 clone / star / fork 本專案之開發者

- **倉庫網址變更**：`github.com/fanchanyu/erpilot` → `github.com/fanchanyu/ouvoca`
- **GitHub 自動 redirect**：舊 URL 仍可短期使用，但**強烈建議**更新本地 git remote：
  ```bash
  git remote set-url origin https://github.com/fanchanyu/ouvoca.git
  ```
- **Issue / PR 連結**：GitHub 會自動遷移既有編號（建議仍更新書籤）
- **Docker image 標籤**：將於下個 release 改為 `ouvoca/backend` / `ouvoca/frontend`

### 📚 對於既有 commit 歷史紀錄

- Git 歷史**仍保留**「erpilot」字串於 2026-05-22 之前之 commit message / file content
  - **原因**：強制改寫歷史（git filter-branch / BFG）會破壞所有既有 commit hash，影響任何已 fork / clone 之鏡像
  - **政策**：以**重命名 commit** 作為時間分界點，前向所有新內容一律 Ouvoca
- 若你需要乾淨歷史，可從重命名 commit 之後 squash / branch off

### 🏢 對於潛在客戶 / 採購評估者

- ✅ **PDF 客戶文件**（72 份雙語）已全部重建，標題與內文一律 Ouvoca
- ✅ **API 描述 / UI 字串 / Tagline**：「**Ouvoca — Conversational AI-Native ERP for SMB Manufacturers**」
- ✅ **法律授權文件**：CLA / LICENSE-COMMERCIAL / LICENSE-SMALL-BUSINESS 均已同步
- ✅ **既有商業洽談聯絡管道**：不變，仍透過 GitHub Issue（標籤 `legal/cla`）

### 🔧 對於既有部署環境

| 影響項 | 說明 |
|---|---|
| Docker 容器名 | 仍可使用 `erpilot-*`（向後相容），新部署建議改用 `ouvoca-*` |
| 環境變數 | 全部保持原名（無 `ERPILOT_*` 前綴變數），無遷移成本 |
| 資料庫 schema | 完全不變 |
| API endpoint paths | 完全不變（無 `/api/erpilot/*` 路徑） |
| 設定檔位置 | 不變 |

---

## ⚠️ 道歉聲明

對於因本次重命名造成之以下困擾，我們**深感抱歉**：

> 1. 對「**erpilot / ERPilot**」既有商標權人造成**名稱混淆之疑慮**
>    — 我們的疏失，未在專案啟動時完成商標檢索盡職調查。
>
> 2. 對讀者 / 貢獻者 / 客戶造成 **URL 變動 / 書籤失效 / 文件引用更新**之不便
>    — 我們將於 README 顯著位置維護重命名公告，並於 2026 年底前完成所有外部引用之更新請求。
>
> 3. 對社群於 **部落格文章 / 教學影片 / 第三方文件**中之引用未能及時通知
>    — 我們無法逐一通知，但歡迎引用者透過 GitHub Issue 取得本公告之 official statement
>    供您於文章更正時引用。

---

## 我們的承諾

| 承諾 | 行動 |
|---|---|
| 未來命名 | 任何新分支 / 衍生產品**事先完成**多管道商標檢索（USPTO / TIPO / WIPO / 域名 / GitHub） |
| 透明溝通 | 若有 erpilot / ERPilot 既有權利人需溝通，請以 GitHub Issue 聯繫，**7 個工作天內回覆** |
| 法律遵循 | 於 2026 Q3 完成 Ouvoca 之 USPTO 商標申請（class 9 + 42） |
| 既有文件 | v3.37-v3.43 之歷史法律聲明（72 份雙語 PDF）已全部重建為 Ouvoca 版本 |

---

## 對 ERPilot 既有權利人之公開致歉

若本公告為「**ERPilot LLC**」「**ERPilot.in**」或其他 erpilot / ERPilot 既有商標 / 公司名稱權利人首次知悉本專案，我們在此**正式致歉**：

> 對於 2026-05-22 之前本專案以「erpilot」名稱於 GitHub 上對公眾傳布
> 任何可能造成貴司之**品牌混淆、市場混淆、或商譽影響**之內容，
> 我們深感抱歉。
>
> 自 2026-05-22 起本專案已**完全停止**使用「erpilot」名稱，並完成
> 全專案範圍之重命名為「**Ouvoca**」。如貴司認為仍有未盡之處需協商
> 或補救（例如要求 git 歷史清理、特定 commit 撤回、或其他補償措施），
> 請以 **GitHub Issue 或本專案 README 內聯絡方式**直接聯繫維護者。
> 我們承諾於 **7 個工作天內回覆**並進入誠意協商。

---

## 法律聲明

1. 本公告**不構成**任何商標權主張之拋棄、讓與或承認侵權之意思表示。
2. 本專案維護者**承認對「erpilot」字樣之過去使用**，並於發現衝突後**立即停止**並完成本次重命名。
3. 自重命名生效日（2026-05-22）起，本專案**以「Ouvoca」名義**於適用法律下尋求商標保護。
4. 於適用法律所允許之最大範圍內，本專案維護者對 **2026-05-22 之前**任何因「erpilot」名稱使用所衍生之**第三方爭議**，僅依誠信原則協商處理，不主動承擔超出法律強制責任以外之賠償義務。

---

**重命名生效日期**：2026-05-22
**對應 commit**：（rename commit hash — 此 commit 訊息會留紀錄）
**新倉庫**：https://github.com/fanchanyu/ouvoca
**新主品牌**：Ouvoca
**新 Tagline**：「**Ouvoca — Conversational AI-Native ERP for SMB Manufacturers**」/「對話式 AI-Native ERP，給 50-100 人小型製造業」

**作者**：Ouvoca 專案維護團隊
