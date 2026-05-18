"""
Smoke: Sprint K quick-create flows (v3.17)

驗收：前端 QuickCreateBar 走的 API 在後端都通。
之前只測過 update/delete，沒測「從零建一筆」的完整路徑。
"""
from __future__ import annotations


# ── Customer create ─────────────────────────────────────────
def test_create_customer_minimum_fields(seeded_client, admin_headers):
    r = seeded_client.post("/api/sales/customers", headers=admin_headers, json={
        "code": "QC-CUST-001", "name": "快速建客戶測試",
    })
    assert r.status_code in (200, 201), r.text
    c = r.json()
    assert c["code"] == "QC-CUST-001"
    assert c["grade"] in ("A", "B", "C", "D", None)


def test_create_customer_all_fields(seeded_client, admin_headers):
    r = seeded_client.post("/api/sales/customers", headers=admin_headers, json={
        "code": "QC-CUST-002", "name": "完整欄位客戶",
        "grade": "A", "contact_person": "王經理", "contact_phone": "02-1234",
        "payment_terms": "月結 30 天", "credit_limit": 500000,
    })
    assert r.status_code in (200, 201), r.text


# ── Supplier create ─────────────────────────────────────────
def test_create_supplier_minimum_fields(seeded_client, admin_headers):
    r = seeded_client.post("/api/purchase/suppliers", headers=admin_headers, json={
        "code": "QC-SUP-001", "name": "快速建供應商",
    })
    assert r.status_code in (200, 201), r.text
    s = r.json()
    assert s["code"] == "QC-SUP-001"


# ── Product create ──────────────────────────────────────────
def test_create_product_minimum_fields(seeded_client, admin_headers):
    r = seeded_client.post("/api/production/products", headers=admin_headers, json={
        "product_no": "QC-PROD-001", "name": "快速建產品",
    })
    assert r.status_code in (200, 201), r.text


# ── Sales Order create (single-line item) ───────────────────
def test_create_sales_order_single_line(seeded_client, admin_headers):
    # 先建 customer + product
    r_c = seeded_client.post("/api/sales/customers", headers=admin_headers,
                              json={"code": "QC-SO-CUST", "name": "SO 測試客戶"})
    cust_id = r_c.json()["id"]

    r_p = seeded_client.post("/api/production/products", headers=admin_headers,
                              json={"product_no": "QC-SO-PROD", "name": "SO 測試產品"})
    prod_id = r_p.json()["id"]

    # 建 SO
    r = seeded_client.post("/api/sales/orders", headers=admin_headers, json={
        "customer_id": cust_id,
        "items": [{"product_id": prod_id, "ordered_qty": 10, "unit_price": 100}],
    })
    assert r.status_code in (200, 201), r.text
    so = r.json()
    assert so["customer_id"] == cust_id
    assert so["total_amount"] == 1000


# ── Purchase Order create (single-line item) ────────────────
def test_create_purchase_order_single_line(seeded_client, admin_headers):
    # 先建 supplier + part
    r_s = seeded_client.post("/api/purchase/suppliers", headers=admin_headers,
                              json={"code": "QC-PO-SUP", "name": "PO 測試供應商"})
    sup_id = r_s.json()["id"]

    r_p = seeded_client.post("/api/inventory/parts", headers=admin_headers, json={
        "part_no": "QC-PO-PART", "name": "PO 測試料件",
        "category": "raw_material", "unit": "pcs",
        "safety_stock": 10, "unit_cost": 50,
    })
    part_id = r_p.json()["id"]

    # 建 PO
    r = seeded_client.post("/api/purchase/orders", headers=admin_headers, json={
        "supplier_id": sup_id,
        "items": [{"part_id": part_id, "ordered_qty": 20, "unit_price": 50}],
    })
    assert r.status_code in (200, 201), r.text
    po = r.json()
    assert po["supplier_id"] == sup_id
    assert po["total_amount"] == 1000


# ── Work Order create ───────────────────────────────────────
def test_create_work_order(seeded_client, admin_headers):
    # 先建 product
    r_p = seeded_client.post("/api/production/products", headers=admin_headers,
                              json={"product_no": "QC-WO-PROD", "name": "WO 測試產品"})
    prod_id = r_p.json()["id"]

    # 建 WO
    r = seeded_client.post("/api/production/work-orders", headers=admin_headers, json={
        "product_id": prod_id, "ordered_qty": 100, "priority": 50,
    })
    assert r.status_code in (200, 201), r.text
    wo = r.json()
    assert wo["ordered_qty"] == 100
    assert wo["status"] in ("draft", "released")  # 預設 draft


# ── Unauthorized rejected ───────────────────────────────────
def test_unauthorized_create_rejected(seeded_client):
    r = seeded_client.post("/api/sales/customers", json={"code": "X", "name": "X"})
    assert r.status_code == 401
    r = seeded_client.post("/api/purchase/suppliers", json={"code": "X", "name": "X"})
    assert r.status_code == 401
    r = seeded_client.post("/api/production/work-orders", json={"product_id": "x", "ordered_qty": 1})
    assert r.status_code == 401
