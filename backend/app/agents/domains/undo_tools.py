"""Undo tools — 90 秒撤銷最近的 hard-write 操作（v3.3 對話智能 G-204）。

設計：
  - 使用者說「取消剛剛那筆」「撤銷剛建的採購單」
  - AI 查最近 90 秒內由該使用者建立的 hard-write 對象
  - 出反向 ConfirmCard（描述要回滾什麼）
  - 使用者點確認 → 真執行反向操作（cancel / revert）

當前實作（PoC）：
  - 只支援 PurchaseOrder（demo moment 1 對應）
  - Phase 2 擴充 SalesOrder / WorkOrder / 通用 audit-based undo
"""
from __future__ import annotations

from datetime import datetime, timedelta, UTC

from sqlalchemy import select

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.purchase import PurchaseOrder


UNDO_WINDOW_SECONDS = 90


@register_tool(
    name="undo_last_purchase_order",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        f"撤銷該使用者在最近 {UNDO_WINDOW_SECONDS} 秒內建立的採購單。"
        "範例：「取消剛剛那筆採購單」「撤銷剛建的 PO」。"
        "會出反向 ConfirmCard 給使用者確認，確認後將 PO 狀態改成 cancelled。"
    ),
    slots=[],
    required_permission="purchase.po.update",
)
async def _undo_last_po(db, user):
    employee_id = (user or {}).get("employee_id")
    if not employee_id:
        return {
            "error": "Undo 需要登入身分才能找到「您剛剛」的操作。",
            "hint": "請先登入。",
        }

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=UNDO_WINDOW_SECONDS)

    # 找該使用者最近建的、還沒 cancel 的 PO
    po = (await db.execute(
        select(PurchaseOrder)
        .where(
            PurchaseOrder.created_by == employee_id,
            PurchaseOrder.created_at >= cutoff,
            PurchaseOrder.status != "cancelled",
        )
        .order_by(PurchaseOrder.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if po is None:
        return {
            "error": f"找不到 {UNDO_WINDOW_SECONDS} 秒內可撤銷的採購單",
            "hint": "如果操作超過 90 秒，請改用「查詢該採購單 → 改狀態為 cancelled」。",
        }

    age_seconds = int((datetime.now(UTC).replace(tzinfo=None) - po.created_at).total_seconds())
    remaining = UNDO_WINDOW_SECONDS - age_seconds

    summary = [
        f"將撤銷採購單：{po.po_no}",
        f"建立於：{po.created_at}（{age_seconds} 秒前）",
        f"金額：${po.total_amount:,.0f}",
        f"狀態：{po.status} → cancelled",
        f"剩餘可撤銷時間：{remaining} 秒",
    ]

    card = make_card(
        tool_name="undo_last_purchase_order",
        title=f"確認撤銷剛建的採購單 {po.po_no}",
        summary=summary,
        slots={
            "po_id": po.id, "po_no": po.po_no,
            "original_status": po.status,
            "age_seconds": age_seconds,
        },
        risk_tier="hard-write",
        ttl_seconds=min(60, remaining),  # 撤銷的 confirm 卡 TTL 不超過剩餘可撤銷時間
        created_by=employee_id,
    )

    async def execute():
        po_fresh = (await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == po.id)
        )).scalar_one()
        if po_fresh.status == "cancelled":
            return {
                "status": "already_cancelled",
                "po_no": po_fresh.po_no,
                "message": f"⚠️ {po_fresh.po_no} 已經是 cancelled 狀態",
            }
        original = po_fresh.status
        po_fresh.status = "cancelled"
        po_fresh.remark = (po_fresh.remark or "") + f"\n[Undo] 由 {employee_id} 在建立 {age_seconds}s 後撤銷"
        await db.commit()
        return {
            "po_no": po_fresh.po_no,
            "id": po_fresh.id,
            "previous_status": original,
            "new_status": "cancelled",
            "message": f"🔄 採購單 {po_fresh.po_no} 已撤銷（原狀態 {original}）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# 把 undo tool 加進 PurchaseAgent（同 domain）
from app.agents.engine import AGENT_REGISTRY

if "purchase" in AGENT_REGISTRY:
    tn = AGENT_REGISTRY["purchase"]["tool_names"]
    if "undo_last_purchase_order" not in tn:
        tn.append("undo_last_purchase_order")
