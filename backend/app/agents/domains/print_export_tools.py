"""列印 / 匯出 LLM tools (v3.36)

電腦小白第 7 天痛點：
  「我要把報價單印給客戶」「客戶清單給會計小姐」
  「設定到那裡了？」「載入示範資料」

設計：
  • 印單據 → 回 base64（前端組 data: URL 下載）or download_url（給前端用）
  • 匯出 → 同上
  • 設定狀態 → 報告各模組筆數、缺什麼

══════════════════════════════════════════════════════════════════
LEGAL（累積適用 v3.25.10 → v3.35 §6）
══════════════════════════════════════════════════════════════════
本模組之 PDF / CSV / Excel 輸出僅為作業參考。
正式對外（報價、合約、發票、出貨單）仍應由經授權之人員簽核後寄發。
於適用法律所允許之最大範圍內，erpilot 對因匯出資料外洩、
PDF 內容錯誤、匯出後第三方處理所衍生之爭議不承擔責任。
"""
from __future__ import annotations

import base64
from sqlalchemy import select, func

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.quotation import Quotation
from app.models.purchase import PurchaseOrder, Supplier
from app.models.crm_sales import SalesOrder, Customer
from app.models.inventory import Part, Inventory
from app.models.organization import Employee, User


# ════════════════════════════════════════════════════════════════════
# 輔助：把 keyword 解析成單號 id
# ════════════════════════════════════════════════════════════════════

async def _resolve_quote(db, keyword: str):
    q = (await db.execute(
        select(Quotation).where(
            (Quotation.quote_no == keyword) | (Quotation.quote_no.contains(keyword))
        )
    )).scalars().first()
    return q


async def _resolve_po(db, keyword: str):
    return (await db.execute(
        select(PurchaseOrder).where(
            (PurchaseOrder.po_no == keyword) | (PurchaseOrder.po_no.contains(keyword))
        )
    )).scalars().first()


async def _resolve_so(db, keyword: str):
    return (await db.execute(
        select(SalesOrder).where(
            (SalesOrder.so_no == keyword) | (SalesOrder.so_no.contains(keyword))
        )
    )).scalars().first()


# ════════════════════════════════════════════════════════════════════
# 1. print_quotation_pdf — 「印 QUO-001」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="print_quotation_pdf",
    domain="print",
    risk_tier=RiskTier.READ,
    description=(
        "把指定報價單產生 PDF。範例：「印報價單 QUO-001」「下載 QUO-2026-001 的 PDF」。"
        "回傳下載連結 + base64 內容（前端可直接觸發下載）。"
    ),
    slots=[Slot("quote_no", "string", required=True, description="報價單編號")],
    required_permission="sales.order.read",
)
async def _print_quotation_pdf(db, user, quote_no: str):
    quote = await _resolve_quote(db, quote_no)
    if quote is None:
        return {"error": f"找不到報價單「{quote_no}」"}

    from app.services.print_service import generate_quotation_pdf
    pdf_bytes = await generate_quotation_pdf(db, quote.id)
    return {
        "summary": (
            f"📄 報價單 PDF 已產生：**{quote.quote_no}**\n"
            f"💾 大小：{len(pdf_bytes) / 1024:.1f} KB\n"
            f"⬇️ 下載：[點此下載 PDF](/api/print/quotation/{quote.id}.pdf)"
        ),
        "raw": {
            "quote_no": quote.quote_no,
            "quote_id": quote.id,
            "download_url": f"/api/print/quotation/{quote.id}.pdf",
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "size_bytes": len(pdf_bytes),
        },
    }


# ════════════════════════════════════════════════════════════════════
# 2. print_purchase_order_pdf — 「印 PO-001」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="print_purchase_order_pdf",
    domain="print",
    risk_tier=RiskTier.READ,
    description=(
        "把指定採購單產生 PDF。範例：「印採購單 PO-2026-001」「PO-001 印出來」。"
    ),
    slots=[Slot("po_no", "string", required=True, description="採購單編號")],
    required_permission="purchase.order.read",
)
async def _print_purchase_order_pdf(db, user, po_no: str):
    po = await _resolve_po(db, po_no)
    if po is None:
        return {"error": f"找不到採購單「{po_no}」"}

    from app.services.print_service import generate_po_pdf
    pdf_bytes = await generate_po_pdf(db, po.id)
    return {
        "summary": (
            f"📄 採購單 PDF 已產生：**{po.po_no}**\n"
            f"💾 大小：{len(pdf_bytes) / 1024:.1f} KB\n"
            f"⬇️ 下載：[點此下載 PDF](/api/print/po/{po.id}.pdf)"
        ),
        "raw": {
            "po_no": po.po_no,
            "po_id": po.id,
            "download_url": f"/api/print/po/{po.id}.pdf",
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "size_bytes": len(pdf_bytes),
        },
    }


# ════════════════════════════════════════════════════════════════════
# 3. print_sales_order_pdf — 「印 SO-001」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="print_sales_order_pdf",
    domain="print",
    risk_tier=RiskTier.READ,
    description=(
        "把指定銷售訂單產生 PDF。範例：「印銷售單 SO-001」「印 SO-2026-001」。"
    ),
    slots=[Slot("so_no", "string", required=True, description="銷售單編號")],
    required_permission="sales.order.read",
)
async def _print_sales_order_pdf(db, user, so_no: str):
    so = await _resolve_so(db, so_no)
    if so is None:
        return {"error": f"找不到銷售單「{so_no}」"}

    from app.services.print_service import generate_so_pdf
    pdf_bytes = await generate_so_pdf(db, so.id, doc_type="sales_order")
    return {
        "summary": (
            f"📄 銷售單 PDF 已產生：**{so.so_no}**\n"
            f"💾 大小：{len(pdf_bytes) / 1024:.1f} KB\n"
            f"⬇️ 下載：[點此下載 PDF](/api/print/so/{so.id}.pdf)"
        ),
        "raw": {
            "so_no": so.so_no,
            "so_id": so.id,
            "download_url": f"/api/print/so/{so.id}.pdf",
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "size_bytes": len(pdf_bytes),
        },
    }


# ════════════════════════════════════════════════════════════════════
# 4. print_delivery_note_pdf — 「印出貨單 SO-001」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="print_delivery_note_pdf",
    domain="print",
    risk_tier=RiskTier.READ,
    description=(
        "把指定 SO 產生「出貨單」PDF（送貨單）。範例：「印出貨單 SO-001」「送貨單 SO-2026-001」。"
    ),
    slots=[Slot("so_no", "string", required=True, description="銷售單編號")],
    required_permission="sales.order.read",
)
async def _print_delivery_note_pdf(db, user, so_no: str):
    so = await _resolve_so(db, so_no)
    if so is None:
        return {"error": f"找不到銷售單「{so_no}」"}

    from app.services.print_service import generate_so_pdf
    pdf_bytes = await generate_so_pdf(db, so.id, doc_type="delivery_note")
    return {
        "summary": (
            f"📄 出貨單 PDF 已產生（SO {so.so_no}）\n"
            f"💾 大小：{len(pdf_bytes) / 1024:.1f} KB\n"
            f"⬇️ 下載：[點此下載 PDF](/api/print/delivery/{so.id}.pdf)"
        ),
        "raw": {
            "so_no": so.so_no,
            "so_id": so.id,
            "download_url": f"/api/print/delivery/{so.id}.pdf",
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "size_bytes": len(pdf_bytes),
        },
    }


# ════════════════════════════════════════════════════════════════════
# 5-10. export_*_to_excel — 通用匯出工具
# ════════════════════════════════════════════════════════════════════

async def _do_export(db, entity: str, fmt: str):
    """通用匯出 helper — entity → export_service function dispatch。"""
    from app.services import export_service
    func_map = {
        "customers":       export_service.export_customers,
        "parts":           export_service.export_parts,
        "suppliers":       export_service.export_suppliers,
        "sales-orders":    export_service.export_sales_orders,
        "purchase-orders": export_service.export_purchase_orders,
        "inventory":       export_service.export_inventory,
    }
    return await func_map[entity](db, fmt=fmt)


async def _export_response(db, entity: str, label: str, icon: str, fmt: str) -> dict:
    """6 個 export tools 共用回應格式 — 排除重複。"""
    if fmt not in ("csv", "xlsx"):
        fmt = "xlsx"
    data = await _do_export(db, entity, fmt)
    url = f"/api/export/{entity}.{fmt}"
    return {
        "summary": (
            f"{icon} {label}已匯出（{fmt.upper()}）\n"
            f"💾 大小：{len(data) / 1024:.1f} KB\n"
            f"⬇️ 下載：[點此下載]({url})"
        ),
        "raw": {
            "entity": entity,
            "fmt": fmt,
            "download_url": url,
            "size_bytes": len(data),
            "base64": base64.b64encode(data).decode("ascii"),
        },
    }


@register_tool(
    name="export_customers_to_excel",
    domain="export",
    risk_tier=RiskTier.READ,
    description=(
        "匯出客戶清單成 Excel 或 CSV。範例：「匯出客戶清單」「客戶名單給我 Excel」。"
    ),
    slots=[Slot("fmt", "string", required=False, description="格式：csv 或 xlsx（預設 xlsx）")],
    required_permission="crm.customer.read",
)
async def _export_customers(db, user, fmt: str = "xlsx"):
    return await _export_response(db, "customers", "客戶清單", "📊", fmt)


@register_tool(
    name="export_parts_to_excel",
    domain="export",
    risk_tier=RiskTier.READ,
    description="匯出料件清單成 Excel 或 CSV。範例：「匯出料件清單」「給我所有料號 Excel」。",
    slots=[Slot("fmt", "string", required=False, description="csv 或 xlsx（預設 xlsx）")],
    required_permission="inventory.part.read",
)
async def _export_parts(db, user, fmt: str = "xlsx"):
    return await _export_response(db, "parts", "料件清單", "📊", fmt)


@register_tool(
    name="export_inventory_to_excel",
    domain="export",
    risk_tier=RiskTier.READ,
    description="匯出當前庫存（含安全庫存警示）成 Excel 或 CSV。範例：「匯出庫存」「庫存表給我」。",
    slots=[Slot("fmt", "string", required=False, description="csv 或 xlsx（預設 xlsx）")],
    required_permission="inventory.part.read",
)
async def _export_inventory(db, user, fmt: str = "xlsx"):
    return await _export_response(db, "inventory", "庫存盤點清單", "📦", fmt)


@register_tool(
    name="export_suppliers_to_excel",
    domain="export",
    risk_tier=RiskTier.READ,
    description="匯出供應商清單。範例：「供應商名單 Excel」。",
    slots=[Slot("fmt", "string", required=False, description="csv 或 xlsx（預設 xlsx）")],
    required_permission="purchase.supplier.read",
)
async def _export_suppliers(db, user, fmt: str = "xlsx"):
    return await _export_response(db, "suppliers", "供應商清單", "📊", fmt)


@register_tool(
    name="export_sales_orders_to_excel",
    domain="export",
    risk_tier=RiskTier.READ,
    description="匯出銷售訂單清單。範例：「銷售訂單匯出」「SO 清單 Excel」。",
    slots=[Slot("fmt", "string", required=False, description="csv 或 xlsx（預設 xlsx）")],
    required_permission="sales.order.read",
)
async def _export_sales_orders(db, user, fmt: str = "xlsx"):
    return await _export_response(db, "sales-orders", "銷售訂單清單", "📊", fmt)


@register_tool(
    name="export_purchase_orders_to_excel",
    domain="export",
    risk_tier=RiskTier.READ,
    description="匯出採購訂單清單。範例：「採購訂單匯出」「PO 清單 Excel」。",
    slots=[Slot("fmt", "string", required=False, description="csv 或 xlsx（預設 xlsx）")],
    required_permission="purchase.order.read",
)
async def _export_purchase_orders(db, user, fmt: str = "xlsx"):
    return await _export_response(db, "purchase-orders", "採購訂單清單", "📊", fmt)


# ════════════════════════════════════════════════════════════════════
# 11. setup_status — 「設定到那裡了？」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="setup_status",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "查詢目前設定到那裡了：各模組筆數、缺什麼基礎資料、Day 1-7 進度。"
        "範例：「erpilot 設定到那？」「我還缺什麼？」「進度如何？」"
    ),
    slots=[],
    required_permission="user.profile.read",
)
async def _setup_status(db, user):
    # Count entities
    n_emp = (await db.execute(select(func.count()).select_from(Employee))).scalar() or 0
    n_user = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    n_cust = (await db.execute(select(func.count()).select_from(Customer))).scalar() or 0
    n_sup = (await db.execute(select(func.count()).select_from(Supplier))).scalar() or 0
    n_part = (await db.execute(select(func.count()).select_from(Part))).scalar() or 0
    n_inv = (await db.execute(select(func.count()).select_from(Inventory))).scalar() or 0
    n_so = (await db.execute(select(func.count()).select_from(SalesOrder))).scalar() or 0
    n_po = (await db.execute(select(func.count()).select_from(PurchaseOrder))).scalar() or 0

    # 進度檢查（Day 1-7）
    day_status = {
        "Day 1 安裝完成":       True,  # 能執行此 tool 就代表後端 OK
        "Day 2 員工建檔":       n_emp > 0,
        "Day 3 客戶建檔":       n_cust > 0,
        "Day 3 供應商建檔":     n_sup > 0,
        "Day 4 料件建檔":       n_part > 0,
        "Day 5 庫存初始化":     n_inv > 0,
        "Day 6 開始接單":       n_so > 0,
        "Day 7 開始採購":       n_po > 0,
    }

    completed = sum(1 for v in day_status.values() if v)
    total = len(day_status)

    lines = [
        f"📊 **目前設定進度：{completed}/{total} ({completed*100//total}%)**",
        "",
    ]
    for label, done in day_status.items():
        lines.append(f"  {'✅' if done else '⬜'} {label}")
    lines.append("")
    lines.append("**模組筆數**：")
    lines.append(f"  👤 員工 {n_emp} / 登入帳號 {n_user}")
    lines.append(f"  🤝 客戶 {n_cust} / 供應商 {n_sup}")
    lines.append(f"  📦 料件 {n_part} / 庫存記錄 {n_inv}")
    lines.append(f"  📄 銷售單 {n_so} / 採購單 {n_po}")

    # 下一步建議
    if n_emp == 0:
        lines.append("\n💡 **建議下一步**：先建員工資料（「新增員工 王董」）")
    elif n_cust == 0:
        lines.append("\n💡 **建議下一步**：建幾個客戶（「新增客戶 ABC公司」）")
    elif n_part == 0:
        lines.append("\n💡 **建議下一步**：建料件主檔（「新增料件 M6 螺絲」）")
    elif n_inv == 0:
        lines.append("\n💡 **建議下一步**：盤點初始庫存（「盤點庫存」）")
    elif n_so == 0 and n_po == 0:
        lines.append("\n💡 **建議下一步**：開始接單 / 採購（「新增銷售單」）")
    else:
        lines.append("\n🎉 基本設定都完成！可以開始正式使用了。")
        lines.append("💡 試試：「印 SO-001」「匯出庫存」「老闆儀表板」")

    return {
        "summary": "\n".join(lines),
        "raw": {
            "completed": completed,
            "total": total,
            "percent": completed * 100 // total,
            "counts": {
                "employees": n_emp, "users": n_user,
                "customers": n_cust, "suppliers": n_sup,
                "parts": n_part, "inventory": n_inv,
                "sales_orders": n_so, "purchase_orders": n_po,
            },
            "day_status": day_status,
        },
    }


# ════════════════════════════════════════════════════════════════════
# 12. seed_demo_data_with_confirm — 「載入示範資料」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="seed_demo_data_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "一鍵載入示範資料（3 客戶 + 3 供應商 + 5 料件 + 1 銷售單 + 1 採購單），"
        "讓電腦小白一開始就有可玩的資料。範例：「載入示範資料」「給我 demo data」。"
        "⚠️ 已有資料時會跳過；空 DB 時才會建。"
    ),
    slots=[],
    required_permission="system.config.update",
)
async def _seed_demo_data_with_confirm(db, user):
    # Check existing data
    n_cust = (await db.execute(select(func.count()).select_from(Customer))).scalar() or 0
    n_sup = (await db.execute(select(func.count()).select_from(Supplier))).scalar() or 0
    n_part = (await db.execute(select(func.count()).select_from(Part))).scalar() or 0

    if n_cust > 0 or n_sup > 0 or n_part > 0:
        return {
            "summary": (
                f"⚠️ DB 已有資料（客戶 {n_cust} / 供應商 {n_sup} / 料件 {n_part}），"
                "為避免重複，不再載入 demo。\n"
                "若要清掉重來：請手動清空再執行此 tool。"
            ),
            "raw": {"skipped": True, "existing": {"customers": n_cust, "suppliers": n_sup, "parts": n_part}},
        }

    summary_lines = [
        "📦 將載入以下示範資料：",
        "  👤 3 客戶（ABC 公司、長江廠、台北科技）",
        "  🏭 3 供應商（精誠鋼鐵、聯華電子、台塑化學）",
        "  🔩 5 料件（M6 螺絲、不鏽鋼板、銅線、機殼、PCB）",
        "  📄 1 銷售訂單 + 1 採購訂單",
        "",
        "✅ 確認後將寫入 DB（**hard-write**）。",
    ]

    card = make_card(
        tool_name="seed_demo_data_with_confirm",
        title="📦 確認載入示範資料",
        summary=summary_lines,
        slots={},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        import uuid
        from datetime import datetime, timedelta

        # 3 客戶
        customers = [
            Customer(id=str(uuid.uuid4()), code="C-001", name="ABC 公司",
                     contact_person="張經理", contact_phone="02-1234-5678",
                     credit_limit=500000),
            Customer(id=str(uuid.uuid4()), code="C-002", name="長江廠",
                     contact_person="李廠長", contact_phone="03-1234-5678",
                     credit_limit=300000),
            Customer(id=str(uuid.uuid4()), code="C-003", name="台北科技",
                     contact_person="王董", contact_phone="02-9876-5432",
                     credit_limit=1000000),
        ]
        for c in customers:
            db.add(c)

        # 3 供應商
        suppliers = [
            Supplier(id=str(uuid.uuid4()), code="S-001", name="精誠鋼鐵",
                     contact_person="陳老闆", lead_time_days=7, is_approved=True),
            Supplier(id=str(uuid.uuid4()), code="S-002", name="聯華電子",
                     contact_person="林經理", lead_time_days=14, is_approved=True),
            Supplier(id=str(uuid.uuid4()), code="S-003", name="台塑化學",
                     contact_person="周業務", lead_time_days=10, is_approved=True),
        ]
        for s in suppliers:
            db.add(s)

        # 5 料件
        parts = [
            Part(id=str(uuid.uuid4()), part_no="M6-BOLT", name="M6 螺絲",
                 unit="pcs", safety_stock=1000, unit_cost=1.5),
            Part(id=str(uuid.uuid4()), part_no="SS-PLATE", name="不鏽鋼板",
                 unit="pcs", safety_stock=100, unit_cost=850),
            Part(id=str(uuid.uuid4()), part_no="CU-WIRE", name="銅線",
                 unit="m", safety_stock=500, unit_cost=45),
            Part(id=str(uuid.uuid4()), part_no="CASE-01", name="機殼",
                 unit="pcs", safety_stock=50, unit_cost=320),
            Part(id=str(uuid.uuid4()), part_no="PCB-A1", name="PCB",
                 unit="pcs", safety_stock=200, unit_cost=180),
        ]
        for p in parts:
            db.add(p)

        await db.commit()

        return {
            "summary": (
                "✅ 示範資料已載入：\n"
                "  • 3 客戶 / 3 供應商 / 5 料件\n"
                "可以試試：「列出客戶」「印 M6 螺絲庫存」「老闆儀表板」"
            ),
            "raw": {
                "customers": len(customers),
                "suppliers": len(suppliers),
                "parts": len(parts),
            },
        }

    await stash_card(card, execute)

    return card.to_chat_payload()
