"""
Smoke: BOM (做法 / Recipe) 多階遞迴爆破 + hard-write tools (v3.25.9)

對應使用者「BOM 表管理有完善嗎？」盤查補完：
  - 補完 1：MRP 從單階 → 多階遞迴爆破（半成品自動展開）
  - 補完 2：3 個 hard-write BOM tools（add / update / delete with ConfirmCard）
"""
from __future__ import annotations

import uuid

import pytest


# ─── helpers ─────────────────────────────────────────────────────

def _seed_part(client, headers, part_no: str, name: str = None, category: str = "raw_material"):
    """建一個 part 並回傳 id（用 API）。"""
    body = {
        "part_no": part_no,
        "name": name or part_no,
        "category": category,
        "unit": "pcs",
    }
    r = client.post("/api/inventory/parts", json=body, headers=headers)
    assert r.status_code in (200, 201), f"seed part failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _seed_product(client, headers, product_no: str, name: str = None):
    r = client.post("/api/production/products", json={
        "product_no": product_no, "name": name or product_no, "unit": "pcs",
    }, headers=headers)
    assert r.status_code in (200, 201), f"seed product failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _add_bom(client, headers, product_id: str, part_id: str, qty_per: float, scrap_rate: float = 0):
    r = client.post("/api/production/bom-items", json={
        "product_id": product_id, "part_id": part_id,
        "qty_per": qty_per, "scrap_rate": scrap_rate,
        "level": 1, "sequence_no": 0, "is_active": True,
    }, headers=headers)
    assert r.status_code in (200, 201), f"add bom failed: {r.status_code} {r.text}"


# ─── Multi-level explosion ───────────────────────────────────────

@pytest.mark.asyncio
async def test_multilevel_explosion_2_levels(seeded_client):
    """2 階：產品 A → 半成品 B (qty 2) → 原料 C (qty 3)。
    結果：1 A 需要 6 C。"""
    import asyncio
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.product import Product, BOMItem
    from app.models.inventory import Part
    from app.services.production import explode_bom_recursive

    suffix = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        # 原料 C
        c_part = Part(id=str(uuid.uuid4()), part_no=f"C-{suffix}", name="Raw C", unit="pcs")
        db.add(c_part)
        # 半成品 B（同時是 Part 和 Product，part_no == product_no）
        b_part = Part(id=str(uuid.uuid4()), part_no=f"B-{suffix}", name="Sub B", unit="pcs",
                      category="semi_finished")
        b_prod = Product(id=str(uuid.uuid4()), product_no=f"B-{suffix}", name="Sub B", unit="pcs")
        db.add(b_part); db.add(b_prod)
        # 成品 A
        a_prod = Product(id=str(uuid.uuid4()), product_no=f"A-{suffix}", name="Final A", unit="pcs")
        db.add(a_prod)
        await db.flush()

        # A 用 2 個 B
        db.add(BOMItem(id=str(uuid.uuid4()), product_id=a_prod.id, part_id=b_part.id,
                       qty_per=2, scrap_rate=0, level=1, is_active=True))
        # B 用 3 個 C
        db.add(BOMItem(id=str(uuid.uuid4()), product_id=b_prod.id, part_id=c_part.id,
                       qty_per=3, scrap_rate=0, level=1, is_active=True))
        await db.commit()

        # 爆破 A：應該得到「6 個 C」（2 × 3）
        result = await explode_bom_recursive(db, a_prod.id, qty=1.0)

    assert len(result) == 1, f"應只有 1 個葉節點，實際 {len(result)}"
    leaf = result[0]
    assert leaf["part_no"] == f"C-{suffix}"
    assert leaf["qty"] == 6.0, f"1 A → 應 6 C，實際 {leaf['qty']}"
    assert leaf["level"] == 2


@pytest.mark.asyncio
async def test_multilevel_explosion_3_levels_with_scrap(seeded_client):
    """3 階 + scrap_rate：A→B(qty=2, scrap=10%)→C(qty=2, scrap=5%)→D(qty=1)。
    1 A → 2 * 1.1 = 2.2 B → 2.2 * 2 * 1.05 = 4.62 C → 4.62 * 1 = 4.62 D"""
    import uuid as _u
    from app.database import AsyncSessionLocal
    from app.models.product import Product, BOMItem
    from app.models.inventory import Part
    from app.services.production import explode_bom_recursive

    s = _u.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        # D 純原料
        d_part = Part(id=str(_u.uuid4()), part_no=f"D-{s}", name="Raw D", unit="pcs")
        # C 半成品（既是 part 又是 product）
        c_part = Part(id=str(_u.uuid4()), part_no=f"C-{s}", name="Sub C", unit="pcs",
                      category="semi_finished")
        c_prod = Product(id=str(_u.uuid4()), product_no=f"C-{s}", name="Sub C", unit="pcs")
        # B 半成品
        b_part = Part(id=str(_u.uuid4()), part_no=f"B-{s}", name="Sub B", unit="pcs",
                      category="semi_finished")
        b_prod = Product(id=str(_u.uuid4()), product_no=f"B-{s}", name="Sub B", unit="pcs")
        # A 成品
        a_prod = Product(id=str(_u.uuid4()), product_no=f"A-{s}", name="Final A", unit="pcs")
        db.add_all([d_part, c_part, c_prod, b_part, b_prod, a_prod])
        await db.flush()

        # A 用 2 個 B（耗損 10%）
        db.add(BOMItem(id=str(_u.uuid4()), product_id=a_prod.id, part_id=b_part.id,
                       qty_per=2, scrap_rate=0.1, level=1, is_active=True))
        # B 用 2 個 C（耗損 5%）
        db.add(BOMItem(id=str(_u.uuid4()), product_id=b_prod.id, part_id=c_part.id,
                       qty_per=2, scrap_rate=0.05, level=1, is_active=True))
        # C 用 1 個 D
        db.add(BOMItem(id=str(_u.uuid4()), product_id=c_prod.id, part_id=d_part.id,
                       qty_per=1, scrap_rate=0, level=1, is_active=True))
        await db.commit()

        result = await explode_bom_recursive(db, a_prod.id, qty=1.0)

    assert len(result) == 1
    leaf = result[0]
    assert leaf["part_no"] == f"D-{s}"
    # 1 * 2 * 1.1 * 2 * 1.05 * 1 = 4.62
    assert abs(leaf["qty"] - 4.62) < 0.001, f"預期 4.62，實際 {leaf['qty']}"
    assert leaf["level"] == 3


@pytest.mark.asyncio
async def test_explosion_cycle_protection(seeded_client):
    """循環依賴：A → [B], B → [A]。不該無窮遞迴。"""
    import uuid as _u
    from app.database import AsyncSessionLocal
    from app.models.product import Product, BOMItem
    from app.models.inventory import Part
    from app.services.production import explode_bom_recursive

    s = _u.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        a_part = Part(id=str(_u.uuid4()), part_no=f"A-{s}", name="A", unit="pcs",
                      category="semi_finished")
        b_part = Part(id=str(_u.uuid4()), part_no=f"B-{s}", name="B", unit="pcs",
                      category="semi_finished")
        a_prod = Product(id=str(_u.uuid4()), product_no=f"A-{s}", name="A", unit="pcs")
        b_prod = Product(id=str(_u.uuid4()), product_no=f"B-{s}", name="B", unit="pcs")
        db.add_all([a_part, b_part, a_prod, b_prod])
        await db.flush()

        # A 用 B
        db.add(BOMItem(id=str(_u.uuid4()), product_id=a_prod.id, part_id=b_part.id,
                       qty_per=1, scrap_rate=0, level=1, is_active=True))
        # B 用 A（循環！）
        db.add(BOMItem(id=str(_u.uuid4()), product_id=b_prod.id, part_id=a_part.id,
                       qty_per=1, scrap_rate=0, level=1, is_active=True))
        await db.commit()

        # 不該爆 RecursionError 或 hang；可回空 list（因為兩個都是半成品，無葉節點）
        import asyncio
        result = await asyncio.wait_for(
            explode_bom_recursive(db, a_prod.id, qty=1.0),
            timeout=5.0,
        )

    # 重點：跑得完且沒爆；空 result 或非空都可接受（兩者都是半成品無葉）
    assert isinstance(result, list)


# ─── BOM hard-write tools ────────────────────────────────────────

def test_add_bom_item_with_confirm(seeded_client, admin_headers):
    """新增 BOM 行 → 出 ConfirmCard → 點確認 → 真寫入。"""
    s = uuid.uuid4().hex[:6]
    prod_id = _seed_product(seeded_client, admin_headers, f"PROD-{s}")
    part_id = _seed_part(seeded_client, admin_headers, f"PART-{s}")

    # 透過 chat agent 走 hard-write tool
    r = seeded_client.post("/api/agents/exec/add_bom_item_with_confirm", json={
        "product_no": f"PROD-{s}",
        "part_no": f"PART-{s}",
        "qty_per": 4,
        "scrap_rate": 0.05,
    }, headers=admin_headers)
    assert r.status_code == 200, r.text
    payload = r.json()
    # 應該回 ConfirmCard，不是直接執行
    assert payload.get("type") == "confirm_card" or "card_id" in payload, \
        f"應回 ConfirmCard，實際：{payload}"


def test_update_bom_item_with_confirm(seeded_client, admin_headers):
    """更新 BOM 用量 → 出 ConfirmCard。"""
    s = uuid.uuid4().hex[:6]
    prod_id = _seed_product(seeded_client, admin_headers, f"PROD-{s}")
    part_id = _seed_part(seeded_client, admin_headers, f"PART-{s}")
    _add_bom(seeded_client, admin_headers, prod_id, part_id, qty_per=4)

    r = seeded_client.post("/api/agents/exec/update_bom_item_with_confirm", json={
        "product_no": f"PROD-{s}",
        "part_no": f"PART-{s}",
        "qty_per": 6,
    }, headers=admin_headers)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload.get("type") == "confirm_card" or "card_id" in payload


def test_delete_bom_item_with_confirm(seeded_client, admin_headers):
    """刪除 BOM 行（軟刪除）→ 出 ConfirmCard。"""
    s = uuid.uuid4().hex[:6]
    prod_id = _seed_product(seeded_client, admin_headers, f"PROD-{s}")
    part_id = _seed_part(seeded_client, admin_headers, f"PART-{s}")
    _add_bom(seeded_client, admin_headers, prod_id, part_id, qty_per=4)

    r = seeded_client.post("/api/agents/exec/delete_bom_item_with_confirm", json={
        "product_no": f"PROD-{s}",
        "part_no": f"PART-{s}",
        "reason": "test cleanup",
    }, headers=admin_headers)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload.get("type") == "confirm_card" or "card_id" in payload


def test_add_bom_item_duplicate_protection(seeded_client, admin_headers):
    """同產品同料件已存在時 → 回 error + 建議 update。"""
    s = uuid.uuid4().hex[:6]
    prod_id = _seed_product(seeded_client, admin_headers, f"PROD-{s}")
    part_id = _seed_part(seeded_client, admin_headers, f"PART-{s}")
    _add_bom(seeded_client, admin_headers, prod_id, part_id, qty_per=4)

    r = seeded_client.post("/api/agents/exec/add_bom_item_with_confirm", json={
        "product_no": f"PROD-{s}",
        "part_no": f"PART-{s}",
        "qty_per": 8,
    }, headers=admin_headers)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert "error" in payload, f"應回 error，實際：{payload}"
    assert "已存在" in payload["error"]


def test_update_bom_no_changes(seeded_client, admin_headers):
    """update 但兩個欄位都沒給 → error。"""
    s = uuid.uuid4().hex[:6]
    prod_id = _seed_product(seeded_client, admin_headers, f"PROD-{s}")
    part_id = _seed_part(seeded_client, admin_headers, f"PART-{s}")
    _add_bom(seeded_client, admin_headers, prod_id, part_id, qty_per=4)

    r = seeded_client.post("/api/agents/exec/update_bom_item_with_confirm", json={
        "product_no": f"PROD-{s}", "part_no": f"PART-{s}",
    }, headers=admin_headers)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert "error" in payload


@pytest.mark.asyncio
async def test_where_used(seeded_client):
    """where_used 反查：M6 螺絲被用在哪些產品？"""
    import uuid as _u
    from app.database import AsyncSessionLocal
    from app.models.product import Product, BOMItem
    from app.models.inventory import Part
    from app.services.production import where_used

    s = _u.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        shared = Part(id=str(_u.uuid4()), part_no=f"SHARED-{s}", name="Shared Bolt", unit="pcs")
        p1 = Product(id=str(_u.uuid4()), product_no=f"P1-{s}", name="Product 1", unit="pcs")
        p2 = Product(id=str(_u.uuid4()), product_no=f"P2-{s}", name="Product 2", unit="pcs")
        db.add_all([shared, p1, p2])
        await db.flush()
        db.add(BOMItem(id=str(_u.uuid4()), product_id=p1.id, part_id=shared.id,
                       qty_per=4, scrap_rate=0, level=1, is_active=True))
        db.add(BOMItem(id=str(_u.uuid4()), product_id=p2.id, part_id=shared.id,
                       qty_per=8, scrap_rate=0, level=1, is_active=True))
        await db.commit()

        result = await where_used(db, shared.id)

    product_nos = {r["product_no"] for r in result}
    assert f"P1-{s}" in product_nos
    assert f"P2-{s}" in product_nos
    assert len(result) >= 2
