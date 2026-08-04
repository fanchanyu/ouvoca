# M1 詳盡規劃：科目表 + 角色矩陣 + 系統組態

> 前置：`docs/TURNKEY_PHASE0_SEED_SPEC.md`（Phase 0 總規格，本檔為 M1 細化）
> 範圍：M1 = P0-1（科目表）+ P0-2（角色矩陣）+ P0-6（系統組態）＋ **M1-0 權限碼對齊審計**（實地勘察發現的新增工作項）
> 工時：**5 工作天**（原估 3.5d + 審計 1d + 緩衝 0.5d）

---

## 0. M1 定義與驗收總覽

### 0.1 交付物

| # | 交付 | 檔案 | 驗收金標準 |
|---|---|---|---|
| M1-0 | 權限碼對齊審計 | `backend/scripts/audit_permission_codes.py`（新）+ `tests/smoke/test_permission_code_alignment.py`（新） | 所有 `require_permission()` 與 tool `required_permission` 引用的碼，100% 存在於 `PermissionDef`；CI 防回歸 |
| M1-1 | 會計科目表種子 | `backend/scripts/seed_accounts.py`（新）+ migration v006 | 79 科目、五硬編碼保護、`fs_line` 全填、雙跑冪等 |
| M1-2 | 角色矩陣落地 | `backend/scripts/seed_permissions.py`（改） | 10 角色全量 UPSERT（is_system 限定）、矩陣與 spec 一致 |
| M1-3 | 系統組態 | `backend/app/models/system_setting.py`（新）+ `backend/app/services/system_defaults.py`（新）+ `backend/app/api/system_settings.py`（新） | 14 項預設 + GET/PUT API + audit |

### 0.2 執行順序（有依賴）

```
M1-0 審計 ──→ 修碼（seed 補碼）──→ M1-2 角色矩陣
M1-1 科目表（獨立，可並行）
M1-3 系統組態（獨立，可並行）
最後：seed.py 串接 → 全測試綠
```

---

## 1. M1-0 權限碼對齊審計（新發現，P0 級）

### 1.1 問題事實（實地勘察確認）

工具宣告的 `required_permission` 與 seed 的 `PermissionDef` **大面積不一致**（下表為已確認部分）：

| 工具引用（存在於 code） | seed 實際定義 | 一致性 |
|---|---|---|
| `tax.einvoice.issue/void/read` | `accounting.einvoice.issue/void/read` | ❌ |
| `tax.tax_id.validate`、`tax.report.read` | `accounting.tax_report` | ❌ |
| `approval.request.read/approve/reject` | **完全沒有 approval module** | ❌ |
| `quality.ncr.create/read` | `quality.nc.read/list` | ❌ |
| `purchase.po.create/approve/read/update` | `purchase.order.*`（僅補丁 `purchase.po.update`） | ❌ |

**影響**：
- 現行 Chat 路徑不查 tool 權限，所以還沒爆；但 `/api/agents/exec/*`（前端 Edit/Delete 按鈕直連）會 403 擋下所有人（非 super_user 一律被拒）—— 等於這些工具對一般使用者「永遠不可用」。
- 一旦 Phase A1（chat 管線 tool 級 RBAC）上線，所有引用未定義碼的 tool 會對所有人 fail-closed。
- `tax.einvoice.read` 被 print_export.py:115 以 `accounting.einvoice.read` 引用 → **兩套碼同時在 codebase 中被使用**，不可只刪一邊。

### 1.2 決策：雙軌 seed（canonical + legacy）

> 以「使用中的碼」全部正式化，不刪任何已引用碼；`is_system=True` 標記；語意對等者記錄 alias 於審計測試。

| 正式化為 canonical | 保留 legacy | 備註 |
|---|---|---|
| `tax.einvoice.issue/void/read` | `accounting.einvoice.issue/void/read` | 新增 tax 模組權限碼（對應 `integrations/einvoice_tw.py`） |
| `tax.tax_id.validate` | `accounting.tax_report` | 新增 |
| `tax.report.read` | — | 新增 |
| `approval.request.read/approve/reject` | — | 新增 approval 模組（對應 `api/approval.py`、`services/approval.py`） |
| `quality.ncr.create/read` | `quality.nc.read/list` | 新增（NCR = NonConformance） |
| `purchase.po.create/approve/read/update` | `purchase.order.*` | 新增（PO 短碼，與長碼同義） |

### 1.3 審計工具規格（`audit_permission_codes.py`）

```
靜態掃描（ast 解析，不 import app）：
  1. backend/app/**/*.py 內 require_permission("...") 字面量
  2. agents/domains/*.py 內 required_permission="..."
  3. 對照 DB 內 PermissionDef.code（跑在 seed 之後）
輸出：
  - MISSING（引用但未 seed）→ 依 §1.2 對照表補 seed，exit 1
  - ORPHAN（seed 但無任何引用）→ 僅警告
  - ALIAS 對照表維持檔（JSON，人工維護）→ tests 引用
exit code：MISSING > 0 → 1（CI gate）
```

### 1.4 測試規格（`test_permission_code_alignment.py`）

```python
def test_all_api_permissions_are_seeded():    # 掃描 require_permission 字面量
def test_all_tool_permissions_are_seeded():   # 掃描 registry required_permission
def test_alias_table_consistent():            # ALIAS 對照表兩邊皆存在
def test_no_orphan_sensitive_permission():    # is_sensitive 碼必須至少被 1 角色引用
```

> 工時：1d（審計工具 0.5d + 補碼 0.3d + 測試 0.2d）

---

## 2. M1-1 會計科目表種子

### 2.1 模型變更（migration `v006_add_account_fs_line.py`，比照 v004/v005 樣式）

```python
# app/models/accounting.py — Account 新增 2 欄
fs_line = Column(String(80))        # 三大報表行對應（見 spec §1.2）
is_system = Column(Boolean, default=False)  # 硬編碼五碼保護
```

- **不做 tenant 化**（單公司部署）；多租戶科目表排 Phase E
- migration 內容：`add_column(fs_line)` + `add_column(is_system)` + `UPDATE accounts SET is_system=1 WHERE code IN ('1100','1200','2100','2200','4100')`（既有安裝回填）

### 2.2 `seed_accounts.py` 設計

```python
# 資料結構：tuple 型別同 spec §1.2（79 筆）
ACCOUNTS: list[dict] = [
    {"code": "1100", "name": "現金及銀行存款", "account_type": "asset",
     "is_debit_normal": True, "parent_code": None, "fs_line": "bs_current_asset",
     "is_system": True},  # 1100/1200/2100/2200/4100 → is_system=True
    ...
]

async def seed_accounts():   # 入口：UPSERT by code
    # 1. 存在 → 更新 name/fs_line/is_system；is_system 永不降級
    # 2. 不存在 → 新增
    # 3. 驗證：借貸方向、父科目存在、fs_line 非空 → 失敗 print + exit 1
    # 4. 報表平衡檢查（資產=負債+權益 的 seed 階段只驗方向，不平衝是資料問題）
```

- **父科目以 `parent_code` 解析**，seed 後二次 pass 補 `parent_id`（避免建立順序問題）
- `seed.py` 串接：`seed_permissions()` → `seed_accounts()` → 既有資料 seed

### 2.3 API 保護（`api/accounting.py` 小改）

| 行為 | 規則 |
|---|---|
| 修改 is_system 科目的 code | 403（BusinessRuleError：「系統內建科目不可改號」） |
| 停用 is_system 科目 | 允許（is_active=False） |
| 刪除科目 | 目前無 delete endpoint → 新增時一併禁止 is_system |

### 2.4 測試（`test_seed_accounts.py`）

```python
def test_account_count_and_hardcoded_codes():   # ≥79 + 五碼 is_system
def test_fs_line_mapping_complete():            # 全部 fs_line 非空且為白名單值
def test_debit_credit_direction():              # 資產/成本/費用 debit；負債/權益/收入 credit
def test_seed_idempotent():                     # 跑兩次，筆數不變
def test_parent_resolution():                   # 無懸空 parent_code
def test_system_account_protected():            # API 改 code → 403
```

> 工時：1.5d（migration 0.5d + seed 0.5d + API/測試 0.5d）

---

## 3. M1-2 角色矩陣落地

### 3.1 現況與問題

- 10 角色已存在（`super_admin/boss/plant_manager/sales_manager/sales_rep/purchaser/warehouse_keeper/accountant/inspector/operator`），用 wildcard pattern + scope 授權（`("sales.*", "tenant")`）
- **角色 seed 是 skip-if-exists（`if existing: continue`）**—— 舊安裝永遠拿不到矩陣修正（v3.50 只修了 permission UPSERT，沒修角色）
- spec §2.2 矩陣中「warehouse」角色實際 code 為 `warehouse_keeper`（以現行 code 為準）

### 3.2 改造：角色全量 UPSERT（is_system 限定）

```python
# seed_permissions.py 主流程修改
for role_spec in ROLES:
    existing = select(RoleDef).where(code==code, tenant_id IS NULL)
    if existing:
        if not existing.is_system: continue        # 客戶複製角色絕不碰
        # SYNC：以 seed 的 (pattern, scope) 清單為準
        #   1. 刪除既有 links（role 內）
        #   2. 依清單重新建立（沿用 _expand_wildcard + dedupe）
    else:
        create（同現況）
```

- **絕不觸碰**：`tenant_id` 非空角色、`is_system=False` 角色（客戶從模板複製的）
- 每個 sync 寫 `PermissionAudit`（change_type=`seed_sync_role`，actor=`system`）

### 3.3 矩陣定義（轉成 pattern+scope，對齊 spec §2.2 與現行 ROLES 差異）

現行 ROLES 與 spec 矩陣的**差異修正點**（M1 要改的）：

| 角色 | 現行缺/錯 | M1 修正 |
|---|---|---|
| boss | 有 `organization.user.create/update`（可建帳號） | 保留（老闆可建帳號合理）；**補** `approval.request.*`（審批權） |
| sales_manager | 無 approval 權 | **補** `approval.request.read/approve/reject` |
| plant_manager | 無 approval 權 | **補** `approval.request.*`；**補** `accounting.ar.read/list`（出貨關聯查詢） |
| purchaser | 無 approval | **補** `approval.request.read` |
| warehouse_keeper | 無調撥權 | **補** `inventory.transfer.*`（若碼存在；否則加碼） |
| inspector | 無 ncr 碼 | M1-0 補 `quality.ncr.*` 後 → **補** 給 inspector |
| operator | `work_order.complete(assigned)` 偏高風險 | 維持（報工是 operator 職責）；確認 scope=assigned |
| 全部 | 無 `tax.*` | M1-0 補碼後，accountant 角色 `accounting.*` wildcard 已涵蓋；boss/plant_manager 補 `tax.report.read` |

- 敏感欄位（`unit_cost`/`credit_limit` strip）：v3.54 已實作，M1 驗證矩陣無 `accounting.*` 的角色（sales_rep/warehouse_keeper/operator/inspector/purchaser）在權限 API 不回傳該欄位即可，**不新增 code**
- RowFilter 種子 6 個既有，符合 spec；新增 `scope.department` 已存在 → 無新增

### 3.4 測試（`test_role_matrix.py`）

```python
MATRIX = {  # spec §2.2 摘要成 fixture：(role, permission_code, expect)
    ("sales_rep", "sales.customer.read", True),
    ("sales_rep", "accounting.journal.read", False),
    ("sales_rep", "inventory.part.read", True),      # 業務可查料但不看成本
    ("warehouse_keeper", "accounting.ar.read", False),
    ("accountant", "production.work_order.release", False),
    ("plant_manager", "production.work_order.release", True),
    ("boss", "approval.request.approve", True),
    ("operator", "production.dispatch.create", True),
    ("operator", "purchase.order.create", False),
    ("sales_manager", "sales.order.ship", True),     # 出貨須主管級（矩陣定義）
}
def test_matrix_positive():  # expect=True 的組合全部命中
def test_matrix_negative():  # expect=False 的組合全部不命中
def test_no_empty_roles():   # 每角色 ≥1 權限
def test_every_role_seeded_scope():  # 角色數 = 10，is_system=True
def test_custom_role_untouched():    # 複製角色在 re-seed 後權限不變
```

> 工時：1.5d（UPSERT 0.5d + 矩陣修正 0.5d + 測試 0.5d；M1-0 的補碼先行）

---

## 4. M1-3 系統組態

### 4.1 模型（migration v006 一併）：`SystemSetting`

```python
class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String(80), primary_key=True)
    value = Column(JSON, nullable=False)
    group = Column(String(40), default="general")   # general/company/finance/backup/ai
    description = Column(String(200))
    is_system = Column(Boolean, default=False)      # seed 預設項目
    updated_by = Column(String(36))
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
```

> 不沿用 `FactoryConfig`（MESH 節點用途）與 `Tenant.settings`（單 JSON blob，併寫會互相覆蓋）。

### 4.2 `system_defaults.py`

```python
DEFAULTS: list[dict] = [   # 14 項，對齊 spec §6.1
    {"key": "company.name",       "value": "",          "group": "company"},
    {"key": "company.tax_id",     "value": "",          "group": "company"},
    {"key": "company.address",    "value": "",          "group": "company"},
    {"key": "company.phone",      "value": "",          "group": "company"},
    {"key": "company.logo_path",  "value": "",          "group": "company"},
    {"key": "currency",           "value": "TWD",       "group": "finance"},
    {"key": "vat_rate",           "value": 0.05,        "group": "finance"},
    {"key": "tax_type",           "value": "taxable",   "group": "finance"},
    {"key": "timezone",           "value": "Asia/Taipei", "group": "general"},
    {"key": "workweek",           "value": ["Mon","Tue","Wed","Thu","Fri"], "group": "general"},
    {"key": "payment_terms_default", "value": "net30",  "group": "finance"},
    {"key": "credit_check_enabled",  "value": True,     "group": "finance"},
    {"key": "inventory_cost_method", "value": "weighted_average", "group": "finance"},
    {"key": "backup.enabled",     "value": True,        "group": "backup"},
    {"key": "backup.retention_days", "value": 30,       "group": "backup"},
    {"key": "ai.daily_limit_per_user", "value": 200,    "group": "ai"},
]

async def seed_system_settings(db): ...   # UPSERT by key，is_system=True
async def get_setting(db, key, default=None) -> Any
async def set_setting(db, key, value, actor_id, reason=None) -> SystemSetting  # 寫 audit
```

**讀取優先序（寫入 README/程式註解）**：`env 變數 > DB SystemSetting > code 預設`
（env 用於啟動/部署層，DB 用於 runtime 調整；`config.py` 讀不到 env 時 service 回 DB 值）

### 4.3 API：`/api/system/settings`

| Method | Path | 權限 | 行為 |
|---|---|---|---|
| GET | `/api/system/settings` | `system.config.read` | 回全部分組設定（敏感組：backup 路徑不在此回） |
| GET | `/api/system/settings/{key}` | `system.config.read` | 單鍵 |
| PUT | `/api/system/settings/{key}` | `system.config.update` | 更新 + `AuditLog` + `PermissionAudit` 不適用（用 AuditLog entity=SystemSetting） |
| DELETE | `/api/system/settings/{key}` | `system.config.update` | is_system 禁止刪除 |

- 前端：Settings.tsx 新增「系統預設」分頁（**列為 M1 選做**；API 先行，UI 排 M2）
- 既有 `onboarding.py` 公司資料寫入 → 改讀寫 `company.*` 設定（M1 只做後端讀寫相容，不重寫 wizard）

### 4.4 `.env.example` 補充

```
# ── System defaults (runtime overridable in Settings) ──
TZ=Asia/Taipei
CURRENCY=TWD
VAT_RATE=0.05
DEFAULT_PAYMENT_TERMS=net30
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
```

### 4.5 測試（`test_system_defaults.py`）

```python
def test_seed_creates_14_defaults()      # 跑 seed 後 ≥14 筆、is_system=True
def test_get_setting_default_fallback()  # 未設 key 回 default
def test_put_updates_and_reads_back()    # PUT → GET 一致
def test_system_key_not_deletable()      # DELETE → 403/400
def test_audit_log_written()             # PUT 後 audit_logs 有記錄
def test_env_precedence()                # os.environ 設值 > DB 值（service 層邏輯）
```

> 工時：1d（模型 0.3d + service 0.3d + API 0.2d + 測試 0.2d）

---

## 5. seed.py 串接與升級路徑

### 5.1 全新安裝順序（`scripts/seed.py`）

```
init_db()
→ scripts.seed_permissions.seed_permissions()   # 既有（含 M1-0 補碼 + M1-2 角色 UPSERT）
→ scripts.seed_accounts.seed_accounts()         # 新
→ scripts.seed_system_settings()（system_defaults 內）  # 新
→ 既有：部門/員工/admin/示範資料
```

### 5.2 既有安裝升級路徑

```
git pull → update.bat
→ alembic upgrade head（v006：fs_line / is_system / system_settings 表）
→ seed 全量重跑（全部 idempotent）：
    權限碼補齊（M1-0）→ 角色矩陣 sync（M1-2，is_system 限定）
    → 科目表出現（M1-1）→ 系統預設出現（M1-3）
→ 既有客戶資料、複製角色、override 全部不動
```

### 5.3 回滾防護

- 角色 sync 前先 snapshot `PermissionAudit`（before_state 全量 links）→ 出錯可還原
- 科目 seed 不刪除任何既有科目（只新增/更新）

---

## 6. WBS 總表

| # | 任務 | 檔案 | 依賴 | 工時 |
|---|---|---|---|---|
| M1-0.1 | 審計工具（ast 掃描） | `scripts/audit_permission_codes.py` | — | 0.5d |
| M1-0.2 | seed 補碼（tax/approval/quality.ncr/purchase.po + alias） | `scripts/seed_permissions.py` | 0.1 | 0.3d |
| M1-0.3 | 對齊測試 + alias 檔 | `tests/smoke/test_permission_code_alignment.py`、`backend/data/permission_alias.json` | 0.2 | 0.2d |
| M1-1.1 | migration v006（Account 2 欄 + SystemSetting 表） | `alembic/versions/v006_*.py`、`app/models/accounting.py`、`app/models/system_setting.py` | — | 0.5d |
| M1-1.2 | seed_accounts.py（79 科目 + 驗證） | `scripts/seed_accounts.py` | 1.1 | 0.5d |
| M1-1.3 | 科目 API 保護 + 測試 | `app/api/accounting.py`、`tests/smoke/test_seed_accounts.py` | 1.2 | 0.5d |
| M1-2.1 | 角色 UPSERT（sync 邏輯 + audit） | `scripts/seed_permissions.py` | 0.2 | 0.5d |
| M1-2.2 | 矩陣修正（7 角色差異點） | `scripts/seed_permissions.py` ROLES | 2.1 | 0.5d |
| M1-2.3 | 矩陣測試 | `tests/smoke/test_role_matrix.py` | 2.2 | 0.5d |
| M1-3.1 | SystemSetting model + system_defaults service | `app/services/system_defaults.py` | 1.1 | 0.6d |
| M1-3.2 | settings API + audit | `app/api/system_settings.py`（router 註冊進 main.py） | 3.1 | 0.2d |
| M1-3.3 | 設定測試 + .env.example | `tests/smoke/test_system_defaults.py`、`.env.example` | 3.2 | 0.2d |
| M1-4 | seed.py 串接 + 升級路徑驗證 | `scripts/seed.py` | 全部 | 0.3d |
| — | **合計** | | | **~5.0d** |

---

## 7. 驗收劇本（M1 專用，跑「全新」與「升級」兩軌）

```
【全新軌】
0:00  python -m scripts.seed（SQLite 全新）
0:05  檢查點 1：PermissionDef ≥ 120 碼（含新增 tax/approval/ncr/po）；無 MISSING
0:10  檢查點 2：Account = 79；五硬編碼 is_system=True；fs_line 全填
0:15  檢查點 3：RoleDef = 10（is_system）；sales_rep 無 accounting.*
0:20  檢查點 4：SystemSetting ≥ 14 筆；GET /api/system/settings 回完整分組
0:25  權限實測：sales_rep 登入 → POST /api/agents/exec/create_purchase_order → 403
                     → POST /api/chat-v2 講「建採購單」→ 出 ConfirmCard（不是 403）
       （驗證：chat 與 exec 路徑行為符合 Phase A1 前之現況，無回歸）
0:30  pytest -q → 全綠（701 既有 + 6 支新）

【升級軌】
0:00  用 v3.55 舊 DB（含客戶自訂角色/override）
0:05  alembic upgrade head → 無錯誤
0:10  python -m scripts.seed → 科目/權限/設定出現；自訂角色 links 數不變
0:15  檢查 PermissionAudit：seed_sync_role 記錄含 before_state
0:20  完成 ✅
```

---

## 8. 風險與對策

| 風險 | 影響 | 對策 |
|---|---|---|
| 權限碼標準化後，既有工具 required_permission 與角色授權失配（如 inspector 原本有 quality.* wildcard，現行 seed 是 quality.* → 涵蓋 ncr） | 權限意外收緊/放寬 | M1-2.3 矩陣測試逐一 assert；審計測試進 CI |
| 角色全量 sync 覆寫管理員手動調整的系統角色權限 | 設定被 seed 覆蓋 | 只 sync is_system 角色；sync 前 PermissionAudit snapshot + 文檔明示「系統角色以 seed 為準，客製請複製角色」 |
| `fs_line` 白名單值日後與 Phase 1 報表產生器對不上 | 報表錯行 | fs_line 值域集中在 `app/services/fs_statements.py` 常數（M1 先建常數檔，Phase 1 直接引用） |
| 科目 is_system 保護阻礙既有安裝客製科目 | 客戶不能改 1100 名稱 | 只鎖 code/刪除，允許改名/停用（is_system 只保編號完整性） |
| `tax.*`/`accounting.einvoice.*` 雙軌造成新 code 誤用 | 未來 drift | alias JSON 檔 + 審計測試強制：新引用碼必須在 alias 或 canonical 宣告 |
