"""
CRUD Completion Tools — 補完最常被問但 LLM 答不出來的硬寫操作  (v3.31)
═══════════════════════════════════════════════════════════════════════

審計 v3.25.9-v3.30 之 LLM tool 覆蓋發現缺口：
  ❌ 「取消這張 PO」  → service 有但無 LLM tool
  ❌ 「收貨入庫」      → service 有但無 LLM tool
  ❌ 「取消這張 SO」  → service 有但無 LLM tool
  ❌ 「出貨」          → service 有但無 LLM tool
  ❌ 「取消這張工單」 → service 有但無 LLM tool
  ❌ 「QC 合格 / 不合格」→ service 有但無 LLM tool
  ❌ 「過帳這筆 JE」  → service 有但無 LLM tool
  ❌ 「揀貨完成」      → service 有但無 LLM tool

本檔補完此 8 個高頻 hard-write，每個都用同一模板：
  1. 自然語言查找實體（如 PO-20260520-001 → uuid）
  2. 業務規則檢查（如「狀態為 received 不可取消」）
  3. build ConfirmCard 含 summary + slots
  4. stash executor closure 等使用者確認

──────────────────────────────────────────────────────────────────────
LEGAL / 法律說明
──────────────────────────────────────────────────────────────────────
這些 hard-write 操作對企業業務有直接財務 / 法律影響：

  • **取消 PO / SO** 可能涉及對供應商 / 客戶之契約違約
  • **收貨** 觸發應付帳款入帳
  • **出貨** 觸發應收帳款入帳
  • **QC 結果** 影響產品交付 / 召回判定
  • **JE 過帳** 影響財務報表

凡 LLM 用此類 tool，**ConfirmCard 為法律意義之確認點**：
  - 使用者按「確認」前應檢視 ConfirmCard 上之具體 slot 值
  - 不可僅依 LLM 之 summary 自動執行
  - 重大金額 / 重大客戶 / 重大供應商交易應額外有主管覆核流程

於適用法律所允許之最大範圍內，Ouvoca 對於 LLM 抽錯 slot 或客戶
誤按確認所衍生之契約 / 財務 / 稅務後果，不承擔責任。詳見
docs/CONVERSATIONAL_PLANNING_DESIGN_ZH.md §6 累積適用之聲明。

本模組所有 hard-write 嚴守 ConfirmCard 流程（不可繞過）。
"""
from __future__ import annotations

from datetime import datetime, UTC
from sqlalchemy import select

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.purchase import PurchaseOrder, Supplier
from app.models.crm_sales import SalesOrder, Customer
from app.models.production import ProductionOrder
from app.models.quality import InspectionOrder
from app.models.accounting import JournalEntry
from app.models.warehouse import PickTask


# ════════════════════════════════════════════════════════════════════
# 1. cancel_purchase_order_with_confirm
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="cancel_purchase_order_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "取消採購單（draft / approved 狀態才能取消，已收貨不可）。"
        "AI 出 ConfirmCard 給使用者確認後才執行。"
        "範例：「取消 PO-20260520-001」「把長江廠那張單作廢」"
    ),
    slots=[
        Slot("po_no", "string", required=True, description="採購單號"),
        Slot("reason", "string", required=False, description="取消原因（審計用）"),
    ],
    required_permission="purchase.order.cancel",
)
async def _cancel_po_with_confirm(db, user, po_no: str, reason: str = ""):
    po = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.po_no == po_no)
    )).scalar_one_or_none()
    if po is None:
        return {"error": f"找不到採購單「{po_no}」"}
    if po.status in ("received", "cancelled", "closed"):
        return {
            "error": f"採購單狀態 {po.status!r}，不可取消",
            "hint": "已收貨 / 已結案之單據需走逆轉流程而非取消",
        }

    # Load supplier name for display
    supplier_name = ""
    if po.supplier_id:
        sup = (await db.execute(
            select(Supplier).where(Supplier.id == po.supplier_id)
        )).scalar_one_or_none()
        supplier_name = sup.name if sup else "(未知)"

    summary = [
        f"📋 採購單號：{po.po_no}",
        f"🏭 供應商：{supplier_name}",
        f"💰 總額：${po.total_amount or 0:,.0f}",
        f"📊 狀態：{po.status} → cancelled",
        f"📝 取消原因：{reason or '(未填)'}",
        "",
        "⚠️ 取消後不可逆 — 已通知供應商之單據請另行通知撤回",
    ]
    card = make_card(
        tool_name="cancel_purchase_order_with_confirm",
        title="🚫 確認取消採購單",
        summary=summary,
        slots={"po_id": po.id, "po_no": po.po_no, "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.purchase import cancel_purchase_order
        cancelled = await cancel_purchase_order(db, po.id, user=user, reason=reason)
        return {
            "po_no": cancelled.po_no, "status": cancelled.status,
            "message": f"✅ 採購單 {cancelled.po_no} 已取消",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 2. receive_purchase_order_with_confirm
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="receive_purchase_order_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "PO 收貨入庫：將採購單之品項數量入庫存。"
        "出 ConfirmCard 列出每項收多少。範例：「收貨 PO-20260520-001」"
    ),
    slots=[
        Slot("po_no", "string", required=True, description="採購單號"),
        Slot("received_qty_map", "object", required=False,
             description='指定每項實際收到數量，格式 {"item_id": qty}；'
                         '不填則依 PO 訂購量全部入庫'),
    ],
    required_permission="purchase.order.receive",
)
async def _receive_po_with_confirm(db, user, po_no: str, received_qty_map: dict = None):
    from sqlalchemy.orm import selectinload
    po = (await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.po_no == po_no)
    )).scalar_one_or_none()
    if po is None:
        return {"error": f"找不到採購單「{po_no}」"}
    if po.status in ("received", "cancelled", "closed"):
        return {"error": f"採購單狀態 {po.status!r}，不可再收貨"}
    if not po.items:
        return {"error": "採購單無品項可收貨"}

    summary = [
        f"📦 採購單：{po.po_no}",
        f"📊 狀態：{po.status} → received",
        "",
        "**收貨明細**：",
    ]
    total_value = 0.0
    for item in po.items:
        actual_qty = (received_qty_map or {}).get(item.id, item.ordered_qty)
        total_value += actual_qty * (item.unit_price or 0)
        summary.append(
            f"  • {item.part_id[:8]}... × {actual_qty:g}（@ ${item.unit_price or 0:,.0f}）"
        )
    summary.append(f"💰 入庫總值：${total_value:,.0f}")
    summary.append("⚠️ 收貨即觸發應付帳款入帳，請確認數量與品質")

    card = make_card(
        tool_name="receive_purchase_order_with_confirm",
        title="📥 確認 PO 收貨入庫",
        summary=summary,
        slots={"po_id": po.id, "po_no": po.po_no,
               "received_qty_map": received_qty_map or {}},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.purchase import receive_purchase_order
        # Convert dict[item_id → qty] to list[{"item_id", "received_qty"}] (service signature)
        receipts = (
            [{"item_id": k, "received_qty": v} for k, v in (received_qty_map or {}).items()]
            if received_qty_map
            else [{"item_id": item.id, "received_qty": item.ordered_qty} for item in po.items]
        )
        result = await receive_purchase_order(db, po.id, receipts=receipts, user=user or {})
        return {"po_no": po.po_no, "message": "✅ 收貨完成，庫存已更新"}

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 3. cancel_sales_order_with_confirm
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="cancel_sales_order_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "取消銷售單（draft / confirmed 狀態才能取消，已出貨不可）。"
        "範例：「取消 SO-20260520-001」「客戶撤單」"
    ),
    slots=[
        Slot("so_no", "string", required=True, description="銷售單號"),
        Slot("reason", "string", required=False, description="取消原因"),
    ],
    required_permission="sales.order.cancel",
)
async def _cancel_so_with_confirm(db, user, so_no: str, reason: str = ""):
    so = (await db.execute(
        select(SalesOrder).where(SalesOrder.so_no == so_no)
    )).scalar_one_or_none()
    if so is None:
        return {"error": f"找不到銷售單「{so_no}」"}
    if so.status in ("shipped", "cancelled", "closed"):
        return {"error": f"銷售單狀態 {so.status!r}，不可取消"}

    customer_name = ""
    if so.customer_id:
        cu = (await db.execute(
            select(Customer).where(Customer.id == so.customer_id)
        )).scalar_one_or_none()
        customer_name = cu.name if cu else "(未知)"

    summary = [
        f"📋 銷售單：{so.so_no}",
        f"👤 客戶：{customer_name}",
        f"💰 總額：${so.total_amount or 0:,.0f}",
        f"📊 狀態：{so.status} → cancelled",
        f"📝 取消原因：{reason or '(未填)'}",
        "",
        "⚠️ 若已通知客戶生產 / 出貨，請另行通知撤回",
    ]
    card = make_card(
        tool_name="cancel_sales_order_with_confirm",
        title="🚫 確認取消銷售單",
        summary=summary,
        slots={"so_id": so.id, "so_no": so.so_no, "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.sales import cancel_sales_order
        cancelled = await cancel_sales_order(db, so.id, user=user, reason=reason)
        return {
            "so_no": cancelled.so_no, "status": cancelled.status,
            "message": f"✅ 銷售單 {cancelled.so_no} 已取消",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 4. ship_sales_order_with_confirm
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="ship_sales_order_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "銷售單出貨：扣減成品庫存、產生出貨單、觸發應收帳款。"
        "範例：「出貨 SO-20260520-001」「把這張單發貨」"
    ),
    slots=[
        Slot("so_no", "string", required=True, description="銷售單號"),
    ],
    required_permission="sales.order.ship",
)
async def _ship_so_with_confirm(db, user, so_no: str):
    so = (await db.execute(
        select(SalesOrder).where(SalesOrder.so_no == so_no)
    )).scalar_one_or_none()
    if so is None:
        return {"error": f"找不到銷售單「{so_no}」"}
    if so.status != "confirmed":
        return {"error": f"狀態為 {so.status!r}，須先 confirmed 才能出貨"}

    customer_name = "(未知)"
    if so.customer_id:
        cu = (await db.execute(
            select(Customer).where(Customer.id == so.customer_id)
        )).scalar_one_or_none()
        if cu:
            customer_name = cu.name

    summary = [
        f"📋 銷售單：{so.so_no}",
        f"👤 客戶：{customer_name}",
        f"💰 總額：${so.total_amount or 0:,.0f}",
        f"📊 狀態：{so.status} → shipped",
        "",
        "📌 v3.55：確認後將自動建立：",
        "  1. 出貨單 (DeliveryNote)",
        "  2. 電子發票（若客戶有統編）",
        "  3. 會計傳票 (DR AR / CR 銷售收入 / CR 銷項稅額)",
        "  4. 應收帳款 (AR) 入帳",
        "  5. 扣減成品庫存 + 反寫 SO.delivery_note_no/invoice_no/ar_id",
        "",
        "⚠️ 出貨後不可逆 — 全鏈原子化，失敗則全部 rollback",
    ]
    card = make_card(
        tool_name="ship_sales_order_with_confirm",
        title="🚚 確認出貨（O2C 全鏈）",
        summary=summary,
        slots={"so_id": so.id, "so_no": so.so_no},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.sales import ship_sales_order
        result = await ship_sales_order(
            db, so.id, user=user,
            auto_invoice=True, auto_journal=True,
        )
        # v3.55: result is dict with delivery_note / invoice / journal_entry / ar
        dn = (result or {}).get("delivery_note") or {}
        inv = (result or {}).get("invoice") or {}
        je = (result or {}).get("journal_entry") or {}
        msg_parts = [f"✅ 銷售單 {so.so_no} 已出貨"]
        if dn.get("dn_no"):
            msg_parts.append(f"出貨單：{dn['dn_no']}")
        if inv.get("invoice_no"):
            msg_parts.append(f"發票：{inv['invoice_no']}")
        if je.get("entry_no"):
            msg_parts.append(f"傳票：{je['entry_no']}")
        return {
            "so_no": so.so_no, "status": "shipped",
            "delivery_note": dn,
            "invoice": inv or None,
            "journal_entry": je or None,
            "ar": (result or {}).get("ar"),
            "total_amount": (result or {}).get("total_amount"),
            "message": " / ".join(msg_parts),
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 5. cancel_production_order_with_confirm
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="cancel_production_order_with_confirm",
    domain="production",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "取消生產工單（completed / cancelled 狀態不可）。"
        "範例：「取消工單 WO-20260520-001」「砍掉這張單」"
    ),
    slots=[
        Slot("wo_no", "string", required=True, description="工單號"),
        Slot("reason", "string", required=False, description="取消原因"),
    ],
    required_permission="production.work_order.cancel",
)
async def _cancel_wo_with_confirm(db, user, wo_no: str, reason: str = ""):
    wo = (await db.execute(
        select(ProductionOrder).where(ProductionOrder.wo_no == wo_no)
    )).scalar_one_or_none()
    if wo is None:
        return {"error": f"找不到工單「{wo_no}」"}
    if wo.status in ("completed", "cancelled"):
        return {"error": f"工單狀態 {wo.status!r}，不可取消"}

    summary = [
        f"📋 工單：{wo.wo_no}",
        f"📦 產品 ID：{wo.product_id[:8] if wo.product_id else 'N/A'}...",
        f"📊 訂單量：{wo.ordered_qty:g}",
        f"✅ 已完成：{wo.completed_qty:g}",
        f"🔴 狀態：{wo.status} → cancelled",
        f"📝 取消原因：{reason or '(未填)'}",
        "",
        "⚠️ 已完工部分仍計入產量；未完成部分將釋放保留之物料",
    ]
    card = make_card(
        tool_name="cancel_production_order_with_confirm",
        title="🚫 確認取消工單",
        summary=summary,
        slots={"wo_id": wo.id, "wo_no": wo.wo_no, "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.production import cancel_production_order
        cancelled = await cancel_production_order(db, wo.id, user=user or {}, reason=reason)
        return {
            "wo_no": cancelled.wo_no, "status": cancelled.status,
            "message": f"✅ 工單 {cancelled.wo_no} 已取消",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 6. complete_inspection_with_confirm
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="complete_inspection_with_confirm",
    domain="quality",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "完成 QC 檢驗：標示合格 / 不合格 + 數量。"
        "若 reject 數量 > 0 會自動觸發 NonConformance 紀錄。"
        "範例：「QC INS-20260520-001 合格 100 個」「不合格 5 個」"
    ),
    slots=[
        Slot("inspection_no", "string", required=True, description="檢驗單號"),
        Slot("accepted_qty", "number", required=True, description="合格數量"),
        Slot("rejected_qty", "number", required=False, description="不合格數量（預設 0）"),
        Slot("notes", "string", required=False, description="檢驗備註"),
    ],
    required_permission="quality.inspection.complete",
)
async def _complete_inspection_with_confirm(
    db, user, inspection_no: str,
    accepted_qty: float, rejected_qty: float = 0, notes: str = "",
):
    insp = (await db.execute(
        select(InspectionOrder).where(InspectionOrder.inspection_no == inspection_no)
    )).scalar_one_or_none()
    if insp is None:
        return {"error": f"找不到檢驗單「{inspection_no}」"}
    if insp.status in ("completed", "cancelled"):
        return {"error": f"檢驗單狀態 {insp.status!r}，不可再完成"}

    pass_rate = accepted_qty / (accepted_qty + rejected_qty) if (accepted_qty + rejected_qty) > 0 else 0
    icon = "✅" if rejected_qty == 0 else "⚠️"

    summary = [
        f"{icon} 檢驗單：{insp.inspection_no}",
        f"✅ 合格：{accepted_qty:g}",
        f"❌ 不合格：{rejected_qty:g}",
        f"📊 良率：{pass_rate:.1%}",
        f"📝 備註：{notes or '(無)'}",
        "",
        f"{'❗ 不合格 > 0 將自動產生 NCR' if rejected_qty > 0 else '✅ 全數合格'}",
    ]
    card = make_card(
        tool_name="complete_inspection_with_confirm",
        title=f"{icon} 確認 QC 結果",
        summary=summary,
        slots={"inspection_id": insp.id, "inspection_no": insp.inspection_no,
               "accepted_qty": accepted_qty, "rejected_qty": rejected_qty,
               "notes": notes},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.quality import complete_inspection
        # service does not take notes param; we keep notes in audit log via ConfirmCard slots
        result = await complete_inspection(
            db, insp.id,
            accepted_qty=accepted_qty,
            rejected_qty=rejected_qty,
            user=user or {},
        )
        return {
            "inspection_no": insp.inspection_no,
            "message": f"✅ 檢驗 {insp.inspection_no} 已完成（合格 {accepted_qty:g} / 不合格 {rejected_qty:g}）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 7. post_journal_entry_with_confirm
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="post_journal_entry_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "過帳會計傳票（draft → posted），鎖定不可改。"
        "範例：「過帳 JE-20260520-001」「把這筆傳票過帳」"
    ),
    slots=[
        Slot("entry_no", "string", required=True, description="傳票號"),
    ],
    required_permission="accounting.journal.post",
)
async def _post_journal_with_confirm(db, user, entry_no: str):
    je = (await db.execute(
        select(JournalEntry).where(JournalEntry.entry_no == entry_no)
    )).scalar_one_or_none()
    if je is None:
        return {"error": f"找不到傳票「{entry_no}」"}
    if je.status == "posted":
        return {"error": f"傳票 {entry_no} 已過帳，不可重複"}

    summary = [
        f"📒 傳票號：{je.entry_no}",
        f"📅 日期：{je.entry_date}",
        f"📊 狀態：{je.status} → posted（**鎖定不可改**）",
        f"💰 借方總額：${je.total_debit or 0:,.0f}",
        f"💰 貸方總額：${je.total_credit or 0:,.0f}",
        f"📝 摘要：{je.description or '(無)'}",
        "",
        "⚠️ 過帳後不可逆（需走沖正傳票）— 請確認借貸平衡 + 科目正確",
    ]
    card = make_card(
        tool_name="post_journal_entry_with_confirm",
        title="📒 確認過帳傳票",
        summary=summary,
        slots={"entry_id": je.id, "entry_no": je.entry_no},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.accounting import post_journal
        posted = await post_journal(db, je.id, user=user or {})
        return {
            "entry_no": posted.entry_no, "status": posted.status,
            "message": f"✅ 傳票 {posted.entry_no} 已過帳",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 8. complete_pick_task_with_confirm
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="complete_pick_task_with_confirm",
    domain="warehouse",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "倉儲揀貨完成：標示揀貨任務 done + 實際揀貨量。"
        "範例：「揀貨完成 PICK-20260520-001 揀了 50 個」"
    ),
    slots=[
        Slot("pick_no", "string", required=True, description="揀貨單號"),
        Slot("picked_qty", "number", required=True, description="實際揀貨數量"),
    ],
    required_permission="warehouse.pick.complete",
)
async def _complete_pick_with_confirm(db, user, pick_no: str, picked_qty: float):
    pick = (await db.execute(
        select(PickTask).where(PickTask.pick_no == pick_no)
    )).scalar_one_or_none()
    if pick is None:
        return {"error": f"找不到揀貨單「{pick_no}」"}
    if pick.status in ("completed", "cancelled"):
        return {"error": f"揀貨單狀態 {pick.status!r}，不可重複完成"}

    requested = pick.requested_qty or 0
    diff = picked_qty - requested
    diff_icon = "✅" if diff == 0 else ("⚠️" if abs(diff) <= requested * 0.05 else "❌")

    summary = [
        f"📦 揀貨單：{pick.pick_no}",
        f"📋 要求數量：{requested:g}",
        f"📥 實際揀貨：{picked_qty:g}",
        f"{diff_icon} 差異：{diff:+g}",
        f"📊 狀態：{pick.status} → completed",
        "",
        f"{'✅ 與要求一致' if diff == 0 else '⚠️ 有差異，請確認是否為短揀'}",
    ]
    card = make_card(
        tool_name="complete_pick_task_with_confirm",
        title="📦 確認揀貨完成",
        summary=summary,
        slots={"pick_id": pick.id, "pick_no": pick.pick_no, "picked_qty": picked_qty},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.warehouse import complete_pick
        completed = await complete_pick(db, pick.id, picked_qty=picked_qty, user=user or {})
        return {
            "pick_no": completed.pick_no, "status": completed.status,
            "message": f"✅ 揀貨 {completed.pick_no} 已完成（揀了 {picked_qty:g}）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# Auto-add these 8 tools to relevant existing domain agents
# ════════════════════════════════════════════════════════════════════

from app.agents.engine import AGENT_REGISTRY as _AGENT_REGISTRY

_DOMAIN_TOOL_MAP = {
    "purchase": [
        "cancel_purchase_order_with_confirm",
        "receive_purchase_order_with_confirm",
    ],
    "sales": [
        "cancel_sales_order_with_confirm",
        "ship_sales_order_with_confirm",
    ],
    "production": [
        "cancel_production_order_with_confirm",
    ],
    "quality": [
        "complete_inspection_with_confirm",
    ],
    "accounting": [
        "post_journal_entry_with_confirm",
    ],
    "warehouse": [
        "complete_pick_task_with_confirm",
    ],
}

for _domain, _tools in _DOMAIN_TOOL_MAP.items():
    if _domain in _AGENT_REGISTRY:
        _tn = _AGENT_REGISTRY[_domain]["tool_names"]
        for _t in _tools:
            if _t not in _tn:
                _tn.append(_t)
