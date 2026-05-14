# 權限模型設計（PERMISSION MODEL）

> **設計哲學**：
> - **商業化**：客戶 10 分鐘配完權限，不用找工程師
> - **使用者友善**：勾選即可（不寫 JSON）、UI 顯示中文、立即生效
> - **架構輕量**：RBAC + Row-Level（不過度 ABAC）、單次 query 完成檢查、可快取
> - **DB 易擴充**：JSON 欄位保彈性、多租戶從 Day 1、軟刪除 + 版本號
>
> **核心定位**：權限系統是**架構級基礎**，不是某個 Phase 的功能。所有現有 / 未來 API 都必須通過權限檢查。

---

## 1. 五層權限模型總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                      L1: Tenant (租戶/廠別)                       │
│            HQ / 主廠 / 鍍鋅廠 / 外協廠 / 客戶 Portal              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 隔離單位
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      L2: User (使用者)                            │
│                員工、外協廠老闆、客戶採購                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 1:N (時效授權)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      L3: Role (角色)                              │
│         admin / boss / sales / plant_manager / outsource          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ M:N (含條件)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  L4: Permission (權限碼)                          │
│      sales.order.read / inventory.transaction.create / ...        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 每個權限附帶 scope
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  L5: Row-Level Scope (行級範圍)                   │
│       all / tenant / department / team / own / assigned           │
└─────────────────────────────────────────────────────────────────┘
```

### 1.1 五層的職責邊界

| 層 | 解決什麼問題 | 例子 |
|---|---|---|
| **L1 Tenant** | 「不同公司/廠別不能互看資料」 | HQ 看不到 OUTSOURCE-WU 的私有數據 |
| **L2 User** | 「誰是這個操作的主體」 | 王董 / 小陳 / 老吳 |
| **L3 Role** | 「批量授權，避免逐人設定」 | sales 角色直接給整組業務員 |
| **L4 Permission** | 「能做什麼動作」 | sales.order.create（建銷售單） |
| **L5 Row-Level** | 「能看到哪些資料」 | 業務 A 只能看自己的客戶 |

---

## 2. 資料表設計（8 張表）

> 既有 Phase 0 已有 `roles`, `permissions`, `employee_roles`, `role_permissions` 4 張表（schema 級 RBAC）。
> 本設計**擴充 + 強化**，不破壞既有結構。

### 2.1 `tenants` ⭐ 新增

> 多廠 / 外協 / 客戶 portal 隔離單位。也是 MESH 戰略基石。

```sql
CREATE TABLE tenants (
    id           VARCHAR(36) PRIMARY KEY,
    code         VARCHAR(50) UNIQUE NOT NULL,    -- "HQ", "FACTORY-A", "OS-WU"
    name         VARCHAR(200) NOT NULL,           -- "總部", "鍍鋅外協廠-吳老闆"
    tenant_type  VARCHAR(30) NOT NULL,            -- hq / factory / outsource / customer_portal
    parent_id    VARCHAR(36),                     -- 外協廠隸屬於哪個主廠（樹狀）
    mesh_role    VARCHAR(20),                     -- central / node / partner
    is_active    BOOLEAN DEFAULT true,
    settings     JSON,                            -- 廠特定設定（時區、貨幣...）
    created_at   DATETIME NOT NULL,
    updated_at   DATETIME NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES tenants(id)
);
CREATE INDEX idx_tenants_type ON tenants(tenant_type);
```

**所有業務表都加 `tenant_id` 欄位**（Phase 1 同步遷移）：
- `parts.tenant_id`, `inventory.tenant_id`, `purchase_orders.tenant_id`, ...
- 預設值為 "HQ"，向後兼容

### 2.2 `permissions` ⭐ 強化版

> 既有表已存在，本設計**升級欄位**。

```sql
CREATE TABLE permissions (
    id              VARCHAR(36) PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,  -- "sales.order.create"
    resource        VARCHAR(50) NOT NULL,          -- "sales.order"
    action          VARCHAR(30) NOT NULL,          -- "read/create/update/delete/approve/export/list"
    module          VARCHAR(30) NOT NULL,          -- "sales", "purchase", "production"...
    name_zh         VARCHAR(100),                  -- "建立銷售單"
    description     TEXT,                          -- "可建立新的銷售訂單"
    is_system       BOOLEAN DEFAULT false,         -- 系統內建（不可刪）
    is_sensitive    BOOLEAN DEFAULT false,         -- 高敏感（需簽核）
    risk_level      VARCHAR(10) DEFAULT 'low',     -- low / medium / high / critical
    created_at      DATETIME NOT NULL
);
CREATE INDEX idx_permissions_resource ON permissions(resource);
CREATE INDEX idx_permissions_module ON permissions(module);
```

### 2.3 `roles` ⭐ 強化版

```sql
CREATE TABLE roles (
    id            VARCHAR(36) PRIMARY KEY,
    tenant_id     VARCHAR(36),                  -- NULL = 全租戶共用（系統角色）
    code          VARCHAR(50) NOT NULL,          -- "sales_rep", "plant_manager"
    name_zh       VARCHAR(100) NOT NULL,         -- "業務員", "廠長"
    description   TEXT,
    is_system     BOOLEAN DEFAULT false,         -- 內建模板（可複製不可刪）
    is_active     BOOLEAN DEFAULT true,
    priority      INTEGER DEFAULT 50,            -- 衝突時優先級（高蓋低）
    icon          VARCHAR(20),                   -- emoji，UI 顯示用
    color         VARCHAR(20),                   -- 顏色標籤
    created_at    DATETIME NOT NULL,
    updated_at    DATETIME NOT NULL,
    UNIQUE(tenant_id, code),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
CREATE INDEX idx_roles_tenant ON roles(tenant_id);
```

### 2.4 `role_permissions` ⭐ 強化版（加入 scope）

```sql
CREATE TABLE role_permissions (
    role_id       VARCHAR(36) NOT NULL,
    permission_id VARCHAR(36) NOT NULL,
    scope         VARCHAR(20) DEFAULT 'tenant',  -- all/tenant/department/team/own/assigned
    conditions    JSON,                          -- 額外條件（未來 ABAC 用）
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);
```

### 2.5 `user_roles` ⭐ 強化版（時效 + 代理）

```sql
CREATE TABLE user_roles (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    role_id         VARCHAR(36) NOT NULL,
    tenant_id       VARCHAR(36) NOT NULL,        -- 在哪個 tenant 下擔此角色
    granted_at      DATETIME NOT NULL,
    granted_by      VARCHAR(36),                  -- 誰授權的
    expires_at      DATETIME,                     -- ★ 時效授權（NULL = 永久）
    delegation_from VARCHAR(36),                  -- 若是代理，from 誰
    reason          TEXT,                         -- 授權原因（稽核用）
    is_active       BOOLEAN DEFAULT true,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
CREATE INDEX idx_user_roles_user ON user_roles(user_id, is_active);
CREATE INDEX idx_user_roles_expires ON user_roles(expires_at) WHERE expires_at IS NOT NULL;
```

### 2.6 `permission_overrides` ⭐ 新增（個別授權）

> 不想為了一次例外建一個 role。

```sql
CREATE TABLE permission_overrides (
    id               VARCHAR(36) PRIMARY KEY,
    user_id          VARCHAR(36) NOT NULL,
    permission_code  VARCHAR(100) NOT NULL,        -- "sales.order.export"
    grant_or_revoke  VARCHAR(10) NOT NULL,         -- 'grant' / 'revoke'
    resource_type    VARCHAR(50),                  -- 可選：限定到某資源類型
    resource_id      VARCHAR(36),                  -- 可選：限定到單一 record
    granted_by       VARCHAR(36) NOT NULL,
    granted_at       DATETIME NOT NULL,
    expires_at       DATETIME,                     -- 時效（建議必填）
    reason           TEXT NOT NULL,                -- ★ 必填，稽核用
    is_active        BOOLEAN DEFAULT true,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_permission_overrides_user ON permission_overrides(user_id, is_active);
```

### 2.7 `row_filters` ⭐ 新增（行級過濾規則庫）

> 把「業務只能看自己的客戶」這種規則做成可配置。

```sql
CREATE TABLE row_filters (
    id           VARCHAR(36) PRIMARY KEY,
    code         VARCHAR(50) UNIQUE NOT NULL,    -- "sales.order.own_only"
    resource     VARCHAR(50) NOT NULL,            -- "sales.order"
    scope        VARCHAR(20) NOT NULL,            -- own/department/team/assigned
    filter_expr  JSON NOT NULL,                   -- {"created_by": "{user.id}"}
    description  TEXT,
    is_system    BOOLEAN DEFAULT false,
    created_at   DATETIME NOT NULL
);
```

### 2.8 `permission_audit` ⭐ 新增（權限變更稽核）

```sql
CREATE TABLE permission_audit (
    id              VARCHAR(36) PRIMARY KEY,
    actor_id        VARCHAR(36) NOT NULL,         -- 操作者
    target_user_id  VARCHAR(36),                  -- 被影響的使用者
    target_role_id  VARCHAR(36),                  -- 被影響的角色
    change_type     VARCHAR(30) NOT NULL,         -- grant_role/revoke_role/modify_perm/...
    before_state    JSON,
    after_state     JSON,
    ip_address      VARCHAR(50),
    user_agent      VARCHAR(500),
    created_at      DATETIME NOT NULL
);
CREATE INDEX idx_perm_audit_target ON permission_audit(target_user_id, created_at DESC);
```

---

## 3. Permission Code 命名規範

### 3.1 格式：`<module>.<resource>.<action>`

| 部分 | 內容 | 範例 |
|---|---|---|
| **module** | ERP 模組 | sales / purchase / production / inventory / ... |
| **resource** | 資源名稱（單數） | order / customer / part / supplier |
| **action** | 動作 | read / list / create / update / delete / approve / export |

### 3.2 完整 Permission Code 對照表（共 ~95 個）

| 模組 | 資源 | 可用 actions |
|---|---|---|
| **inventory** | part | read, list, create, update, delete, export |
| inventory | transaction | read, list, create, export |
| inventory | inventory | read, list, adjust |
| **purchase** | supplier | read, list, create, update, delete |
| purchase | order | read, list, create, update, delete, approve, export, receive |
| **production** | product | read, list, create, update, delete |
| production | bom | read, list, create, update, delete |
| production | work_order | read, list, create, update, release, complete, delete |
| production | dispatch | read, list, create, update |
| **sales** | customer | read, list, create, update, delete |
| sales | order | read, list, create, update, delete, approve, confirm, ship, export |
| **quality** | inspection | read, list, create, complete |
| quality | nc | read, list, create |
| quality | capa | read, list, create, update |
| **accounting** | account | read, list, create, update |
| accounting | journal | read, list, create, post, export |
| accounting | ar | read, list, create, update, export |
| accounting | month_close | execute |
| **warehouse** | zone | read, list, create, update |
| warehouse | bin | read, list, create, update |
| warehouse | pick | read, list, create, complete |
| warehouse | cycle_count | read, list, create |
| **crm** | lead | read, list, create, update, convert |
| crm | opportunity | read, list, create, update, change_stage |
| **mps_mrp** | mps | read, list, create, run |
| mps_mrp | mrp | read, list, run |
| **outsource** | order | read, list, create, dispatch, receive |
| **organization** | employee | read, list, create, update, delete |
| organization | department | read, list, create, update, delete |
| organization | role | read, list, create, update, delete |
| organization | user | read, list, create, update, delete |
| **system** | config | read, update |
| system | tenant | read, list, create, update |
| system | permission | read, list, grant, revoke |
| system | audit | read, list, export |
| **ai** | agent | use, configure |
| **mesh** | factory | read, list, register, query |

→ 詳細 95 條清單在 `scripts/seed_permissions.py`。

### 3.3 Wildcard 支援

| 寫法 | 意義 |
|---|---|
| `*` | 所有權限（僅 superuser） |
| `sales.*` | 所有 sales 模組權限 |
| `sales.order.*` | 所有 sales.order 動作 |
| `*.read` | 所有 read 動作 |

---

## 4. Row-Level Scope 規格

### 4.1 6 種預設 scope

| Scope | 意義 | SQL WHERE 條件 |
|---|---|---|
| **all** | 跨租戶看全部（系統管理員） | （不加條件） |
| **tenant** | 看本租戶全部 | `tenant_id = :user.tenant_id` |
| **department** | 看本部門 | `created_by IN (SELECT id FROM employees WHERE dept_id = :user.dept_id)` |
| **team** | 看本團隊（同部門同層級） | `created_by IN (... team)` |
| **own** | 只看自己建的 | `created_by = :user.employee_id` |
| **assigned** | 只看派給自己的 | `assigned_to = :user.employee_id` |

### 4.2 自訂 scope（透過 row_filters 表）

例：「中區業務只看中區客戶」
```json
{
  "code": "sales.customer.region_central",
  "resource": "sales.customer",
  "filter_expr": {"region": "central"}
}
```

---

## 5. 預設角色模板（10 個）

> 客戶開帳即用，10 分鐘上線。

### 5.1 角色矩陣總覽

| 角色 code | 中文名 | 對應 persona | 預設 scope |
|---|---|---|---|
| `super_admin` | 系統管理員 | IT | all |
| `boss` | 老闆 | 王董 | tenant |
| `plant_manager` | 廠長 | 林廠長 | tenant |
| `sales_manager` | 業務主管 | – | tenant |
| `sales_rep` | 業務員 | 小陳 | own |
| `purchaser` | 採購 | 阿玲（採購） | tenant |
| `warehouse_keeper` | 倉管 | 阿玲（倉管） | tenant |
| `accountant` | 會計 | – | tenant |
| `inspector` | 品檢員 | – | tenant |
| `operator` | 作業員 | – | assigned |
| `outsource_partner` | 外協廠 | 老吳 | assigned |
| `customer_portal` | 客戶端 | – | own |

### 5.2 各角色預設權限（精選顯示）

**boss（王董）**：
```
sales.*.read, sales.*.list, sales.*.export
purchase.*.read, purchase.*.list, purchase.*.export
purchase.order.approve              ← 高金額 PO 簽核
production.*.read, production.*.list
inventory.*.read, inventory.*.list
accounting.*.read, accounting.*.list, accounting.*.export
mps_mrp.*.read
ai.agent.use, ai.agent.configure
mesh.factory.*
```

**sales_rep（小陳）**：
```
sales.customer.read (scope: own)         ← 只看自己客戶
sales.customer.create
sales.customer.update (scope: own)
sales.order.read (scope: own)
sales.order.create
sales.order.update (scope: own)
inventory.part.read                       ← 報價需要查料
inventory.inventory.read                  ← 查庫存
ai.agent.use
```

**plant_manager（林廠長）**：
```
production.*.read, production.*.list
production.work_order.create
production.work_order.release
production.work_order.update
production.dispatch.*
outsource.order.*
quality.*.read
inventory.*.read
mps_mrp.*.read
ai.agent.use
```

**purchaser（阿玲，採購視角）**：
```
purchase.*.read, purchase.*.list, purchase.*.create
purchase.order.update
purchase.order.receive
purchase.supplier.*
inventory.part.read
inventory.transaction.create              ← 收貨入庫
ai.agent.use
```

**outsource_partner（老吳）**：
```
outsource.order.read (scope: assigned)    ← 只看派給他的
outsource.order.complete (scope: assigned)
ai.agent.use (limited tools)              ← LINE Bot 限定工具集
```

→ 完整矩陣見 `scripts/seed_permissions.py`。

---

## 6. 商業化 UX 設計

### 6.1 管理者體驗（給 IT / 老闆 / HR）

**畫面 1：角色管理**
```
┌─ 角色管理 ─────────────────────────────────┐
│                                              │
│  [+ 新增角色]      [從模板複製] ▼            │
│                                              │
│  📋 角色列表                                 │
│  ┌────────────────────────────────────────┐│
│  │ 🛡️ 系統管理員        2 人  [編輯] [複製]││
│  │ 👔 老闆              1 人  [編輯] [複製]││
│  │ 👨‍💼 業務員（小陳專屬）3 人  [編輯] [複製]││
│  │ 👨‍🏭 廠長              1 人  [編輯] [複製]││
│  │ 🔗 外協廠            5 人  [編輯] [複製]││
│  └────────────────────────────────────────┘│
└──────────────────────────────────────────────┘
```

**畫面 2：權限勾選（不寫 JSON）**
```
┌─ 編輯角色：sales_rep（業務員） ──────────────┐
│                                              │
│  📦 庫存                                      │
│  ☑ 查看零件   ☐ 建立零件   ☐ 修改零件      │
│  ☑ 查看庫存   ☐ 庫存調整                    │
│                                              │
│  💰 銷售                                      │
│  ☑ 查看訂單 [👁 範圍: 只看自己 ▼]            │
│  ☑ 建立訂單                                  │
│  ☑ 修改訂單 [👁 範圍: 只看自己 ▼]            │
│  ☐ 刪除訂單   ☐ 簽核訂單                    │
│                                              │
│  [儲存]  [取消]                              │
└──────────────────────────────────────────────┘
```

**畫面 3：個別授權（臨時/例外）**
```
┌─ 給小陳臨時授權 ─────────────────────────────┐
│                                              │
│  使用者：小陳                                │
│  權限：  匯出採購單（PO Export）             │
│  原因：  協助 5 月底結帳                     │
│  到期：  2026-05-31 23:59                    │
│                                              │
│  [送出]                                      │
└──────────────────────────────────────────────┘
```

### 6.2 一般員工體驗

- 權限變更後**立刻生效**（不需重新登入）
- 看不到的功能直接**從選單隱藏**（不是按了才說「無權限」）
- LINE Bot 收到無權限請求時，禮貌回覆 + 建議找誰申請

### 6.3 AI Agent 整合

LLM 可呼叫的權限管理 tools：

| Tool | 範例 |
|---|---|
| `list_user_permissions` | 「小陳有什麼權限？」 |
| `grant_temporary_permission` | 「給小陳臨時開放匯出 PO 一週」 |
| `revoke_permission` | 「收回阿玲的庫存調整權限」 |
| `who_can_approve_po` | 「誰能簽核 100 萬以上 PO？」 |

→ 這些 tools 自身需要 `system.permission.grant/revoke` 權限才能執行。

---

## 7. 架構師思維：精簡輕量的實作

### 7.1 權限檢查單次 query

❌ **錯誤做法**（N+1）：
```python
user = get_user()
for permission_code in required:
    if not has_permission(user, permission_code):  # 每次都 query
        raise
```

✅ **正確做法**（單次 load + cache）：
```python
@lru_cache(maxsize=10000)
async def load_user_permissions(user_id: str, tenant_id: str) -> frozenset[tuple[str, str]]:
    """一次 load 所有 (permission_code, scope)，cache 5 分鐘。"""
    # 一個 JOIN query 拿到所有效權限
    ...
```

### 7.2 FastAPI Dependency 風格

```python
@router.post("/sales/orders")
async def create_so(
    data: SalesOrderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("sales.order.create")),
):
    ...

@router.get("/sales/orders")
async def list_so(
    db: AsyncSession = Depends(get_db),
    user_ctx: UserContext = Depends(require_permission("sales.order.list")),
):
    query = select(SalesOrder)
    query = apply_row_filter(query, user_ctx, "sales.order")  # 自動加 WHERE
    return await db.execute(query)
```

### 7.3 快取策略

| 層 | 快取對象 | 失效時機 | 工具 |
|---|---|---|---|
| 記憶體 | user_permissions | TTL 5 分鐘 / 權限變更廣播 | `functools.lru_cache` |
| 記憶體 | role_permissions | TTL 10 分鐘 / 系統重啟 | dict |
| Redis（可選） | 跨節點同步失效 | publish/subscribe | Phase 5+ |

權限變更 → emit event `permission.changed` → 各節點清快取。

### 7.4 資料庫設計兼容性

- **既有表保留**：roles / permissions / role_permissions / employee_roles 不刪
- **欄位增量加**：`ALTER TABLE permissions ADD COLUMN module VARCHAR(30)`
- **舊 employee_roles 仍可用**：作為 user_roles 的子集
- **migration 順序**：先加表 → 加 FK → 跑 backfill seed → 啟用 enforcement

---

## 8. 演進路徑

### 8.1 v1.0（Phase 1 立即實作）

- [x] 8 張表完整 schema
- [x] 95 個 permission code seed
- [x] 10 個預設角色 seed
- [x] `require_permission` decorator
- [x] `apply_row_filter` 自動加 WHERE
- [x] 6 種預設 scope
- [x] 後端 API 全面套用（既有 87 個 endpoint 全部加保護）
- [x] 前端選單依權限隱藏

### 8.2 v1.5（Phase 2）

- [ ] 個別授權（permission_overrides）UI
- [ ] 代理 / 委派功能
- [ ] 權限變更 audit log
- [ ] 時效自動回收（cron）
- [ ] AI Agent 權限管理 tools

### 8.3 v2.0（Phase 5+，按需要）

- [ ] 自訂 row filter（不只預設 6 種）
- [ ] ABAC 屬性權限（如「金額 > 100 萬才能簽核」）
- [ ] 動態權限（依時間/地點/IP）
- [ ] SSO / SAML / OIDC
- [ ] 跨租戶查詢（HQ 統計多廠）

---

## 9. 典型情境驗證（10 個）

### S-01 業務看不到別人的客戶
- 小陳查 GET /api/sales/customers
- 系統：載入小陳的權限 → 找到 `sales.customer.read` scope=`own`
- 自動加 WHERE `created_by = '小陳'`
- 小陳只看到自己建的客戶

### S-02 廠長能看全廠生產
- 林廠長查 GET /api/production/work-orders
- 系統：scope=`tenant`
- 自動加 WHERE `tenant_id = 'HQ'`
- 看到全廠工單

### S-03 外協廠只能看派給自己的
- 老吳掃 QR 進 LINE
- 查 outsource.order.read scope=`assigned`
- 自動加 WHERE `assigned_outsource_id = '老吳'`
- 只看到派給他的

### S-04 老闆出差，臨時授權代理
- 王董：「我請假，林廠長 5/20-5/22 代理我」
- 系統：建立 user_roles row（delegation_from=王董, expires_at=5/22）
- 林廠長期間擁有王董權限
- 5/23 自動失效

### S-05 高金額 PO 需老闆簽核
- 阿玲建 PO $200 萬
- 系統：檢查 `purchase.order.approve` + risk_level=`critical`
- 阿玲無此權限 → 進入 ApprovalRequest 流程
- 推 LINE 給王董：「待簽核 PO」

### S-06 新員工入職
- HR 新增員工小李
- 從模板選 `sales_rep` 角色
- 一鍵完成，2 分鐘上工

### S-07 員工離職
- HR 標記離職
- 系統：user.is_active=false + 所有 user_roles 軟刪
- 立即失去所有權限

### S-08 IT 想稽核：誰改過誰的權限？
- 查 permission_audit 表
- 看到完整變更歷史（誰、何時、改了什麼、為什麼）

### S-09 老闆要看「最近一週權限變更」
- 王董 LINE 問
- AI 呼叫 list_recent_permission_changes
- 摘要回覆

### S-10 多廠 MESH 場景
- 王董問「全廠 M6 庫存」
- 系統：王董有 `mesh.factory.query` 權限
- HQ 並發查 N 個廠 → 聚合
- 各廠用本地權限（廠長僅自己廠的庫存可查）

---

## 10. 實作優先級

> 對應到 [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) 新增的 G-RBAC 系列。

| # | 任務 | 優先 | 工時 | Phase |
|---|---|---|---|---|
| G-RBAC-01 | 8 張表 model + alembic migration | P0 | 1d | P1 |
| G-RBAC-02 | seed 95 permissions + 10 roles | P0 | 0.5d | P1 |
| G-RBAC-03 | `require_permission` decorator | P0 | 0.5d | P1 |
| G-RBAC-04 | `apply_row_filter` helper | P0 | 1d | P1 |
| G-RBAC-05 | 既有 87 endpoints 全部加保護 | P0 | 1.5d | P1 |
| G-RBAC-06 | 權限管理 API（CRUD） | P0 | 1d | P1 |
| G-RBAC-07 | 前端權限管理頁 | P1 | 2d | P1 |
| G-RBAC-08 | 前端依權限隱藏選單 | P1 | 0.5d | P1 |
| G-RBAC-09 | 個別授權 / 時效 / 代理 UI | P2 | 1.5d | P2 |
| G-RBAC-10 | AI Agent 權限管理 tools | P2 | 1d | P2 |
| G-RBAC-11 | permission_audit 寫入點完整化 | P1 | 0.5d | P1 |
| G-RBAC-12 | 時效自動回收 cron | P2 | 0.5d | P2 |

**Phase 1 合計**：~7 工作日（含現有 endpoint 套保護）

---

**最後更新**：2026-05-14
**設計者**：Claude
**Review 待辦**：使用者確認 10 個預設角色是否覆蓋實際需求
