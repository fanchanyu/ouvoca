"""台灣 401/405 營業稅申報表（M2-2）。

401 = 銷項（銷售方申報）：來源 EInvoiceRecord（status=issued，排除作廢）。
405 = 進項（進貨方申報）：來源 AccountsPayable（供應商發票）。
   - 有 sales_amount/tax_amount 欄位者直接取用
   - 舊資料只有 amount（含稅總額）→ 以 5% 拆算（sales = amount / 1.05）

期間格式：YYYYMM（每兩個月申報一次為常態，本工具支援任意月份）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import AccountsPayable
from app.models.tax_tw import EInvoiceRecord

_TAX_RATE = 0.05


def _split_tax(total: float) -> tuple[float, float]:
    """含稅總額 → (銷售額, 稅額)，5% 拆算。"""
    sales = round(total / (1 + _TAX_RATE), 2)
    return sales, round(total - sales, 2)


async def _sales_tax_401(db: AsyncSession, period: str) -> dict:
    """401 銷項：期間內已開立（未作廢）電子發票。"""
    q = (
        select(
            func.coalesce(func.sum(EInvoiceRecord.sales_amount), 0),
            func.coalesce(func.sum(EInvoiceRecord.tax_amount), 0),
            func.coalesce(func.sum(EInvoiceRecord.total_amount), 0),
            func.count(EInvoiceRecord.id),
        )
        .where(
            EInvoiceRecord.invoice_date.like(f"{period}%"),
            EInvoiceRecord.status == "issued",
        )
    )
    sales, tax, total, count = (await db.execute(q)).one()
    # 零稅率 / 免稅 / 外銷：目前只有一般應稅，提供欄位為 0 以符合 401 格式
    return {
        "period": period,
        "sales_general": round(float(sales), 2),
        "tax_general": round(float(tax), 2),
        "total_amount": round(float(total), 2),
        "zero_tax_sales": 0.0,
        "exempt_sales": 0.0,
        "export_sales": 0.0,
        "invoice_count": int(count),
    }


async def _purchase_tax_405(db: AsyncSession, period: str) -> dict:
    """405 進項：期間內供應商發票（AP）。"""
    from sqlalchemy import extract
    year, month = int(period[:4]), int(period[4:6])
    rows = (await db.execute(
        select(AccountsPayable).where(
            extract("year", AccountsPayable.invoice_date) == year,
            extract("month", AccountsPayable.invoice_date) == month,
        )
    )).scalars().all()
    sales_sum = 0.0
    tax_sum = 0.0
    total_sum = 0.0
    count = 0
    for ap in rows:
        total = float(ap.amount or 0)
        if getattr(ap, "tax_amount", None) is not None and getattr(ap, "sales_amount", None) is not None:
            sales, tax = float(ap.sales_amount), float(ap.tax_amount)
        else:
            sales, tax = _split_tax(total)
        sales_sum += sales
        tax_sum += tax
        total_sum += total
        count += 1
    return {
        "period": period,
        "purchase_general": round(sales_sum, 2),
        "tax_general": round(tax_sum, 2),
        "total_amount": round(total_sum, 2),
        "invoice_count": count,
    }


async def tax_report_401_405(db: AsyncSession, period: str) -> dict:
    """產出某期間（YYYYMM）的 401/405 申報表。"""
    sales = await _sales_tax_401(db, period)
    purchase = await _purchase_tax_405(db, period)
    net_tax = round(sales["tax_general"] - purchase["tax_general"], 2)
    return {
        "report": "401_405",
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "tax_rate": _TAX_RATE,
        "sales": sales,      # 401
        "purchase": purchase,  # 405
        "net_tax_payable": net_tax,
        "note": "401 來源為已開立電子發票；405 舊資料（無 tax 欄位）以 5% 由含稅額拆算。",
    }
