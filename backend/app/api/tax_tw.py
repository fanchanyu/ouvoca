"""
台灣稅務報表 API — 401 / 403 / 405 + 電子發票管理。

設計：
- 401 (一般營業稅申報書)：每兩月一次，4/5/9/10 等月底前申報
- 403 (進銷項憑證明細)：明細
- 405 (零稅率銷售額)：外銷專用

所有 endpoint 走 RBAC，需要 `accounting.tax_report` 權限。
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional
from zoneinfo import ZoneInfo

# v3.54 P0：統一發票使用辦法要求發票日期時間為「台灣時間（UTC+8）」。
# 若以 UTC 戳記，台灣凌晨 00:00–08:00 開立的發票會被打上前一天日期，
# 跨月時甚至影響營業稅期別歸屬，直接違反法規。所有「代表台灣稅務日期/期別」
# 的欄位皆改用 TAIWAN_TZ；純系統時間戳（例：generated_at audit log）保留 UTC。
TAIWAN_TZ = ZoneInfo("Asia/Taipei")
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import require_permission, UserContext
from app.integrations.einvoice_tw import (
    EInvoice, InvoiceLineItem, validate_tax_id,
    validate_invoice_no, calc_tax, default_provider,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tax/tw", tags=["Taiwan Tax"])


# ─── Period helpers ─────────────────────────────────────────

def _bi_monthly_period(year: int, period_no: int) -> tuple[datetime, datetime]:
    """回傳兩個月期的 (start, end_inclusive)。
    period_no: 1=1-2月 / 2=3-4月 / 3=5-6月 / 4=7-8月 / 5=9-10月 / 6=11-12月
    """
    if not (1 <= period_no <= 6):
        raise ValueError(f"period_no 應 1-6，得 {period_no}")
    start_month = (period_no - 1) * 2 + 1
    end_month = start_month + 1
    start = datetime(year, start_month, 1)
    # End: end_month 的最後一天
    if end_month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(year, end_month + 1, 1) - timedelta(seconds=1)
    return start, end


# ─── 401 一般營業稅申報書 ──────────────────────────────────

class Form401Response(BaseModel):
    form: str = "401"
    period: str           # e.g. "2026-Q1" (1-2月)
    year: int
    period_no: int

    # 銷售額
    sales_taxable: float          # 應稅銷售額（5%）
    sales_zero_rate: float        # 零稅率銷售額
    sales_exempt: float           # 免稅銷售額
    sales_total: float

    # 銷項稅額
    output_tax: float

    # 進項稅額（可扣抵）
    input_tax_general: float
    input_tax_fixed_asset: float

    # 應納稅額
    tax_payable: float            # 銷項 - 進項，正數要繳

    generated_at: datetime


@router.get("/401", response_model=Form401Response)
async def form_401(
    year: int = Query(..., ge=2020, le=2050),
    period_no: int = Query(..., ge=1, le=6, description="1=1-2月, 2=3-4月..."),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.tax_report")),
):
    """產生 401 申報書資料（兩月期）。"""
    from app.models.crm_sales import SalesOrder
    from app.models.purchase import PurchaseOrder

    start, end = _bi_monthly_period(year, period_no)

    # 銷售額：已出貨 SO 累積
    sales_q = select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
        and_(
            SalesOrder.actual_delivery_date.between(start, end),
            SalesOrder.status.in_(("shipped", "delivered", "closed")),
        )
    )
    sales_total = float((await db.execute(sales_q)).scalar() or 0)

    # 簡化：100% 應稅（之後依 customer.country 切零稅率 / 免稅）
    sales_taxable = sales_total
    output_tax = round(sales_taxable * 0.05 / 1.05)  # 內含稅 vs 外加稅依公司政策

    # 進項：已核准 PO
    purch_q = select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).where(
        and_(
            PurchaseOrder.order_date.between(start, end),
            PurchaseOrder.status.in_(("approved", "received", "partial_received")),
        )
    )
    purchase_total = float((await db.execute(purch_q)).scalar() or 0)
    input_tax_general = round(purchase_total * 0.05 / 1.05)

    return Form401Response(
        period=f"{year}-P{period_no}",
        year=year,
        period_no=period_no,
        sales_taxable=sales_taxable,
        sales_zero_rate=0,
        sales_exempt=0,
        sales_total=sales_total,
        output_tax=output_tax,
        input_tax_general=input_tax_general,
        input_tax_fixed_asset=0,
        tax_payable=output_tax - input_tax_general,
        generated_at=datetime.now(UTC).replace(tzinfo=None),
    )


# ─── 403 進銷項明細 ────────────────────────────────────────

@router.get("/403")
async def form_403(
    year: int = Query(..., ge=2020, le=2050),
    period_no: int = Query(..., ge=1, le=6),
    direction: str = Query("sales", regex="^(sales|purchase)$"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.tax_report")),
):
    """進銷項明細表。direction=sales（銷項）or purchase（進項）。"""
    from app.models.crm_sales import SalesOrder, Customer
    from app.models.purchase import PurchaseOrder, Supplier
    start, end = _bi_monthly_period(year, period_no)

    if direction == "sales":
        q = (
            select(SalesOrder, Customer)
            .join(Customer, Customer.id == SalesOrder.customer_id)
            .where(and_(
                SalesOrder.actual_delivery_date.between(start, end),
                SalesOrder.status.in_(("shipped", "delivered", "closed")),
            ))
            .order_by(SalesOrder.actual_delivery_date)
        )
        rows = (await db.execute(q)).all()
        return {
            "form": "403",
            "direction": "sales",
            "period": f"{year}-P{period_no}",
            "items": [
                {
                    "date": so.actual_delivery_date.isoformat() if so.actual_delivery_date else None,
                    "doc_no": so.so_no,
                    "counterparty_id": getattr(cust, "tax_id", "") or "",
                    "counterparty_name": cust.name,
                    "amount_excl_tax": round(float(so.total_amount or 0) / 1.05),
                    "tax": round(float(so.total_amount or 0) * 0.05 / 1.05),
                    "amount_incl_tax": float(so.total_amount or 0),
                }
                for so, cust in rows
            ],
            "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
        }
    else:  # purchase
        q = (
            select(PurchaseOrder, Supplier)
            .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
            .where(and_(
                PurchaseOrder.order_date.between(start, end),
                PurchaseOrder.status.in_(("approved", "received", "partial_received")),
            ))
            .order_by(PurchaseOrder.order_date)
        )
        rows = (await db.execute(q)).all()
        return {
            "form": "403",
            "direction": "purchase",
            "period": f"{year}-P{period_no}",
            "items": [
                {
                    "date": po.order_date.isoformat() if po.order_date else None,
                    "doc_no": po.po_no,
                    "counterparty_id": getattr(sup, "tax_id", "") or "",
                    "counterparty_name": sup.name,
                    "amount_excl_tax": round(float(po.total_amount or 0) / 1.05),
                    "tax": round(float(po.total_amount or 0) * 0.05 / 1.05),
                    "amount_incl_tax": float(po.total_amount or 0),
                }
                for po, sup in rows
            ],
            "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
        }


# ─── 電子發票管理 ─────────────────────────────────────────

class EInvoiceCreateRequest(BaseModel):
    invoice_no: str
    seller_tax_id: str
    seller_name: str
    buyer_tax_id: str = ""
    buyer_name: str = ""
    items: list[dict] = []  # 每項 {description, qty, unit_price}
    so_id: Optional[str] = None  # v3.54: 對應之 SalesOrder（建立合規追溯鏈）


@router.post("/einvoice/issue")
async def issue_einvoice(
    req: EInvoiceCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.einvoice.issue")),
):
    """開立電子發票（送加值中心 / 財政部）。

    v3.54: 成功後落 DB（EInvoiceRecord）並反寫 SalesOrder.invoice_no，
    形成 SO -> Invoice 合規追溯鏈（統一發票使用辦法 5 年保存要求）。
    """
    items = [
        InvoiceLineItem(
            description=it["description"],
            qty=float(it["qty"]),
            unit_price=float(it["unit_price"]),
            amount=round(float(it["qty"]) * float(it["unit_price"])),
        )
        for it in req.items
    ]
    sales_amount = sum(it.amount for it in items) / 1.05
    tax, total = calc_tax(round(sales_amount))

    # v3.54 P0 fix：發票時間必須用台灣時區（統一發票使用辦法），不能用 UTC。
    _taipei_now = datetime.now(TAIWAN_TZ)
    inv = EInvoice(
        invoice_no=req.invoice_no,
        invoice_date=_taipei_now.strftime("%Y%m%d"),
        invoice_time=_taipei_now.strftime("%H:%M:%S"),
        seller_tax_id=req.seller_tax_id,
        seller_name=req.seller_name,
        buyer_tax_id=req.buyer_tax_id,
        buyer_name=req.buyer_name,
        sales_amount=round(sales_amount),
        tax_amount=tax,
        total_amount=total,
        line_items=items,
    )
    result = default_provider.submit(inv)
    if not result["success"]:
        raise HTTPException(400, detail={
            "code": "einvoice_invalid", "errors": result["errors"],
        })

    # v3.54: 持久化發票記錄 + 反寫 SO.invoice_no（合規追溯鏈）
    from app.models.tax_tw import EInvoiceRecord
    from app.models.crm_sales import SalesOrder

    linked_so = None
    if req.so_id:
        linked_so = (await db.execute(
            select(SalesOrder).where(SalesOrder.id == req.so_id)
        )).scalar_one_or_none()

    raw_user = getattr(user, "raw_user", None) or {}
    einvoice_rec = EInvoiceRecord(
        invoice_no=inv.invoice_no,
        invoice_date=inv.invoice_date,
        invoice_time=inv.invoice_time,
        seller_tax_id=inv.seller_tax_id,
        buyer_tax_id=inv.buyer_tax_id or None,
        buyer_name=inv.buyer_name or "",
        sales_amount=inv.sales_amount,
        tax_amount=inv.tax_amount,
        total_amount=inv.total_amount,
        so_id=linked_so.id if linked_so else None,
        status="issued",
        tracking_no=result.get("tracking_no"),
        mig_payload=result.get("mig_payload") or result,
        tenant_id=raw_user.get("tenant_id", "HQ"),
        created_by=raw_user.get("employee_id"),
    )
    db.add(einvoice_rec)

    # 反寫 SO.invoice_no（追溯鏈關鍵步驟）
    if linked_so:
        linked_so.invoice_no = inv.invoice_no

    await db.commit()

    # v3.50: 寫 audit log（不上 ORM 表，純 logger，方便日後查證 / 重印）
    log.info(
        "E-invoice issued: invoice_no=%s seller=%s buyer=%s amount=%.2f tracking_no=%s so_id=%s",
        req.invoice_no, req.seller_tax_id, req.buyer_tax_id or "(個人)",
        float(total), result.get("tracking_no", ""), req.so_id or "(none)",
    )
    return result


@router.post("/einvoice/cancel/{invoice_no}")
async def cancel_einvoice(
    invoice_no: str,
    reason: str,
    user: UserContext = Depends(require_permission("accounting.einvoice.cancel")),
):
    result = default_provider.cancel(invoice_no, reason)
    if not result["success"]:
        raise HTTPException(400, detail=result)
    return result


@router.get("/einvoice/list")
async def list_einvoices(
    start_date: Optional[str] = None,   # YYYYMMDD
    end_date: Optional[str] = None,     # YYYYMMDD
    buyer_tax_id: Optional[str] = None,
    status: Optional[str] = None,       # issued / cancelled / voided
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.einvoice.read")),
):
    """v3.54: 已開發票清單（合規必備：5 年保存 + 查詢）。

    支援以日期 / 買方統編 / 狀態過濾，預設依 invoice_date desc 排序。
    """
    from app.models.tax_tw import EInvoiceRecord

    q = select(EInvoiceRecord).order_by(
        EInvoiceRecord.invoice_date.desc(),
        EInvoiceRecord.invoice_no.desc(),
    )
    if start_date:
        q = q.where(EInvoiceRecord.invoice_date >= start_date)
    if end_date:
        q = q.where(EInvoiceRecord.invoice_date <= end_date)
    if buyer_tax_id:
        q = q.where(EInvoiceRecord.buyer_tax_id == buyer_tax_id)
    if status:
        q = q.where(EInvoiceRecord.status == status)

    all_rows = (await db.execute(q)).scalars().all()
    items = all_rows[offset:offset + limit]
    return {
        "total": len(all_rows),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "invoice_no": e.invoice_no,
                "invoice_date": e.invoice_date,
                "invoice_time": e.invoice_time,
                "buyer_tax_id": e.buyer_tax_id,
                "buyer_name": e.buyer_name,
                "sales_amount": e.sales_amount,
                "tax_amount": e.tax_amount,
                "total_amount": e.total_amount,
                "status": e.status,
                "tracking_no": e.tracking_no,
                "so_id": e.so_id,
                "journal_entry_id": e.journal_entry_id,
            }
            for e in items
        ],
    }


@router.get("/einvoice/{invoice_no}")
async def query_einvoice(
    invoice_no: str,
    user: UserContext = Depends(require_permission("accounting.einvoice.read")),
):
    result = default_provider.query(invoice_no)
    if not result["success"]:
        raise HTTPException(404, detail=result)
    return result


@router.get("/validate-tax-id/{tax_id}")
async def check_tax_id(tax_id: str, country: str = "TW"):
    """公開：驗證統編 / 商號註冊號（不需 auth）。

    v3.20：支援多國，預設 TW。傳 ?country=CN/US/JP/EU/GENERIC 使用該國規則。
    """
    from app.integrations.tax_id_validators import validate, list_supported
    result = validate(tax_id, country)
    return {
        "tax_id": tax_id,
        "country": result.country,
        "valid": result.valid,
        "message": result.message,
        "formatted": result.formatted,
        "supported_countries": list_supported() if not result.valid else None,
    }


@router.get("/validate-tax-id-countries")
async def list_validator_countries():
    """公開：列出當前支援的國家統編驗證。"""
    from app.integrations.tax_id_validators import list_supported
    return {"countries": list_supported()}
