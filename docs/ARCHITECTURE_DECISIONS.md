# 架構決策紀錄（ADR：Architecture Decision Records）

> **本檔目的**：記錄專案重大架構決策的「為什麼」，不只是「怎麼做」。讓未來任何人（包括未來的我們）能理解當時的取捨。
>
> **格式（Michael Nygard ADR）**：
> - **狀態**：Proposed / Accepted / Deprecated / Superseded
> - **脈絡（Context）**：當時面對什麼問題？
> - **決策（Decision）**：選了什麼？
> - **後果（Consequences）**：好壞影響？

---

## ADR-001：採用 RBAC + Row-Level Security，不從 Day 1 上 ABAC

**狀態**：Accepted（2026-05-14）

**脈絡**：
- 客戶 10-100 人，但業務 A 不能看業務 B 的客戶
- 外協廠不能看別家外協廠的工單
- 需要規模化授權（不能每人一個 ACL）
- 但小廠不需要 ABAC 那種「金額 > X 時才能簽核」的複雜屬性權限

**決策**：
1. **採用 5 層模型**：Tenant → User → Role → Permission → Row-Level Scope
2. **RBAC 為核心**（10 個預設角色）
3. **Row-Level Scope 6 種預設**（all/tenant/department/team/own/assigned）
4. **JSON 欄位保留 ABAC 擴展空間**（RolePermissionLink.conditions）

**後果**：
- ✅ 小廠 10 分鐘配完權限
- ✅ 業務跳槽帶不走客戶（own scope）
- ✅ 未來 ABAC 不用 ALTER TABLE（用 JSON conditions）
- ⚠️ Scope 衝突時取最寬鬆（多角色衝突時可能太寬，但小廠可控）

---

## ADR-002：多租戶 Schema-shared，Day 1 就上 tenant_id

**狀態**：Accepted（2026-05-14）

**脈絡**：
- 客戶會成長：從 10 人廠 → 50 人廠 → 100 人廠
- 多廠 / 外協 / 客戶 portal 必須資料隔離
- 我們不會幫每個客戶獨立部署一套（成本太高）

**選項評估**：

| 方案 | 優點 | 缺點 | 決定 |
|---|---|---|---|
| **A. Schema-per-tenant** | 強隔離 | 維運複雜、跨租戶查詢困難 | ❌ |
| **B. DB-per-tenant** | 最強隔離 | 部署一套就一份 DB | ❌（過度） |
| **C. Shared schema + tenant_id 欄位** | 維運簡單、運算便宜 | 程式紀律要求高 | ✅ |

**決策**：
- 全部業務表共享同一 schema，加 `tenant_id` 欄位
- 預設值 "HQ"，向後相容既有單廠資料
- 每個 query 都自動加 `WHERE tenant_id = ?`（透過 `apply_row_filter`）
- index 在 `tenant_id` 欄位

**後果**：
- ✅ 部署簡單：一份 Docker、一份 DB、N 個 tenant
- ✅ 跨廠查詢容易（HQ 看全廠合計）
- ✅ Backup / migrate / 升級成本低
- ⚠️ 必須在 service / API 層紀律：永遠加 tenant filter
- ⚠️ 防呆機制：在 `apply_row_filter` 預設 fallback 為 `tenant` scope

---

## ADR-003：採用 SQLite (dev) → PostgreSQL (prod) 雙軌

**狀態**：Accepted（2026-05-13）

**脈絡**：
- 客戶第一次安裝想要「零配置」
- 但生產環境需要 50+ 人併發、長期存放數年資料

**決策**：
- Dev / 試用：SQLite + aiosqlite
- Prod：PostgreSQL + asyncpg
- 切換靠 `DATABASE_DRIVER` 環境變數
- Alembic 同時支援兩者

**後果**：
- ✅ 試用門檻最低（`docker compose up`）
- ✅ 客戶滿意後切 PG，相容 99% 既有功能
- ⚠️ JSON 欄位行為略有不同（SQLite JSON1 vs PG JSONB），程式碼用標準 SQLAlchemy JSON 避開

---

## ADR-004：Event-Driven 設計但**不採用** Event Sourcing

**狀態**：Accepted（2026-05-14）

**脈絡**：
- 庫存、訂單、工單變動頻繁
- 客戶需要即時通知（推播、SSE）
- 但 Event Sourcing 學習曲線陡、查詢複雜

**決策**：
- **採用 Event-Driven**：EventBus + Domain Events + SSE
- **不採用 Event Sourcing**：仍以 CRUD 為主、用 audit_logs 做變更紀錄
- 任何 service 寫操作 → emit DomainEvent → 通知 + SSE + Audit

**後果**：
- ✅ 取得 Event-Driven 80% 好處（通知、解耦、可重播）
- ✅ 避開 Event Sourcing 90% 複雜度（聚合根、Snapshot、CQRS）
- ⚠️ 想要完整時序回溯，要靠 audit_logs（雖然不如 ES 完美）

---

## ADR-005：MESH 多廠為一等公民，不是後期插件

**狀態**：Accepted（2026-05-14）

**脈絡**：
- 客戶實際結構：本廠 10-20 人 + 外協鏈 N 家
- 外協廠不會註冊 ERP、不會學新系統
- 競品（SAP / 正航 / 鼎新）都是中央集中式，做不到

**決策**：
- 從 Day 1 就有 `tenants` 表 + `mesh_role` 欄位（central / node / partner）
- 工廠節點獨立部署：`factory_node.py` 只回**聚合結果**，不傳原始資料（VMI 友善）
- HQ 用 Multi-Agent + LLM 統一查詢介面（自然語言跨廠）
- 外協廠用 LINE Bot 不用註冊（QR 內含一次性 token）

**後果**：
- ✅ 競爭差異化護城河（傳統 ERP 做不到）
- ✅ 資料主權（每廠保留自家明細）
- ✅ 外協廠零導入成本
- ⚠️ MESH 跨節點查詢有 timeout 風險，需 fallback 機制（已設計 `MESH_TIMEOUT_SECONDS`）

---

## ADR-006：LLM Provider Abstraction，不綁特定廠商

**狀態**：Accepted（2026-05-13）

**脈絡**：
- 客戶在 Anthropic / OpenAI / DeepSeek / 地端 Ollama 之間有不同偏好
- LLM 是核心依賴，不能 vendor lock-in

**決策**：
- `app/agents/engine.py:chat_completion()` 分發到 4 個 provider
- 統一輸入輸出格式（OpenAI tool calling spec）
- Anthropic 透過 schema 轉換相容
- Ollama 本地模型供 MESH 工廠節點隱私場景

**後果**：
- ✅ 客戶可選最便宜或最隱私的 provider
- ✅ 切換無痛（改 .env 一行）
- ⚠️ 各家 LLM tool-calling 品質不一致，需要持續測試

---

## ADR-007：Multi-Agent Tool-Scoping 而非 single mega-agent

**狀態**：Accepted（2026-05-14）

**脈絡**：
- 26+ tools 給單一 agent 處理，LLM 容易誤呼叫
- 例如「庫存」問題不該誤觸發「會計」工具

**決策**：
- 用 IntentClassifier（加權關鍵字）先分類
- 10 個 domain agent，每個只看自己 4-6 個 tools
- General agent 作為 fallback

**後果**：
- ✅ Tool 誤觸大幅下降
- ✅ 各 agent 系統提示可專精化
- ✅ 新增 domain 不影響既有
- ⚠️ Intent 分類錯誤時可能無法處理跨域問題（未來可考慮 routing chain）

---

## ADR-008：行動端不用 PWA，用 Expo Native + LINE Bot 雙軌

**狀態**：Accepted（2026-05-14）

**脈絡**：
- 老闆（王董）用 LINE，不會裝 App
- 業務（小陳）需要相機掃 QR、語音輸入、推播
- 廠長（林廠長）需要即時警示

**決策**：
- **LINE Bot**：給老闆、外協廠（不裝 App 的人）
- **Expo Native App**：給業務、廠長、倉管（需要相機/掃描的人）
- **不做 PWA**：相機 / 推播在瀏覽器體驗差

**後果**：
- ✅ 涵蓋所有 persona
- ✅ LINE Bot 零安裝門檻
- ⚠️ 兩套介面要維護（但共用 API + Multi-Agent）

---

## ADR-009：權限變更走 Audit Trail，**不採用** Approval Workflow

**狀態**：Accepted（2026-05-14）

**脈絡**：
- 小廠老闆通常一聲令下就過了
- 多階審批太重、太慢

**決策**：
- 權限授予/撤銷直接寫 `permission_audit` 表
- 必填 `reason` 欄位
- 不導入多階審批工作流（schema 有但不啟用）
- 高風險權限（如 `purchase.order.approve`）標 `is_sensitive=true`

**後果**：
- ✅ 流程快（小廠最在乎）
- ✅ 仍有稽核軌跡
- ⚠️ 上市櫃客戶可能要求多階審批 → 屆時啟用（schema 已備）

---

## ADR-010：DB 膨脹採用「冷熱分層」而非分區

**狀態**：Proposed → 待 Phase 5+ 實作（2026-05-14）

**脈絡**：
- 5 年後預估資料量：audit_logs 900 萬、inventory_transactions 90 萬、conversation_logs 36 萬
- 客戶會抱怨查詢變慢
- 但不是所有資料都需要熱存取（90% 查詢命中近 30 天）

**選項評估**：

| 方案 | 優 | 缺 | 決定 |
|---|---|---|---|
| **A. Postgres Partitioning** | 標準作法 | 維運複雜 | 🟡 P5+ |
| **B. 冷熱分層（30d 熱 + 歷史冷）** | 簡單、最快 | 跨表查詢稍麻煩 | ✅ |
| **C. TimescaleDB** | 時序最佳化 | 多一個依賴 | 🟡 P5+ |
| **D. 不處理** | 不做 | 5 年後爆炸 | ❌ |

**決策**：
- Phase 1-4：不處理（資料量還可控）
- Phase 5+：實作冷熱分層
  - 熱表：`audit_logs`（近 90 天）
  - 冷表：`audit_logs_archive`（每月歸檔）
  - 用 cron job 搬資料
  - 報表查詢用 UNION ALL
- 詳細見 [DATA_LIFECYCLE.md](./DATA_LIFECYCLE.md)

**後果**：
- ✅ 熱表永遠快（索引小）
- ✅ 歷史資料仍可查（只是稍慢）
- ⚠️ 報表 SQL 要記得 UNION 兩張表

---

## ADR-011：前端用 Tailwind + 自製 Design System，不用 MUI/Antd

**狀態**：Accepted（2026-05-14）

**脈絡**：
- 客戶想要「現代化、好看」
- 但 MUI / Ant Design bundle 大（300KB+）、客製化困難

**決策**：
- Tailwind utility CSS + 自製 UI 元件庫
- Design tokens（color/typography/spacing）寫在 tailwind.config
- 自製：Card / Button / Toast / Skeleton / EmptyState / ErrorState / Badge
- 共約 20 個元件就涵蓋所有頁面

**後果**：
- ✅ Bundle 小（27KB CSS / 218KB JS gzipped to 5.5KB / 68KB）
- ✅ 風格統一、品牌感強
- ✅ 客戶要改色票超快（改 tokens 即可）
- ⚠️ 開發初期慢一些（要造輪子）→ 但只造 20 個元件，可接受

---

## ADR-012：Demo Bypass 自動偵測 JWT_SECRET，無需手動關閉

**狀態**：Accepted（2026-05-14）

**脈絡**：
- 試用時希望 Bearer "demo" 就能進入（不用建帳號）
- 但 production 絕對不能保留這後門
- 不能仰賴開發者「記得關掉」

**決策**：
- `settings.demo_bypass_active = ALLOW_DEMO_BYPASS and "change-me" in JWT_SECRET`
- 一旦設定真實 JWT_SECRET，demo bypass **自動失效**
- UI 上 health endpoint 顯示 `demo_bypass: true/false`

**後果**：
- ✅ 試用體驗極佳
- ✅ Production 安全（不可能不小心開著）
- ✅ Login 頁依 health endpoint 決定是否顯示「Demo Mode」按鈕

---

## ADR 索引（依日期倒序）

| ID | 標題 | 日期 | 狀態 |
|---|---|---|---|
| ADR-012 | Demo Bypass 自動偵測 | 2026-05-14 | Accepted |
| ADR-011 | Tailwind + 自製 Design System | 2026-05-14 | Accepted |
| ADR-010 | DB 冷熱分層 | 2026-05-14 | Proposed |
| ADR-009 | 權限走 Audit 而非審批 | 2026-05-14 | Accepted |
| ADR-008 | Expo Native + LINE Bot 雙軌 | 2026-05-14 | Accepted |
| ADR-007 | Multi-Agent Tool-Scoping | 2026-05-14 | Accepted |
| ADR-006 | LLM Provider Abstraction | 2026-05-13 | Accepted |
| ADR-005 | MESH 為一等公民 | 2026-05-14 | Accepted |
| ADR-004 | Event-Driven 非 Event Sourcing | 2026-05-14 | Accepted |
| ADR-003 | SQLite + PostgreSQL 雙軌 | 2026-05-13 | Accepted |
| ADR-002 | 多租戶 Shared Schema | 2026-05-14 | Accepted |
| ADR-001 | RBAC + Row-Level | 2026-05-14 | Accepted |

---

## 如何新增 ADR

1. 編號往下接（ADR-013, ADR-014, ...）
2. 用同樣的 5 段格式：脈絡 / 決策 / 選項評估（可選）/ 後果 / 狀態
3. 必須有日期
4. 若取代舊 ADR，舊的標記 Superseded by ADR-XXX
