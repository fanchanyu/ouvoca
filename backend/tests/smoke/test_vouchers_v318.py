"""
Smoke: Sprint L — 票據 + 進貨 + 出貨 + 會計（v3.18）

驗收：5 個關鍵 ERP 票據流前後端可用：
  - 進貨 (PO receive)
  - 出貨 (SO ship) → 自動扣庫存
  - 會計科目 / 傳票 / 過帳
  - 應收帳款 (AR)
"""
from __future__ import annotations


def _seed_supplier_part_po(client, headers, code_suffix="L01"):
    """建一條完整 PO 鏈：supplier + part + PO（draft）"""
    sup = client.post("/api/purchase/suppliers", headers=headers,
                      json={"code": f"VCH-SUP-{code_suffix}", "name": f"票據測試供應商 {code_suffix}"}).json()
    part = client.post("/api/inventory/parts", headers=headers, json={
        "part_no": f"VCH-PART-{code_suffix}", "name": f"票據測試料件 {code_suffix}",
        "category": "raw_material", "unit": "pcs", "safety_stock": 10, "unit_cost": 50,
    }).json()
    po = client.post("/api/purchase/orders", headers=headers, json={
        "supplier_id": sup["id"],
        "items": [{"part_id": part["id"], "ordered_qty": 20, "unit_price": 50}],
    }).json()
    return sup, part, po


# ── 進貨 (PO receive) ─────────────────────────────────────
def test_receive_po_full_flow(seeded_client, admin_headers):
    sup, part, po = _seed_supplier_part_po(seeded_client, admin_headers, "RCV01")

    # PO 應為 draft，先 approve
    r = seeded_client.post(f"/api/purchase/orders/{po['id']}/approve", headers=admin_headers)
    assert r.status_code == 200, r.text

    # 取得 PO 完整資料拿 item_id
    r = seeded_client.get(f"/api/purchase/orders/{po['id']}", headers=admin_headers)
    assert r.status_code == 200
    po_detail = r.json()
    items = po_detail.get("items", [])
    assert len(items) >= 1
    item_id = items[0]["id"]

    # 進貨：收 20 個（全收）
    r = seeded_client.post(f"/api/purchase/orders/{po['id']}/receive", headers=admin_headers,
                           json={"receipts": [{"item_id": item_id, "received_qty": 20}]})
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["status"] in ("received", "partial_received")


def test_receive_po_partial(seeded_client, admin_headers):
    sup, part, po = _seed_supplier_part_po(seeded_client, admin_headers, "RCV02")
    seeded_client.post(f"/api/purchase/orders/{po['id']}/approve", headers=admin_headers)
    po_detail = seeded_client.get(f"/api/purchase/orders/{po['id']}", headers=admin_headers).json()
    item_id = po_detail["items"][0]["id"]

    # 只收 5 個（部分）
    r = seeded_client.post(f"/api/purchase/orders/{po['id']}/receive", headers=admin_headers,
                           json={"receipts": [{"item_id": item_id, "received_qty": 5}]})
    assert r.status_code == 200
    assert r.json()["status"] == "partial_received"


# ── 出貨 (SO ship) ─────────────────────────────────────────
def test_ship_so_flow(seeded_client, admin_headers):
    # 建 customer + product + SO
    cust = seeded_client.post("/api/sales/customers", headers=admin_headers,
                              json={"code": "VCH-CUST-SH01", "name": "出貨測試客戶"}).json()
    prod = seeded_client.post("/api/production/products", headers=admin_headers,
                              json={"product_no": "VCH-PROD-SH01", "name": "出貨測試產品"}).json()
    so = seeded_client.post("/api/sales/orders", headers=admin_headers, json={
        "customer_id": cust["id"],
        "items": [{"product_id": prod["id"], "ordered_qty": 5, "unit_price": 200}],
    }).json()

    # 確認 SO（draft → confirmed）
    r = seeded_client.post(f"/api/sales/orders/{so['id']}/confirm", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    # 出貨
    r = seeded_client.post(f"/api/sales/orders/{so['id']}/ship", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("shipped", "delivered")


# ── 會計科目 ──────────────────────────────────────────────
def test_create_account_and_list(seeded_client, admin_headers):
    r = seeded_client.post("/api/accounting/accounts", headers=admin_headers, json={
        "code": "VCH-1101", "name": "現金 (測試)", "account_type": "asset",
        "is_debit_normal": True,
    })
    assert r.status_code == 200, r.text
    acc = r.json()
    assert acc["code"] == "VCH-1101"

    r = seeded_client.get("/api/accounting/accounts", headers=admin_headers)
    assert any(a["id"] == acc["id"] for a in r.json())


# ── 傳票 ───────────────────────────────────────────────────
def test_create_journal_with_balanced_lines(seeded_client, admin_headers):
    # 先建 2 個科目
    cash = seeded_client.post("/api/accounting/accounts", headers=admin_headers, json={
        "code": "VCH-JE-1101", "name": "現金", "account_type": "asset", "is_debit_normal": True,
    }).json()
    revenue = seeded_client.post("/api/accounting/accounts", headers=admin_headers, json={
        "code": "VCH-JE-4001", "name": "銷貨收入", "account_type": "revenue", "is_debit_normal": False,
    }).json()

    # 建傳票（借現金 1000 / 貸銷貨 1000）
    r = seeded_client.post("/api/accounting/journals", headers=admin_headers, json={
        "description": "5/15 收現金銷貨 NT$ 1000",
        "entry_date": "2026-05-15T00:00:00",  # backend NOT NULL
        "lines": [
            {"account_id": cash["id"], "debit": 1000, "credit": 0},
            {"account_id": revenue["id"], "debit": 0, "credit": 1000},
        ],
    })
    assert r.status_code == 200, r.text
    je = r.json()
    assert je["status"] == "draft"
    assert "entry_no" in je

    # 過帳
    r = seeded_client.post(f"/api/accounting/journals/{je['id']}/post", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "posted"


# ── AR 應收帳款 ──────────────────────────────────────────
def test_create_ar_and_list(seeded_client, admin_headers):
    cust = seeded_client.post("/api/sales/customers", headers=admin_headers,
                              json={"code": "VCH-AR-CUST", "name": "AR 測試客戶"}).json()

    r = seeded_client.post("/api/accounting/receivables", headers=admin_headers, json={
        "customer_id": cust["id"],
        "invoice_no": "INV-VCH-001",
        "invoice_date": "2026-05-15T00:00:00",
        "due_date": "2026-06-15T00:00:00",
        "amount": 50000,
    })
    assert r.status_code == 200, r.text
    ar = r.json()
    assert ar["amount"] == 50000
    assert ar["paid_amount"] == 0
    assert ar["status"] in ("open", "unpaid")

    # 列表
    r = seeded_client.get("/api/accounting/receivables", headers=admin_headers)
    assert any(x["id"] == ar["id"] for x in r.json())


def test_unauthorized_accounting_rejected(seeded_client):
    r = seeded_client.get("/api/accounting/journals")
    assert r.status_code == 401
    r = seeded_client.get("/api/accounting/receivables")
    assert r.status_code == 401
