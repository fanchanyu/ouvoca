"""法規 / 月度報表 API endpoints（v3.10 Track C）。

  GET /api/reports/tax-401.html?year=2026&period_no=3
      → HTML（browser ctrl+P 存 PDF）
  GET /api/reports/ar-aging.xlsx?overdue_only=true
      → Excel
  GET /api/reports/inventory-monthly.xlsx
      → Excel
"""
from __future__ import annotations

from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import UserContext, require_permission
from app.services.reports import (
    render_ar_aging_xlsx, render_form_401_html, render_inventory_monthly_xlsx,
)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


# ─── 401 申報書 HTML ───────────────────────────────────────

@router.get("/tax-401.html", response_class=HTMLResponse)
async def report_tax_401_html(
    year: int = Query(..., ge=2020, le=2050),
    period_no: int = Query(..., ge=1, le=6),
    company_name: str = Query("", description="公司名稱（顯示在 header）"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.tax_report")),
):
    """401 營業稅申報書 HTML（browser print 存 PDF）。"""
    # Reuse 既有 tax_tw API 的計算邏輯
    from app.api.tax_tw import form_401
    form = await form_401(year=year, period_no=period_no, db=db, user=user)
    form_dict = form.model_dump(mode="json") if hasattr(form, "model_dump") else dict(form)
    html = render_form_401_html(form_dict, company_name=company_name)
    return HTMLResponse(html)


# ─── 應收帳齡 Excel ────────────────────────────────────────

@router.get("/ar-aging.xlsx")
async def report_ar_aging_xlsx(
    overdue_only: bool = Query(False),
    limit: int = Query(500, le=10000),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.ar.list")),
):
    """應收帳齡 Excel。"""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.accounting import AccountsReceivable
    from app.models.crm_sales import Customer

    q = (
        select(AccountsReceivable, Customer)
        .join(Customer, AccountsReceivable.customer_id == Customer.id, isouter=True)
        .order_by(AccountsReceivable.due_date)
        .limit(limit)
    )
    if overdue_only:
        q = q.where(AccountsReceivable.due_date < datetime.now(UTC).replace(tzinfo=None))
        q = q.where(AccountsReceivable.status != "paid")

    rows_orm = (await db.execute(q)).all()
    rows = [
        {
            "invoice_no": ar.invoice_no,
            "customer_name": cust.name if cust else "",
            "amount": ar.amount,
            "paid_amount": ar.paid_amount,
            "due_date": str(ar.due_date),
            "aging_days": ar.aging_days,
            "status": ar.status,
        }
        for ar, cust in rows_orm
    ]
    generated = datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="minutes")
    xlsx_bytes = render_ar_aging_xlsx(rows, generated_at=generated)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="ar_aging_{generated.replace(":", "")}.xlsx"',
        },
    )


# ─── 庫存月報 Excel ────────────────────────────────────────

@router.get("/inventory-monthly.xlsx")
async def report_inventory_monthly_xlsx(
    period_label: str = Query("", description="期別文字（如 2026-05）"),
    only_low: bool = Query(False, description="只列低於安全庫存的品項"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.part.list")),
):
    """庫存月報 Excel。低於安全庫存自動黃底高亮。"""
    from sqlalchemy import select
    from app.models.inventory import Inventory, Part

    q = (
        select(Inventory, Part)
        .join(Part, Inventory.part_id == Part.id)
        .order_by(Part.part_no)
    )
    if only_low:
        q = q.where(Inventory.qty_available < Part.safety_stock)
        q = q.where(Part.safety_stock > 0)

    rows_orm = (await db.execute(q)).all()
    rows = [
        {
            "part_no": p.part_no, "name": p.name,
            "category": p.category, "unit": p.unit,
            "qty_on_hand": inv.qty_on_hand,
            "qty_available": inv.qty_available,
            "safety_stock": p.safety_stock,
            "unit_cost": p.unit_cost,
            "value": (inv.qty_on_hand or 0) * (p.unit_cost or 0),
        }
        for inv, p in rows_orm
    ]
    label = period_label or datetime.now(UTC).strftime("%Y-%m")
    xlsx_bytes = render_inventory_monthly_xlsx(rows, period_label=label)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="inventory_{label}.xlsx"',
        },
    )
