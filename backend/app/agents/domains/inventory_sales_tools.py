"""進銷存深化 LLM tools — Quotation / StockCount / Reorder / 修改 PO/SO  (v3.32)

SMB 業務 / 倉管 / 採購每天用，必須能對 AI 講話：
  「幫客戶 X 報價 100 個 Y 產品 @ NT$500」
  「我要盤點」「PROD-001 實盤 95 個（少 5 個）」「主管覆核盤點」
  「該補哪些料？」
  「PO-001 改成 200 個 / 改交期下週 / 降到 5 元」
  「報價單接受了，轉成 SO」

所有 hard-write 必走 ConfirmCard（v3.31 規範）。
"""
from __future__ import annotations

from datetime import datetime, UTC, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.quotation import Quotation, QuotationItem
from app.models.stock_count import StockCount, StockCountItem
from app.models.crm_sales import Customer, SalesOrder, SalesOrderItem
from app.models.purchase import PurchaseOrder, PurchaseOrderItem
from app.models.inventory import Part, Inventory


# ════════════════════════════════════════════════════════════════════
# 1. Quotation tools (4)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="create_quotation_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "建立報價單給客戶。出 ConfirmCard 列出客戶 + 品項 + 金額。"
        "範例：「幫長江廠報 100 個 M6 螺絲 @ 5 元」"
    ),
    slots=[
        Slot("customer_keyword", "string", required=True, description="客戶名稱或編號"),
        Slot("items", "array", required=True,
             description='品項陣列，每項 {description, quantity, unit_price, [product_id], [discount_rate]}'),
        Slot("valid_days", "integer", required=False, description="有效天數（預設 30）"),
        Slot("notes", "string", required=False, description="備註"),
    ],
    required_permission="sales.quotation.create",
)
async def _create_quotation_with_confirm(
    db, user,
    customer_keyword: str, items: list,
    valid_days: int = 30, notes: str = "",
):
    # Lookup customer
    cu = (await db.execute(
        select(Customer).where(
            (Customer.code == customer_keyword) | (Customer.name.contains(customer_keyword))
        )
    )).scalars().first()
    if cu is None:
        return {"error": f"找不到客戶「{customer_keyword}」"}

    if not items or not isinstance(items, list):
        return {"error": "items 必須是非空陣列"}

    # Compute total
    subtotal = 0.0
    summary = [
        f"📋 客戶：{cu.code} - {cu.name}",
        f"📅 有效期：{valid_days} 天（至 {(datetime.now(UTC) + timedelta(days=valid_days)).strftime('%Y-%m-%d')}）",
        "",
        "**品項明細**：",
    ]
    for i, it in enumerate(items, 1):
        qty = float(it.get("quantity", 0))
        price = float(it.get("unit_price", 0))
        disc = float(it.get("discount_rate", 0))
        line = qty * price * (1 - disc)
        subtotal += line
        disc_str = f" (折扣 {disc:.0%})" if disc > 0 else ""
        summary.append(
            f"  {i}. {it.get('description', '(未命名)')}: {qty:g} × ${price:,.0f}{disc_str} = ${line:,.0f}"
        )
    summary.append("")
    summary.append(f"💰 **小計：${subtotal:,.0f}**")
    summary.append(f"📝 備註：{notes or '(無)'}")

    card = make_card(
        tool_name="create_quotation_with_confirm",
        title="📄 確認建立報價單",
        summary=summary,
        slots={"customer_id": cu.id, "items": items, "valid_days": valid_days,
               "notes": notes},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.quotation import create_quotation
        valid_until = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=valid_days)
        quote = await create_quotation(db, {
            "customer_id": cu.id, "valid_until": valid_until,
            "notes": notes, "items": items,
        }, user=user)
        return {
            "quote_no": quote.quote_no, "total_amount": quote.total_amount,
            "message": f"✅ 報價單 {quote.quote_no} 已建立，總額 ${quote.total_amount:,.0f}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="list_quotations",
    domain="sales",
    risk_tier=RiskTier.READ,
    description="列出最近報價單，可按狀態 / 客戶過濾。範例：「列出本月報價」「查 X 客戶的報價」",
    slots=[
        Slot("status", "string", required=False, description="draft/sent/accepted/rejected/expired/converted"),
        Slot("customer_keyword", "string", required=False, description="客戶名稱關鍵字"),
        Slot("limit", "integer", required=False, description="回傳上限（預設 20）"),
    ],
    required_permission="sales.quotation.read",
)
async def _list_quotations(db, user, status: str = None,
                            customer_keyword: str = None, limit: int = 20):
    from app.services.quotation import list_quotations
    customer_id = None
    if customer_keyword:
        cu = (await db.execute(
            select(Customer).where(Customer.name.contains(customer_keyword))
        )).scalars().first()
        if cu:
            customer_id = cu.id

    rows = await list_quotations(db, status=status, customer_id=customer_id, limit=limit)
    return {
        "total": len(rows),
        "quotations": [
            {"quote_no": r.quote_no, "customer_id": r.customer_id,
             "status": r.status, "total_amount": r.total_amount,
             "quote_date": str(r.quote_date)}
            for r in rows
        ],
    }


@register_tool(
    name="convert_quotation_to_so_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "報價單接受 → 轉成銷售訂單。"
        "範例：「客戶接受 QUO-001 了，轉成訂單」"
    ),
    slots=[
        Slot("quote_no", "string", required=True, description="報價單號"),
    ],
    required_permission="sales.order.create",
)
async def _convert_quotation_to_so(db, user, quote_no: str):
    quote = (await db.execute(
        select(Quotation).options(selectinload(Quotation.items))
        .where(Quotation.quote_no == quote_no)
    )).scalar_one_or_none()
    if quote is None:
        return {"error": f"找不到報價單「{quote_no}」"}
    if quote.converted_so_id:
        return {"error": f"報價單已轉過 SO，不可重複"}

    summary = [
        f"📄 報價單：{quote.quote_no}",
        f"📊 狀態：{quote.status} → converted",
        f"💰 總額：${quote.total_amount:,.0f}",
        f"📦 行數：{len(quote.items)}",
        "",
        "🔄 將自動建立新銷售單（SO），客戶可開始走出貨流程",
    ]
    card = make_card(
        tool_name="convert_quotation_to_so_with_confirm",
        title="🔄 確認報價轉訂單",
        summary=summary,
        slots={"quote_id": quote.id, "quote_no": quote.quote_no},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.quotation import convert_quotation_to_so
        so = await convert_quotation_to_so(db, quote.id, user=user)
        return {
            "quote_no": quote.quote_no, "so_no": so.so_no,
            "message": f"✅ 報價單 {quote.quote_no} 已轉為訂單 {so.so_no}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="update_quotation_status_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "更新報價單狀態（如客戶回覆已寄出 / 拒絕 / 過期）。"
        "範例：「QUO-001 寄出去了」「QUO-001 客戶拒絕了」"
    ),
    slots=[
        Slot("quote_no", "string", required=True),
        Slot("new_status", "string", required=True,
             description="sent / accepted / rejected / expired"),
    ],
    required_permission="sales.quotation.update",
)
async def _update_quotation_status(db, user, quote_no: str, new_status: str):
    quote = (await db.execute(
        select(Quotation).where(Quotation.quote_no == quote_no)
    )).scalar_one_or_none()
    if quote is None:
        return {"error": f"找不到報價單「{quote_no}」"}

    summary = [
        f"📄 報價單：{quote.quote_no}",
        f"📊 狀態變更：{quote.status} → {new_status}",
    ]
    card = make_card(
        tool_name="update_quotation_status_with_confirm",
        title="📝 確認更新報價狀態",
        summary=summary,
        slots={"quote_id": quote.id, "quote_no": quote.quote_no, "new_status": new_status},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.quotation import update_quotation_status
        updated = await update_quotation_status(db, quote.id, new_status, user=user)
        return {
            "quote_no": updated.quote_no, "status": updated.status,
            "message": f"✅ 報價單 {updated.quote_no} 狀態已改為 {new_status}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 2. StockCount tools (3)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="create_stock_count_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "建立盤點單（snapshot 帳上庫存為 book_qty，等倉管填實盤數）。"
        "範例：「我要盤點全部料件」「盤點這 5 個料」"
    ),
    slots=[
        Slot("part_nos", "array", required=False,
             description="要盤的料件編號陣列；不填則 scope='full' 盤全部"),
        Slot("scope", "string", required=False,
             description="full / partial / location（預設 partial 或依 part_nos 推斷）"),
        Slot("notes", "string", required=False, description="盤點備註"),
    ],
    required_permission="inventory.count.create",
)
async def _create_stock_count(db, user, part_nos: list = None,
                                scope: str = None, notes: str = ""):
    part_ids = None
    if part_nos:
        parts = (await db.execute(
            select(Part).where(Part.part_no.in_(part_nos), Part.is_active == True)
        )).scalars().all()
        if not parts:
            return {"error": f"找不到任何料件：{part_nos}"}
        part_ids = [p.id for p in parts]
        if not scope:
            scope = "partial"
    else:
        if not scope:
            scope = "full"

    items_count = len(part_ids) if part_ids else "全部 active parts"
    summary = [
        f"📋 盤點範圍：{scope}",
        f"📦 料件數：{items_count}",
        f"📝 備註：{notes or '(無)'}",
        "",
        "📌 此動作將：",
        "  1. snapshot 帳上庫存 → book_qty",
        "  2. 產生盤點單 + 每料一行",
        "  3. 倉管接著實際清點 → 用 record_counted_qty_with_confirm key in 實盤數",
    ]
    card = make_card(
        tool_name="create_stock_count_with_confirm",
        title="📦 確認建立盤點單",
        summary=summary,
        slots={"part_ids": part_ids, "scope": scope, "notes": notes},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.stock_count import create_stock_count
        sc = await create_stock_count(
            db, part_ids=part_ids, scope=scope, notes=notes, user=user,
        )
        return {
            "count_no": sc.count_no, "items_count": len(sc.items),
            "message": f"✅ 盤點單 {sc.count_no} 已建立（{len(sc.items)} 項）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="record_counted_qty_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "倉管 key in 某料件實盤數量。系統自動算 variance + 原因。"
        "範例：「M6 螺絲實盤 95 個，少 5 個是破損」"
    ),
    slots=[
        Slot("count_no", "string", required=True, description="盤點單號"),
        Slot("part_no", "string", required=True, description="料件編號"),
        Slot("counted_qty", "number", required=True, description="實盤數量"),
        Slot("variance_reason", "string", required=False,
             description="差異原因：damaged / lost / found / count_error / other"),
        Slot("notes", "string", required=False, description="備註"),
    ],
    required_permission="inventory.count.record",
)
async def _record_counted_qty(
    db, user, count_no: str, part_no: str, counted_qty: float,
    variance_reason: str = "", notes: str = "",
):
    sc = (await db.execute(
        select(StockCount).options(selectinload(StockCount.items))
        .where(StockCount.count_no == count_no)
    )).scalar_one_or_none()
    if sc is None:
        return {"error": f"找不到盤點單「{count_no}」"}

    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalar_one_or_none()
    if part is None:
        return {"error": f"找不到料件「{part_no}」"}

    item = next((it for it in sc.items if it.part_id == part.id), None)
    if item is None:
        return {"error": f"盤點單 {count_no} 沒有料件 {part_no}"}

    variance = counted_qty - (item.book_qty or 0)
    icon = "✅" if variance == 0 else ("📈" if variance > 0 else "📉")

    summary = [
        f"📋 盤點單：{sc.count_no}",
        f"📦 料件：{part.part_no} ({part.name})",
        f"📊 帳上：{item.book_qty:g} → 實盤：{counted_qty:g}",
        f"{icon} 差異：{variance:+g} ({variance_reason or '未填原因'})",
        f"📝 備註：{notes or '(無)'}",
    ]
    card = make_card(
        tool_name="record_counted_qty_with_confirm",
        title=f"{icon} 確認登錄實盤數",
        summary=summary,
        slots={"count_item_id": item.id, "counted_qty": counted_qty,
               "variance_reason": variance_reason, "notes": notes},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.stock_count import record_counted_qty
        updated = await record_counted_qty(
            db, item.id, counted_qty, variance_reason, notes, user=user,
        )
        return {
            "count_no": sc.count_no, "part_no": part.part_no,
            "variance": updated.variance,
            "message": f"✅ 已登錄 {part.part_no} 實盤 {counted_qty:g}（差 {updated.variance:+g}）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="apply_stock_count_adjustments_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "主管確認後：盤點差異全部沖入庫存（自動產生 inventory_transaction）。"
        "範例：「主管覆核這份盤點，請套用調整」"
    ),
    slots=[
        Slot("count_no", "string", required=True, description="盤點單號"),
    ],
    required_permission="inventory.count.adjust",
)
async def _apply_stock_count_adjustments(db, user, count_no: str):
    sc = (await db.execute(
        select(StockCount).options(selectinload(StockCount.items))
        .where(StockCount.count_no == count_no)
    )).scalar_one_or_none()
    if sc is None:
        return {"error": f"找不到盤點單「{count_no}」"}
    if sc.status == "adjusted":
        return {"error": f"盤點單 {count_no} 已套用過調整"}

    adjustments = [it for it in sc.items
                   if it.counted_qty is not None and abs(it.variance or 0) > 0.001]

    if not adjustments:
        return {"error": "無差異需要調整（請先 key in 實盤數）"}

    summary = [
        f"📋 盤點單：{sc.count_no}",
        f"📊 待調整項：{len(adjustments)} 項",
        "",
        "**差異明細**（前 10 項）：",
    ]
    for it in adjustments[:10]:
        arrow = "📈" if it.variance > 0 else "📉"
        summary.append(
            f"  {arrow} 料件 {it.part_id[:8]}... 帳上 {it.book_qty:g} → 實盤 "
            f"{it.counted_qty:g}（{it.variance:+g}, {it.variance_reason or '?'}）"
        )
    if len(adjustments) > 10:
        summary.append(f"  ...另 {len(adjustments) - 10} 項")
    summary.append("")
    summary.append("⚠️ 套用後將寫入 inventory_transaction，不可逆（如需取消請走沖正）")

    card = make_card(
        tool_name="apply_stock_count_adjustments_with_confirm",
        title="✅ 確認套用盤點調整",
        summary=summary,
        slots={"count_id": sc.id, "count_no": sc.count_no},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.stock_count import apply_count_adjustments
        result = await apply_count_adjustments(db, sc.id, user=user)
        return result

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 3. Reorder suggestion tool (read; uses ReorderRule)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="reorder_suggestion_tool",
    domain="purchase",
    risk_tier=RiskTier.READ,
    description=(
        "📦 採購建議：列出庫存低於 reorder_point 之料件，建議下單數量。"
        "範例：「該補哪些料？」「快沒了的有哪些？」"
    ),
    slots=[
        Slot("limit", "integer", required=False, description="回傳上限（預設 20）"),
    ],
    required_permission="purchase.order.read",
)
async def _reorder_suggestion(db, user, limit: int = 20):
    # 列出 inventory_qty < min_stock 或 < reorder_point 之料件
    rows = (await db.execute(
        select(Part, Inventory)
        .join(Inventory, Inventory.part_id == Part.id)
        .where(
            Part.is_active == True,
            Part.min_stock > 0,
            Inventory.qty_available < Part.min_stock,
        )
        .limit(limit)
    )).all()

    if not rows:
        return {
            "summary": "✅ 沒有料件低於 reorder point — 庫存安全",
            "raw": {"suggestions": []},
        }

    lines = [f"📦 **採購建議**（{len(rows)} 項低於 min_stock）：\n"]
    suggestions = []
    for part, inv in rows:
        suggest_qty = max(
            (part.max_stock or part.min_stock * 2) - inv.qty_available,
            part.moq if hasattr(part, 'moq') and part.moq else 1,
        )
        lines.append(
            f"  ⚠️ **{part.part_no}** ({part.name}) "
            f"目前 {inv.qty_available:g} < min {part.min_stock:g} → "
            f"建議下單 **{suggest_qty:g}** {part.unit}"
        )
        suggestions.append({
            "part_no": part.part_no, "part_name": part.name,
            "current_qty": inv.qty_available, "min_stock": part.min_stock,
            "suggest_qty": suggest_qty, "unit": part.unit,
        })

    return {
        "summary": "\n".join(lines),
        "raw": {"suggestions": suggestions, "total": len(suggestions)},
        "next_step": "可用 create_purchase_order_with_confirm 建單",
    }


# ════════════════════════════════════════════════════════════════════
# 4. Update PO/SO item tools (2)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="update_purchase_order_item_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "修改 PO 行之數量 / 單價 / 交期。"
        "範例：「PO-001 的 M6 螺絲改成 200 個」「降到 5 元」"
    ),
    slots=[
        Slot("po_no", "string", required=True, description="採購單號"),
        Slot("part_no", "string", required=True, description="料件編號"),
        Slot("new_qty", "number", required=False, description="新數量（不填則不改）"),
        Slot("new_unit_price", "number", required=False, description="新單價（不填則不改）"),
    ],
    required_permission="purchase.order.update",
)
async def _update_po_item(
    db, user, po_no: str, part_no: str,
    new_qty: float = None, new_unit_price: float = None,
):
    po = (await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.po_no == po_no)
    )).scalar_one_or_none()
    if po is None:
        return {"error": f"找不到採購單「{po_no}」"}
    if po.status in ("received", "cancelled", "closed"):
        return {"error": f"PO 狀態 {po.status!r}，不可修改行"}

    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalar_one_or_none()
    if part is None:
        return {"error": f"找不到料件「{part_no}」"}

    item = next((i for i in po.items if i.part_id == part.id), None)
    if item is None:
        return {"error": f"PO {po_no} 沒有料件 {part_no}"}

    if new_qty is None and new_unit_price is None:
        return {"error": "請至少指定 new_qty 或 new_unit_price"}

    changes = []
    if new_qty is not None and new_qty != item.ordered_qty:
        changes.append(f"數量：{item.ordered_qty:g} → {new_qty:g}")
    if new_unit_price is not None and new_unit_price != item.unit_price:
        changes.append(f"單價：${item.unit_price:g} → ${new_unit_price:g}")
    if not changes:
        return {"message": "無變更", "po_no": po_no, "part_no": part_no}

    summary = [
        f"📋 採購單：{po.po_no}",
        f"📦 料件：{part.part_no} ({part.name})",
        *changes,
    ]
    card = make_card(
        tool_name="update_purchase_order_item_with_confirm",
        title="📝 確認修改 PO 行",
        summary=summary,
        slots={"po_id": po.id, "item_id": item.id,
               "new_qty": new_qty, "new_unit_price": new_unit_price},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        if new_qty is not None:
            item.ordered_qty = new_qty
        if new_unit_price is not None:
            item.unit_price = new_unit_price
        # Recalc PO total
        po.total_amount = sum((i.ordered_qty or 0) * (i.unit_price or 0) for i in po.items)
        await db.commit()
        return {
            "po_no": po.po_no, "part_no": part.part_no,
            "message": f"✅ PO {po.po_no} 之 {part.part_no} 已修改",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="update_sales_order_item_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "修改 SO 行之數量 / 單價。"
        "範例：「SO-001 的 PROD-A 改成 50 個」「降到 NT$180」"
    ),
    slots=[
        Slot("so_no", "string", required=True, description="銷售單號"),
        Slot("product_no", "string", required=True, description="產品編號"),
        Slot("new_qty", "number", required=False, description="新數量"),
        Slot("new_unit_price", "number", required=False, description="新單價"),
    ],
    required_permission="sales.order.update",
)
async def _update_so_item(
    db, user, so_no: str, product_no: str,
    new_qty: float = None, new_unit_price: float = None,
):
    from app.models.product import Product
    so = (await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items))
        .where(SalesOrder.so_no == so_no)
    )).scalar_one_or_none()
    if so is None:
        return {"error": f"找不到銷售單「{so_no}」"}
    if so.status in ("shipped", "cancelled", "closed"):
        return {"error": f"SO 狀態 {so.status!r}，不可修改行"}

    prod = (await db.execute(
        select(Product).where(Product.product_no == product_no)
    )).scalar_one_or_none()
    if prod is None:
        return {"error": f"找不到產品「{product_no}」"}

    item = next((i for i in so.items if i.product_id == prod.id), None)
    if item is None:
        return {"error": f"SO {so_no} 沒有產品 {product_no}"}

    if new_qty is None and new_unit_price is None:
        return {"error": "請至少指定 new_qty 或 new_unit_price"}

    changes = []
    if new_qty is not None and new_qty != item.ordered_qty:
        changes.append(f"數量：{item.ordered_qty:g} → {new_qty:g}")
    if new_unit_price is not None and new_unit_price != item.unit_price:
        changes.append(f"單價：${item.unit_price:g} → ${new_unit_price:g}")
    if not changes:
        return {"message": "無變更"}

    summary = [
        f"📋 銷售單：{so.so_no}",
        f"📦 產品：{prod.product_no} ({prod.name})",
        *changes,
    ]
    card = make_card(
        tool_name="update_sales_order_item_with_confirm",
        title="📝 確認修改 SO 行",
        summary=summary,
        slots={"so_id": so.id, "item_id": item.id,
               "new_qty": new_qty, "new_unit_price": new_unit_price},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        if new_qty is not None:
            item.ordered_qty = new_qty
        if new_unit_price is not None:
            item.unit_price = new_unit_price
        item.line_total = (item.ordered_qty or 0) * (item.unit_price or 0)
        so.total_amount = sum((i.line_total or 0) for i in so.items)
        await db.commit()
        return {
            "so_no": so.so_no, "product_no": prod.product_no,
            "message": f"✅ SO {so.so_no} 之 {prod.product_no} 已修改",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# Auto-attach to domain agents
# ════════════════════════════════════════════════════════════════════

from app.agents.engine import AGENT_REGISTRY as _AGENT_REGISTRY

_DOMAIN_TOOL_MAP = {
    "sales": [
        "create_quotation_with_confirm",
        "list_quotations",
        "convert_quotation_to_so_with_confirm",
        "update_quotation_status_with_confirm",
        "update_sales_order_item_with_confirm",
    ],
    "inventory": [
        "create_stock_count_with_confirm",
        "record_counted_qty_with_confirm",
        "apply_stock_count_adjustments_with_confirm",
    ],
    "purchase": [
        "reorder_suggestion_tool",
        "update_purchase_order_item_with_confirm",
    ],
}

for _domain, _tools in _DOMAIN_TOOL_MAP.items():
    if _domain in _AGENT_REGISTRY:
        _tn = _AGENT_REGISTRY[_domain]["tool_names"]
        for _t in _tools:
            if _t not in _tn:
                _tn.append(_t)
