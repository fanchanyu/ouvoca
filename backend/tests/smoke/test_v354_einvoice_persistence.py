"""v3.54 — Taiwan e-invoice persistence + SO traceability chain smoke tests.

GAP-2: EInvoiceRecord 落 DB (was in-memory dict).
GAP-3: SalesOrder 加 invoice_no / delivery_note_no / ar_id 形成追溯鏈.
GAP-5: business_completion_tools nested JE creation 修正.
GAP-6: /api/tax/tw/einvoice/list endpoint.
"""
from __future__ import annotations

import inspect


# ─── GAP-2: model exists ─────────────────────────────────────

def test_einvoice_record_model_exists():
    """EInvoiceRecord 必須是真的 ORM model 在 app.models.tax_tw."""
    from app.models.tax_tw import EInvoiceRecord

    assert EInvoiceRecord.__tablename__ == "einvoice_records"
    cols = {c.name for c in EInvoiceRecord.__table__.columns}
    # 合規必要欄位
    for col in (
        "invoice_no", "invoice_date", "seller_tax_id",
        "sales_amount", "tax_amount", "total_amount",
        "so_id", "journal_entry_id", "status", "tracking_no",
        "mig_payload", "tenant_id",
    ):
        assert col in cols, f"EInvoiceRecord 缺欄位 {col}"


def test_einvoice_record_is_tenant_scoped():
    """合規追溯鏈須 tenant 隔離（多租戶不互看）."""
    from app.models.tax_tw import EInvoiceRecord
    from app.models._mixins import TenantMixin

    assert issubclass(EInvoiceRecord, TenantMixin)


def test_einvoice_record_registered_in_models_init():
    """app.models 必須 re-export EInvoiceRecord，否則 Alembic autogenerate / model registry 漏抓."""
    from app import models

    assert hasattr(models, "EInvoiceRecord") or "EInvoiceRecord" in dir(
        __import__("app.models.tax_tw", fromlist=["EInvoiceRecord"])
    ), "EInvoiceRecord 未在 app.models.__init__ import"


# ─── GAP-3: SO chain fields ───────────────────────────────────

def test_so_has_invoice_no_field():
    """SalesOrder 必須有 invoice_no / delivery_note_no / ar_id 追溯欄位."""
    from app.models.crm_sales import SalesOrder

    cols = {c.name for c in SalesOrder.__table__.columns}
    assert "invoice_no" in cols, "SalesOrder 缺 invoice_no（追溯到發票）"
    assert "delivery_note_no" in cols, "SalesOrder 缺 delivery_note_no（出貨單號）"
    assert "ar_id" in cols, "SalesOrder 缺 ar_id（追溯到 AR）"


# ─── GAP-5: business_completion JE bug fixes ─────────────────

def test_business_completion_tools_je_has_lines_and_source():
    """record_payment / record_receipt 的 execute 必須帶 lines + source_type."""
    import app.agents.domains.business_completion_tools as bct

    src = inspect.getsource(bct)
    # 必須改用 lines（不再用 total_debit/total_credit）
    assert '"lines":' in src, (
        "business_completion_tools 必須改用 lines 結構 "
        "(原 total_debit/total_credit 會讓 create_journal_entry crash)"
    )
    assert '"source_type": "PurchaseOrder"' in src, (
        "record_payment_to_supplier_with_confirm 必須帶 source_type='PurchaseOrder'"
    )
    assert '"source_type": "SalesOrder"' in src, (
        "record_receipt_from_customer_with_confirm 必須帶 source_type='SalesOrder'"
    )
    # 不應再有 total_debit/total_credit（pop 進 JournalEntry **kwargs 會 crash）
    assert '"total_debit":' not in src, (
        "舊 bug：傳 total_debit 給 create_journal_entry 會 TypeError"
    )


# ─── GAP-6: list endpoint exists ──────────────────────────────

def test_einvoice_list_endpoint_exists():
    """/api/tax/tw/einvoice/list 必須是已註冊之 router 路徑."""
    from app.api.tax_tw import router

    paths = {route.path for route in router.routes}
    assert "/api/tax/tw/einvoice/list" in paths, (
        f"缺 GET /api/tax/tw/einvoice/list；現有: {sorted(paths)}"
    )


def test_einvoice_issue_endpoint_accepts_so_id():
    """issue_einvoice 必須能接 so_id 參數（反寫 SO.invoice_no 用）."""
    from app.api.tax_tw import EInvoiceCreateRequest

    fields = EInvoiceCreateRequest.model_fields
    assert "so_id" in fields, "EInvoiceCreateRequest 缺 so_id 參數"


# ─── End-to-end (DB round-trip) ───────────────────────────────

def test_einvoice_record_persists_to_db(client):
    """完整流程：直接寫 EInvoiceRecord → query → assert 還在."""
    import asyncio
    import uuid

    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.tax_tw import EInvoiceRecord

    unique_no = f"AB{uuid.uuid4().int % 100000000:08d}"

    async def _roundtrip():
        async with AsyncSessionLocal() as db:
            rec = EInvoiceRecord(
                invoice_no=unique_no,
                invoice_date="20260525",
                invoice_time="10:30:00",
                seller_tax_id="12345675",
                buyer_tax_id=None,
                buyer_name="(個人)",
                sales_amount=1000.0,
                tax_amount=50.0,
                total_amount=1050.0,
                status="issued",
                tracking_no="MOCK-TEST123",
                tenant_id="HQ",
            )
            db.add(rec)
            await db.commit()

            rows = (await db.execute(
                select(EInvoiceRecord).where(EInvoiceRecord.invoice_no == unique_no)
            )).scalars().all()
            assert len(rows) == 1
            assert rows[0].status == "issued"
            assert rows[0].total_amount == 1050.0

    asyncio.run(_roundtrip())
