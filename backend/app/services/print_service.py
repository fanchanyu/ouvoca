"""PDF 列印服務 (v3.36) — Quotation / PO / SO / Invoice / Delivery Note

用 reportlab 純 Python 產生 A4 PDF。中文字型 fallback 鏈：
  系統內 NotoSansTC → Microsoft JhengHei → fallback 預設

設計原則：
  • 一個函式產一張 PDF（接 entity_id，回 bytes）
  • 不寫檔，直接回 bytes → caller 走 FastAPI Response 下載
  • 標準台頭 + 公司資訊（從 settings / FactoryConfig 動態）
  • 簽章區（買方/賣方/業務員）

電腦小白 demo：
  Chat: 「印 QUO-001」→ LLM tool → 此服務 → 回 base64 → 前端下載
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


# ════════════════════════════════════════════════════════════════════
# 中文字型 fallback
# ════════════════════════════════════════════════════════════════════

_FONT_REGISTERED = False
_FONT_NAME = "Helvetica"  # fallback


def _try_register_chinese_font() -> str:
    """嘗試註冊中文字型；找不到回 Helvetica fallback。"""
    global _FONT_REGISTERED, _FONT_NAME
    if _FONT_REGISTERED:
        return _FONT_NAME

    candidates = [
        # Windows
        ("MSJH", r"C:\Windows\Fonts\msjh.ttc"),
        ("MSJH", r"C:\Windows\Fonts\msjh.ttf"),
        ("MSYH", r"C:\Windows\Fonts\msyh.ttc"),
        # macOS
        ("PingFang", "/System/Library/Fonts/PingFang.ttc"),
        # Linux — Debian/Ubuntu fonts-noto-cjk 套件實際路徑（v3.37 修字型亂碼）
        ("NotoSansCJK", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        ("NotoSerifCJK", "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
        ("NotoSansSC", "/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf"),
        ("NotoSansTC", "/usr/share/fonts/opentype/noto/NotoSansTC-Regular.otf"),
        # Fallback truetype paths
        ("NotoSans", "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        ("WQY", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        ("WQYZenHei", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ]
    for name, path in candidates:
        try:
            import os
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                _FONT_NAME = name
                _FONT_REGISTERED = True
                return _FONT_NAME
        except Exception:
            continue

    _FONT_REGISTERED = True
    return _FONT_NAME  # Helvetica fallback (英文 + 部分符號)


# ════════════════════════════════════════════════════════════════════
# Common helpers
# ════════════════════════════════════════════════════════════════════

def _styles():
    font = _try_register_chinese_font()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"],
                                fontName=font, fontSize=20,
                                alignment=TA_CENTER, spaceAfter=10),
        "heading": ParagraphStyle("heading", parent=base["Heading2"],
                                  fontName=font, fontSize=12,
                                  spaceAfter=6),
        "body": ParagraphStyle("body", parent=base["Normal"],
                               fontName=font, fontSize=10,
                               leading=14),
        "small": ParagraphStyle("small", parent=base["Normal"],
                                fontName=font, fontSize=9,
                                textColor=colors.grey),
        "right": ParagraphStyle("right", parent=base["Normal"],
                                fontName=font, fontSize=10,
                                alignment=TA_RIGHT),
    }


def _company_header(s, company_name: str = "Ouvoca 範例公司",
                    tax_id: str = "", address: str = "", phone: str = "",
                    logo_b64: str = "") -> list:
    """頂部公司資訊區（v3.37 統編/地址/電話、v3.39 LOGO）。"""
    out: list = []
    # v3.39 K1: LOGO（若有）→ 印頂部，限高 1.5cm
    if logo_b64:
        try:
            import base64 as _b64
            from reportlab.platypus import Image
            img_bytes = _b64.b64decode(logo_b64)
            img = Image(io.BytesIO(img_bytes), width=4 * cm, height=1.5 * cm, kind="bound")
            img.hAlign = "LEFT"
            out.append(img)
            out.append(Spacer(1, 0.2 * cm))
        except Exception:
            # LOGO 壞掉 silent fallback — 不要 fail 整張 PDF
            pass
    out.append(Paragraph(f"<b>{company_name}</b>", s["title"]))
    sub_parts = []
    if tax_id:
        sub_parts.append(f"統編：{tax_id}")
    if phone:
        sub_parts.append(f"電話：{phone}")
    if address:
        sub_parts.append(address[:60])
    if sub_parts:
        out.append(Paragraph(" · ".join(sub_parts), s["small"]))
    out.append(Paragraph("Powered by Ouvoca", s["small"]))
    out.append(Spacer(1, 0.4 * cm))
    return out


async def _resolve_company(db: AsyncSession) -> dict:
    """從 Tenant.settings 撈當前公司資訊；找不到回 fallback。

    Tenant.settings JSON 預期欄位：name / tax_id / address / phone。
    若 settings 無 name 則 fallback 用 Tenant.name 本身。
    """
    from app.models.permission import Tenant
    t = (await db.execute(
        select(Tenant).where(Tenant.code == "HQ")
    )).scalar_one_or_none()
    if t is None:
        return {"name": "Ouvoca 範例公司", "tax_id": "", "address": "", "phone": ""}
    settings = t.settings or {}
    return {
        "name": settings.get("name") or t.name or "Ouvoca 範例公司",
        "tax_id": settings.get("tax_id", ""),
        "address": settings.get("address", ""),
        "phone": settings.get("phone", ""),
        "logo_b64": settings.get("logo_b64", ""),  # v3.39 K1
    }


def _signature_block(s) -> Table:
    """底部簽章區（買方 / 賣方 / 業務）。"""
    data = [
        [Paragraph("買方簽章", s["body"]),
         Paragraph("賣方簽章", s["body"]),
         Paragraph("業務員簽章", s["body"])],
        ["", "", ""],
        ["", "", ""],
    ]
    t = Table(data, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm], rowHeights=[0.6 * cm, 1.5 * cm, 0.3 * cm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LINEABOVE", (0, 2), (-1, 2), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, 0), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), _try_register_chinese_font()),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
    ]))
    return t


# ════════════════════════════════════════════════════════════════════
# Quotation PDF
# ════════════════════════════════════════════════════════════════════

async def generate_quotation_pdf(
    db: AsyncSession, quote_id: str, company_name: Optional[str] = None,
) -> bytes:
    """產生報價單 PDF（A4），回 bytes。

    company_name 留空時，自動從 Tenant.settings 撈（v3.37）。
    """
    from app.models.quotation import Quotation
    from app.models.crm_sales import Customer

    quote = (await db.execute(
        select(Quotation).options(selectinload(Quotation.items))
        .where(Quotation.id == quote_id)
    )).scalar_one_or_none()
    if quote is None:
        raise ValueError(f"找不到報價單 {quote_id}")

    customer = (await db.execute(
        select(Customer).where(Customer.id == quote.customer_id)
    )).scalar_one_or_none() if quote.customer_id else None

    company = await _resolve_company(db)
    if company_name:
        company["name"] = company_name

    s = _styles()
    font = _try_register_chinese_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm,
                             title=f"報價單 {quote.quote_no}")

    story = list(_company_header(s, company["name"], company["tax_id"],
                                  company["address"], company["phone"],
                                  company.get("logo_b64", "")))

    # 大標題
    story.append(Paragraph(f"<b>報 價 單</b>", s["title"]))
    story.append(Paragraph(f"Quotation No: {quote.quote_no}", s["small"]))
    story.append(Spacer(1, 0.3 * cm))

    # 客戶 + 日期 區塊
    cu_name = f"{customer.code} - {customer.name}" if customer else "(未指定客戶)"
    contact = customer.contact_person if customer else ""
    addr = (customer.address or "")[:50] if customer else ""
    info_data = [
        ["客戶 / Customer:", cu_name],
        ["聯絡人 / Contact:", contact],
        ["地址 / Address:", addr],
        ["報價日 / Date:", str(quote.quote_date.date()) if quote.quote_date else ""],
        ["有效期 / Valid Until:", str(quote.valid_until.date()) if quote.valid_until else "(未設)"],
    ]
    t = Table(info_data, colWidths=[3.5 * cm, 12.5 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # 品項表
    header = ["#", "品名 / Description", "數量", "單位", "單價", "折扣", "小計"]
    table_data = [header]
    for i, it in enumerate(quote.items, 1):
        table_data.append([
            str(i),
            it.description[:40] if it.description else "",
            f"{it.quantity:g}" if it.quantity else "0",
            it.unit or "",
            f"${it.unit_price:,.0f}" if it.unit_price else "$0",
            f"{(it.discount_rate or 0):.0%}" if it.discount_rate else "-",
            f"${it.line_total:,.0f}" if it.line_total else "$0",
        ])
    # 小計列
    table_data.append(["", "", "", "", "", "小計", f"${quote.subtotal or 0:,.0f}"])
    table_data.append(["", "", "", "", "", "稅額", f"${quote.tax_amount or 0:,.0f}"])
    table_data.append(["", "", "", "", "", "**總計**", f"**${quote.total_amount or 0:,.0f}**"])

    items_table = Table(
        table_data,
        colWidths=[0.8 * cm, 6 * cm, 1.8 * cm, 1.2 * cm, 2 * cm, 1.5 * cm, 2.7 * cm],
    )
    items_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -4), 0.4, colors.grey),
        ("BACKGROUND", (-2, -3), (-1, -1), colors.HexColor("#f3f4f6")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (-2, -1), (-1, -1), 11),  # 總計加大
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.5 * cm))

    # 備註
    if quote.notes:
        story.append(Paragraph(f"<b>備註 / Notes:</b>", s["heading"]))
        story.append(Paragraph(quote.notes, s["body"]))
        story.append(Spacer(1, 0.3 * cm))

    # 條款（小字）
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "本報價單為要約之邀請，最終契約以雙方書面簽章為準。"
        "報價金額除特別註明外含稅。逾有效期之報價恕不適用，需重新報價。",
        s["small"]
    ))
    story.append(Spacer(1, 1 * cm))

    # 簽章區
    story.append(_signature_block(s))

    doc.build(story)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════
# Purchase Order PDF
# ════════════════════════════════════════════════════════════════════

async def generate_po_pdf(
    db: AsyncSession, po_id: str, company_name: Optional[str] = None,
) -> bytes:
    from app.models.purchase import PurchaseOrder, Supplier

    po = (await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
    )).scalar_one_or_none()
    if po is None:
        raise ValueError(f"找不到 PO {po_id}")

    supplier = (await db.execute(
        select(Supplier).where(Supplier.id == po.supplier_id)
    )).scalar_one_or_none() if po.supplier_id else None

    company = await _resolve_company(db)
    if company_name:
        company["name"] = company_name

    s = _styles()
    font = _try_register_chinese_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm,
                             title=f"採購單 {po.po_no}")
    story = list(_company_header(s, company["name"], company["tax_id"],
                                  company["address"], company["phone"],
                                  company.get("logo_b64", "")))
    story.append(Paragraph(f"<b>採 購 單 / Purchase Order</b>", s["title"]))
    story.append(Paragraph(f"PO No: {po.po_no}", s["small"]))
    story.append(Spacer(1, 0.3 * cm))

    sup_name = f"{supplier.code} - {supplier.name}" if supplier else "(未指定供應商)"
    info_data = [
        ["供應商 / Supplier:", sup_name],
        ["訂單日 / Date:", str(po.order_date.date()) if po.order_date else ""],
        ["預計交期 / ETA:", str(po.expected_delivery_date.date()) if po.expected_delivery_date else "(未設)"],
        ["狀態 / Status:", po.status or ""],
    ]
    t = Table(info_data, colWidths=[3.5 * cm, 12.5 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # 品項表
    header = ["#", "料件 / Part", "數量", "單價", "小計"]
    table_data = [header]
    for i, it in enumerate(po.items, 1):
        table_data.append([
            str(i),
            (it.part_id[:8] + "...") if it.part_id else "",
            f"{it.ordered_qty:g}" if it.ordered_qty else "0",
            f"${it.unit_price or 0:,.0f}",
            f"${(it.ordered_qty or 0) * (it.unit_price or 0):,.0f}",
        ])
    table_data.append(["", "", "", "**總計**", f"**${po.total_amount or 0:,.0f}**"])

    items_table = Table(
        table_data,
        colWidths=[0.8 * cm, 8.5 * cm, 2 * cm, 2.2 * cm, 2.7 * cm],
    )
    items_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f59e0b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -2), 0.4, colors.grey),
        ("BACKGROUND", (-2, -1), (-1, -1), colors.HexColor("#fef3c7")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (-2, -1), (-1, -1), 11),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.5 * cm))

    if po.remark:
        story.append(Paragraph(f"<b>備註:</b> {po.remark}", s["body"]))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Spacer(1, 1 * cm))
    story.append(_signature_block(s))

    doc.build(story)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════
# Sales Order / Delivery Note PDF
# ════════════════════════════════════════════════════════════════════

async def generate_so_pdf(
    db: AsyncSession, so_id: str, doc_type: str = "sales_order",
    company_name: Optional[str] = None,
) -> bytes:
    """產生銷售單或出貨單 PDF。doc_type = sales_order | delivery_note."""
    from app.models.crm_sales import SalesOrder, Customer

    so = (await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items))
        .where(SalesOrder.id == so_id)
    )).scalar_one_or_none()
    if so is None:
        raise ValueError(f"找不到 SO {so_id}")

    customer = (await db.execute(
        select(Customer).where(Customer.id == so.customer_id)
    )).scalar_one_or_none() if so.customer_id else None

    company = await _resolve_company(db)
    if company_name:
        company["name"] = company_name

    s = _styles()
    font = _try_register_chinese_font()
    buf = io.BytesIO()
    title_zh = "銷售訂單" if doc_type == "sales_order" else "出貨單"
    title_en = "Sales Order" if doc_type == "sales_order" else "Delivery Note"
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm,
                             title=f"{title_zh} {so.so_no}")

    story = list(_company_header(s, company["name"], company["tax_id"],
                                  company["address"], company["phone"],
                                  company.get("logo_b64", "")))
    story.append(Paragraph(f"<b>{title_zh} / {title_en}</b>", s["title"]))
    story.append(Paragraph(f"SO No: {so.so_no}", s["small"]))
    story.append(Spacer(1, 0.3 * cm))

    cu_name = f"{customer.code} - {customer.name}" if customer else "(未指定客戶)"
    addr = (customer.address or "")[:50] if customer else ""
    info_data = [
        ["客戶 / Customer:", cu_name],
        ["地址 / Address:", addr],
        ["訂單日 / Date:", str(so.order_date.date()) if so.order_date else ""],
        ["狀態 / Status:", so.status or ""],
    ]
    t = Table(info_data, colWidths=[3.5 * cm, 12.5 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    header = ["#", "產品 / Product", "數量", "單價", "小計"]
    table_data = [header]
    for i, it in enumerate(so.items, 1):
        table_data.append([
            str(i),
            (it.product_id[:8] + "...") if it.product_id else "",
            f"{it.ordered_qty:g}" if it.ordered_qty else "0",
            f"${it.unit_price or 0:,.0f}",
            f"${it.line_total or 0:,.0f}",
        ])
    table_data.append(["", "", "", "**總計**", f"**${so.total_amount or 0:,.0f}**"])

    items_table = Table(
        table_data,
        colWidths=[0.8 * cm, 8.5 * cm, 2 * cm, 2.2 * cm, 2.7 * cm],
    )
    items_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -2), 0.4, colors.grey),
        ("BACKGROUND", (-2, -1), (-1, -1), colors.HexColor("#d1fae5")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (-2, -1), (-1, -1), 11),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 1 * cm))

    story.append(_signature_block(s))

    doc.build(story)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════
# E-Invoice PDF (v3.50)
# ════════════════════════════════════════════════════════════════════

def generate_einvoice_pdf(invoice_data: dict) -> bytes:
    """產生電子發票 PDF（A4），回 bytes。

    invoice_data 預期欄位：
      invoice_no, invoice_date (optional), buyer_tax_id, buyer_name,
      seller_tax_id, seller_name,
      items: [{description, qty, unit_price, amount}],
      total (含稅小計, optional), tax (5%, optional), grand_total (optional),
      tracking_no (optional)

    若 total / tax / grand_total 缺，自動由 items 重算。
    無 DB 相依 — 完全在記憶體中產生（前端傳 snapshot 即可）。
    """
    s = _styles()
    font = _try_register_chinese_font()

    invoice_no = str(invoice_data.get("invoice_no") or "—")
    invoice_date = str(
        invoice_data.get("invoice_date")
        or datetime.now().strftime("%Y-%m-%d")
    )
    buyer_tax_id = str(invoice_data.get("buyer_tax_id") or "")
    buyer_name = str(invoice_data.get("buyer_name") or "個人 / 無")
    seller_tax_id = str(invoice_data.get("seller_tax_id") or "")
    seller_name = str(invoice_data.get("seller_name") or "示範公司")
    tracking_no = str(invoice_data.get("tracking_no") or "")

    items = invoice_data.get("items") or []

    # 重算總計（若呼叫端沒給）
    def _f(x, default=0.0):
        try:
            return float(x)
        except (TypeError, ValueError):
            return default

    computed_total = 0.0
    for it in items:
        amt = it.get("amount")
        if amt is None:
            amt = _f(it.get("qty")) * _f(it.get("unit_price"))
        computed_total += _f(amt)

    grand_total = _f(invoice_data.get("grand_total"), computed_total)
    if grand_total <= 0:
        grand_total = computed_total
    sales_amount = _f(invoice_data.get("total"), round(grand_total / 1.05))
    tax = _f(invoice_data.get("tax"), round(grand_total - sales_amount))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=f"電子發票 {invoice_no}",
    )

    story: list = []
    # 賣方 header（直接用 seller_name，不查 DB — 純記憶體運作）
    story.append(Paragraph(f"<b>{seller_name}</b>", s["title"]))
    sub_parts = []
    if seller_tax_id:
        sub_parts.append(f"統編：{seller_tax_id}")
    if sub_parts:
        story.append(Paragraph(" · ".join(sub_parts), s["small"]))
    story.append(Paragraph("Powered by Ouvoca", s["small"]))
    story.append(Spacer(1, 0.4 * cm))

    # 大標題
    story.append(Paragraph("<b>電 子 發 票 / e-Invoice</b>", s["title"]))
    story.append(Paragraph(f"Invoice No: {invoice_no}", s["small"]))
    story.append(Paragraph(f"Date: {invoice_date}", s["small"]))
    story.append(Spacer(1, 0.3 * cm))

    # 買賣方資訊
    info_data = [
        ["賣方 / Seller:", seller_name],
        ["賣方統編:", seller_tax_id or "—"],
        ["買方 / Buyer:", buyer_name],
        ["買方統編:", buyer_tax_id or "—（個人）"],
    ]
    if tracking_no:
        info_data.append(["追蹤碼 / Tracking:", tracking_no])
    t = Table(info_data, colWidths=[3.5 * cm, 12.5 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # 品項表（**完整明細，非摘要**）
    header = ["#", "品名 / Description", "數量", "單價", "小計（含稅）"]
    table_data = [header]
    for i, it in enumerate(items, 1):
        qty = _f(it.get("qty"))
        unit_price = _f(it.get("unit_price"))
        amt = it.get("amount")
        if amt is None:
            amt = qty * unit_price
        table_data.append([
            str(i),
            str(it.get("description") or "")[:50],
            f"{qty:g}",
            f"${unit_price:,.0f}",
            f"${_f(amt):,.0f}",
        ])

    # 三列總計
    table_data.append(["", "", "", "未稅 Sales", f"${sales_amount:,.0f}"])
    table_data.append(["", "", "", "稅額 Tax 5%", f"${tax:,.0f}"])
    table_data.append(["", "", "", "**總計 Total**", f"**${grand_total:,.0f}**"])

    items_table = Table(
        table_data,
        colWidths=[0.8 * cm, 8.5 * cm, 2 * cm, 2.5 * cm, 2.4 * cm],
    )
    items_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0ea5e9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -4), 0.4, colors.grey),
        ("BACKGROUND", (-2, -3), (-1, -1), colors.HexColor("#e0f2fe")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (-2, -1), (-1, -1), 11),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.5 * cm))

    # 8-char placeholder 條碼 / QR（之後可接真實 39 barcode lib）
    short_code = invoice_no.replace("-", "")[-8:].upper().ljust(8, "0")
    story.append(Paragraph(
        f"<b>條碼 / Barcode (placeholder):</b> [ {short_code} ]",
        s["body"]
    ))
    story.append(Paragraph(
        f"<b>QR Code (placeholder):</b> {invoice_no}|{invoice_date}|{int(grand_total)}",
        s["small"]
    ))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph(
        "本電子發票依財政部 MIG 規範開立。如有問題請洽國稅局或開立公司。",
        s["small"]
    ))
    story.append(Spacer(1, 1 * cm))
    story.append(_signature_block(s))

    doc.build(story)
    return buf.getvalue()
