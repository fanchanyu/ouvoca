"""Smoke tests for v3.10 update/delete endpoints + service functions。

驗證 root cause fix: 之前 UI 沒有 Edit/Delete buttons 因為 API 根本沒這些 endpoints。
這次補完 4 個 domain × (update + delete + cancel) 共 9 個 endpoint。
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def demo_user():
    return {"employee_id": "emp-v310-001", "username": "tester", "roles": ["admin"]}


# ============================================================
# Service layer tests
# ============================================================

class TestUpdatePart:
    @pytest.mark.asyncio
    async def test_update_part_whitelist(self, db, demo_user):
        from app.services.inventory import create_part, update_part
        p = await create_part(db, {
            "part_no": "U310-P1", "name": "old", "category": "component",
            "safety_stock": 100,
        })
        updated = await update_part(db, p.id, {
            "name": "new", "safety_stock": 200,
            "part_no": "HACKED",  # 不在白名單，應被忽略
        }, user=demo_user)
        assert updated.name == "new"
        assert updated.safety_stock == 200
        assert updated.part_no == "U310-P1"  # 未變

    @pytest.mark.asyncio
    async def test_update_part_no_changes_short_circuit(self, db, demo_user):
        from app.services.inventory import create_part, update_part
        p = await create_part(db, {"part_no": "U310-P2", "name": "x", "category": "component"})
        # 改成同樣的值 → 不 commit
        result = await update_part(db, p.id, {"name": "x"}, user=demo_user)
        assert result.name == "x"

    @pytest.mark.asyncio
    async def test_update_part_not_found(self, db, demo_user):
        from app.services.inventory import update_part
        from app.core.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            await update_part(db, "nonexistent-uuid", {"name": "x"}, user=demo_user)


class TestDeletePart:
    @pytest.mark.asyncio
    async def test_delete_part_no_txn_succeeds(self, db, demo_user):
        from app.services.inventory import create_part, delete_part
        from app.models.inventory import Part
        from sqlalchemy import select
        p = await create_part(db, {"part_no": "U310-DEL1", "name": "x", "category": "component"})
        result = await delete_part(db, p.id, user=demo_user)
        assert result["deleted"] is True
        # 確認 Part 真的不見了
        rows = (await db.execute(select(Part).where(Part.part_no == "U310-DEL1"))).scalars().all()
        assert len(rows) == 0

    @pytest.mark.asyncio
    async def test_delete_part_with_transaction_blocked(self, db, demo_user):
        from app.services.inventory import create_part, add_inventory_transaction, delete_part
        from app.core.exceptions import BusinessRuleError
        p = await create_part(db, {"part_no": "U310-DEL2", "name": "x", "category": "component"})
        await add_inventory_transaction(db, {
            "part_id": p.id, "transaction_type": "inbound", "qty": 10,
        }, user=demo_user)
        with pytest.raises(BusinessRuleError, match="交易紀錄"):
            await delete_part(db, p.id, user=demo_user)

    @pytest.mark.asyncio
    async def test_delete_part_with_inventory_qty_blocked(self, db, demo_user):
        from app.services.inventory import create_part, delete_part
        from app.core.exceptions import BusinessRuleError
        from app.models.inventory import Inventory
        from sqlalchemy import select
        p = await create_part(db, {"part_no": "U310-DEL3", "name": "x", "category": "component"})
        # 手動把 inventory qty 設大於 0（service create_part 已建空 Inventory）
        inv = (await db.execute(select(Inventory).where(Inventory.part_id == p.id))).scalar_one()
        inv.qty_on_hand = 5
        await db.commit()
        with pytest.raises(BusinessRuleError, match="庫存未歸零"):
            await delete_part(db, p.id, user=demo_user)


class TestUpdateSupplier:
    @pytest.mark.asyncio
    async def test_update_supplier(self, db, demo_user):
        from app.services.purchase import create_supplier, update_supplier
        s = await create_supplier(db, {"code": "U310-SUP1", "name": "old"})
        updated = await update_supplier(db, s.id, {
            "name": "新供應商", "tier": "T1", "is_approved": True,
        }, user=demo_user)
        assert updated.name == "新供應商"
        assert updated.tier == "T1"
        assert updated.is_approved is True


class TestDeleteSupplier:
    @pytest.mark.asyncio
    async def test_delete_supplier_with_po_blocked(self, db, demo_user):
        from app.services.purchase import create_supplier, create_purchase_order, delete_supplier
        from app.services.inventory import create_part
        from app.core.exceptions import BusinessRuleError
        s = await create_supplier(db, {"code": "U310-SUP2", "name": "x"})
        part = await create_part(db, {
            "part_no": "U310-SUP2-P", "name": "x", "category": "component", "unit_cost": 1,
        })
        await create_purchase_order(db, {
            "supplier_id": s.id,
            "items": [{"part_id": part.id, "ordered_qty": 1, "unit_price": 1}],
        }, user=demo_user)
        with pytest.raises(BusinessRuleError, match="已有採購單"):
            await delete_supplier(db, s.id, user=demo_user)


class TestCancelPO:
    @pytest.mark.asyncio
    async def test_cancel_po(self, db, demo_user):
        from app.services.purchase import create_supplier, create_purchase_order, cancel_purchase_order
        from app.services.inventory import create_part
        s = await create_supplier(db, {"code": "U310-CPO", "name": "x"})
        part = await create_part(db, {
            "part_no": "U310-CPO-P", "name": "x", "category": "component", "unit_cost": 1,
        })
        po = await create_purchase_order(db, {
            "supplier_id": s.id,
            "items": [{"part_id": part.id, "ordered_qty": 1, "unit_price": 1}],
        }, user=demo_user)
        result = await cancel_purchase_order(db, po.id, user=demo_user, reason="供應商取消")
        assert result.status == "cancelled"
        assert "供應商取消" in (result.remark or "")


class TestUpdateCustomer:
    @pytest.mark.asyncio
    async def test_update_customer(self, db, demo_user):
        from app.services.sales import create_customer, update_customer
        c = await create_customer(db, {"code": "U310-CUS1", "name": "old", "grade": "C"})
        updated = await update_customer(db, c.id, {
            "name": "新客戶", "grade": "A", "credit_limit": 500000,
        }, user=demo_user)
        assert updated.name == "新客戶"
        assert updated.grade == "A"
        assert updated.credit_limit == 500000


class TestDeleteCustomer:
    @pytest.mark.asyncio
    async def test_delete_customer_no_so_succeeds(self, db, demo_user):
        from app.services.sales import create_customer, delete_customer
        from app.models.crm_sales import Customer
        from sqlalchemy import select
        c = await create_customer(db, {"code": "U310-DCUS", "name": "x"})
        result = await delete_customer(db, c.id, user=demo_user)
        assert result["deleted"] is True
        rows = (await db.execute(select(Customer).where(Customer.code == "U310-DCUS"))).scalars().all()
        assert len(rows) == 0


class TestCancelSO:
    @pytest.mark.asyncio
    async def test_cancel_so(self, db, demo_user):
        from app.services.sales import create_customer, create_sales_order, cancel_sales_order
        from app.services.production import create_product
        c = await create_customer(db, {"code": "U310-CSO", "name": "x"})
        prod = await create_product(db, {"product_no": "U310-CSO-P", "name": "p"})
        so = await create_sales_order(db, {
            "customer_id": c.id,
            "items": [{"product_id": prod.id, "ordered_qty": 1, "unit_price": 100}],
        }, user=demo_user)
        result = await cancel_sales_order(db, so.id, user=demo_user, reason="客戶取消")
        assert result.status == "cancelled"


class TestCancelWO:
    @pytest.mark.asyncio
    async def test_cancel_wo(self, db, demo_user):
        from app.services.production import create_product, create_production_order, cancel_production_order
        prod = await create_product(db, {"product_no": "U310-CWO-P", "name": "p"})
        wo = await create_production_order(db, {
            "product_id": prod.id, "ordered_qty": 100, "priority": "normal",
        }, user=demo_user)
        result = await cancel_production_order(db, wo.id, user=demo_user)
        assert result.status == "cancelled"


# ============================================================
# API endpoint tests
# ============================================================

class TestAPIEndpoints:
    def test_patch_part_endpoint_exists(self, seeded_client, admin_headers):
        """確認 PATCH /api/inventory/parts/{id} 註冊。"""
        # 先建一個 part 透過 POST
        r = seeded_client.post(
            "/api/inventory/parts", headers=admin_headers,
            json={"part_no": "U310-API-P1", "name": "API 測試料",
                  "category": "component"},
        )
        assert r.status_code == 200, r.text
        part_id = r.json()["id"]

        # PATCH
        r = seeded_client.patch(
            f"/api/inventory/parts/{part_id}", headers=admin_headers,
            json={"name": "PATCHed", "safety_stock": 999},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == "PATCHed"
        assert body["safety_stock"] == 999

    def test_delete_part_endpoint(self, seeded_client, admin_headers):
        r = seeded_client.post(
            "/api/inventory/parts", headers=admin_headers,
            json={"part_no": "U310-API-P2", "name": "del-test",
                  "category": "component"},
        )
        part_id = r.json()["id"]
        r = seeded_client.delete(
            f"/api/inventory/parts/{part_id}", headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["deleted"] is True

    def test_patch_supplier_endpoint(self, seeded_client, admin_headers):
        r = seeded_client.post(
            "/api/purchase/suppliers", headers=admin_headers,
            json={"code": "U310-API-SUP", "name": "old", "tier": "T3"},
        )
        assert r.status_code == 200, r.text
        sup_id = r.json()["id"]
        r = seeded_client.patch(
            f"/api/purchase/suppliers/{sup_id}", headers=admin_headers,
            json={"name": "PATCHed Sup", "tier": "T1"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "PATCHed Sup"
        assert r.json()["tier"] == "T1"

    def test_patch_customer_endpoint(self, seeded_client, admin_headers):
        r = seeded_client.post(
            "/api/sales/customers", headers=admin_headers,
            json={"code": "U310-API-CUS", "name": "old"},
        )
        assert r.status_code == 200, r.text
        cust_id = r.json()["id"]
        r = seeded_client.patch(
            f"/api/sales/customers/{cust_id}", headers=admin_headers,
            json={"name": "PATCHed Cust", "grade": "A"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "PATCHed Cust"


def test_endpoint_route_inventory():
    """所有新 endpoints 都註冊到 app.routes。

    Note：FastAPI 同 path 不同 method 是分開的 route 物件，要 aggregate。
    """
    from app.main import app
    paths = [r.path for r in app.routes if hasattr(r, "path")]
    # Aggregate methods per path (一個 path 可有多個 route)
    methods_by_path: dict[str, set] = {}
    for r in app.routes:
        if not (hasattr(r, "methods") and hasattr(r, "path")):
            continue
        methods_by_path.setdefault(r.path, set()).update(r.methods)

    # PATCH endpoints
    assert "PATCH" in methods_by_path.get("/api/inventory/parts/{part_id}", set())
    assert "PATCH" in methods_by_path.get("/api/purchase/suppliers/{supplier_id}", set())
    assert "PATCH" in methods_by_path.get("/api/sales/customers/{customer_id}", set())
    # DELETE endpoints
    assert "DELETE" in methods_by_path.get("/api/inventory/parts/{part_id}", set())
    assert "DELETE" in methods_by_path.get("/api/purchase/suppliers/{supplier_id}", set())
    assert "DELETE" in methods_by_path.get("/api/sales/customers/{customer_id}", set())
    # Cancel
    assert "/api/purchase/orders/{po_id}/cancel" in paths
    assert "/api/sales/orders/{so_id}/cancel" in paths
    assert "/api/production/work-orders/{wo_id}/cancel" in paths
