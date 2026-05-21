"""Smoke: 進銷存再深化 v3.33（12 LLM tools + 雙語法律聲明）

電腦小白每天用：
  「QUO-001 內容是？」「複製上次給長江的報價」「寄給客戶」「QUO-001 作廢」
  「SC-001 盤點進度？」「批次 keyin 實盤」「取消盤點」
  「智慧採購建議（含 lead time）」
  「PO-001 加 100 個 M8」「刪掉 M6 那行」「交期改 6/5」「SO-001 加 50 個 PROD-B」
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


NEW_TOOLS_V333 = [
    # Quotation 深化 (4)
    "query_quotation_detail",
    "clone_quotation_with_confirm",
    "send_quotation_email_with_confirm",
    "cancel_quotation_with_confirm",
    # StockCount 深化 (3)
    "query_stock_count_progress",
    "batch_record_counted_qty_with_confirm",
    "cancel_stock_count_with_confirm",
    # Reorder 深化 (1)
    "smart_reorder_with_lead_time_tool",
    # PO/SO 行操作 (4)
    "add_purchase_order_item_with_confirm",
    "remove_purchase_order_item_with_confirm",
    "update_purchase_order_delivery_with_confirm",
    "add_sales_order_item_with_confirm",
]


def test_all_12_v333_tools_registered():
    for n in NEW_TOOLS_V333:
        assert get_tool(n) is not None, f"Tool {n!r} 未註冊"


def test_v333_hard_writes_have_permission():
    for n in NEW_TOOLS_V333:
        if "with_confirm" in n:
            meta = get_tool(n)
            assert meta.risk_tier == RiskTier.HARD_WRITE
            assert meta.required_permission, f"{n} 缺 permission"


def test_v333_read_tools_correct_tier():
    for n in ["query_quotation_detail", "query_stock_count_progress",
              "smart_reorder_with_lead_time_tool"]:
        assert get_tool(n).risk_tier == RiskTier.READ


# ════════════════════════════════════════════════════════════════════
# Graceful errors
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_query_quotation_missing(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_deep_tools import _query_quotation_detail
    async with AsyncSessionLocal() as db:
        result = await _query_quotation_detail(
            db, {"employee_id": "test"}, quote_no="MISSING-QUO-X",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_clone_quotation_missing(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_deep_tools import _clone_quotation_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _clone_quotation_with_confirm(
            db, {"employee_id": "test"}, source_quote_no="MISSING-X",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_query_stock_count_progress_missing(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_deep_tools import _query_stock_count_progress
    async with AsyncSessionLocal() as db:
        result = await _query_stock_count_progress(
            db, {"employee_id": "test"}, count_no="MISSING-SC-X",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_batch_record_empty_counts(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_deep_tools import _batch_record_counted_qty
    async with AsyncSessionLocal() as db:
        result = await _batch_record_counted_qty(
            db, {"employee_id": "test"}, count_no="X", counts=[],
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_add_po_item_missing_po(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_deep_tools import _add_po_item
    async with AsyncSessionLocal() as db:
        result = await _add_po_item(
            db, {"employee_id": "test"},
            po_no="MISS-PO-X", part_no="M6", quantity=10, unit_price=5,
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_update_po_delivery_invalid_date(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.purchase import Supplier, PurchaseOrder
    from datetime import datetime, UTC
    from app.agents.domains.inventory_sales_deep_tools import _update_po_delivery

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        sup = Supplier(id=str(uuid.uuid4()), code=f"SUP-DT-{s}", name="x")
        db.add(sup)
        await db.flush()
        po = PurchaseOrder(
            id=str(uuid.uuid4()), po_no=f"PO-DT-{s}",
            supplier_id=sup.id, status="draft",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(po)
        await db.commit()
        result = await _update_po_delivery(
            db, {"employee_id": "test"},
            po_no=f"PO-DT-{s}", new_delivery_date="not-a-date",
        )
    assert "error" in result
    assert "格式" in result["error"]


@pytest.mark.asyncio
async def test_smart_reorder_runs(seeded_client):
    """智慧採購不會 crash。"""
    from app.database import AsyncSessionLocal
    from app.agents.domains.inventory_sales_deep_tools import _smart_reorder_with_lead_time
    async with AsyncSessionLocal() as db:
        result = await _smart_reorder_with_lead_time(
            db, {"employee_id": "test"}, forecast_days=30,
        )
    assert "summary" in result
    assert "raw" in result


# ════════════════════════════════════════════════════════════════════
# ConfirmCard for hard-writes
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_clone_quotation_produces_confirm_card(seeded_client):
    from datetime import datetime, UTC
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from app.models.quotation import Quotation, QuotationItem
    from app.agents.domains.inventory_sales_deep_tools import _clone_quotation_with_confirm

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"CC-{s}", name="Cust")
        db.add(cu)
        await db.flush()
        quote = Quotation(
            id=str(uuid.uuid4()), quote_no=f"QUO-SRC-{s}",
            customer_id=cu.id, status="sent", total_amount=1000,
            subtotal=1000,
            quote_date=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(quote)
        await db.flush()
        db.add(QuotationItem(
            id=str(uuid.uuid4()), quotation_id=quote.id,
            description="Test item", quantity=10, unit_price=100,
            line_total=1000,
        ))
        await db.commit()

        result = await _clone_quotation_with_confirm(
            db, {"employee_id": "test"},
            source_quote_no=f"QUO-SRC-{s}", new_valid_days=14,
        )

    assert "card_id" in result or result.get("type") == "confirm_card"


@pytest.mark.asyncio
async def test_query_stock_count_progress_full(seeded_client):
    """端到端：建盤點 → 查進度 → 應顯示 0% counted."""
    from app.database import AsyncSessionLocal
    from app.models.inventory import Part, Inventory
    from app.services.stock_count import create_stock_count
    from app.agents.domains.inventory_sales_deep_tools import _query_stock_count_progress

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        p = Part(id=str(uuid.uuid4()), part_no=f"P-PROG-{s}", name="X", unit="pcs")
        db.add(p)
        await db.flush()
        db.add(Inventory(id=str(uuid.uuid4()), part_id=p.id,
                         qty_available=50, qty_on_hand=50))
        await db.commit()

        sc = await create_stock_count(db, part_ids=[p.id], scope="partial")
        sc_no = sc.count_no

    async with AsyncSessionLocal() as db:
        result = await _query_stock_count_progress(
            db, {"employee_id": "test"}, count_no=sc_no,
        )
    assert "raw" in result
    assert result["raw"]["total"] == 1
    assert result["raw"]["counted"] == 0


@pytest.mark.asyncio
async def test_legal_notice_files_exist():
    """雙語法律聲明檔案必須存在。"""
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    base = os.path.abspath(os.path.join(base, ".."))
    zh = os.path.join(base, "docs", "INVENTORY_SALES_LEGAL_NOTICE_ZH.md")
    en = os.path.join(base, "docs", "INVENTORY_SALES_LEGAL_NOTICE_EN.md")
    assert os.path.exists(zh), f"ZH legal notice missing: {zh}"
    assert os.path.exists(en), f"EN legal notice missing: {en}"
    # 確認包含關鍵段落
    with open(zh, encoding="utf-8") as f:
        content_zh = f.read()
    assert "累積適用" in content_zh
    assert "TMEPL" in content_zh or "適用法律所允許之最大範圍" in content_zh
    with open(en, encoding="utf-8") as f:
        content_en = f.read()
    assert "cumulatively" in content_en
    assert "maximum extent permitted by applicable law" in content_en
