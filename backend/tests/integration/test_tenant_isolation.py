"""
Multi-tenant 隔離測試 — 商業 SaaS 的命脈。

絕對不能跨 tenant 看到別人的資料。一旦發生 = 法律訴訟 + 信譽歸零。

驗收：
1. Tenant A 建的零件，Tenant B 用 API 看不到
2. Tenant A 的 Customer，Tenant B 查 customer list 拿不到
3. AuditLog / DecisionLog 也走 tenant 隔離
4. 即使用 superuser 也只能看自己 tenant（除非顯式有 cross-tenant 權限）
"""
from __future__ import annotations
import uuid as _uuid
import asyncio
import pytest


@pytest.fixture(scope="module")
def two_tenants(seeded_client):
    """直接 DB insert 建兩個 tenant + 各自的 admin user。"""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.permission import Tenant, RoleDef, UserRoleAssignment
    from app.models.organization import User, Employee, Department
    from app.services.auth import hash_password
    from datetime import datetime

    async def _setup():
        async with AsyncSessionLocal() as db:
            results = {}

            # 確保有一個 admin role（給 assignment 用）
            admin_role = (await db.execute(
                select(RoleDef).where(RoleDef.code == "admin")
            )).scalar_one_or_none()
            if admin_role is None:
                admin_role = RoleDef(
                    id=str(_uuid.uuid4()),
                    code="admin",
                    name_zh="系統管理員",
                    tenant_id=None,
                )
                db.add(admin_role)
                await db.flush()

            for tag, name in [("TA", "A 公司"), ("TB", "B 公司")]:
                # 建 tenant
                tenant = (await db.execute(
                    select(Tenant).where(Tenant.code == tag)
                )).scalar_one_or_none()
                if tenant is None:
                    tenant = Tenant(
                        id=str(_uuid.uuid4()),
                        code=tag,
                        name=name,
                        tenant_type="factory",
                    )
                    db.add(tenant)
                    await db.flush()

                # 建 department + employee + user
                dept = Department(
                    id=str(_uuid.uuid4()),
                    code=f"DEPT-{tag}",
                    name=f"{tag} 部門",
                )
                db.add(dept)
                await db.flush()

                emp = Employee(
                    id=str(_uuid.uuid4()),
                    employee_no=f"EMP-{tag}-001",
                    name=f"admin-{tag}",
                    email=f"admin-{tag}@test.local",
                    department_id=dept.id,
                    title="Admin",
                    hire_date=datetime.utcnow(),
                )
                db.add(emp)
                await db.flush()

                user = User(
                    id=str(_uuid.uuid4()),
                    username=f"admin-{tag}",
                    hashed_password=hash_password(f"PassFor{tag}!"),
                    employee_id=emp.id,
                    is_superuser=True,
                    is_active=True,
                )
                db.add(user)
                await db.flush()

                # 關鍵：建 UserRoleAssignment 把 user 綁到對應 tenant
                # 沒這條 → load_user_context 拿不到 tenant → default 'HQ' → 隔離失效
                assignment = UserRoleAssignment(
                    id=str(_uuid.uuid4()),
                    user_id=user.id,
                    role_id=admin_role.id,
                    tenant_id=tenant.id,
                    is_active=True,
                    granted_at=datetime.utcnow(),
                )
                db.add(assignment)

                results[tag] = {
                    "tenant_id": tenant.id,
                    "tenant_code": tag,
                    "username": f"admin-{tag}",
                    "password": f"PassFor{tag}!",
                    "user_id": user.id,
                }
            await db.commit()
            return results

    return asyncio.run(_setup())


def _login(client, username, password) -> dict:
    r = client.post("/api/auth/login", json={
        "username": username, "password": password,
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_tenant_a_creates_part_b_cannot_see(seeded_client, two_tenants):
    """T-A 建立的 part，T-B 不該看到。"""
    ta = two_tenants["TA"]
    tb = two_tenants["TB"]
    h_a = _login(seeded_client, ta["username"], ta["password"])
    h_b = _login(seeded_client, tb["username"], tb["password"])

    # A 建零件
    pn = f"TENANT-A-{_uuid.uuid4().hex[:6].upper()}"
    r = seeded_client.post("/api/inventory/parts", json={
        "part_no": pn, "name": "A 的零件",
        "category": "raw", "safety_stock": 100, "unit_cost": 1.0,
    }, headers=h_a)
    assert r.status_code in (200, 201), r.text

    # A 自己看得到
    r = seeded_client.get("/api/inventory/parts", headers=h_a)
    assert any(p["part_no"] == pn for p in r.json()), \
        f"T-A 看不到自己剛建的 {pn}"

    # B 查同一個 endpoint，**不該看到 A 的零件**
    r = seeded_client.get("/api/inventory/parts", headers=h_b)
    b_visible = [p["part_no"] for p in r.json()]
    assert pn not in b_visible, \
        f"⚠️ TENANT LEAK: T-B 看到了 T-A 的零件 {pn}！可見：{b_visible}"


def test_tenant_a_creates_customer_b_cannot_see(seeded_client, two_tenants):
    """T-A 建立的客戶，T-B 不該看到。"""
    ta = two_tenants["TA"]
    tb = two_tenants["TB"]
    h_a = _login(seeded_client, ta["username"], ta["password"])
    h_b = _login(seeded_client, tb["username"], tb["password"])

    code = f"CUST-A-{_uuid.uuid4().hex[:6].upper()}"
    r = seeded_client.post("/api/sales/customers", json={
        "code": code, "name": "A 的客戶",
    }, headers=h_a)
    assert r.status_code in (200, 201), r.text

    # B 查
    r = seeded_client.get("/api/sales/customers", headers=h_b)
    b_visible = [c["code"] for c in r.json()]
    assert code not in b_visible, \
        f"⚠️ TENANT LEAK: T-B 看到了 T-A 的客戶 {code}！可見：{b_visible}"


def test_tenant_isolation_works_both_ways(seeded_client, two_tenants):
    """雙向驗證 — B 也不可被 A 看到。"""
    ta = two_tenants["TA"]
    tb = two_tenants["TB"]
    h_a = _login(seeded_client, ta["username"], ta["password"])
    h_b = _login(seeded_client, tb["username"], tb["password"])

    pn_b = f"TENANT-B-{_uuid.uuid4().hex[:6].upper()}"
    r = seeded_client.post("/api/inventory/parts", json={
        "part_no": pn_b, "name": "B 的零件",
        "category": "raw", "safety_stock": 0, "unit_cost": 1.0,
    }, headers=h_b)
    assert r.status_code in (200, 201), r.text

    r = seeded_client.get("/api/inventory/parts", headers=h_a)
    a_visible = [p["part_no"] for p in r.json()]
    assert pn_b not in a_visible, \
        f"⚠️ TENANT LEAK: T-A 看到了 T-B 的零件 {pn_b}！"


def test_tenant_isolation_get_by_id_returns_404(seeded_client, two_tenants):
    """直接知道別人 part_id 也不能用 GET /parts/{id} 拿到（防 ID-guessing 攻擊）。"""
    ta = two_tenants["TA"]
    tb = two_tenants["TB"]
    h_a = _login(seeded_client, ta["username"], ta["password"])
    h_b = _login(seeded_client, tb["username"], tb["password"])

    # A 建零件並拿到 ID
    pn = f"SECRET-{_uuid.uuid4().hex[:6].upper()}"
    r = seeded_client.post("/api/inventory/parts", json={
        "part_no": pn, "name": "Secret", "category": "raw",
        "safety_stock": 0, "unit_cost": 1.0,
    }, headers=h_a)
    assert r.status_code in (200, 201), r.text
    secret_id = r.json()["id"]

    # B 拿著 ID 嘗試查 — 應該 404 / 403（不可洩漏存在性）
    # 注意：當前實作可能還沒做這層 — 此測試會抓出缺口
    r = seeded_client.get(f"/api/inventory/parts/{pn}", headers=h_b)
    # 接受 404（找不到）或 403（無權限）；200 = 大洩漏
    assert r.status_code in (403, 404), \
        f"⚠️ TENANT LEAK: T-B 透過 ID/part_no 直接查到 T-A 的零件 {pn}！status={r.status_code}"
