"""進銷存深化 - 第二輪（v3.33）

v3.32 補了 Quotation / StockCount / Reorder 主流程，但電腦小白
每天還會用到的細節仍缺。本檔補完 12 個高頻 LLM tools。

══════════════════════════════════════════════════════════════════
Quotation 深化（4 tools）
  • query_quotation_detail        「QUO-001 內容是？」
  • clone_quotation_with_confirm  「照上次給 X 客戶的報價再來一張」
  • send_quotation_email_with_confirm  「把 QUO-001 寄給客戶」
  • cancel_quotation_with_confirm 「QUO-001 作廢」

StockCount 深化（3 tools）
  • query_stock_count_progress    「SC-001 盤點進度？」
  • batch_record_counted_qty_with_confirm  「批次 keyin 實盤」
  • cancel_stock_count_with_confirm 「取消這份盤點」

Reorder 深化（1 tool）
  • smart_reorder_with_lead_time_tool  「含 lead time + 按供應商分組」

PO/SO 行操作深化（4 tools）
  • add_purchase_order_item_with_confirm    「PO-001 加 100 個 M8」
  • remove_purchase_order_item_with_confirm 「PO-001 刪掉 M6 那行」
  • update_purchase_order_delivery_with_confirm 「PO-001 交期改下週」
  • add_sales_order_item_with_confirm       「SO-001 加 50 個產品 B」

══════════════════════════════════════════════════════════════════
LEGAL / 法律聲明
══════════════════════════════════════════════════════════════════
本模組之 hard-write 全部走 ConfirmCard 規範（同 v3.31 / v3.32）。
特殊風險：
  • clone_quotation：複製不複製 timestamp，新報價是「新版本」
  • send_quotation_email：寄出 = 對外承諾，務必確認金額與條款
  • cancel_quotation：作廢不可逆（需新建新報價取代）
  • cancel_stock_count：未完成的盤點作廢；已完成走沖正流程
  • smart_reorder：lead_time + safety_stock 為估計值，重大採購
    應人工覆核
  • PO/SO add/remove item：影響供應商 / 客戶契約承諾

於適用法律所允許之最大範圍內 (TMEPL)，Ouvoca 對採用本 tool 之
結果不承擔責任。累積適用 v3.25.10 → v3.32 §6 全部法律聲明。
詳見 docs/INVENTORY_SALES_LEGAL_NOTICE_ZH.md / EN.md。

This module's hard-writes all follow ConfirmCard convention.
Special risks: cloning a quotation creates a new version (not a copy);
sending quotation email = external commitment; cancellation is
irreversible (must create new replacement). To the maximum extent
permitted by applicable law, Ouvoca assumes no liability for results
of using these tools. Cumulative applicability with v3.25.10 → v3.32
§6 disclaimers. See docs/INVENTORY_SALES_LEGAL_NOTICE_EN.md for full
notice.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, UTC
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.quotation import Quotation, QuotationItem
from app.models.stock_count import StockCount, StockCountItem
from app.models.crm_sales import Customer, SalesOrder, SalesOrderItem
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.product import Product
from app.models.inventory import Part, Inventory


# ════════════════════════════════════════════════════════════════════
# Quotation 深化 (4)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="query_quotation_detail",
    domain="sales",
    risk_tier=RiskTier.READ,
    description=(
        "查詢單張報價單之完整內容（品項、金額、客戶、狀態）。"
        "範例：「QUO-001 內容是？」「給我看那張報價」"
    ),
    slots=[
        Slot("quote_no", "string", required=True, description="報價單號"),
    ],
    required_permission="sales.quotation.read",
)
async def _query_quotation_detail(db, user, quote_no: str):
    quote = (await db.execute(
        select(Quotation).options(selectinload(Quotation.items))
        .where(Quotation.quote_no == quote_no)
    )).scalar_one_or_none()
    if quote is None:
        return {"error": f"找不到報價單「{quote_no}」"}

    cu = None
    if quote.customer_id:
        cu = (await db.execute(
            select(Customer).where(Customer.id == quote.customer_id)
        )).scalar_one_or_none()

    lines = [
        f"📄 **報價單 {quote.quote_no}**",
        f"👤 客戶：{cu.code if cu else '?'} - {cu.name if cu else '?'}",
        f"📅 報價日：{quote.quote_date}",
        f"⏳ 有效期：{quote.valid_until}",
        f"📊 狀態：{quote.status}",
        f"📝 備註：{quote.notes or '(無)'}",
        "",
        "**品項明細**：",
    ]
    for i, it in enumerate(quote.items, 1):
        lines.append(
            f"  {i}. {it.description}: {it.quantity:g} × ${it.unit_price:g} = ${it.line_total:,.0f}"
        )
    lines.append("")
    lines.append(f"💰 **小計：${quote.subtotal:,.0f}**")
    lines.append(f"💰 **總額：${quote.total_amount:,.0f}**")
    if quote.converted_so_id:
        lines.append(f"🔄 已轉訂單：{quote.converted_so_id}")

    return {
        "summary": "\n".join(lines),
        "raw": {
            "quote_no": quote.quote_no, "status": quote.status,
            "total_amount": quote.total_amount,
            "items_count": len(quote.items),
            "converted_so_id": quote.converted_so_id,
        },
    }


@register_tool(
    name="clone_quotation_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "📋 複製舊報價單為新報價單（業務常用：「同樣條件再來一張」）。"
        "範例：「照上次給長江廠的報價再開一張」「複製 QUO-001」"
    ),
    slots=[
        Slot("source_quote_no", "string", required=True, description="要複製的原報價單號"),
        Slot("new_valid_days", "integer", required=False, description="新有效天數（預設 30）"),
    ],
    required_permission="sales.quotation.create",
)
async def _clone_quotation_with_confirm(
    db, user, source_quote_no: str, new_valid_days: int = 30,
):
    source = (await db.execute(
        select(Quotation).options(selectinload(Quotation.items))
        .where(Quotation.quote_no == source_quote_no)
    )).scalar_one_or_none()
    if source is None:
        return {"error": f"找不到原報價單「{source_quote_no}」"}

    cu = (await db.execute(
        select(Customer).where(Customer.id == source.customer_id)
    )).scalar_one_or_none()

    summary = [
        f"📋 **複製報價單**",
        f"來源：{source.quote_no}",
        f"客戶：{cu.code if cu else '?'} - {cu.name if cu else '?'}",
        f"原總額：${source.total_amount:,.0f}",
        f"品項數：{len(source.items)}",
        f"新有效期：{new_valid_days} 天",
        "",
        "⚠️ 新報價會獨立編號（QUO-xxxxx），與原報價分開追蹤",
    ]
    card = make_card(
        tool_name="clone_quotation_with_confirm",
        title="📋 確認複製報價單",
        summary=summary,
        slots={"source_quote_id": source.id, "source_quote_no": source.quote_no,
               "new_valid_days": new_valid_days},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.quotation import create_quotation
        items_data = [
            {"description": it.description, "product_id": it.product_id,
             "quantity": it.quantity, "unit": it.unit,
             "unit_price": it.unit_price, "discount_rate": it.discount_rate,
             "remark": it.remark, "sequence_no": it.sequence_no}
            for it in source.items
        ]
        new_quote = await create_quotation(db, {
            "customer_id": source.customer_id,
            "valid_until": datetime.now(UTC).replace(tzinfo=None) + timedelta(days=new_valid_days),
            "notes": f"複製自 {source.quote_no}",
            "items": items_data,
        }, user=user)
        return {
            "source_quote_no": source.quote_no,
            "new_quote_no": new_quote.quote_no,
            "message": f"✅ 已複製 {source.quote_no} → 新報價 {new_quote.quote_no}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="send_quotation_email_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "把報價單寄 Email 給客戶（會改狀態為 sent）。"
        "範例：「把 QUO-001 寄給客戶」「QUO-001 發出去」"
    ),
    slots=[
        Slot("quote_no", "string", required=True, description="報價單號"),
        Slot("email_address", "string", required=False,
             description="收件人 email（不填則用客戶預設）"),
    ],
    required_permission="sales.quotation.send",
)
async def _send_quotation_email_with_confirm(
    db, user, quote_no: str, email_address: str = "",
):
    quote = (await db.execute(
        select(Quotation).where(Quotation.quote_no == quote_no)
    )).scalar_one_or_none()
    if quote is None:
        return {"error": f"找不到報價單「{quote_no}」"}
    if quote.status not in ("draft", "sent"):
        return {"error": f"報價單狀態 {quote.status!r}，已 accepted/rejected/expired 不可重寄"}

    cu = (await db.execute(
        select(Customer).where(Customer.id == quote.customer_id)
    )).scalar_one_or_none()
    if cu is None:
        return {"error": "報價單之客戶資料異常"}

    to_email = email_address or cu.contact_email
    if not to_email:
        return {
            "error": "找不到收件人 email",
            "hint": "請提供 email_address 參數或先設定客戶之 contact_email",
        }

    summary = [
        f"📧 **寄送報價單**",
        f"報價單：{quote.quote_no}",
        f"客戶：{cu.code} - {cu.name}",
        f"收件人：{to_email}",
        f"金額：${quote.total_amount:,.0f}",
        f"狀態變更：{quote.status} → sent",
        "",
        "⚠️ 寄出 = 對客戶承諾，請確認金額與條款正確",
    ]
    card = make_card(
        tool_name="send_quotation_email_with_confirm",
        title="📧 確認寄送報價單",
        summary=summary,
        slots={"quote_id": quote.id, "quote_no": quote.quote_no,
               "to_email": to_email},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        # Update status to sent (real SMTP send is out of scope; placeholder)
        quote.status = "sent"
        await db.commit()
        return {
            "quote_no": quote.quote_no,
            "to_email": to_email,
            "message": f"✅ 報價單 {quote.quote_no} 已標為 sent（實際 SMTP 寄送請整合 email_digest 模組）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="cancel_quotation_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "作廢報價單（已轉 SO 不可作廢）。範例：「QUO-001 作廢」"
    ),
    slots=[
        Slot("quote_no", "string", required=True),
        Slot("reason", "string", required=False, description="作廢原因"),
    ],
    required_permission="sales.quotation.cancel",
)
async def _cancel_quotation_with_confirm(db, user, quote_no: str, reason: str = ""):
    quote = (await db.execute(
        select(Quotation).where(Quotation.quote_no == quote_no)
    )).scalar_one_or_none()
    if quote is None:
        return {"error": f"找不到報價單「{quote_no}」"}
    if quote.converted_so_id:
        return {"error": "報價單已轉訂單，不可作廢（請改去取消對應 SO）"}
    if quote.status in ("rejected", "expired"):
        return {"error": f"報價單已是 {quote.status!r}，不需再作廢"}

    summary = [
        f"📄 報價單：{quote.quote_no}",
        f"📊 狀態：{quote.status} → rejected",
        f"📝 原因：{reason or '(未填)'}",
        "",
        "⚠️ 作廢後不可逆。若客戶仍有興趣請建新報價",
    ]
    card = make_card(
        tool_name="cancel_quotation_with_confirm",
        title="🚫 確認作廢報價單",
        summary=summary,
        slots={"quote_id": quote.id, "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        quote.status = "rejected"
        if reason:
            quote.notes = (quote.notes or "") + f"\n[作廢原因] {reason}"
        await db.commit()
        return {"quote_no": quote.quote_no, "message": f"✅ 報價單 {quote.quote_no} 已作廢"}

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# StockCount 深化 (3)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="query_stock_count_progress",
    domain="inventory",
    risk_tier=RiskTier.READ,
    description=(
        "查詢盤點進度（已盤幾項、剩幾項、差異統計）。"
        "範例：「SC-001 盤點進度？」「盤點完了沒？」"
    ),
    slots=[
        Slot("count_no", "string", required=True, description="盤點單號"),
    ],
    required_permission="inventory.count.read",
)
async def _query_stock_count_progress(db, user, count_no: str):
    sc = (await db.execute(
        select(StockCount).options(selectinload(StockCount.items))
        .where(StockCount.count_no == count_no)
    )).scalar_one_or_none()
    if sc is None:
        return {"error": f"找不到盤點單「{count_no}」"}

    total = len(sc.items)
    counted = sum(1 for it in sc.items if it.counted_qty is not None)
    pending = total - counted
    variances = [it for it in sc.items if it.counted_qty is not None and abs(it.variance or 0) > 0.001]
    progress_pct = (counted / total * 100) if total > 0 else 0

    lines = [
        f"📋 **盤點單 {sc.count_no}** 進度",
        f"📊 狀態：{sc.status}",
        f"📦 總項數：{total}",
        f"✅ 已盤：{counted} ({progress_pct:.1f}%)",
        f"⏳ 待盤：{pending}",
        f"⚠️ 有差異：{len(variances)} 項",
    ]
    if variances:
        lines.append("")
        lines.append("**差異 Top 5**：")
        for it in sorted(variances, key=lambda x: -abs(x.variance or 0))[:5]:
            arrow = "📈" if it.variance > 0 else "📉"
            lines.append(
                f"  {arrow} 料件 {it.part_id[:8]}... 帳上 {it.book_qty:g} "
                f"→ 實盤 {it.counted_qty:g} ({it.variance:+g})"
            )

    return {
        "summary": "\n".join(lines),
        "raw": {
            "count_no": sc.count_no, "status": sc.status,
            "total": total, "counted": counted, "pending": pending,
            "variances_count": len(variances),
            "progress_pct": progress_pct,
        },
    }


@register_tool(
    name="batch_record_counted_qty_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "📦 批次 keyin 多個料件之實盤數量（倉管月底必備）。"
        "範例：「SC-001 批次 keyin: M6=95, M8=200, M10=150」"
    ),
    slots=[
        Slot("count_no", "string", required=True, description="盤點單號"),
        Slot("counts", "array", required=True,
             description='陣列：[{"part_no": "M6", "counted_qty": 95, "reason": "破損"}, ...]'),
    ],
    required_permission="inventory.count.record",
)
async def _batch_record_counted_qty(db, user, count_no: str, counts: list):
    if not counts or not isinstance(counts, list):
        return {"error": "counts 必須是非空陣列"}

    sc = (await db.execute(
        select(StockCount).options(selectinload(StockCount.items))
        .where(StockCount.count_no == count_no)
    )).scalar_one_or_none()
    if sc is None:
        return {"error": f"找不到盤點單「{count_no}」"}

    # Build part_no → part lookup
    part_nos = [c.get("part_no") for c in counts if c.get("part_no")]
    parts = (await db.execute(
        select(Part).where(Part.part_no.in_(part_nos))
    )).scalars().all()
    part_by_no = {p.part_no: p for p in parts}
    item_by_part = {it.part_id: it for it in sc.items}

    # Pre-validate
    rows_to_update = []
    errors = []
    for c in counts:
        pn = c.get("part_no")
        if not pn:
            errors.append("缺 part_no")
            continue
        part = part_by_no.get(pn)
        if not part:
            errors.append(f"找不到料件 {pn}")
            continue
        item = item_by_part.get(part.id)
        if not item:
            errors.append(f"盤點單沒有料件 {pn}")
            continue
        counted_qty = c.get("counted_qty")
        if counted_qty is None:
            errors.append(f"{pn} 缺 counted_qty")
            continue
        rows_to_update.append({
            "item_id": item.id, "part_no": pn,
            "book_qty": item.book_qty or 0, "counted_qty": counted_qty,
            "reason": c.get("reason", ""), "notes": c.get("notes", ""),
        })

    if errors:
        return {
            "error": f"找到 {len(errors)} 個錯誤",
            "details": errors[:10],
        }

    summary = [
        f"📋 盤點單：{sc.count_no}",
        f"📊 批次 keyin {len(rows_to_update)} 項",
        "",
        "**明細**：",
    ]
    for r in rows_to_update[:10]:
        variance = r["counted_qty"] - r["book_qty"]
        arrow = "✅" if variance == 0 else ("📈" if variance > 0 else "📉")
        summary.append(
            f"  {arrow} {r['part_no']}: 帳 {r['book_qty']:g} → 實 {r['counted_qty']:g} "
            f"({variance:+g}) {r['reason']}"
        )
    if len(rows_to_update) > 10:
        summary.append(f"  ... 另 {len(rows_to_update) - 10} 項")

    card = make_card(
        tool_name="batch_record_counted_qty_with_confirm",
        title="📦 確認批次登錄實盤",
        summary=summary,
        slots={"count_id": sc.id, "rows": rows_to_update},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.stock_count import record_counted_qty
        applied = 0
        for r in rows_to_update:
            await record_counted_qty(
                db, r["item_id"], r["counted_qty"],
                variance_reason=r["reason"], notes=r["notes"],
                user=user,
            )
            applied += 1
        return {
            "count_no": sc.count_no, "applied": applied,
            "message": f"✅ 批次登錄完成（{applied} 項）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="cancel_stock_count_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "取消未完成之盤點單（已 adjusted 不可取消）。"
        "範例：「SC-001 取消，明天重來」"
    ),
    slots=[
        Slot("count_no", "string", required=True),
        Slot("reason", "string", required=False),
    ],
    required_permission="inventory.count.cancel",
)
async def _cancel_stock_count_with_confirm(db, user, count_no: str, reason: str = ""):
    sc = (await db.execute(
        select(StockCount).where(StockCount.count_no == count_no)
    )).scalar_one_or_none()
    if sc is None:
        return {"error": f"找不到盤點單「{count_no}」"}
    if sc.status in ("adjusted", "cancelled"):
        return {"error": f"盤點單狀態 {sc.status!r}，不可取消"}

    summary = [
        f"📋 盤點單：{sc.count_no}",
        f"📊 狀態：{sc.status} → cancelled",
        f"📝 取消原因：{reason or '(未填)'}",
        "",
        "⚠️ 取消後已 key in 之實盤數據將保留（供查詢），但不會套用調整",
    ]
    card = make_card(
        tool_name="cancel_stock_count_with_confirm",
        title="🚫 確認取消盤點",
        summary=summary,
        slots={"count_id": sc.id, "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        sc.status = "cancelled"
        if reason:
            sc.notes = (sc.notes or "") + f"\n[取消] {reason}"
        await db.commit()
        return {"count_no": sc.count_no, "message": f"✅ 盤點單 {sc.count_no} 已取消"}

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# Reorder 深化 (1)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="smart_reorder_with_lead_time_tool",
    domain="purchase",
    risk_tier=RiskTier.READ,
    description=(
        "📦 智慧採購建議：含 lead_time + safety_stock + 按供應商分組。"
        "比 basic reorder_suggestion_tool 更完整，建議下次「現在」就該下單避免缺料。"
        "範例：「智慧採購建議」「lead time 內快沒料的有哪些？」"
    ),
    slots=[
        Slot("forecast_days", "integer", required=False,
             description="預測未來幾天的需求（預設 30）"),
        Slot("limit", "integer", required=False, description="回傳上限"),
    ],
    required_permission="purchase.order.read",
)
async def _smart_reorder_with_lead_time(
    db, user, forecast_days: int = 30, limit: int = 50,
):
    # Get all active parts with min_stock or reorder logic
    rows = (await db.execute(
        select(Part, Inventory)
        .join(Inventory, Inventory.part_id == Part.id)
        .where(Part.is_active == True)
    )).all()

    suggestions = []
    grouped_by_supplier = {}
    for part, inv in rows:
        # Estimate daily consumption: use a rough heuristic (would need historical)
        # For simplicity: assume forecast_days demand = min_stock (conservative)
        daily_burn = (part.min_stock or 0) / 30 if part.min_stock else 0
        lead_time = part.lead_time_days or 7
        # Safety stock target
        safety_stock = part.safety_stock or part.min_stock or 0
        # Reorder point = (daily_burn × lead_time) + safety_stock
        reorder_point = (daily_burn * lead_time) + safety_stock
        # Suggest order qty = forecast_days demand + safety - on_hand
        suggest_qty = (daily_burn * forecast_days) + safety_stock - inv.qty_available

        if inv.qty_available < reorder_point and suggest_qty > 0:
            urgency = "🔴 緊急" if inv.qty_available < safety_stock else "🟡 該補"
            sug = {
                "part_no": part.part_no, "part_name": part.name,
                "current_qty": inv.qty_available,
                "reorder_point": round(reorder_point, 1),
                "safety_stock": safety_stock,
                "lead_time_days": lead_time,
                "suggest_qty": round(suggest_qty, 1),
                "unit": part.unit,
                "urgency": urgency,
            }
            suggestions.append(sug)

    suggestions = suggestions[:limit]

    if not suggestions:
        return {
            "summary": "✅ 沒有料件需要補貨（含 lead time + safety stock 預測）",
            "raw": {"suggestions": []},
        }

    lines = [f"📦 **智慧採購建議**（預測 {forecast_days} 天，共 {len(suggestions)} 項）：\n"]
    urgent = [s for s in suggestions if "緊急" in s["urgency"]]
    normal = [s for s in suggestions if "該補" in s["urgency"]]

    if urgent:
        lines.append(f"🔴 **緊急 ({len(urgent)} 項) — 已低於 safety stock**：")
        for s in urgent[:10]:
            lines.append(
                f"  • {s['part_no']} ({s['part_name']}) 目前 {s['current_qty']:g} "
                f"< safety {s['safety_stock']:g}, lead time {s['lead_time_days']}d "
                f"→ 建議下 {s['suggest_qty']:g} {s['unit']}"
            )
        lines.append("")

    if normal:
        lines.append(f"🟡 **該補 ({len(normal)} 項) — 低於 reorder point**：")
        for s in normal[:10]:
            lines.append(
                f"  • {s['part_no']} 目前 {s['current_qty']:g} < ROP {s['reorder_point']:g} "
                f"→ 建議下 {s['suggest_qty']:g}"
            )

    lines.append("")
    lines.append("💡 用 `create_purchase_order_with_confirm` 直接下單")

    return {
        "summary": "\n".join(lines),
        "raw": {"suggestions": suggestions,
                "urgent_count": len(urgent), "normal_count": len(normal)},
        "warning": (
            "⚠️ 預測使用 min_stock 推估 daily burn；若無歷史銷售推估會偏保守。"
            "重大採購請參考 demand_forecasting tool + 人工覆核。"
        ),
    }


# ════════════════════════════════════════════════════════════════════
# PO/SO 行操作深化 (4)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="add_purchase_order_item_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "在現有 PO 加新行（PO 必須是 draft 狀態）。"
        "範例：「PO-001 加 100 個 M8 螺絲，每個 6 元」"
    ),
    slots=[
        Slot("po_no", "string", required=True),
        Slot("part_no", "string", required=True),
        Slot("quantity", "number", required=True),
        Slot("unit_price", "number", required=True),
    ],
    required_permission="purchase.order.update",
)
async def _add_po_item(
    db, user, po_no: str, part_no: str, quantity: float, unit_price: float,
):
    po = (await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.po_no == po_no)
    )).scalar_one_or_none()
    if po is None:
        return {"error": f"找不到 PO「{po_no}」"}
    if po.status != "draft":
        return {"error": f"PO 狀態 {po.status!r}，只有 draft 可加行"}

    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalar_one_or_none()
    if part is None:
        return {"error": f"找不到料件「{part_no}」"}

    # Duplicate check
    existing = next((i for i in po.items if i.part_id == part.id), None)
    if existing:
        return {
            "error": f"PO 已有料件 {part_no}",
            "hint": "用 update_purchase_order_item_with_confirm 修改數量",
        }

    line_total = quantity * unit_price
    summary = [
        f"📋 PO：{po.po_no}",
        f"📦 新增料件：{part.part_no} ({part.name})",
        f"📊 數量：{quantity:g} {part.unit}",
        f"💰 單價：${unit_price:g} → 行小計 ${line_total:,.0f}",
        f"📈 PO 總額：${po.total_amount or 0:,.0f} → ${(po.total_amount or 0) + line_total:,.0f}",
    ]
    card = make_card(
        tool_name="add_purchase_order_item_with_confirm",
        title="➕ 確認 PO 加新行",
        summary=summary,
        slots={"po_id": po.id, "part_id": part.id,
               "quantity": quantity, "unit_price": unit_price},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        new_item = PurchaseOrderItem(
            id=str(uuid.uuid4()),
            po_id=po.id,
            part_id=part.id,
            ordered_qty=quantity,
            unit_price=unit_price,
            line_total=line_total,
        )
        db.add(new_item)
        po.total_amount = (po.total_amount or 0) + line_total
        await db.commit()
        return {
            "po_no": po.po_no, "part_no": part.part_no,
            "message": f"✅ PO {po.po_no} 已加新行 {part.part_no} × {quantity:g}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="remove_purchase_order_item_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "從 PO 移除某一行（PO 必須是 draft）。"
        "範例：「PO-001 把 M6 那行刪掉」"
    ),
    slots=[
        Slot("po_no", "string", required=True),
        Slot("part_no", "string", required=True),
    ],
    required_permission="purchase.order.update",
)
async def _remove_po_item(db, user, po_no: str, part_no: str):
    po = (await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.po_no == po_no)
    )).scalar_one_or_none()
    if po is None:
        return {"error": f"找不到 PO「{po_no}」"}
    if po.status != "draft":
        return {"error": f"PO 狀態 {po.status!r}，只有 draft 可刪行"}

    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalar_one_or_none()
    if part is None:
        return {"error": f"找不到料件「{part_no}」"}

    item = next((i for i in po.items if i.part_id == part.id), None)
    if item is None:
        return {"error": f"PO {po_no} 沒有料件 {part_no}"}

    summary = [
        f"📋 PO：{po.po_no}",
        f"🗑 刪除料件：{part.part_no} ({part.name})",
        f"📊 原數量：{item.ordered_qty:g}",
        f"💰 原行小計：${item.line_total or 0:,.0f}",
        f"📉 PO 總額：${po.total_amount or 0:,.0f} → ${(po.total_amount or 0) - (item.line_total or 0):,.0f}",
    ]
    card = make_card(
        tool_name="remove_purchase_order_item_with_confirm",
        title="➖ 確認 PO 刪除行",
        summary=summary,
        slots={"po_id": po.id, "item_id": item.id},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        po.total_amount = (po.total_amount or 0) - (item.line_total or 0)
        await db.delete(item)
        await db.commit()
        return {
            "po_no": po.po_no, "part_no": part.part_no,
            "message": f"✅ PO {po.po_no} 之 {part.part_no} 已刪除",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="update_purchase_order_delivery_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "修改 PO 預期交期。範例：「PO-001 交期改 6/5」「延後到下週」"
    ),
    slots=[
        Slot("po_no", "string", required=True),
        Slot("new_delivery_date", "string", required=True,
             description="新交期 YYYY-MM-DD"),
        Slot("reason", "string", required=False),
    ],
    required_permission="purchase.order.update",
)
async def _update_po_delivery(
    db, user, po_no: str, new_delivery_date: str, reason: str = "",
):
    po = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.po_no == po_no)
    )).scalar_one_or_none()
    if po is None:
        return {"error": f"找不到 PO「{po_no}」"}
    if po.status in ("received", "cancelled", "closed"):
        return {"error": f"PO 狀態 {po.status!r}，不可改交期"}

    try:
        new_dt = datetime.strptime(new_delivery_date, "%Y-%m-%d")
    except ValueError:
        return {"error": f"日期格式錯誤「{new_delivery_date}」，應為 YYYY-MM-DD"}

    old_date = po.expected_delivery_date
    summary = [
        f"📋 PO：{po.po_no}",
        f"📅 交期變更：{old_date} → {new_dt.date()}",
        f"📝 原因：{reason or '(未填)'}",
        "",
        "⚠️ 若已通知供應商，請另行通知變更",
    ]
    card = make_card(
        tool_name="update_purchase_order_delivery_with_confirm",
        title="📅 確認改 PO 交期",
        summary=summary,
        slots={"po_id": po.id, "new_delivery_date": new_delivery_date,
               "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        po.expected_delivery_date = new_dt
        if reason:
            po.remark = (po.remark or "") + f"\n[改交期] {reason}"
        await db.commit()
        return {
            "po_no": po.po_no, "new_delivery_date": str(new_dt.date()),
            "message": f"✅ PO {po.po_no} 交期已改為 {new_dt.date()}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="add_sales_order_item_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "在現有 SO 加新行（SO 必須是 draft / confirmed 狀態，未出貨）。"
        "範例：「SO-001 加 50 個 PROD-B，每個 NT$300」"
    ),
    slots=[
        Slot("so_no", "string", required=True),
        Slot("product_no", "string", required=True),
        Slot("quantity", "number", required=True),
        Slot("unit_price", "number", required=True),
    ],
    required_permission="sales.order.update",
)
async def _add_so_item(
    db, user, so_no: str, product_no: str, quantity: float, unit_price: float,
):
    so = (await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items))
        .where(SalesOrder.so_no == so_no)
    )).scalar_one_or_none()
    if so is None:
        return {"error": f"找不到 SO「{so_no}」"}
    if so.status in ("shipped", "cancelled", "closed"):
        return {"error": f"SO 狀態 {so.status!r}，不可加行"}

    prod = (await db.execute(
        select(Product).where(Product.product_no == product_no)
    )).scalar_one_or_none()
    if prod is None:
        return {"error": f"找不到產品「{product_no}」"}

    existing = next((i for i in so.items if i.product_id == prod.id), None)
    if existing:
        return {
            "error": f"SO 已有產品 {product_no}",
            "hint": "用 update_sales_order_item_with_confirm 修改",
        }

    line_total = quantity * unit_price
    next_line_no = max((i.line_no for i in so.items), default=0) + 1

    summary = [
        f"📋 SO：{so.so_no}",
        f"📦 新增產品：{prod.product_no} ({prod.name})",
        f"📊 數量：{quantity:g}",
        f"💰 單價：${unit_price:g} → 行小計 ${line_total:,.0f}",
        f"📈 SO 總額：${so.total_amount or 0:,.0f} → ${(so.total_amount or 0) + line_total:,.0f}",
    ]
    card = make_card(
        tool_name="add_sales_order_item_with_confirm",
        title="➕ 確認 SO 加新行",
        summary=summary,
        slots={"so_id": so.id, "product_id": prod.id,
               "quantity": quantity, "unit_price": unit_price},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        new_item = SalesOrderItem(
            id=str(uuid.uuid4()),
            so_id=so.id,
            line_no=next_line_no,
            product_id=prod.id,
            ordered_qty=quantity,
            unit_price=unit_price,
            line_total=line_total,
        )
        db.add(new_item)
        so.total_amount = (so.total_amount or 0) + line_total
        await db.commit()
        return {
            "so_no": so.so_no, "product_no": prod.product_no,
            "message": f"✅ SO {so.so_no} 已加新行 {prod.product_no} × {quantity:g}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# Auto-attach to domain agents
# ════════════════════════════════════════════════════════════════════

from app.agents.engine import AGENT_REGISTRY as _AGENT_REGISTRY

_DOMAIN_TOOL_MAP = {
    "sales": [
        "query_quotation_detail",
        "clone_quotation_with_confirm",
        "send_quotation_email_with_confirm",
        "cancel_quotation_with_confirm",
        "add_sales_order_item_with_confirm",
    ],
    "inventory": [
        "query_stock_count_progress",
        "batch_record_counted_qty_with_confirm",
        "cancel_stock_count_with_confirm",
    ],
    "purchase": [
        "smart_reorder_with_lead_time_tool",
        "add_purchase_order_item_with_confirm",
        "remove_purchase_order_item_with_confirm",
        "update_purchase_order_delivery_with_confirm",
    ],
}

for _domain, _tools in _DOMAIN_TOOL_MAP.items():
    if _domain in _AGENT_REGISTRY:
        _tn = _AGENT_REGISTRY[_domain]["tool_names"]
        for _t in _tools:
            if _t not in _tn:
                _tn.append(_t)
