"""
台灣稅務模組 smoke tests:
1. 統一編號驗證（真實演算法）
2. 電子發票格式驗證
3. 401 endpoint 回應
4. 電子發票 mock provider 流程
"""
import pytest
from app.integrations.einvoice_tw import (
    validate_tax_id,
    validate_invoice_no,
    calc_tax,
    EInvoice,
    InvoiceLineItem,
    MockEInvoiceProvider,
)


# ─── 1. 統編驗證 ───────────────────────────────────────────

@pytest.mark.parametrize("valid_id", [
    "12345675",   # 經典演算法測試值
    "04595257",   # 統一超商（公開資料）
])
def test_valid_tax_ids(valid_id):
    """常見已知正確的統編應通過."""
    assert validate_tax_id(valid_id), f"{valid_id} 應有效"


@pytest.mark.parametrize("invalid_id", [
    "",
    "1234",          # 太短
    "123456789",     # 太長
    "abcdefgh",      # 非數字
    "12345678",      # 8 位但 checksum 不對
])
def test_invalid_tax_ids(invalid_id):
    assert not validate_tax_id(invalid_id), f"{invalid_id} 不應有效"


# ─── 2. 發票格式驗證 ──────────────────────────────────────

@pytest.mark.parametrize("valid", ["AB12345678", "AB-12345678", "ZX99999999"])
def test_invoice_no_valid(valid):
    assert validate_invoice_no(valid)


@pytest.mark.parametrize("invalid", ["12345678", "AB1234567", "ABCD12345678", ""])
def test_invoice_no_invalid(invalid):
    assert not validate_invoice_no(invalid)


# ─── 3. 稅額計算 ───────────────────────────────────────────

def test_tax_calculation_5_percent():
    tax, total = calc_tax(1000)
    assert tax == 50
    assert total == 1050


def test_tax_rounding():
    # 99 * 0.05 = 4.95 → 應四捨五入到 5
    tax, total = calc_tax(99)
    assert tax == 5
    assert total == 104


# ─── 4. EInvoice 全流程 ────────────────────────────────────

def test_einvoice_valid_submission():
    p = MockEInvoiceProvider()
    inv = EInvoice(
        invoice_no="AB12345678",
        invoice_date="20260514",
        invoice_time="14:30:00",
        seller_tax_id="12345675",
        seller_name="測試公司",
        buyer_tax_id="04595257",
        buyer_name="統一超商",
        sales_amount=1000,
        tax_amount=50,
        total_amount=1050,
        line_items=[
            InvoiceLineItem(description="M6 螺絲", qty=100, unit_price=10.5, amount=1050),
        ],
    )
    result = p.submit(inv)
    assert result["success"], result.get("errors")
    assert result["tracking_no"]


def test_einvoice_invalid_tax_id_rejected():
    p = MockEInvoiceProvider()
    inv = EInvoice(
        invoice_no="AB12345678",
        invoice_date="20260514",
        invoice_time="14:30:00",
        seller_tax_id="00000000",  # 無效統編
        seller_name="壞公司",
        sales_amount=1000,
        tax_amount=50,
        total_amount=1050,
    )
    result = p.submit(inv)
    assert not result["success"]
    assert any("統編" in e for e in result["errors"])


def test_einvoice_mig_dict_structure():
    inv = EInvoice(
        invoice_no="AB12345678",
        invoice_date="20260514",
        invoice_time="14:30:00",
        seller_tax_id="12345675",
        seller_name="X",
        sales_amount=1000, tax_amount=50, total_amount=1050,
    )
    d = inv.to_mig_dict()
    # 對應財政部 MIG 3.2.1 的關鍵欄位
    for k in ("InvoiceNumber", "InvoiceDate", "Seller", "Buyer",
              "SalesAmount", "TaxAmount", "TotalAmount", "RandomNumber"):
        assert k in d, f"MIG 缺欄位 {k}"


# ─── 5. API endpoints ────────────────────────────────────

def test_validate_tax_id_endpoint_valid(client):
    """公開 endpoint：驗證有效統編。"""
    r = client.get("/api/tax/tw/validate-tax-id/12345675")
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_validate_tax_id_endpoint_invalid(client):
    r = client.get("/api/tax/tw/validate-tax-id/00000000")
    assert r.status_code == 200
    assert r.json()["valid"] is False


def test_form_401_endpoint(seeded_client, admin_headers):
    """401 申報表能產出（即使沒資料也應回 0）。"""
    r = seeded_client.get(
        "/api/tax/tw/401?year=2026&period_no=1",
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["form"] == "401"
    for k in ("sales_taxable", "output_tax", "input_tax_general", "tax_payable"):
        assert k in data


def test_form_403_sales(seeded_client, admin_headers):
    r = seeded_client.get(
        "/api/tax/tw/403?year=2026&period_no=1&direction=sales",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["direction"] == "sales"


def test_form_403_purchase(seeded_client, admin_headers):
    r = seeded_client.get(
        "/api/tax/tw/403?year=2026&period_no=1&direction=purchase",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["direction"] == "purchase"


def test_einvoice_issue_endpoint(seeded_client, admin_headers):
    """開立電子發票全流程."""
    r = seeded_client.post(
        "/api/tax/tw/einvoice/issue",
        json={
            "invoice_no": "AB99999999",
            "seller_tax_id": "12345675",
            "seller_name": "Seller",
            "buyer_tax_id": "04595257",
            "buyer_name": "Buyer",
            "items": [{"description": "M6", "qty": 100, "unit_price": 10.5}],
        },
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["success"]
    assert r.json()["tracking_no"]
