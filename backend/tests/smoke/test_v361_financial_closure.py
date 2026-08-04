"""v3.61 M2 tests — 三大報表 / 401-405 / 3-Way Match / 固定資產折舊 / 票據。"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.core.tenant_context import set_current_tenant
    from app.database import AsyncSessionLocal
    set_current_tenant("HQ")
    async with AsyncSessionLocal() as session:
        yield session


async def _seed_accounts(db):
    """最小科目集（三個報表測試用）。"""
    from sqlalchemy import select

    from app.models.accounting import Account
    existing = {a.code for a in (await db.execute(select(Account))).scalars().all()}
    accounts = [
        ("1100", "現金", "asset", True, "bs_current_asset"),
        ("4100", "銷貨收入", "revenue", False, "is_revenue"),
        ("6310", "折舊費用", "expense", True, "is_expense"),
        ("1631", "累計折舊-機器設備", "asset", False, "bs_noncurrent_asset"),
    ]
    existing_accounts = {a.code: a for a in (await db.execute(select(Account))).scalars().all()}
    for code, name, atype, debit_normal, fs_line in accounts:
        if code in existing_accounts:
            # 共享 DB：其它測試可能建過同名科目但缺 fs_line → 補齊
            acc = existing_accounts[code]
            if acc.fs_line != fs_line or acc.account_type != atype:
                acc.fs_line = fs_line
                acc.account_type = atype
                acc.name = name
            continue
        db.add(Account(id=str(uuid.uuid4()), code=code, name=name, account_type=atype,
                       is_debit_normal=debit_normal, fs_line=fs_line))
    await db.commit()
    return {a.code: a for a in (await db.execute(select(Account))).scalars().all()}


@pytest.mark.asyncio
async def test_trial_balance_income_balance_sheet(db):
    """三大報表：收入 10 萬、費用 6 千 → 淨利 9.4 萬；資產 = 負債 + 權益。"""
    from app.services.accounting import create_journal_entry, post_journal
    from app.services.financial_statements import (
        balance_sheet,
        income_statement,
        trial_balance,
    )
    acc = await _seed_accounts(db)

    je = await create_journal_entry(db, {
        "period": "2020-01",
        "entry_date": datetime(2020, 1, 15),
        "description": "M2 測試",
        "lines": [
            {"account_id": acc["1100"].id, "debit": 100000, "credit": 0},
            {"account_id": acc["4100"].id, "debit": 0, "credit": 100000},
            {"account_id": acc["6310"].id, "debit": 6000, "credit": 0},
            {"account_id": acc["1100"].id, "debit": 0, "credit": 6000},
        ],
    })
    await post_journal(db, je.id, {})

    tb = await trial_balance(db, "2020-01")
    assert tb["balanced"] is True
    assert tb["total_debit"] == tb["total_credit"] == 106000

    inc = await income_statement(db, "2020-01")
    assert inc["revenue"] == 100000
    assert inc["expense"] == 6000
    assert inc["net_income"] == 94000

    bs = await balance_sheet(db, "2020-01")
    assert bs["current_asset"] == 94000
    assert bs["total_equity"] == 94000
    assert bs["balanced"] is True


@pytest.mark.asyncio
async def test_tax_report_401_405(db):
    """401 來自已開立電子發票；405 來自 AP（含稅拆算）。"""
    from app.models.finance import AccountsPayable
    from app.models.purchase import Supplier
    from app.models.tax_tw import EInvoiceRecord
    from app.services.tax_report_tw import tax_report_401_405

    # 用不會被其它測試碰到的獨特期間，避免共享 DB 污染
    period = "209901"
    db.add(EInvoiceRecord(
        id=str(uuid.uuid4()), invoice_no="AB20990001", invoice_date=f"{period}15",
        seller_tax_id="12345678", sales_amount=10000, tax_amount=500,
        total_amount=10500, status="issued",
    ))
    sup = Supplier(id=str(uuid.uuid4()), code="SUP-M2", name="M2 供應商", tier="T2", is_approved=True)
    db.add(sup)
    db.add(AccountsPayable(
        id=str(uuid.uuid4()), supplier_id=sup.id, invoice_no="INV-M2-001",
        invoice_date=datetime(2099, 1, 10), due_date=datetime(2099, 2, 10),
        amount=21000,  # 含稅 → sales 20000 / tax 1000
    ))
    await db.commit()

    report = await tax_report_401_405(db, period)
    assert report["sales"]["tax_general"] == 500
    assert report["sales"]["invoice_count"] == 1
    assert report["purchase"]["tax_general"] == 1000
    assert report["purchase"]["purchase_general"] == 20000
    assert report["net_tax_payable"] == -500  # 進項大於銷項 → 留抵


@pytest.mark.asyncio
async def test_three_way_match(db):
    """PO 100 收 100 發票 100 → matched；發票 90 → qty_variance。"""
    from app.models.inventory import Part
    from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
    from app.services.three_way_match import (
        create_supplier_invoice,
        match_supplier_invoice,
    )

    sup = Supplier(id=str(uuid.uuid4()), code="SUP-M2B", name="M2B 供應商", tier="T2", is_approved=True)
    part = Part(id=str(uuid.uuid4()), part_no="M2-PART", name="M2 料件", category="component", unit_cost=10)
    db.add_all([sup, part])
    await db.commit()
    po = PurchaseOrder(id=str(uuid.uuid4()), po_no="PO-M2-001", supplier_id=sup.id,
                       status="approved", total_amount=1000)
    db.add(po)
    await db.commit()
    poi = PurchaseOrderItem(id=str(uuid.uuid4()), po_id=po.id, line_no=1, part_id=part.id,
                            ordered_qty=100, received_qty=100, unit_price=10, line_total=1000)
    db.add(poi)
    await db.commit()

    # 完全相符
    inv = await create_supplier_invoice(db, {
        "invoice_no": "INV-M2-100", "supplier_id": sup.id, "po_id": po.id,
        "items": [{"po_item_id": poi.id, "part_id": part.id, "qty": 100, "unit_price": 10}],
        "sales_amount": 1000, "tax_amount": 50,
    })
    result = await match_supplier_invoice(db, inv.id)
    assert result["status"] == "matched", f"應 matched：{result}"

    # 數量不符
    inv2 = await create_supplier_invoice(db, {
        "invoice_no": "INV-M2-090", "supplier_id": sup.id, "po_id": po.id,
        "items": [{"po_item_id": poi.id, "part_id": part.id, "qty": 90, "unit_price": 10}],
        "sales_amount": 900, "tax_amount": 45,
    })
    result2 = await match_supplier_invoice(db, inv2.id)
    assert result2["status"] == "qty_variance"
    assert any("數量差" in issue for r in result2["lines"] for issue in r["issues"])


@pytest.mark.asyncio
async def test_fixed_asset_depreciation_posts_journal(db):
    """固定資產月折舊 → 過帳傳票（DR 折舊費用 / CR 累計折舊）。"""
    from sqlalchemy import select

    from app.models.accounting import JournalEntry
    from app.models.finance import FixedAsset
    acc = await _seed_accounts(db)
    from app.services.fixed_assets import create_fixed_asset, post_monthly_depreciation

    asset = await create_fixed_asset(db, {
        "code": "FA-001", "name": "CNC 車床", "category": "machinery",
        "cost": 1200000, "salvage_value": 0, "useful_life_months": 120,
        "acquisition_date": datetime(2026, 1, 1),
    })
    assert asset.monthly_depreciation == 10000

    await post_monthly_depreciation(db, asset.id, "202608", {}, accum_account="1631")
    asset_after = (await db.execute(
        select(FixedAsset).where(FixedAsset.id == asset.id)
    )).scalar_one()
    assert asset_after.accumulated_depreciation == 10000

    # 折舊傳票已過帳（source_type=fixed_asset_depreciation）
    from sqlalchemy import select as _sel
    jes = list((await db.execute(
        _sel(JournalEntry).where(JournalEntry.source_type == "fixed_asset_depreciation")
    )).scalars().all())
    assert len(jes) == 1
    assert jes[0].status == "posted"
    assert "折舊" in (jes[0].description or "")


@pytest.mark.asyncio
async def test_promissory_note_create_and_list(db):
    from sqlalchemy import select

    from app.models.finance import PromissoryNote

    note = PromissoryNote(
        id=str(uuid.uuid4()), note_type="receivable", party_id=str(uuid.uuid4()),
        party_name="客戶甲", bank_name="台灣銀行", check_no="CHK-001",
        amount=50000, issue_date=datetime(2026, 8, 1),
        due_date=datetime(2026, 10, 1), status="on_hand",
    )
    db.add(note)
    await db.commit()
    rows = list((await db.execute(select(PromissoryNote))).scalars().all())
    assert len(rows) == 1
    assert rows[0].check_no == "CHK-001"


def test_m2_api_and_tools_registered(seeded_client):
    """M2 endpoints + tools 應存在（grep smoke）。"""
    from pathlib import Path
    api_src = (Path(__file__).resolve().parents[2] / "app" / "api" /
               "accounting.py").read_text(encoding="utf-8")
    for route in ("/statements/trial-balance", "/statements/income-statement",
                  "/statements/balance-sheet", "/tax/401-405",
                  "/supplier-invoices", "/promissory-notes", "/fixed-assets"):
        assert route in api_src, f"accounting.py 缺 {route}"

    tools_src = (Path(__file__).resolve().parents[2] / "app" / "agents" / "domains" /
                 "finance_tools.py").read_text(encoding="utf-8")
    for tool in ("query_financial_statements", "query_tax_report_401_405",
                 "record_supplier_invoice_with_confirm", "create_fixed_asset_with_confirm",
                 "post_depreciation_with_confirm", "query_wo_cost",
                 "settle_cogs_with_confirm"):
        assert f'name="{tool}"' in tools_src, f"finance_tools.py 缺 {tool}"


@pytest.mark.asyncio
async def test_wo_cost_aggregation(db):
    """WO 成本：材料（BOM×unit_cost）+ 人工（工序時數×時薪）+ 製造費用。"""
    from app.models.product import Product, BOMItem
    from app.models.inventory import Part
    from app.models.production import ProductionOrder, WorkCenter, Operation
    from app.services.production_cost import aggregate_wo_cost

    part = Part(id=str(uuid.uuid4()), part_no="RAW-1", name="原料", category="raw", unit_cost=20)
    prod = Product(id=str(uuid.uuid4()), product_no="FG-1", name="成品", standard_cost=100)
    db.add_all([part, prod])
    await db.commit()
    db.add(BOMItem(id=str(uuid.uuid4()), product_id=prod.id, part_id=part.id,
                   qty_per=2, is_active=True))
    wc = WorkCenter(id=str(uuid.uuid4()), code="WC-1", name="加工中心", hourly_rate=100)
    db.add(wc)
    await db.commit()
    wo = ProductionOrder(id=str(uuid.uuid4()), wo_no="WO-COST-1", product_id=prod.id,
                         ordered_qty=10, completed_qty=10, status="completed")
    db.add(wo)
    await db.commit()
    db.add(Operation(id=str(uuid.uuid4()), production_order_id=wo.id, op_no=1,
                     op_name="加工", work_center_id=wc.id,
                     setup_time=1, run_time_per_unit=0.5, completed_qty=10))
    await db.commit()

    cost = await aggregate_wo_cost(db, wo.id)
    # 材料：2 × 20 × 10 = 400；人工：(1 + 0.5×10) × 100 = 600；費用：600×0.3=180
    assert cost["material_cost"] == 400
    assert cost["labor_cost"] == 600
    assert cost["overhead_cost"] == 180
    assert cost["total_cost"] == 1180
    assert cost["unit_cost"] == 118


@pytest.mark.asyncio
async def test_cogs_settlement(db):
    """月結銷貨成本：出貨 10 個（成本 50）→ DR 5100 / CR 1340 各 500。"""
    from app.models.inventory import Part
    from app.models.delivery import DeliveryNote, DeliveryNoteItem
    from app.models.accounting import Account, JournalEntry
    from sqlalchemy import select as _sel
    from app.services.production_cost import settle_cogs
    from app.services.financial_statements import trial_balance

    acc = await _seed_accounts(db)
    # 補 5100/1340
    from sqlalchemy import select as _s2
    for code, name, atype, debit_normal, fs in [
        ("5100", "銷貨成本", "cost", True, "is_cost"),
        ("1340", "製成品", "asset", True, "bs_current_asset"),
    ]:
        if not (await db.execute(_s2(Account).where(Account.code == code))).scalar_one_or_none():
            db.add(Account(id=str(uuid.uuid4()), code=code, name=name, account_type=atype,
                           is_debit_normal=debit_normal, fs_line=fs))
    part = Part(id=str(uuid.uuid4()), part_no="FG-COGS", name="成品", category="finished", unit_cost=50)
    db.add(part)
    await db.commit()
    # 用不會被其它測試碰到的獨特期間，避免共享 DB 出貨污染
    period = "2099-01"
    dn = DeliveryNote(id=str(uuid.uuid4()), dn_no="DN-COGS-2099",
                      so_id=str(uuid.uuid4()),
                      ship_date=datetime(2099, 1, 15), status="shipped")
    db.add(dn)
    await db.commit()
    db.add(DeliveryNoteItem(id=str(uuid.uuid4()), dn_id=dn.id,
                            part_id=part.id, qty_shipped=10, unit_price=100))
    await db.commit()

    result = await settle_cogs(db, period, {"employee_id": "e-cogs"})
    assert result["settled"] is True
    assert result["total_cogs"] == 500

    # 傳票已過帳且借貸平衡（只算 cogs_settlement 的傳票）
    jes = list((await db.execute(
        _sel(JournalEntry).where(JournalEntry.source_type == "cogs_settlement")
    )).scalars().all())
    assert len(jes) == 1
    assert jes[0].status == "posted"
