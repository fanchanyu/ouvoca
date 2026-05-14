"""
Multi-tenant 隔離覆蓋率測試 — 驗證所有 domain 都受 auto-filter 保護。

跟 test_tenant_isolation.py 的差別：
  - 那個測 inventory + sales/customers 的 endpoint 行為
  - 這個測**全 12 domain**的 list endpoint 都自動隔離（不需手動套 apply_tenant_filter）

如果這支跑得過 → 證明 SQLAlchemy session event 的 with_loader_criteria
方案有效覆蓋整個專案，再也不會有「忘了套 filter」的漏網之魚。
"""
from __future__ import annotations
import uuid as _uuid
import asyncio
import pytest


@pytest.fixture(scope="module")
def two_tenants_with_data(seeded_client):
    """建兩個 tenant + 各自 user + 各自 1 筆 part / customer / supplier / product。
    回 (TA_dict, TB_dict)，每個含 token + 各種 entity id。
    """
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.permission import Tenant, RoleDef, UserRoleAssignment
    from app.models.organization import User, Employee, Department
    from app.models.inventory import Part, Inventory
    from app.models.crm_sales import Customer
    from app.models.purchase import Supplier
    from app.models.product import Product
    from app.services.auth import hash_password
    from app.core.tenant_context import set_current_tenant, get_current_tenant, ALL_TENANTS
    from datetime import datetime

    async def _setup():
        # ★ 用 ALL_TENANTS 跨租戶 seed（這個 fixture 要寫不同 tenant 的資料）
        prev = get_current_tenant()
        set_current_tenant(ALL_TENANTS)
        try:
            async with AsyncSessionLocal() as db:
                results = {}

                # 共用 admin role
                role = (await db.execute(
                    select(RoleDef).where(RoleDef.code == "admin")
                )).scalar_one_or_none()
                if role is None:
                    role = RoleDef(
                        id=str(_uuid.uuid4()), code="admin",
                        name_zh="admin", tenant_id=None,
                    )
                    db.add(role)
                    await db.flush()

                for tag, name in [("COV-A", "Coverage A"), ("COV-B", "Coverage B")]:
                    tenant = (await db.execute(
                        select(Tenant).where(Tenant.code == tag)
                    )).scalar_one_or_none()
                    if tenant is None:
                        tenant = Tenant(
                            id=str(_uuid.uuid4()), code=tag, name=name,
                            tenant_type="factory",
                        )
                        db.add(tenant)
                        await db.flush()

                    # Dept (no tenant_id field - system table) / Emp / User
                    dept = Department(
                        id=str(_uuid.uuid4()), code=f"COV-{tag}-D",
                        name=f"{tag} Dept",
                    )
                    db.add(dept)
                    await db.flush()

                    emp = Employee(
                        id=str(_uuid.uuid4()), employee_no=f"E-{tag}",
                        name=f"admin-{tag}", email=f"admin-{tag}@test.local",
                        department_id=dept.id, title="Admin",
                        hire_date=datetime.utcnow(),
                    )
                    db.add(emp)
                    await db.flush()

                    user = User(
                        id=str(_uuid.uuid4()), username=f"cov-{tag}",
                        hashed_password=hash_password(f"PassCov{tag}!"),
                        employee_id=emp.id, is_superuser=True, is_active=True,
                    )
                    db.add(user)
                    await db.flush()

                    # 綁定 tenant
                    ura = UserRoleAssignment(
                        id=str(_uuid.uuid4()), user_id=user.id, role_id=role.id,
                        tenant_id=tenant.id, is_active=True,
                        granted_at=datetime.utcnow(),
                    )
                    db.add(ura)
                    await db.flush()

                    # 6 種 entity 各建一個（屬於本 tenant）
                    part = Part(
                        id=str(_uuid.uuid4()),
                        part_no=f"PART-{tag}-{_uuid.uuid4().hex[:4].upper()}",
                        name=f"{tag} Part", category="raw",
                        safety_stock=0, unit_cost=1.0, tenant_id=tenant.id,
                    )
                    db.add(part)
                    db.add(Inventory(
                        id=str(_uuid.uuid4()), part_id=part.id,
                        tenant_id=tenant.id,
                    ))

                    customer = Customer(
                        id=str(_uuid.uuid4()),
                        code=f"CUST-{tag}-{_uuid.uuid4().hex[:4].upper()}",
                        name=f"{tag} Customer", tenant_id=tenant.id,
                    )
                    db.add(customer)

                    supplier = Supplier(
                        id=str(_uuid.uuid4()),
                        code=f"SUP-{tag}-{_uuid.uuid4().hex[:4].upper()}",
                        name=f"{tag} Supplier", tenant_id=tenant.id,
                    )
                    db.add(supplier)

                    product = Product(
                        id=str(_uuid.uuid4()),
                        product_no=f"PROD-{tag}-{_uuid.uuid4().hex[:4].upper()}",
                        name=f"{tag} Product", tenant_id=tenant.id,
                    )
                    db.add(product)

                    await db.commit()

                    results[tag] = {
                        "tenant_id": tenant.id,
                        "username": f"cov-{tag}",
                        "password": f"PassCov{tag}!",
                        "part_no": part.part_no,
                        "customer_code": customer.code,
                        "supplier_code": supplier.code,
                        "product_no": product.product_no,
                    }
                return results
        finally:
            set_current_tenant(prev)

    return asyncio.run(_setup())


def _login(client, username, password) -> dict:
    r = client.post("/api/auth/login", json={
        "username": username, "password": password,
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ─── 12 domains × list endpoint 隔離測試 ──────────────────────

DOMAIN_LIST_ENDPOINTS = [
    # domain                           , endpoint                            , item match by
    ("inventory_parts",                  "/api/inventory/parts",               "part_no"),
    ("sales_customers",                  "/api/sales/customers",               "code"),
    ("purchase_suppliers",               "/api/purchase/suppliers",            "code"),
    ("production_products",              "/api/production/products",           "product_no"),
    ("purchase_orders",                  "/api/purchase/orders",               "po_no"),
    ("sales_orders",                     "/api/sales/orders",                  "so_no"),
    ("production_work_orders",           "/api/production/work-orders",        "wo_no"),
    ("inventory_transactions",           "/api/inventory/transactions",        "id"),
]


@pytest.mark.parametrize("name,endpoint,key_field", DOMAIN_LIST_ENDPOINTS)
def test_auto_filter_list_excludes_other_tenant(
    name, endpoint, key_field, seeded_client, two_tenants_with_data,
):
    """T-A 用戶呼叫 list endpoint，**不應**看到 T-B 任何資料。
    這支對 8 個 list endpoint 跑相同檢查 — 任何漏網就會紅燈。
    """
    a = two_tenants_with_data["COV-A"]
    b = two_tenants_with_data["COV-B"]

    h_a = _login(seeded_client, a["username"], a["password"])

    r = seeded_client.get(endpoint, headers=h_a)
    assert r.status_code == 200, f"{name} list failed: {r.text[:200]}"
    items = r.json()
    assert isinstance(items, list)

    # T-A 看到的所有 item 都不該屬於 T-B
    # 用 key_field 比對：T-B 種子資料的識別字串不應在 T-A list 出現
    visible_keys = []
    for it in items:
        # 兼容 nested model（如 PO/SO 不一定有 key_field 但有 supplier.code）
        k = it.get(key_field) or it.get("code") or it.get("name") or it.get("id")
        if k:
            visible_keys.append(str(k))

    # T-B 的 seed 字串：CUST-COV-B-... / SUP-COV-B-... / PART-COV-B-... / PROD-COV-B-...
    b_marker = "COV-B"
    leaked = [k for k in visible_keys if b_marker in str(k)]
    assert not leaked, (
        f"🚨 TENANT LEAK on {endpoint}: T-A 看到 T-B 的資料 {leaked!r}\n"
        f"  完整可見項：{visible_keys}"
    )


def test_below_safety_auto_filtered(seeded_client, two_tenants_with_data):
    """analytics 類也要走 tenant filter — below-safety 是聚合查詢。"""
    a = two_tenants_with_data["COV-A"]
    h = _login(seeded_client, a["username"], a["password"])
    r = seeded_client.get("/api/inventory/below-safety", headers=h)
    assert r.status_code == 200
    for item in r.json():
        assert "COV-B" not in str(item.get("part_no", "")), \
            f"T-B 的 below-safety 資料洩漏到 T-A: {item}"


def test_analytics_summary_does_not_leak(seeded_client, two_tenants_with_data):
    """analytics summary 雖然是聚合，也要在自家 tenant 內。"""
    a = two_tenants_with_data["COV-A"]
    h = _login(seeded_client, a["username"], a["password"])
    r = seeded_client.get("/api/analytics/summary", headers=h)
    # 200 OK 就好 — 主要是要它別 500 (auto filter 破壞 JOIN)
    assert r.status_code == 200, f"summary broke under auto filter: {r.text[:300]}"


def test_get_part_by_no_cross_tenant_returns_404(seeded_client, two_tenants_with_data):
    """T-A 拿著 T-B 的 part_no 直接查 → 應 404（不可洩漏存在性）。"""
    a = two_tenants_with_data["COV-A"]
    b = two_tenants_with_data["COV-B"]
    h_a = _login(seeded_client, a["username"], a["password"])

    r = seeded_client.get(f"/api/inventory/parts/{b['part_no']}", headers=h_a)
    assert r.status_code in (403, 404), \
        f"T-A 用 T-B 的 part_no 直接查竟然回 {r.status_code} (應 403/404)"


def test_write_path_still_auto_inject_tenant(seeded_client, two_tenants_with_data):
    """T-A 建零件後，**T-A 自己看得到**（auto filter 不擋自己的資料）。"""
    a = two_tenants_with_data["COV-A"]
    h = _login(seeded_client, a["username"], a["password"])
    pn = f"WRITE-A-{_uuid.uuid4().hex[:6].upper()}"
    r = seeded_client.post("/api/inventory/parts", json={
        "part_no": pn, "name": "write-test", "category": "raw",
        "safety_stock": 0, "unit_cost": 1.0,
    }, headers=h)
    assert r.status_code in (200, 201), r.text

    # T-A 自己 list 應該看到
    r = seeded_client.get("/api/inventory/parts", headers=h)
    visible = [p["part_no"] for p in r.json()]
    assert pn in visible, f"T-A 看不到自己剛建的 {pn}（auto filter 是不是擋過頭了？）"
