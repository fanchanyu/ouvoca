"""
業務閉環測試：P2I (Plan-to-Inventory) 完整生命週期

流程：
  1. 建原料 + 成品 part
  2. 建 product（生產用）+ BOM (1 成品 = 2 原料)
  3. 建 WO (draft, qty=10)
  4. 釋放 WO (released) — 校驗 BOM 存在
  5. 完工 WO (qty=10) → 成品入庫
  6. 驗證 finished goods inventory 真的增加

驗收：
  • WO 狀態流轉正確 (draft → released → completed)
  • 完工後成品 part 庫存增加 10
  • inventory_transaction 有 inbound 紀錄、reference 指向 WO
"""
from __future__ import annotations
import uuid
import pytest


@pytest.fixture(scope="module")
def p2i_setup(seeded_client, admin_headers):
    """P2I 測試共用：1 個原料、1 個成品（產品+零件）、BOM。"""
    c, h = seeded_client, admin_headers
    suffix = uuid.uuid4().hex[:6].upper()

    # 1. 建原料 part
    raw_pn = f"RAW-P2I-{suffix}"
    r = c.post("/api/inventory/parts", json={
        "part_no": raw_pn, "name": "P2I 原料",
        "category": "raw", "safety_stock": 0, "unit_cost": 10.0,
    }, headers=h)
    assert r.status_code in (200, 201), r.text
    raw_part = r.json()

    # 2. 建成品 part
    fg_pn = f"FG-P2I-{suffix}"
    r = c.post("/api/inventory/parts", json={
        "part_no": fg_pn, "name": "P2I 成品",
        "category": "finished", "safety_stock": 0, "unit_cost": 30.0,
    }, headers=h)
    assert r.status_code in (200, 201), r.text
    fg_part = r.json()

    # 3. 建 production product（用 fg_pn 確保 product_no = part_no）
    r = c.post("/api/production/products", json={
        "product_no": fg_pn, "name": "P2I 成品",
    }, headers=h)
    assert r.status_code in (200, 201), r.text
    product = r.json()

    # 4. 建 BOM (1 成品 = 2 原料)
    r = c.post("/api/production/bom-items", json={
        "product_id": product["id"],
        "part_id": raw_part["id"],
        "qty_per_unit": 2.0,
    }, headers=h)
    assert r.status_code in (200, 201), f"建 BOM 失敗 {r.status_code} {r.text}"

    return {
        "raw_part": raw_part,
        "fg_part": fg_part,
        "product": product,
        "wo_qty": 10,
    }


def test_p2i_step1_create_wo(p2i_setup, seeded_client, admin_headers):
    """建 WO（draft）。"""
    s = p2i_setup
    r = seeded_client.post("/api/production/work-orders", json={
        "product_id": s["product"]["id"],
        "ordered_qty": s["wo_qty"],
        "priority": 1,
    }, headers=admin_headers)
    assert r.status_code in (200, 201), f"建 WO 失敗 {r.status_code} {r.text}"
    wo = r.json()
    assert wo["ordered_qty"] == s["wo_qty"]
    assert wo["status"] in ("draft", "DRAFT")
    s["wo_id"] = wo["id"]


def test_p2i_step2_release_wo(p2i_setup, seeded_client, admin_headers):
    """釋放 WO（需 BOM 存在；draft → released）。"""
    s = p2i_setup
    r = seeded_client.post(
        f"/api/production/work-orders/{s['wo_id']}/release",
        headers=admin_headers,
    )
    assert r.status_code in (200, 201), f"釋放失敗 {r.status_code} {r.text}"
    wo = r.json()
    assert wo["status"] in ("released", "RELEASED")


def test_p2i_step3_complete_wo(p2i_setup, seeded_client, admin_headers):
    """完工 WO + 驗證成品入庫。"""
    s = p2i_setup
    r = seeded_client.post(
        f"/api/production/work-orders/{s['wo_id']}/complete",
        json={"completed_qty": s["wo_qty"]},
        headers=admin_headers,
    )
    assert r.status_code in (200, 201), f"完工失敗 {r.status_code} {r.text}"
    wo = r.json()
    assert wo["status"] in ("completed", "COMPLETED")
    assert wo["completed_qty"] == s["wo_qty"]


def test_p2i_step4_fg_inventory_increased(p2i_setup, seeded_client, admin_headers):
    """**關鍵驗證**：完工後成品庫存真的有加（防沉默 bug）。"""
    s = p2i_setup
    r = seeded_client.get(
        f"/api/inventory/transactions?part_id={s['fg_part']['id']}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    txs = r.json()

    in_txs = [t for t in txs if t["transaction_type"] in ("inbound", "receipt")]
    assert len(in_txs) >= 1, \
        f"完工後沒有成品 inbound 交易（complete event 沒把 FG 入庫）：{txs}"

    total_in = sum(t["qty"] for t in in_txs)
    assert total_in >= s["wo_qty"], \
        f"成品入庫 {total_in} < 期望 {s['wo_qty']}"

    # 確認 reference_id 指向 WO
    matched = [t for t in in_txs if t.get("reference_id") == s["wo_id"]]
    assert matched, f"沒有 reference 指向 WO 的入庫紀錄"
