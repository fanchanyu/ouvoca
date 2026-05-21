"""PDF 列印 + CSV/Excel 匯出 API (v3.36)

電腦小白痛點：
  • 老闆要客戶清單 → 一個按鈕匯 Excel 給會計小姐
  • 出貨給客戶要單據 → 點下載 PDF 印
  • LLM 要回單據 → 拿 base64 給前端下載

設計：
  • GET /api/print/quotation/{quote_id}.pdf  → 報價單 PDF
  • GET /api/print/po/{po_id}.pdf            → 採購單 PDF
  • GET /api/print/so/{so_id}.pdf            → 銷售單 PDF
  • GET /api/print/delivery/{so_id}.pdf      → 出貨單 PDF
  • GET /api/export/customers.{csv|xlsx}     → 客戶清單
  • GET /api/export/parts.{csv|xlsx}         → 料件清單
  • GET /api/export/suppliers.{csv|xlsx}     → 供應商清單
  • GET /api/export/sales-orders.{csv|xlsx}  → 銷售訂單清單
  • GET /api/export/purchase-orders.{csv|xlsx} → 採購訂單清單
  • GET /api/export/inventory.{csv|xlsx}     → 庫存盤點
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import UserContext, require_permission
from app.services.print_service import (
    generate_quotation_pdf, generate_po_pdf, generate_so_pdf,
)
from app.services.export_service import (
    export_customers, export_parts, export_suppliers,
    export_sales_orders, export_purchase_orders, export_inventory,
)


# ════════════════════════════════════════════════════════════════════
# Print (PDF)
# ════════════════════════════════════════════════════════════════════

print_router = APIRouter(prefix="/api/print", tags=["Print"])


def _pdf_response(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@print_router.get("/quotation/{quote_id}.pdf")
async def print_quotation(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.read")),
):
    """報價單 PDF 下載。"""
    try:
        data = await generate_quotation_pdf(db, quote_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return _pdf_response(data, f"quotation-{quote_id[:8]}.pdf")


@print_router.get("/po/{po_id}.pdf")
async def print_po(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("purchase.order.read")),
):
    """採購單 PDF 下載。"""
    try:
        data = await generate_po_pdf(db, po_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return _pdf_response(data, f"po-{po_id[:8]}.pdf")


@print_router.get("/so/{so_id}.pdf")
async def print_so(
    so_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.read")),
):
    """銷售訂單 PDF 下載。"""
    try:
        data = await generate_so_pdf(db, so_id, doc_type="sales_order")
    except ValueError as e:
        raise HTTPException(404, str(e))
    return _pdf_response(data, f"so-{so_id[:8]}.pdf")


@print_router.get("/delivery/{so_id}.pdf")
async def print_delivery_note(
    so_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("sales.order.read")),
):
    """出貨單 PDF 下載（用 SO 衍生）。"""
    try:
        data = await generate_so_pdf(db, so_id, doc_type="delivery_note")
    except ValueError as e:
        raise HTTPException(404, str(e))
    return _pdf_response(data, f"delivery-{so_id[:8]}.pdf")


# ════════════════════════════════════════════════════════════════════
# Export (CSV / XLSX)
# ════════════════════════════════════════════════════════════════════

export_router = APIRouter(prefix="/api/export", tags=["Export"])

_EXPORTERS = {
    "customers":        (export_customers,       "crm.customer.read"),
    "parts":            (export_parts,           "inventory.part.read"),
    "suppliers":        (export_suppliers,       "purchase.supplier.read"),
    "sales-orders":     (export_sales_orders,    "sales.order.read"),
    "purchase-orders":  (export_purchase_orders, "purchase.order.read"),
    "inventory":        (export_inventory,       "inventory.part.read"),
}


def _attachment_response(data: bytes, filename: str, fmt: str) -> Response:
    media = "text/csv; charset=utf-8" if fmt == "csv" else (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_export_endpoint(entity: str, fmt: str):
    """產生一個 GET endpoint 給 (entity, fmt)。closure 抓住 entity/fmt。"""
    func, perm = _EXPORTERS[entity]

    async def endpoint(
        db: AsyncSession = Depends(get_db),
        user: UserContext = Depends(require_permission(perm)),
    ):
        data = await func(db, fmt=fmt)
        ts = datetime.now().strftime("%Y%m%d")
        return _attachment_response(data, f"{entity}-{ts}.{fmt}", fmt)

    return endpoint


# 註冊 6 entity × 2 fmt = 12 endpoints
for entity_name in _EXPORTERS:
    for file_fmt in ("csv", "xlsx"):
        export_router.add_api_route(
            f"/{entity_name}.{file_fmt}",
            _build_export_endpoint(entity_name, file_fmt),
            methods=["GET"],
            name=f"export_{entity_name}_{file_fmt}",
        )
