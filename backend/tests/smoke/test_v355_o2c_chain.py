"""v3.55 — O2C 全鏈 (SO -> DN -> EInvoice -> JE -> AR) smoke tests.

王董：「出貨單沒對應傳票及發票號碼，進銷存三者沒有同步會很麻煩」
本測試確保 ship_sales_order 原子化建立整條鏈。
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

import pytest
from sqlalchemy import select


# ─── 1. DeliveryNote model ────────────────────────────────────

def test_delivery_note_model_exists():
    """DeliveryNote 必須是真的 ORM model 在 app.models.delivery。"""
    from app.models.delivery import DeliveryNote, DeliveryNoteItem

    assert DeliveryNote.__tablename__ == "delivery_notes"
    assert DeliveryNoteItem.__tablename__ == "delivery_note_items"
    cols = {c.name for c in DeliveryNote.__table__.columns}
    for col in (
        "id", "dn_no", "so_id", "ship_date", "carrier", "tracking_no",
        "signed_by", "signed_at", "status", "invoice_no",
        "journal_entry_id", "remarks", "tenant_id", "created_at", "created_by",
    ):
        assert col in cols, f"DeliveryNote 缺欄位 {col}"


def test_delivery_note_has_so_id_fk():
    """DeliveryNote.so_id 必須 FK 到 sales_orders.id。"""
    from app.models.delivery import DeliveryNote

    fks = DeliveryNote.__table__.c.so_id.foreign_keys
    assert any("sales_orders.id" in str(fk.target_fullname) for fk in fks), (
        "DeliveryNote.so_id 缺 FK 到 sales_orders.id"
    )


def test_delivery_note_registered_in_models_init():
    from app import models
    assert hasattr(models, "DeliveryNote"), "DeliveryNote 未在 app.models.__init__ import"
    assert hasattr(models, "DeliveryNoteItem")


def test_delivery_note_is_tenant_scoped():
    from app.models.delivery import DeliveryNote, DeliveryNoteItem
    from app.models._mixins import TenantMixin
    assert issubclass(DeliveryNote, TenantMixin)
    assert issubclass(DeliveryNoteItem, TenantMixin)


# ─── 2. Service signature ─────────────────────────────────────

def test_ship_sales_order_has_auto_invoice_param():
    """v3.55: ship_sales_order 必須支援 auto_invoice / auto_journal kwargs。"""
    import inspect
    from app.services.sales import ship_sales_order
    sig = inspect.signature(ship_sales_order)
    for p in ("auto_invoice", "auto_journal", "carrier", "tracking_no", "qty_to_ship"):
        assert p in sig.parameters, f"ship_sales_order 缺 {p} 參數"


# ─── 3. End-to-end (full chain) ──────────────────────────────

async def _setup_full_chain(buyer_tax_id: str | None = "12345675"):
    """建立必要的客戶/產品/料件/庫存/SO，回傳 (so_id, customer_id)。

    若 buyer_tax_id=None 則建立 B2C 客戶（無統編，應 skip einvoice）。
    """
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder, SalesOrderItem
    from app.models.product import Product
    from app.models.inventory import Part, Inventory
    from app.models.accounting import Account

    async with AsyncSessionLocal() as db:
        # 確保 chart of accounts 存在（v3.55 補入的 2200 銷項稅額）
        for code, name, atype, normal in [
            ("1200", "應收帳款", "asset", True),
            ("2200", "銷項稅額", "liability", False),
            ("4100", "銷售收入", "revenue", False),
        ]:
            existing = (await db.execute(
                select(Account).where(Account.code == code)
            )).scalar_one_or_none()
            if not existing:
                db.add(Account(
                    id=str(uuid.uuid4()), code=code, name=name,
                    account_type=atype, is_debit_normal=normal,
                ))

        uid = uuid.uuid4().hex[:8]
        # Customer (with optional tax_id — Customer 本表沒此欄，但 service 用 getattr)
        cust = Customer(
            id=str(uuid.uuid4()),
            code=f"O2C-CUST-{uid}",
            name=f"O2C 測試客戶 {uid}",
            grade="A", credit_limit=1_000_000,
            is_active=True, tenant_id="HQ",
        )
        # 動態塞 tax_id（model 沒此欄，但測試端用 setattr）
        if buyer_tax_id:
            try:
                cust.tax_id = buyer_tax_id
            except Exception:
                pass
        db.add(cust)

        # Part + Inventory
        part = Part(
            id=str(uuid.uuid4()),
            part_no=f"O2C-PART-{uid}",
            name="O2C 測試料件", category="component", unit="pcs",
            safety_stock=10, unit_cost=100, tenant_id="HQ",
        )
        db.add(part)
        inv = Inventory(
            id=str(uuid.uuid4()), part_id=part.id,
            qty_on_hand=1000, qty_allocated=0,
            qty_available=1000, qty_in_transit=0, tenant_id="HQ",
        )
        db.add(inv)

        # Product (product_no == part.part_no 約定)
        prod = Product(
            id=str(uuid.uuid4()),
            product_no=f"O2C-PART-{uid}",
            name="O2C 測試成品",
            category="成品", unit="pcs",
            selling_price=1050, standard_cost=500,
        )
        db.add(prod)
        await db.flush()

        # SO + item（單價 1050 含 5% 稅）
        so = SalesOrder(
            id=str(uuid.uuid4()),
            so_no=f"SO-O2C-{uid}",
            customer_id=cust.id,
            status="confirmed",
            order_date=datetime.utcnow(),
            total_amount=10500,  # 10 * 1050
            currency="TWD",
            tenant_id="HQ",
        )
        db.add(so)
        await db.flush()

        soi = SalesOrderItem(
            id=str(uuid.uuid4()),
            so_id=so.id, line_no=1, product_id=prod.id,
            ordered_qty=10, shipped_qty=0,
            unit_price=1050, line_total=10500,
        )
        db.add(soi)
        await db.commit()
        return so.id, cust.id


def test_ship_sales_order_creates_delivery_note(client):
    """ship_sales_order 必須生 DeliveryNote 並反寫 so.delivery_note_no。"""
    from app.database import AsyncSessionLocal
    from app.services.sales import ship_sales_order
    from app.models.delivery import DeliveryNote
    from app.models.crm_sales import SalesOrder

    so_id, _ = asyncio.run(_setup_full_chain(buyer_tax_id="12345675"))

    async def _ship():
        async with AsyncSessionLocal() as db:
            result = await ship_sales_order(db, so_id, user={"employee_id": "test"})
            return result

    result = asyncio.run(_ship())
    assert result["delivery_note"]["dn_no"].startswith("DN-")
    dn_id = result["delivery_note"]["id"]

    async def _verify():
        async with AsyncSessionLocal() as db:
            dn = (await db.execute(
                select(DeliveryNote).where(DeliveryNote.id == dn_id)
            )).scalar_one_or_none()
            assert dn is not None
            assert dn.so_id == so_id
            assert dn.status == "shipped"

            so = (await db.execute(
                select(SalesOrder).where(SalesOrder.id == so_id)
            )).scalar_one_or_none()
            assert so.delivery_note_no == dn.dn_no
            assert so.status == "shipped"

    asyncio.run(_verify())


def test_ship_sales_order_auto_creates_einvoice_if_taxid(client):
    """若 customer 有 tax_id → 自動建 EInvoiceRecord + 反寫 so.invoice_no。"""
    from app.database import AsyncSessionLocal
    from app.services.sales import ship_sales_order
    from app.models.tax_tw import EInvoiceRecord
    from app.models.crm_sales import SalesOrder

    so_id, _ = asyncio.run(_setup_full_chain(buyer_tax_id="12345675"))

    async def _ship():
        async with AsyncSessionLocal() as db:
            return await ship_sales_order(db, so_id, user={"employee_id": "test"})

    result = asyncio.run(_ship())
    assert result["invoice"] is not None, "B2B 客戶應自動產生發票"
    invoice_no = result["invoice"]["invoice_no"]
    assert invoice_no.startswith("AB")

    async def _verify():
        async with AsyncSessionLocal() as db:
            inv = (await db.execute(
                select(EInvoiceRecord).where(EInvoiceRecord.invoice_no == invoice_no)
            )).scalar_one_or_none()
            assert inv is not None
            assert inv.so_id == so_id
            assert inv.status == "issued"
            so = (await db.execute(
                select(SalesOrder).where(SalesOrder.id == so_id)
            )).scalar_one_or_none()
            assert so.invoice_no == invoice_no

    asyncio.run(_verify())


def test_ship_sales_order_auto_creates_journal_entry(client):
    """自動建 JE：DR AR / CR Revenue / CR Output Tax + source_type='SalesOrder'。"""
    from app.database import AsyncSessionLocal
    from app.services.sales import ship_sales_order
    from app.models.accounting import JournalEntry, JournalLine, Account

    so_id, _ = asyncio.run(_setup_full_chain(buyer_tax_id="12345675"))

    async def _ship():
        async with AsyncSessionLocal() as db:
            return await ship_sales_order(db, so_id, user={"employee_id": "test"})

    result = asyncio.run(_ship())
    assert result["journal_entry"] is not None
    je_id = result["journal_entry"]["id"]

    async def _verify():
        async with AsyncSessionLocal() as db:
            je = (await db.execute(
                select(JournalEntry).where(JournalEntry.id == je_id)
            )).scalar_one_or_none()
            assert je is not None
            assert je.source_type == "SalesOrder"
            assert je.source_id == so_id
            lines = (await db.execute(
                select(JournalLine).where(JournalLine.journal_entry_id == je_id)
            )).scalars().all()
            assert len(lines) == 3, "應有 3 行：DR AR / CR Revenue / CR Output Tax"

            total_debit = sum(l.debit or 0 for l in lines)
            total_credit = sum(l.credit or 0 for l in lines)
            assert round(total_debit, 2) == round(total_credit, 2), "借貸不平"

            # 確認對應科目
            codes_seen = set()
            for l in lines:
                acc = (await db.execute(
                    select(Account).where(Account.id == l.account_id)
                )).scalar_one_or_none()
                codes_seen.add(acc.code)
            assert codes_seen == {"1200", "4100", "2200"}, f"科目錯誤: {codes_seen}"

    asyncio.run(_verify())


def test_ship_sales_order_back_writes_so_invoice_no(client):
    """SO.invoice_no / delivery_note_no / ar_id 三個欄位必須回寫。"""
    from app.database import AsyncSessionLocal
    from app.services.sales import ship_sales_order
    from app.models.crm_sales import SalesOrder

    so_id, _ = asyncio.run(_setup_full_chain(buyer_tax_id="12345675"))

    async def _go():
        async with AsyncSessionLocal() as db:
            await ship_sales_order(db, so_id, user={"employee_id": "test"})
            so = (await db.execute(
                select(SalesOrder).where(SalesOrder.id == so_id)
            )).scalar_one_or_none()
            return so.invoice_no, so.delivery_note_no, so.ar_id

    invoice_no, dn_no, ar_id = asyncio.run(_go())
    assert invoice_no, "so.invoice_no 未回寫"
    assert dn_no, "so.delivery_note_no 未回寫"
    assert ar_id, "so.ar_id 未回寫"


def test_ship_sales_order_atomic_rollback_on_failure(client):
    """若中途 fail（例如 SO 狀態不對），不應留下任何 DN/JE。"""
    from app.database import AsyncSessionLocal
    from app.services.sales import ship_sales_order
    from app.core.exceptions import BusinessRuleError
    from app.models.delivery import DeliveryNote

    so_id, _ = asyncio.run(_setup_full_chain(buyer_tax_id="12345675"))

    async def _verify_before():
        async with AsyncSessionLocal() as db:
            cnt = (await db.execute(
                select(DeliveryNote).where(DeliveryNote.so_id == so_id)
            )).scalars().all()
            return len(cnt)

    before = asyncio.run(_verify_before())

    async def _ship_twice():
        # 第一次出貨成功，第二次（狀態已 shipped）應 fail
        async with AsyncSessionLocal() as db:
            await ship_sales_order(db, so_id, user={"employee_id": "test"})
        async with AsyncSessionLocal() as db:
            with pytest.raises(BusinessRuleError):
                await ship_sales_order(db, so_id, user={"employee_id": "test"})

    asyncio.run(_ship_twice())

    async def _verify_after():
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(DeliveryNote).where(DeliveryNote.so_id == so_id)
            )).scalars().all()
            return len(rows)

    after = asyncio.run(_verify_after())
    # 應只有 1 張 DN（第一次成功）；第二次 fail 不應產生第二張
    assert after - before == 1, f"預期 1 張 DN，實得 {after - before}（rollback 失敗）"


def test_ship_sales_order_b2c_skips_einvoice(client):
    """B2C（無 tax_id）：仍建 DN/JE/AR，但 invoice=None。"""
    from app.database import AsyncSessionLocal
    from app.services.sales import ship_sales_order

    so_id, _ = asyncio.run(_setup_full_chain(buyer_tax_id=None))

    async def _ship():
        async with AsyncSessionLocal() as db:
            return await ship_sales_order(db, so_id, user={"employee_id": "test"})

    result = asyncio.run(_ship())
    assert result["delivery_note"]["dn_no"], "B2C 仍應有 DN"
    assert result["invoice"] is None, "B2C 應 skip einvoice"
    assert result["journal_entry"] is not None, "B2C 仍應有 JE"
    assert result["ar"] is not None, "B2C 仍應有 AR"


# ─── 4. API endpoints ────────────────────────────────────────

def test_list_delivery_notes_endpoint_exists():
    from app.api.sales import router
    paths = {route.path for route in router.routes}
    assert "/api/sales/delivery-notes" in paths, (
        f"缺 GET /api/sales/delivery-notes；現有: {sorted(paths)}"
    )


def test_get_delivery_note_endpoint_exists():
    from app.api.sales import router
    paths = {route.path for route in router.routes}
    assert "/api/sales/delivery-notes/{dn_id}" in paths


def test_ship_endpoint_accepts_auto_invoice_param():
    """ship 端點 ShipRequest body 必須有 auto_invoice/auto_journal/carrier/tracking_no。"""
    from app.api.sales import ShipRequest
    fields = ShipRequest.model_fields
    for f in ("auto_invoice", "auto_journal", "carrier", "tracking_no", "qty_to_ship"):
        assert f in fields, f"ShipRequest 缺欄位 {f}"
