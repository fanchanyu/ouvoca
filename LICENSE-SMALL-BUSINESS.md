# Ouvoca Small Business License (SBL) v1.0

> **中文 / English bilingual** — both versions are equally authoritative.
> Last updated: 2026-05-16
>
> This is **one of three** license tracks for Ouvoca:
> 🟢 [AGPL-3.0](./LICENSE) · 🌱 **Small Business License (this file)** · 🔵 [Commercial](./LICENSE-COMMERCIAL.md)

---

## TL;DR / 一句話版

**If your organization has ≤ 20 concurrent Ouvoca users AND meets the
exclusion criteria below, you may use Ouvoca — including all closed-source
connectors — for free, without AGPL-3.0 source disclosure obligations.**

**只要你公司同時在線 Ouvoca 用戶 ≤ 20 人，且符合下列排除條件，你可以
完全免費使用 Ouvoca 全套功能（含閉源 connector），且不必依 AGPL-3.0 揭露改動 source。**

---

## 1. Eligibility / 適用條件

To use Ouvoca under this Small Business License, **ALL** of the following
must be true:

要採本 Small Business License 條款，以下條件**全部**都要成立：

### 1.1 Scale Limit / 規模上限

The **peak concurrent active users** of your Ouvoca deployment, measured
over any rolling 24-hour window, **must not exceed 20**.

"Concurrent active user" means: a logged-in user whose session has
performed at least one authenticated action (request, page load, or
WebSocket/SSE event) within the preceding 15 minutes.

你的 Ouvoca 部署在**任一連續 24 小時內的同時在線活躍用戶峰值**不得超過 **20 人**。

「同時在線活躍用戶」定義：已登入用戶，且該用戶 session 在過去 **15 分鐘內**
有至少一次經驗證的行為（請求、頁面載入、WebSocket / SSE event）。

### 1.2 Single Legal Entity / 單一法人

The Ouvoca deployment must be used **by and within a single legal
entity** (one company, one government agency, one school, etc.). Use
across multiple legal entities — even within the same corporate group —
is NOT covered by this license.

Ouvoca 部署必須由**單一法人**（一家公司、一個政府機關、一所學校等）
**內部使用**。跨法人使用——即使同一企業集團——**不適用**本授權。

### 1.3 No External Service / 不對外提供服務

You must NOT use Ouvoca to provide a service to parties outside your
legal entity, including (but not limited to):

你**不得**用 Ouvoca 對你的法人以外提供服務，包含但不限於：

- (a) SaaS / hosted service to third-party customers
      （SaaS / 託管服務給第三方客戶）
- (b) Multi-tenant deployments serving multiple organizations
      （多租戶部署服務多個組織）
- (c) Internal services exposed to vendors, customers, or partners
      （延伸到供應商 / 客戶 / 合作夥伴的內部服務）

### 1.4 No Embedding / 不嵌入產品

You must NOT embed Ouvoca (in whole or in part) into any product,
service, or system that is sold, licensed, distributed, or otherwise
provided to third parties.

你**不得**將 Ouvoca（全部或部分）嵌入任何銷售 / 授權 / 散布 / 提供給
第三方的產品、服務、或系統。

This includes: ISV / OEM packaging, software resale, embedding in
hardware products.

包含：ISV / OEM 包裝、軟體轉售、嵌入硬體產品。

### 1.5 No Consultancy Distribution / 顧問散布禁止

If you are a system integrator, IT consultancy, or service provider, you
may deploy Ouvoca for individual clients ONLY when **each such client
independently qualifies under this license**. You may NOT distribute
modifications of Ouvoca to multiple clients without commercial licensing.

如果你是 SI / IT 顧問 / 服務商，你可以為個別客戶部署 Ouvoca，但**每個
客戶**必須**獨立符合**本授權條件。你**不得**未取得商業授權即把 Ouvoca
的修改版散布給多個客戶。

---

## 2. Grant / 授權範圍

Subject to compliance with Section 1, the Project Maintainer grants
You a **non-exclusive, royalty-free, non-transferable** license to:

在符合 Section 1 的條件下，專案維護者授予你**非專屬、免權利金、不可移轉**的
授權，允許你：

- (a) **Use** Ouvoca for any internal business purpose, including in
       production;
       將 Ouvoca 用於任何內部商業目的（含 production 環境）；
- (b) **Modify** Ouvoca's source code for internal use;
       修改 Ouvoca source code 供內部使用；
- (c) **Use closed-source connectors** (鼎新 / 正航 / SAP / Oracle, etc.)
       made available by the Project Maintainer **for technical connectivity only**;
       使用維護者提供的閉源 connector（鼎新 / 正航 / SAP / Oracle 等）**僅作為技術連線元件**；

       ⚠️ **Note — Third-Party ERP Licensing**: The connector grant under
       this license covers **Ouvoca's own technical components only**.
       Connecting Ouvoca to Your incumbent commercial ERP system
       (e.g., products from vendors such as Workflow / ChengHang / SAP B1 /
       Vitals) is a separate matter: each vendor's license agreement may
       treat shared or service-account connections differently, and the
       specifics depend on Your contract with that vendor. **You** are
       responsible for confirming authorization scope with the incumbent
       ERP vendor and obtaining any required written authorization before
       enabling a connector. The Project Maintainer **does not participate
       in or represent You in** any contracts or licensing matters with
       third-party ERP vendors, and, to the maximum extent permitted by
       applicable law, assumes no liability for consequences arising from
       enabling a connection without obtaining appropriate authorization.
       See
       [`docs/EXTERNAL_DB_LICENSING_NOTICE_EN.md`](./docs/EXTERNAL_DB_LICENSING_NOTICE_EN.md)
       / [中文](./docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md).

       ⚠️ **附註 — 第三方 ERP 授權**：本授權所提供之 connector 僅為
       **Ouvoca 自身的技術元件**。將 Ouvoca 串接到貴司**現有商用 ERP**
       系統（例如 Workflow / ChengHang / SAP B1 / Vitals 等廠商之產品）
       為另一議題：各廠商之授權合約對「以共用或服務帳號連線」之規定可能不同，
       具體請依貴司與該廠商之合約為準。**貴司**負責與原 ERP 廠商確認授權
       範圍，並於必要時取得書面授權，方啟用 connector。維護者**不參與、
       不代理**貴司與第三方 ERP 廠商間之合約 / 授權事務；於適用法律所允許
       之最大範圍內，對客戶未取得適當授權即啟用連線所衍生之後果不承擔責任。
       詳見
       [`docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./docs/EXTERNAL_DB_LICENSING_NOTICE_ZH.md)。

- (d) **Deploy** Ouvoca across multiple physical facilities (MESH nodes)
       within Your single legal entity;
       在你的單一法人下跨多廠（MESH nodes）部署；
- (e) **Keep modifications private** — You are NOT obligated to disclose
       Your modifications, derivative works, or configuration, even when
       users access Ouvoca over a network. The AGPL-3.0 §13 ("Network
       use is distribution") clause is **explicitly waived** under this
       license.
       **保留修改不公開** — 你**沒有**揭露改動 / 衍生作品 / 設定的義務，
       即使使用者透過網路存取 Ouvoca。**AGPL-3.0 §13**「網路使用即散布」
       條款於本授權**明示豁免**。

---

## 3. Restrictions / 限制條款

### 3.1 Attribution / 署名要求

You must retain a visible "Powered by Ouvoca Community" attribution in
at least one user-facing location (e.g. application footer, "About"
dialog, or settings page). You may not represent Ouvoca as Your own
product.

你必須在至少一處使用者可見處（如：應用程式 footer / "About" 對話框 /
設定頁）保留可見的 "Powered by Ouvoca Community" 署名。你**不得**把
Ouvoca 表現為你自己的產品。

### 3.2 No Sublicense / 不得再授權

You may NOT sublicense Ouvoca to third parties. Each end-user
organization must independently obtain its own license (AGPL-3.0, Small
Business, or Commercial).

你**不得**對第三方再授權 Ouvoca。每個終端使用組織必須**各自**取得自己的
授權（AGPL-3.0 / Small Business / Commercial）。

### 3.3 No Warranty / 無擔保

Ouvoca is provided "**AS IS**", without warranty of any kind, express
or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose, and noninfringement.

Ouvoca 以「**現狀**」提供，不附任何明示或默示擔保，包含但不限於商業性、
特定用途適用性、和不侵權之擔保。

### 3.4 No Support SLA / 無 SLA 支援

Under this license, You are entitled only to community support
(GitHub Issues, Discord, etc.). You are NOT entitled to any service-
level agreement (SLA), response time guarantee, or dedicated support.

本授權下你只享有社群支援（GitHub Issues / Discord 等），**沒有**任何
SLA、應答時間保證、或專屬支援。

### 3.5 No IP Indemnification / 無智財侵權賠償

The Project Maintainer does NOT provide intellectual property
indemnification under this license. If You require IP indemnification,
You must upgrade to a Commercial License.

維護者**不**在本授權下提供智慧財產侵權賠償。如需 IP indemnification，
請升級商業授權。

---

## 4. Upgrade Trigger / 升級觸發

If at any point any of the eligibility criteria in Section 1 cease to
hold, you have **30 calendar days** ("Grace Period") to either:

當 Section 1 的任一條件不再成立時，你有 **30 個日曆日**（"Grace Period"）
做以下其一：

(a) Restore compliance (e.g., reduce concurrent users below 20); OR
    恢復合規（例如：把同時在線降回 20 以下）；或
(b) Apply for a Commercial License (see [LICENSE-COMMERCIAL.md](./LICENSE-COMMERCIAL.md)); OR
    申請商業授權（見 [LICENSE-COMMERCIAL.md](./LICENSE-COMMERCIAL.md)）；或
(c) Migrate to AGPL-3.0 terms (which requires disclosing Your
    modifications to Your users).
    改採 AGPL-3.0 條款（這意味著你必須揭露改動給你的使用者）。

During the Grace Period, You may continue using Ouvoca under this
license. After the Grace Period, continued use without (b) or migration
to (c) constitutes a license violation.

Grace Period 內你可繼續按本授權使用 Ouvoca。Grace Period 後若沒申請商業
授權或改採 AGPL-3.0，即構成違反授權。

---

## 5. Audit Right / 抽查權

The Project Maintainer reserves the right, no more than **once per
calendar year** and with at least **30 days written notice**, to
request from You evidence of compliance, including:

維護者保留每年至多**一次**、且**提前 30 日書面通知**後，要求你提供合規
證據的權利，包含：

- Peak concurrent user counts from Your analytics dashboard
- Confirmation of single-legal-entity use
- Confirmation of non-embedding and non-redistribution

You may redact business-sensitive information; the maintainer's interest
is solely confirmation of Section 1 compliance.

你可遮蔽商業敏感資訊；維護者的關切僅限於確認 Section 1 合規。

> 實務上，維護者**不會**主動抽查 — 我們相信 SMB 老闆的誠信。
> 此條款僅供極端爭議情況使用。

---

## 6. Termination / 終止

This license terminates automatically if You materially violate any of
its terms and fail to cure within 30 days of written notice.

如你重大違反本授權條款且未在書面通知後 30 日內補正，本授權自動終止。

Upon termination, You must either (a) cease all use of Ouvoca, or
(b) transition to AGPL-3.0 or Commercial terms.

授權終止後，你必須(a)停止所有 Ouvoca 使用，或(b)轉換到 AGPL-3.0 或
商業授權條款。

---

## 7. Governing Law / 準據法

This license is governed by the laws of the Republic of China (Taiwan).
Any disputes shall be resolved in the Taiwan Taipei District Court.

本授權以中華民國（台灣）法律為準據法。爭議由台灣台北地方法院管轄。

---

## 8. Contact / 聯絡

For questions about this license, eligibility verification, or upgrade
inquiries, please contact:

關於本授權的問題、適用性確認、或升級諮詢，請聯絡：

- GitHub Issue: https://github.com/fanchanyu/ouvoca/issues (label `legal/small-business`)
- Email: *(to be filled in by maintainer)*

---

*This license is custom-drafted for Ouvoca's tri-license model and
inspired by Elastic License v2's "third-party limitation" clauses,
Sentry's Functional Source License, and BSL (Business Source License)
patterns — but with the distinctive ≤20-concurrent-user free tier as
Ouvoca's strategic differentiator for Taiwan SMB market.*

*本授權專為 Ouvoca 三軌制設計，參考 Elastic License v2 的「第三方使用限制」
條款、Sentry FSL、和 BSL 模式 — 但 ≤20 concurrent user 免費 tier 是
Ouvoca 為 Taiwan SMB 市場專屬設計的戰略差異化。*
