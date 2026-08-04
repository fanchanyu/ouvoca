"""v3.67 Turnkey P0-3 — 家規 20 條。"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.database import AsyncSessionLocal
    from app.core.tenant_context import set_current_tenant
    set_current_tenant("HQ")
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_20_default_house_rules_installed(db):
    """家規至少 20 條（Turnkey P0-3 規格）。"""
    from app.services.policy_engine import DEFAULT_RULES, install_default_rules
    assert len(DEFAULT_RULES) >= 20, f"DEFAULT_RULES 只有 {len(DEFAULT_RULES)} 條"
    await install_default_rules(db, tenant_id="HQ")
    from app.models.policy_rule import PolicyRule
    from sqlalchemy import select, func
    count = (await db.execute(
        select(func.count(PolicyRule.id)).where(PolicyRule.tenant_id == "HQ")
    )).scalar_one()
    assert count >= 20, f"DB 家規只有 {count} 條"


@pytest.mark.asyncio
async def test_so_ship_policy_blocks_draft(db):
    """家規生效：未確認 SO 出貨被擋（so.ship 觸發）。"""
    from app.services.policy_engine import install_default_rules
    from app.services.sales import create_sales_order, ship_sales_order
    from app.models.crm_sales import Customer
    from app.models.product import Product
    from app.core.exceptions import BusinessRuleError

    await install_default_rules(db, tenant_id="HQ")
    cust = Customer(id=str(uuid.uuid4()), code="HR-CUST", name="家規客戶",
                    credit_limit=1000000)
    prod = Product(id=str(uuid.uuid4()), product_no="HR-PROD", name="家規產品",
                   standard_cost=10, selling_price=50)
    db.add_all([cust, prod])
    await db.commit()
    so = await create_sales_order(db, {
        "customer_id": cust.id,
        "items": [{"product_id": prod.id, "ordered_qty": 10, "unit_price": 50}],
    }, {"employee_id": "e-hr"})

    # 未確認就出貨 → so.ship 家規擋下
    with pytest.raises(BusinessRuleError, match="尚未確認"):
        await ship_sales_order(db, so.id, user={"employee_id": "e-hr"})


@pytest.mark.asyncio
async def test_so_create_passes_policy_when_valid(db):
    """家規放行：正常 SO（有額度、有統編）可建立。"""
    from app.services.policy_engine import install_default_rules
    from app.services.sales import create_sales_order
    from app.models.crm_sales import Customer
    from app.models.product import Product

    await install_default_rules(db, tenant_id="HQ")
    cust = Customer(id=str(uuid.uuid4()), code="HR-CUST2", name="家規客戶二",
                    credit_limit=1000000, tax_id="12345678")
    prod = Product(id=str(uuid.uuid4()), product_no="HR-PROD2", name="家規產品二",
                   standard_cost=10, selling_price=50)
    db.add_all([cust, prod])
    await db.commit()
    so = await create_sales_order(db, {
        "customer_id": cust.id,
        "items": [{"product_id": prod.id, "ordered_qty": 10, "unit_price": 50}],
    }, {"employee_id": "e-hr"})
    assert so.so_no.startswith("SO-")


@pytest.mark.asyncio
async def test_inspection_and_stock_count_pdf(db):
    """Turnkey 表單 #7/#8：檢驗報告與盤點表 PDF 可產生。"""
    from app.services.print_service import generate_inspection_pdf, generate_stock_count_pdf
    from app.models.quality import InspectionOrder, InspectionResult
    from app.models.stock_count import StockCount
    from app.models.inventory import Part

    part = Part(id=str(uuid.uuid4()), part_no="PDF-PART-1", name="PDF 料件",
                category="component", unit_cost=5)
    db.add(part)
    await db.commit()
    insp = InspectionOrder(id=str(uuid.uuid4()), inspection_no="INS-PDF-001",
                           part_id=part.id, inspected_qty=10, accepted_qty=9,
                           rejected_qty=1, status="completed")
    db.add(insp)
    db.add(InspectionResult(id=str(uuid.uuid4()), inspection_order_id=insp.id,
                            characteristic="外徑", specification="10±0.1",
                            measured_value="9.95", result="pass"))
    sc = StockCount(id=str(uuid.uuid4()), count_no="SC-PDF-001", scope="partial",
                    status="counting")
    db.add(sc)
    await db.commit()

    pdf1 = await generate_inspection_pdf(db, insp.id)
    assert pdf1[:4] == b"%PDF"
    pdf2 = await generate_stock_count_pdf(db, sc.id)
    assert pdf2[:4] == b"%PDF"
