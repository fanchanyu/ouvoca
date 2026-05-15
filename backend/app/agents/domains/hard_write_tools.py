"""Hard-write tools — 對話式 CRUD 的「寫入端」。

設計原則（v3.1）：
  1. 所有 hard-write 必出 ConfirmCard（人類點確認才執行）
  2. ConfirmCard 內含 summary（人類可讀）+ slots（執行參數，audit）
  3. Tool 自己負責 lookup（如 supplier 關鍵字 → supplier_id）讓 LLM 不用知 UUID
  4. Tool 不直接呼叫 service；包成 executor closure 等 ConfirmCard 確認

這 3 個 tool 代表 3 種 hard-write 樣板：
  - CREATE：create_purchase_order_with_confirm
  - 狀態轉換：release_work_order_with_confirm
  - 欄位更新：update_sales_order_delivery_with_confirm

未來其它 hard-write tool 用同樣樣板（每個 ~30 分鐘 copy-paste-modify）。
"""
from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import select

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.crm_sales import SalesOrder
from app.models.inventory import Part
from app.models.production import ProductionOrder
from app.models.purchase import Supplier


# ============================================================
# Tool 1: create_purchase_order_with_confirm
# ============================================================

@register_tool(
    name="create_purchase_order_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "建立採購單。輸入供應商、品項清單、預期交期。"
        "AI 會出 ConfirmCard 給使用者確認，使用者點「確認」後才真寫入。"
        "範例：「跟長江廠下 100 個 M6 螺絲，交期 5/20」"
    ),
    slots=[
        Slot("supplier_keyword", "string", required=True,
             description="供應商名稱或編號（如「長江」或「SUP-001」）"),
        Slot("items", "array", required=True,
             description=(
                 '品項清單。每筆可用以下任一格式：\n'
                 '  • {"part_id": "uuid...", "ordered_qty": 100, "unit_price": 5}\n'
                 '  • {"part_no": "M6-BOLT-20", "ordered_qty": 100, "unit_price": 5}\n'
                 '  • {"part_keyword": "M6 螺絲", "ordered_qty": 100, "unit_price": 5}\n'
                 'AI 會自動把 part_no / part_keyword lookup 成 part_id。'
                 'unit_price 可省略；省略時用 Part.unit_cost 預設。'
             )),
        Slot("expected_delivery_date", "string", required=True,
             description="預期交期 YYYY-MM-DD"),
        Slot("remark", "string", required=False, description="備註"),
    ],
    required_permission="purchase.po.create",
)
async def _create_po_with_confirm(
    db, user,
    supplier_keyword: str,
    items: list[dict],
    expected_delivery_date: str,
    remark: str = "",
):
    # 1. Lookup supplier
    supplier = await _find_supplier(db, supplier_keyword)
    if supplier is None:
        return {
            "error": f"找不到供應商「{supplier_keyword}」",
            "hint": "請先用 query_supplier 查可用清單。",
        }

    # 2. Resolve + validate items — 支援 part_id / part_no / part_keyword 3 種輸入
    if not items:
        return {"error": "items 不能為空。至少需要 1 項。"}
    total_amount = 0.0
    item_lines: list[str] = []
    resolved_items: list[dict] = []
    for raw in items:
        part = await _resolve_part(db, raw)
        if isinstance(part, dict) and "error" in part:
            # 多筆同名要求人類消歧 — 回 error 給 LLM 反問
            return part
        if part is None:
            kw = raw.get("part_no") or raw.get("part_keyword") or raw.get("part_id") or "?"
            return {
                "error": f"找不到料件「{kw}」",
                "hint": "請先用 query_inventory 確認料號。",
            }
        qty = float(raw.get("ordered_qty", 0))
        unit_price = float(raw.get("unit_price") or part.unit_cost or 0)
        if qty <= 0:
            return {"error": f"無效的數量: {qty}", "part_no": part.part_no}
        if unit_price <= 0:
            return {
                "error": f"無效的單價: {unit_price}（料件 {part.part_no} 也沒設 unit_cost）",
                "hint": "請在 items 中傳 unit_price，或先設定 Part.unit_cost。",
            }
        line_total = qty * unit_price
        total_amount += line_total
        item_lines.append(
            f"  • {part.part_no} {part.name} × {qty:g} @ ${unit_price:g} = ${line_total:,.0f}"
        )
        resolved_items.append({
            "part_id": part.id,
            "ordered_qty": qty,
            "unit_price": unit_price,
        })
    # 取代原 items 為已解析版本（給 service 用 — 只含 PurchaseOrderItem 認得的欄位）
    items = resolved_items

    # 3. Build summary（人類可讀）
    summary = [
        f"供應商：{supplier.name}（{supplier.code}）",
        f"品項數：{len(items)} 項",
        *item_lines,
        f"總金額：${total_amount:,.0f}",
        f"預期交期：{expected_delivery_date}",
    ]
    if remark:
        summary.append(f"備註：{remark}")

    # 4. Build ConfirmCard
    card = make_card(
        tool_name="create_purchase_order_with_confirm",
        title="確認建立採購單",
        summary=summary,
        slots={
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "items": items,
            "expected_delivery_date": expected_delivery_date,
            "remark": remark,
            "total_amount": total_amount,
        },
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    # 5. Build executor closure — 確認時呼叫
    async def execute():
        from app.services.purchase import create_purchase_order
        from datetime import date
        # 把 expected_delivery_date 字串轉 date 物件
        try:
            edd = date.fromisoformat(expected_delivery_date)
        except Exception:
            edd = None
        po = await create_purchase_order(db, {
            "supplier_id": supplier.id,
            "expected_delivery_date": edd,
            "remark": remark,
            "items": items,
        }, user=user)
        return {
            "po_no": po.po_no,
            "id": po.id,
            "total_amount": float(po.total_amount or 0),
            "status": po.status,
            "message": f"✅ 採購單 {po.po_no} 已建立，總金額 ${po.total_amount:,.0f}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ============================================================
# Tool 2: release_work_order_with_confirm
# ============================================================

@register_tool(
    name="release_work_order_with_confirm",
    domain="production",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "釋放生產工單（draft → released）。會檢查 BOM 是否完整。"
        "AI 會出 ConfirmCard 給使用者確認，確認後才執行。"
        "範例：「釋放工單 WO-20260514-001」"
    ),
    slots=[
        Slot("wo_no", "string", required=True, description="工單號（如 WO-20260514-001）"),
    ],
    required_permission="production.work_order.update",
)
async def _release_wo_with_confirm(db, user, wo_no: str):
    wo = (await db.execute(
        select(ProductionOrder).where(ProductionOrder.wo_no == wo_no)
    )).scalar_one_or_none()
    if wo is None:
        return {"error": f"找不到工單「{wo_no}」"}
    if wo.status != "draft":
        return {
            "error": f"工單狀態為 {wo.status!r}，只有 draft 狀態可釋放",
            "wo_no": wo_no,
        }

    summary = [
        f"工單號：{wo.wo_no}",
        f"產品 ID：{wo.product_id}",
        f"訂單量：{wo.ordered_qty:g}",
        f"優先級：{wo.priority}",
        f"狀態變更：draft → released",
    ]

    card = make_card(
        tool_name="release_work_order_with_confirm",
        title="確認釋放工單",
        summary=summary,
        slots={"wo_id": wo.id, "wo_no": wo.wo_no},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.production import release_production_order
        released = await release_production_order(db, wo.id, user=user)
        return {
            "wo_no": released.wo_no,
            "id": released.id,
            "status": released.status,
            "released_by": released.released_by,
            "message": f"✅ 工單 {released.wo_no} 已釋放生產",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ============================================================
# Tool 3: update_sales_order_delivery_with_confirm
# ============================================================

@register_tool(
    name="update_sales_order_delivery_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "修改銷售訂單的預期交期。"
        "AI 會出 ConfirmCard 給使用者確認，確認後才執行。"
        "範例：「把 SO-20260514-002 的交期改成 2026-05-22」"
    ),
    slots=[
        Slot("so_no", "string", required=True, description="銷售訂單號"),
        Slot("new_delivery_date", "string", required=True,
             description="新預期交期 YYYY-MM-DD"),
        Slot("reason", "string", required=False, description="變更原因"),
    ],
    required_permission="sales.order.update",
)
async def _update_so_delivery_with_confirm(
    db, user,
    so_no: str, new_delivery_date: str, reason: str = "",
):
    so = (await db.execute(
        select(SalesOrder).where(SalesOrder.so_no == so_no)
    )).scalar_one_or_none()
    if so is None:
        return {"error": f"找不到銷售訂單「{so_no}」"}
    if so.status in ("shipped", "cancelled"):
        return {
            "error": f"訂單狀態為 {so.status!r}，無法修改交期",
            "so_no": so_no,
        }

    summary = [
        f"訂單號：{so.so_no}",
        f"客戶 ID：{so.customer_id}",
        f"目前交期：{so.requested_delivery_date}",
        f"新交期：{new_delivery_date}",
    ]
    if reason:
        summary.append(f"變更原因：{reason}")

    card = make_card(
        tool_name="update_sales_order_delivery_with_confirm",
        title="確認修改銷售訂單交期",
        summary=summary,
        slots={
            "so_id": so.id, "so_no": so.so_no,
            "old_delivery_date": str(so.requested_delivery_date),
            "new_delivery_date": new_delivery_date,
            "reason": reason,
        },
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from datetime import date
        try:
            edd = date.fromisoformat(new_delivery_date)
        except Exception:
            return {"error": f"無效的日期格式: {new_delivery_date}"}
        # 直接 update（簡單欄位，不走 service）
        so_fresh = (await db.execute(
            select(SalesOrder).where(SalesOrder.id == so.id)
        )).scalar_one()
        old = so_fresh.requested_delivery_date
        so_fresh.requested_delivery_date = edd
        await db.commit()
        return {
            "so_no": so_fresh.so_no,
            "id": so_fresh.id,
            "old_delivery_date": str(old),
            "new_delivery_date": new_delivery_date,
            "message": f"✅ 訂單 {so_fresh.so_no} 交期已改為 {new_delivery_date}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ============================================================
# Helpers
# ============================================================

async def _find_supplier(db, keyword: str):
    """先試 exact code 比對，沒中再試 name LIKE。"""
    # try code exact
    s = (await db.execute(
        select(Supplier).where(Supplier.code == keyword)
    )).scalar_one_or_none()
    if s is not None:
        return s
    # try name LIKE
    like = f"%{keyword}%"
    s = (await db.execute(
        select(Supplier).where(Supplier.name.like(like)).limit(1)
    )).scalar_one_or_none()
    return s


async def _resolve_part(db, raw: dict):
    """把 items 中的單一 raw 解析成 Part 物件。

    優先順序：part_id > part_no > part_keyword（name LIKE）
    回值：
      - Part 物件：找到 1 個
      - {"error": ...}：找到多個（需要人類消歧）
      - None：找不到
    """
    # part_id 直接命中
    if pid := raw.get("part_id"):
        return (await db.execute(
            select(Part).where(Part.id == pid)
        )).scalar_one_or_none()
    # part_no 精確比對
    if pno := raw.get("part_no"):
        return (await db.execute(
            select(Part).where(Part.part_no == pno)
        )).scalar_one_or_none()
    # part_keyword 模糊比對（name + part_no LIKE）
    if kw := raw.get("part_keyword"):
        like = f"%{kw}%"
        rows = (await db.execute(
            select(Part)
            .where((Part.name.like(like)) | (Part.part_no.like(like)))
            .limit(5)
        )).scalars().all()
        if len(rows) == 0:
            return None
        if len(rows) == 1:
            return rows[0]
        # 多個 — 回 error 列出選項給 LLM 反問使用者
        return {
            "error": f"關鍵字「{kw}」找到 {len(rows)} 個料件，請指明 part_no：",
            "candidates": [
                {"part_no": p.part_no, "name": p.name, "category": p.category}
                for p in rows
            ],
        }
    return None


# ============================================================
# Agent 註冊（共用 hard-write agent）
# ============================================================

#
# Note：v3.2.1 起，hard-write tools 不再放在獨立的 HardWriteAgent，
# 而是各自接到對應的 domain agent（PurchaseAgent / ProductionAgent / SalesAgent），
# 因為 intent classifier 走關鍵字（「下單」→ purchase），不會路由到 hard_write。
# 詳見 purchase_tools.py / production_tools.py / sales_tools.py 各自的 register_agent。
