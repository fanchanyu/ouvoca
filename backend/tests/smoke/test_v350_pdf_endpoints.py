"""v3.50 PDF endpoint smoke tests.

Covers:
  • POST /api/print/einvoice — in-memory snapshot → PDF
  • Routes registered for /api/print/po/{id}.pdf, /api/print/so/{id}.pdf,
    /api/print/delivery/{id}.pdf

These endpoints previously had a frontend gap: the UI was printing
HTML summaries that explicitly omitted line items. Now the frontend
calls the backend reportlab generators directly.
"""
from __future__ import annotations


def test_einvoice_pdf_endpoint_returns_pdf(seeded_client, admin_headers):
    """POST /api/print/einvoice with a sample payload returns a PDF blob."""
    payload = {
        "invoice_no": "AA-99999999",
        "invoice_date": "2026-05-24",
        "seller_tax_id": "04595257",
        "seller_name": "示範公司股份有限公司",
        "buyer_tax_id": "12345675",
        "buyer_name": "客戶有限公司",
        "items": [
            {"description": "螺絲 M6 x 100", "qty": 100, "unit_price": 5, "amount": 500},
            {"description": "墊片 W6",       "qty": 200, "unit_price": 2, "amount": 400},
        ],
        "total": 857,         # 未稅
        "tax": 43,            # 5%
        "grand_total": 900,   # 含稅
        "tracking_no": "TR-99999999-XYZ",
    }
    r = seeded_client.post(
        "/api/print/einvoice", json=payload, headers=admin_headers,
    )
    assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
    assert r.headers.get("content-type", "").startswith("application/pdf")
    body = r.content
    # PDF magic header
    assert body[:4] == b"%PDF", "回應不是合法 PDF 檔頭"
    # 完整明細必須出現（之前 HTML 版會省略 → 用 PDF 長度當代理檢核）
    assert len(body) > 1000, f"PDF 過小（{len(body)} bytes），可能未含明細"


def test_einvoice_pdf_works_without_optional_totals(seeded_client, admin_headers):
    """缺 total/tax/grand_total 時自動由 items 重算，不應炸開。"""
    payload = {
        "invoice_no": "AB-11111111",
        "seller_tax_id": "04595257",
        "seller_name": "示範公司",
        "buyer_name": "個人",
        "items": [
            {"description": "服務費", "qty": 1, "unit_price": 1050},
        ],
    }
    r = seeded_client.post(
        "/api/print/einvoice", json=payload, headers=admin_headers,
    )
    assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
    assert r.content[:4] == b"%PDF"


def test_po_so_delivery_pdf_routes_registered(_app):
    """確認 v3.36 的 PO / SO / Delivery PDF 路由仍存在（前端 v3.50 直接呼叫）。"""
    routes = {getattr(r, "path", "") for r in _app.routes}
    assert "/api/print/po/{po_id}.pdf" in routes
    assert "/api/print/so/{so_id}.pdf" in routes
    assert "/api/print/delivery/{so_id}.pdf" in routes
    assert "/api/print/einvoice" in routes  # v3.50 新增


def test_po_pdf_endpoint_404_for_unknown_id(seeded_client, admin_headers):
    """無此 PO 應回 404（不應是 500）。"""
    r = seeded_client.get(
        "/api/print/po/00000000-0000-0000-0000-000000000000.pdf",
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_so_pdf_endpoint_404_for_unknown_id(seeded_client, admin_headers):
    r = seeded_client.get(
        "/api/print/so/00000000-0000-0000-0000-000000000000.pdf",
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_delivery_pdf_endpoint_404_for_unknown_id(seeded_client, admin_headers):
    r = seeded_client.get(
        "/api/print/delivery/00000000-0000-0000-0000-000000000000.pdf",
        headers=admin_headers,
    )
    assert r.status_code == 404
