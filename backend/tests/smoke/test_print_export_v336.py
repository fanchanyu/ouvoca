"""v3.36 PDF 列印 + CSV/Excel 匯出 + setup_status + seed_demo

電腦小白 Day 7：
  「印 QUO-001 PDF」「客戶清單 Excel 給會計小姐」
  「erpilot 設定到那？」「載入示範資料」
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


V336_TOOLS = [
    "print_quotation_pdf",
    "print_purchase_order_pdf",
    "print_sales_order_pdf",
    "print_delivery_note_pdf",
    "export_customers_to_excel",
    "export_parts_to_excel",
    "export_inventory_to_excel",
    "export_suppliers_to_excel",
    "export_sales_orders_to_excel",
    "export_purchase_orders_to_excel",
    "setup_status",
    "seed_demo_data_with_confirm",
]


def test_v336_tools_registered():
    for n in V336_TOOLS:
        assert get_tool(n) is not None, f"{n} 未註冊"


def test_seed_demo_is_hard_write():
    meta = get_tool("seed_demo_data_with_confirm")
    assert meta.risk_tier == RiskTier.HARD_WRITE


def test_print_tools_are_read():
    for n in ["print_quotation_pdf", "print_purchase_order_pdf",
              "print_sales_order_pdf", "print_delivery_note_pdf"]:
        assert get_tool(n).risk_tier == RiskTier.READ


def test_export_tools_are_read():
    for n in V336_TOOLS:
        if n.startswith("export_"):
            assert get_tool(n).risk_tier == RiskTier.READ


# ════════════════════════════════════════════════════════════════════
# setup_status
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_setup_status_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.print_export_tools import _setup_status
    async with AsyncSessionLocal() as db:
        result = await _setup_status(db, None)
    assert "summary" in result
    assert "raw" in result
    # 至少包含計數 key
    assert "counts" in result["raw"]
    assert "day_status" in result["raw"]


# ════════════════════════════════════════════════════════════════════
# Export tools: 各個輸出 bytes（非 None / 至少有 header）
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_export_customers_csv(seeded_client):
    from app.database import AsyncSessionLocal
    from app.services.export_service import export_customers
    async with AsyncSessionLocal() as db:
        data = await export_customers(db, fmt="csv")
    assert isinstance(data, bytes)
    assert len(data) > 0
    # CSV with BOM
    assert data.startswith(b"\xef\xbb\xbf")
    # 應包含中文表頭
    assert "客戶編號".encode("utf-8") in data


@pytest.mark.asyncio
async def test_export_customers_xlsx(seeded_client):
    from app.database import AsyncSessionLocal
    from app.services.export_service import export_customers
    async with AsyncSessionLocal() as db:
        data = await export_customers(db, fmt="xlsx")
    assert isinstance(data, bytes)
    # xlsx 是 zip — 4 bytes magic = "PK\x03\x04"
    assert data[:4] == b"PK\x03\x04"


@pytest.mark.asyncio
async def test_export_parts_csv(seeded_client):
    from app.database import AsyncSessionLocal
    from app.services.export_service import export_parts
    async with AsyncSessionLocal() as db:
        data = await export_parts(db, fmt="csv")
    assert data.startswith(b"\xef\xbb\xbf")
    assert "料號".encode("utf-8") in data


@pytest.mark.asyncio
async def test_export_inventory_xlsx(seeded_client):
    from app.database import AsyncSessionLocal
    from app.services.export_service import export_inventory
    async with AsyncSessionLocal() as db:
        data = await export_inventory(db, fmt="xlsx")
    assert data[:4] == b"PK\x03\x04"


@pytest.mark.asyncio
async def test_export_suppliers_csv(seeded_client):
    from app.database import AsyncSessionLocal
    from app.services.export_service import export_suppliers
    async with AsyncSessionLocal() as db:
        data = await export_suppliers(db, fmt="csv")
    assert data.startswith(b"\xef\xbb\xbf")


@pytest.mark.asyncio
async def test_export_sales_orders_csv(seeded_client):
    from app.database import AsyncSessionLocal
    from app.services.export_service import export_sales_orders
    async with AsyncSessionLocal() as db:
        data = await export_sales_orders(db, fmt="csv")
    assert data.startswith(b"\xef\xbb\xbf")


@pytest.mark.asyncio
async def test_export_purchase_orders_xlsx(seeded_client):
    from app.database import AsyncSessionLocal
    from app.services.export_service import export_purchase_orders
    async with AsyncSessionLocal() as db:
        data = await export_purchase_orders(db, fmt="xlsx")
    assert data[:4] == b"PK\x03\x04"


# ════════════════════════════════════════════════════════════════════
# LLM tool 層：找不到單據時回 error
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_print_quotation_missing(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.print_export_tools import _print_quotation_pdf
    async with AsyncSessionLocal() as db:
        result = await _print_quotation_pdf(db, None, quote_no="NOSUCH-XYZ")
    assert "error" in result


@pytest.mark.asyncio
async def test_print_po_missing(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.print_export_tools import _print_purchase_order_pdf
    async with AsyncSessionLocal() as db:
        result = await _print_purchase_order_pdf(db, None, po_no="NOSUCH-PO")
    assert "error" in result


@pytest.mark.asyncio
async def test_print_so_missing(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.print_export_tools import _print_sales_order_pdf
    async with AsyncSessionLocal() as db:
        result = await _print_sales_order_pdf(db, None, so_no="NOSUCH-SO")
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# End-to-end: 建客戶 + SO → 印 PDF
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_print_sales_order_pdf_end_to_end(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder
    from app.agents.domains.print_export_tools import _print_sales_order_pdf

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"CC-{s}", name=f"Print Test {s}")
        db.add(cu)
        await db.flush()
        so = SalesOrder(
            id=str(uuid.uuid4()),
            so_no=f"SO-PR-{s}",
            customer_id=cu.id,
            status="draft",
            total_amount=12345,
        )
        db.add(so)
        await db.commit()

        result = await _print_sales_order_pdf(db, None, so_no=f"SO-PR-{s}")

    assert "summary" in result
    assert result["raw"]["so_no"] == f"SO-PR-{s}"
    # PDF magic header: %PDF
    import base64 as b64
    pdf_bytes = b64.b64decode(result["raw"]["pdf_base64"])
    assert pdf_bytes[:4] == b"%PDF"


# ════════════════════════════════════════════════════════════════════
# seed_demo_data 行為：第一次成功，第二次 skipped
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_seed_demo_skipped_when_data_exists(seeded_client):
    """seeded_client 已預載資料，所以執行 demo seed 應該 skip。"""
    from app.database import AsyncSessionLocal
    from app.agents.domains.print_export_tools import _seed_demo_data_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _seed_demo_data_with_confirm(db, None)
    # 已有資料 → skipped=True 並回 summary（不是 confirm_card）
    assert "summary" in result
    assert result["raw"]["skipped"] is True
