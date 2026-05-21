"""Smoke: 進銷存深化（Quotation / StockCount / Reorder / 修改 PO/SO 行）v3.32

電腦小白每天用的：
  業務報價 → 客戶接受 → 自動轉 SO
  月底盤點 → 倉管 key 實盤 → 主管覆核 → 自動調整庫存
  「該補哪些料？」「PO-001 改成 200 個」「SO-001 降到 NT$180」
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


# 10 新 tools
NEW_TOOLS = [
    # Quotation
    "create_quotation_with_confirm",
    "list_quotations",
    "convert_quotation_to_so_with_confirm",
    "update_quotation_status_with_confirm",
    # StockCount
    "create_stock_count_with_confirm",
    "record_counted_qty_with_confirm",
    "apply_stock_count_adjustments_with_confirm",
    # Reorder
    "reorder_suggestion_tool",
    # Update PO/SO
    "update_purchase_order_item_with_confirm",
    "update_sales_order_item_with_confirm",
]


def test_all_10_v332_tools_registered():
    for n in NEW_TOOLS:
        assert get_tool(n) is not None, f"Tool {n!r} 未註冊"


def test_quotation_and_stock_count_models_load():
    """v3.32 新增 model 必須能 import。"""
    from app.models import Quotation, QuotationItem, StockCount, StockCountItem
    assert Quotation.__tablename__ == "quotations"
    assert QuotationItem.__tablename__ == "quotation_items"
    assert StockCount.__tablename__ == "stock_counts"
    assert StockCountItem.__tablename__ == "stock_count_items"


def test_hard_write_have_permissions():
    """所有 hard-write tools 必有 required_permission。"""
    hard_writes = [t for t in NEW_TOOLS if "with_confirm" in t]
    for t in hard_writes:
        meta = get_tool(t)
        assert meta.risk_tier == RiskTier.HARD_WRITE
        assert meta.required_permission, f"{t} 缺 permission"


def test_read_tools_correct_tier():
    """list / suggestion 必須 READ。"""
    for t in ["list_quotations", "reorder_suggestion_tool"]:
        meta = get_tool(t)
        assert meta.risk_tier == RiskTier.READ


# ════════════════════════════════════════════════════════════════════
# Quotation tools
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_quotation_missing_customer(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_tools import _create_quotation_with_confirm

    async with AsyncSessionLocal() as db:
        result = await _create_quotation_with_confirm(
            db, {"employee_id": "test"},
            customer_keyword="NO_SUCH_CUSTOMER_XYZ",
            items=[{"description": "test", "quantity": 1, "unit_price": 100}],
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_create_quotation_produces_confirm_card(seeded_client):
    """有實體時應回 ConfirmCard。"""
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from app.agents.domains.inventory_sales_tools import _create_quotation_with_confirm

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        cu = Customer(
            id=str(uuid.uuid4()),
            code=f"CU-Q-{s}", name=f"Test Cust {s}",
        )
        db.add(cu)
        await db.commit()

        result = await _create_quotation_with_confirm(
            db, {"employee_id": "test"},
            customer_keyword=f"CU-Q-{s}",
            items=[
                {"description": "M6 螺絲", "quantity": 100, "unit_price": 5},
                {"description": "M6 螺帽", "quantity": 100, "unit_price": 3,
                 "discount_rate": 0.1},
            ],
            valid_days=14,
        )

    assert "card_id" in result or result.get("type") == "confirm_card"


@pytest.mark.asyncio
async def test_convert_quotation_missing(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_tools import _convert_quotation_to_so

    async with AsyncSessionLocal() as db:
        result = await _convert_quotation_to_so(
            db, {"employee_id": "test"}, quote_no="MISSING-QUO-001",
        )
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# StockCount tools
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_stock_count_produces_confirm_card(seeded_client):
    """建立盤點單 → ConfirmCard。"""
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_tools import _create_stock_count

    async with AsyncSessionLocal() as db:
        result = await _create_stock_count(
            db, {"employee_id": "test"},
            scope="full", notes="Q1 月底盤點",
        )
    assert "card_id" in result or result.get("type") == "confirm_card"


@pytest.mark.asyncio
async def test_record_counted_qty_missing_count(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_tools import _record_counted_qty

    async with AsyncSessionLocal() as db:
        result = await _record_counted_qty(
            db, {"employee_id": "test"},
            count_no="MISSING-SC-001", part_no="X", counted_qty=10,
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_apply_count_adjustments_missing(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_tools import _apply_stock_count_adjustments

    async with AsyncSessionLocal() as db:
        result = await _apply_stock_count_adjustments(
            db, {"employee_id": "test"}, count_no="MISSING-SC-002",
        )
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# Reorder suggestion
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_reorder_suggestion_runs(seeded_client):
    """採購建議 tool 不會 crash，至少回 summary。"""
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_tools import _reorder_suggestion

    async with AsyncSessionLocal() as db:
        result = await _reorder_suggestion(db, {"employee_id": "test"})
    assert "summary" in result
    assert "raw" in result


# ════════════════════════════════════════════════════════════════════
# End-to-end: Quotation service flow
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_quotation_service_create_and_convert(seeded_client):
    """完整流程：建報價 → 轉 SO。"""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder
    from app.models.product import Product
    from app.services.quotation import (
        create_quotation, get_quotation, convert_quotation_to_so,
    )

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        cu = Customer(
            id=str(uuid.uuid4()), code=f"CU-FLOW-{s}",
            name="Flow Test", credit_limit=50000,
        )
        prod = Product(
            id=str(uuid.uuid4()), product_no=f"PROD-FLOW-{s}",
            name="Flow Product", unit="pcs", selling_price=200,
        )
        db.add_all([cu, prod])
        await db.flush()

        quote_obj = await create_quotation(db, {
            "customer_id": cu.id,
            "items": [
                {"description": "Flow Product",
                 "product_id": prod.id,
                 "quantity": 50, "unit_price": 200},
            ],
            "notes": "test quote",
        })
        quote_id = quote_obj.id
        quote_no_check = quote_obj.quote_no
        quote_total = quote_obj.total_amount

    assert quote_no_check.startswith("QUO-")
    assert quote_total == 10000  # 50 × 200

    # Re-fetch with eager load to verify items
    from app.services.quotation import get_quotation as _gq
    async with AsyncSessionLocal() as db:
        quote = await _gq(db, quote_id)
    assert len(quote.items) == 1

    # Convert to SO
    async with AsyncSessionLocal() as db:
        so_obj = await convert_quotation_to_so(db, quote_id)
        so_no = so_obj.so_no
        so_customer_id = so_obj.customer_id
        so_id = so_obj.id

    assert so_no.startswith("SO-")
    assert so_customer_id == cu.id

    # Quote status should be converted
    async with AsyncSessionLocal() as db:
        updated_quote = await get_quotation(db, quote_id)
        assert updated_quote.status == "converted"
        assert updated_quote.converted_so_id == so_id


@pytest.mark.asyncio
async def test_stock_count_service_flow(seeded_client):
    """完整流程：建盤點 → 登錄實盤 → 套用調整。"""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.inventory import Part, Inventory
    from app.services.stock_count import (
        create_stock_count, record_counted_qty, apply_count_adjustments,
    )

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        # 建一個 part + inventory
        part = Part(
            id=str(uuid.uuid4()), part_no=f"SC-FLOW-{s}",
            name="SC Test", unit="pcs",
        )
        db.add(part)
        await db.flush()
        inv = Inventory(
            id=str(uuid.uuid4()), part_id=part.id,
            qty_available=100, qty_on_hand=100,
        )
        db.add(inv)
        await db.commit()

        # 1. 建盤點單
        sc = await create_stock_count(db, part_ids=[part.id], scope="partial")
        sc_id = sc.id

    # Re-fetch with eager load
    from app.services.stock_count import get_stock_count
    async with AsyncSessionLocal() as db:
        sc2 = await get_stock_count(db, sc_id)
        assert len(sc2.items) == 1
        assert sc2.items[0].book_qty == 100
        first_item_id = sc2.items[0].id

        # 2. 登錄實盤（少 5 個）
        await record_counted_qty(
            db, first_item_id, counted_qty=95,
            variance_reason="damaged",
        )

    # 3. 套用調整
    async with AsyncSessionLocal() as db:
        result = await apply_count_adjustments(db, sc_id)

    assert result["adjustments_applied"] == 1
    assert result["outbound_items"] == 1  # 變少 → outbound
