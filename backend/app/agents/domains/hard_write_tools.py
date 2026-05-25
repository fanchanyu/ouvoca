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


# ============================================================
# v3.9 — Day A 8 個 hard-write tools（LLM 全 CRUD 補完）
# ============================================================
# 同樣 pattern：lookup → build summary → make_card → executor closure
# 接到 inventory / purchase / sales / production agent 的 tool_names

from app.models.inventory import Inventory, Part as _Part
from app.models.purchase import PurchaseOrder  # for approve_po
# 注意：Supplier / SalesOrder / ProductionOrder 已在檔案上方 import


# ------------------------------------------------------------
# Inventory: create_part / update_safety / add_transaction
# ------------------------------------------------------------

@register_tool(
    name="create_part_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "新增料件主檔（同時自動建空 Inventory 行）。"
        "範例：「新增料件 M6 螺絲，料號 M6-BOLT-20，類別 component，安全庫存 500」"
    ),
    slots=[
        Slot("part_no", "string", required=True, description="料號（如 M6-BOLT-20），全公司唯一"),
        Slot("name", "string", required=True, description="料件名稱"),
        Slot("category", "string", required=False,
             description="raw_material / semi_finished / component / consumable / packaging"),
        Slot("unit", "string", required=False, description="單位，預設 pcs"),
        Slot("safety_stock", "number", required=False, description="安全庫存"),
        Slot("unit_cost", "number", required=False, description="標準成本"),
    ],
    required_permission="inventory.part.create",
)
async def _create_part_with_confirm(
    db, user,
    part_no: str, name: str,
    category: str = "component", unit: str = "pcs",
    safety_stock: float = 0, unit_cost: float = 0,
):
    # 檢查 part_no 是否已存在
    from sqlalchemy import select as _select
    existing = (await db.execute(_select(_Part).where(_Part.part_no == part_no))).scalar_one_or_none()
    if existing is not None:
        return {"error": f"料號 {part_no!r} 已存在", "existing_id": existing.id}

    summary = [
        f"料號：{part_no}",
        f"名稱：{name}",
        f"類別：{category}",
        f"單位：{unit}",
    ]
    if safety_stock:
        summary.append(f"安全庫存：{safety_stock:g}")
    if unit_cost:
        summary.append(f"標準成本：${unit_cost:g}")

    card = make_card(
        tool_name="create_part_with_confirm",
        title="確認新增料件",
        summary=summary,
        slots={
            "part_no": part_no, "name": name, "category": category,
            "unit": unit, "safety_stock": safety_stock, "unit_cost": unit_cost,
        },
        created_by=(user or {}).get("employee_id"),
    )

    async def execute():
        from app.services.inventory import create_part
        p = await create_part(db, {
            "part_no": part_no, "name": name, "category": category,
            "unit": unit, "safety_stock": safety_stock, "unit_cost": unit_cost,
        })
        return {
            "part_no": p.part_no, "id": p.id, "name": p.name,
            "message": f"✅ 料件 {p.part_no}（{p.name}）已建立，並自動建立空庫存行",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="update_part_safety_stock_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "修改料件的安全庫存設定。"
        "範例：「把 M6-BOLT-20 的安全庫存改成 1000」"
    ),
    slots=[
        Slot("part_no", "string", required=True, description="料號"),
        Slot("new_safety_stock", "number", required=True, description="新安全庫存值"),
        Slot("reason", "string", required=False, description="變更原因"),
    ],
    required_permission="inventory.part.update",
)
async def _update_safety_stock_with_confirm(
    db, user, part_no: str, new_safety_stock: float, reason: str = "",
):
    from sqlalchemy import select as _select
    p = (await db.execute(_select(_Part).where(_Part.part_no == part_no))).scalar_one_or_none()
    if p is None:
        return {"error": f"找不到料號 {part_no!r}"}
    if new_safety_stock < 0:
        return {"error": f"安全庫存不能負數: {new_safety_stock}"}

    summary = [
        f"料號：{p.part_no}（{p.name}）",
        f"目前安全庫存：{p.safety_stock:g}",
        f"新安全庫存：{new_safety_stock:g}",
    ]
    if reason:
        summary.append(f"變更原因：{reason}")

    card = make_card(
        tool_name="update_part_safety_stock_with_confirm",
        title=f"確認修改 {p.part_no} 安全庫存",
        summary=summary,
        slots={
            "part_id": p.id, "part_no": p.part_no,
            "old_safety_stock": p.safety_stock,
            "new_safety_stock": new_safety_stock,
            "reason": reason,
        },
        created_by=(user or {}).get("employee_id"),
    )

    async def execute():
        from sqlalchemy import select as _select
        p_fresh = (await db.execute(_select(_Part).where(_Part.id == p.id))).scalar_one()
        old = p_fresh.safety_stock
        p_fresh.safety_stock = float(new_safety_stock)
        await db.commit()
        return {
            "part_no": p_fresh.part_no,
            "old_safety_stock": old,
            "new_safety_stock": new_safety_stock,
            "message": f"✅ {p_fresh.part_no} 安全庫存 {old:g} → {new_safety_stock:g}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="add_inventory_transaction_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "新增庫存交易（進料 / 出料 / 調整）。"
        "範例：「進料 M6-BOLT-20 +500」「M6 出料 100」「盤點調整 M6 +5」"
    ),
    slots=[
        Slot("part_no", "string", required=True, description="料號"),
        Slot("transaction_type", "string", required=True,
             description="inbound（進料）/ outbound（出料）/ adjustment_in / adjustment_out"),
        Slot("qty", "number", required=True, description="數量（正數）"),
        Slot("remark", "string", required=False, description="備註"),
    ],
    required_permission="inventory.transaction.create",
)
async def _add_inventory_txn_with_confirm(
    db, user, part_no: str, transaction_type: str, qty: float, remark: str = "",
):
    from sqlalchemy import select as _select
    from app.services.inventory import ALL_VALID_TXN_TYPES, VALID_OUTBOUND
    p = (await db.execute(_select(_Part).where(_Part.part_no == part_no))).scalar_one_or_none()
    if p is None:
        return {"error": f"找不到料號 {part_no!r}"}
    if transaction_type not in ALL_VALID_TXN_TYPES:
        return {
            "error": f"無效的交易類型 {transaction_type!r}",
            "valid": sorted(ALL_VALID_TXN_TYPES),
        }
    if qty <= 0:
        return {"error": f"數量必須大於 0: {qty}"}

    inv = (await db.execute(
        _select(Inventory).where(Inventory.part_id == p.id)
    )).scalar_one_or_none()
    current = inv.qty_available if inv else 0

    direction = "出庫" if transaction_type in VALID_OUTBOUND else "入庫"
    summary = [
        f"料號：{p.part_no}（{p.name}）",
        f"類型：{transaction_type}（{direction}）",
        f"數量：{qty:g} {p.unit}",
        f"目前可用：{current:g}",
    ]
    if transaction_type in VALID_OUTBOUND and current < qty:
        summary.append(f"⚠️ 注意：可用庫存 {current:g} < 出庫 {qty:g}，將會被擋")

    if remark:
        summary.append(f"備註：{remark}")

    card = make_card(
        tool_name="add_inventory_transaction_with_confirm",
        title=f"確認 {p.part_no} {direction} {qty:g}",
        summary=summary,
        slots={
            "part_id": p.id, "part_no": p.part_no,
            "transaction_type": transaction_type, "qty": qty, "remark": remark,
        },
        created_by=(user or {}).get("employee_id"),
    )

    async def execute():
        from app.services.inventory import add_inventory_transaction
        txn = await add_inventory_transaction(db, {
            "part_id": p.id, "transaction_type": transaction_type,
            "qty": float(qty), "remark": remark,
        }, user=user)
        # v3.53：service 已改不自行 commit；ConfirmCard 執行端負責 commit
        await db.commit()
        return {
            "txn_id": txn.id, "part_no": p.part_no,
            "transaction_type": transaction_type, "qty": qty,
            "message": f"✅ {p.part_no} {direction} {qty:g} {p.unit} 已記錄",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ------------------------------------------------------------
# Purchase: create_supplier / approve_po
# ------------------------------------------------------------

@register_tool(
    name="create_supplier_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "新增供應商主檔。"
        "範例：「新增供應商 大同電子 編號 SUP-005 等級 T2」"
    ),
    slots=[
        Slot("code", "string", required=True, description="供應商編號（如 SUP-005）"),
        Slot("name", "string", required=True, description="供應商名稱"),
        Slot("tier", "string", required=False, description="等級 T1/T2/T3，預設 T3"),
        Slot("contact_person", "string", required=False, description="聯絡人"),
        Slot("contact_phone", "string", required=False, description="電話"),
        Slot("payment_terms", "string", required=False, description="付款條件（如 月結 60 天）"),
    ],
    required_permission="purchase.supplier.create",
)
async def _create_supplier_with_confirm(
    db, user, code: str, name: str,
    tier: str = "T3", contact_person: str = "",
    contact_phone: str = "", payment_terms: str = "",
):
    from sqlalchemy import select as _select
    existing = (await db.execute(
        _select(Supplier).where(Supplier.code == code)
    )).scalar_one_or_none()
    if existing is not None:
        return {"error": f"供應商編號 {code!r} 已存在", "existing_id": existing.id}

    summary = [
        f"編號：{code}",
        f"名稱：{name}",
        f"等級：{tier}",
    ]
    if contact_person:
        summary.append(f"聯絡人：{contact_person}")
    if contact_phone:
        summary.append(f"電話：{contact_phone}")
    if payment_terms:
        summary.append(f"付款條件：{payment_terms}")

    card = make_card(
        tool_name="create_supplier_with_confirm",
        title="確認新增供應商",
        summary=summary,
        slots={
            "code": code, "name": name, "tier": tier,
            "contact_person": contact_person,
            "contact_phone": contact_phone, "payment_terms": payment_terms,
        },
        created_by=(user or {}).get("employee_id"),
    )

    async def execute():
        from app.services.purchase import create_supplier
        s = await create_supplier(db, {
            "code": code, "name": name, "tier": tier,
            "contact_person": contact_person or None,
            "contact_phone": contact_phone or None,
            "payment_terms": payment_terms or None,
        })
        return {
            "supplier_id": s.id, "code": s.code, "name": s.name,
            "message": f"✅ 供應商 {s.code}（{s.name}）已建立",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="approve_purchase_order_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "審核採購單（draft / pending → approved）。"
        "範例：「審核採購單 PO-20260514-001」"
    ),
    slots=[
        Slot("po_no", "string", required=True, description="採購單號"),
    ],
    required_permission="purchase.po.approve",
)
async def _approve_po_with_confirm(db, user, po_no: str):
    from sqlalchemy import select as _select
    po = (await db.execute(
        _select(PurchaseOrder).where(PurchaseOrder.po_no == po_no)
    )).scalar_one_or_none()
    if po is None:
        return {"error": f"找不到採購單 {po_no!r}"}
    if po.status not in ("draft", "pending"):
        return {
            "error": f"狀態 {po.status!r} 不可審核（只接受 draft/pending）",
            "po_no": po_no,
        }

    summary = [
        f"採購單號：{po.po_no}",
        f"供應商 ID：{po.supplier_id}",
        f"金額：${po.total_amount:,.0f}",
        f"狀態變更：{po.status} → approved",
    ]

    card = make_card(
        tool_name="approve_purchase_order_with_confirm",
        title=f"確認審核採購單 {po.po_no}",
        summary=summary,
        slots={"po_id": po.id, "po_no": po.po_no, "old_status": po.status},
        created_by=(user or {}).get("employee_id"),
    )

    async def execute():
        from app.services.purchase import approve_purchase_order
        approved = await approve_purchase_order(db, po.id, user=user or {})
        return {
            "po_no": approved.po_no, "id": approved.id,
            "status": approved.status, "approved_by": approved.approved_by,
            "message": f"✅ 採購單 {approved.po_no} 已審核",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ------------------------------------------------------------
# Sales: create_customer / create_sales_order
# ------------------------------------------------------------

@register_tool(
    name="create_customer_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "新增客戶主檔。範例：「新增客戶 富士康」「新增客戶 ABC 公司 等級 A」。"
        "v3.37：未提供編號時自動產生（CUS-0001、CUS-0002…），小白不必懂編碼。"
    ),
    slots=[
        Slot("name", "string", required=True, description="客戶名稱"),
        Slot("code", "string", required=False, description="客戶編號（留空自動產生 CUS-0001）"),
        Slot("grade", "string", required=False, description="等級 A/B/C/D，預設 C"),
        Slot("contact_person", "string", required=False, description="聯絡人"),
        Slot("contact_phone", "string", required=False, description="電話"),
        Slot("payment_terms", "string", required=False, description="付款條件"),
        Slot("credit_limit", "number", required=False, description="信用額度"),
    ],
    required_permission="sales.customer.create",
)
async def _create_customer_with_confirm(
    db, user, name: str, code: str = "",
    grade: str = "C", contact_person: str = "",
    contact_phone: str = "", payment_terms: str = "",
    credit_limit: float = 0,
):
    from sqlalchemy import select as _select, func as _func
    from app.models.crm_sales import Customer

    # v3.37: 自動產編 — 找下一個 CUS-####
    if not code or not code.strip():
        max_code = (await db.execute(
            _select(_func.max(Customer.code)).where(Customer.code.like("CUS-%"))
        )).scalar()
        next_num = 1
        if max_code:
            try:
                next_num = int(max_code.split("-")[-1]) + 1
            except (ValueError, IndexError):
                next_num = 1
        code = f"CUS-{next_num:04d}"

    existing = (await db.execute(
        _select(Customer).where(Customer.code == code)
    )).scalar_one_or_none()
    if existing is not None:
        return {"error": f"客戶編號 {code!r} 已存在", "existing_id": existing.id}

    summary = [
        f"編號：{code}",
        f"名稱：{name}",
        f"等級：{grade}",
    ]
    if contact_person:
        summary.append(f"聯絡人：{contact_person}")
    if credit_limit:
        summary.append(f"信用額度：${credit_limit:,.0f}")

    card = make_card(
        tool_name="create_customer_with_confirm",
        title="確認新增客戶",
        summary=summary,
        slots={
            "code": code, "name": name, "grade": grade,
            "contact_person": contact_person, "contact_phone": contact_phone,
            "payment_terms": payment_terms, "credit_limit": credit_limit,
        },
        created_by=(user or {}).get("employee_id"),
    )

    async def execute():
        from app.services.sales import create_customer
        c = await create_customer(db, {
            "code": code, "name": name, "grade": grade,
            "contact_person": contact_person or None,
            "contact_phone": contact_phone or None,
            "payment_terms": payment_terms or None,
            "credit_limit": credit_limit or 0,
        })
        return {
            "customer_id": c.id, "code": c.code, "name": c.name,
            "message": f"✅ 客戶 {c.code}（{c.name}）已建立",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="create_sales_order_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "建立銷售訂單。"
        "範例：「客戶 CUST-A001 下單 100 個 M6 螺絲，單價 5，要求交期 5/30」"
    ),
    slots=[
        Slot("customer_keyword", "string", required=True,
             description="客戶編號或名稱（如 CUST-A001 或「富士康」）"),
        Slot("items", "array", required=True,
             description='品項清單：[{"product_no": "PRD-A", "ordered_qty": 100, "unit_price": 5}]'),
        Slot("requested_delivery_date", "string", required=True,
             description="客戶要求交期 YYYY-MM-DD"),
        Slot("remark", "string", required=False, description="備註"),
    ],
    required_permission="sales.order.create",
)
async def _create_so_with_confirm(
    db, user, customer_keyword: str, items: list,
    requested_delivery_date: str, remark: str = "",
):
    from sqlalchemy import select as _select, func as _func
    from app.models.crm_sales import Customer
    from app.models.product import Product

    # Lookup customer
    cust = (await db.execute(
        _select(Customer).where(Customer.code == customer_keyword)
    )).scalar_one_or_none()
    if cust is None:
        cust = (await db.execute(
            _select(Customer).where(_func.lower(Customer.name).like(_func.lower(f"%{customer_keyword}%"))).limit(1)
        )).scalar_one_or_none()
    if cust is None:
        return {"error": f"找不到客戶 {customer_keyword!r}"}

    if not items:
        return {"error": "items 不能為空"}

    # Resolve products
    total = 0.0
    item_lines: list[str] = []
    resolved: list[dict] = []
    for raw in items:
        prod = None
        if pid := raw.get("product_id"):
            prod = (await db.execute(
                _select(Product).where(Product.id == pid)
            )).scalar_one_or_none()
        elif pno := raw.get("product_no"):
            prod = (await db.execute(
                _select(Product).where(Product.product_no == pno)
            )).scalar_one_or_none()
        if prod is None:
            return {
                "error": f"找不到產品: {raw.get('product_no') or raw.get('product_id') or '?'}"
            }
        qty = float(raw.get("ordered_qty", 0))
        price = float(raw.get("unit_price") or prod.selling_price or 0)
        if qty <= 0 or price <= 0:
            return {
                "error": f"無效 qty={qty} / price={price}",
                "product_no": prod.product_no,
            }
        line_total = qty * price
        total += line_total
        item_lines.append(
            f"  • {prod.product_no} {prod.name} × {qty:g} @ ${price:g} = ${line_total:,.0f}"
        )
        resolved.append({
            "product_id": prod.id, "ordered_qty": qty, "unit_price": price,
        })

    summary = [
        f"客戶：{cust.name}（{cust.code}，等級 {cust.grade}）",
        f"品項數：{len(items)} 項",
        *item_lines,
        f"總金額：${total:,.0f}",
        f"要求交期：{requested_delivery_date}",
    ]
    if remark:
        summary.append(f"備註：{remark}")

    card = make_card(
        tool_name="create_sales_order_with_confirm",
        title="確認建立銷售訂單",
        summary=summary,
        slots={
            "customer_id": cust.id, "customer_name": cust.name,
            "items": resolved, "requested_delivery_date": requested_delivery_date,
            "remark": remark, "total_amount": total,
        },
        created_by=(user or {}).get("employee_id"),
    )

    async def execute():
        from app.services.sales import create_sales_order
        from datetime import date
        try:
            edd = date.fromisoformat(requested_delivery_date)
        except Exception:
            edd = None
        so = await create_sales_order(db, {
            "customer_id": cust.id,
            "requested_delivery_date": edd,
            "remark": remark,
            "items": resolved,
        }, user=user)
        return {
            "so_no": so.so_no, "id": so.id,
            "total_amount": float(so.total_amount or 0),
            "message": f"✅ 銷售訂單 {so.so_no} 已建立，總金額 ${so.total_amount:,.0f}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ------------------------------------------------------------
# Production: complete_work_order
# ------------------------------------------------------------

@register_tool(
    name="complete_work_order_with_confirm",
    domain="production",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "工單報完工：累加完工數量，達訂單量自動轉 completed + 自動入庫。"
        "範例：「工單 WO-20260514-001 完工 100」"
    ),
    slots=[
        Slot("wo_no", "string", required=True, description="工單號"),
        Slot("completed_qty", "number", required=True, description="本次完工數"),
    ],
    required_permission="production.work_order.complete",
)
async def _complete_wo_with_confirm(db, user, wo_no: str, completed_qty: float):
    from sqlalchemy import select as _select
    wo = (await db.execute(
        _select(ProductionOrder).where(ProductionOrder.wo_no == wo_no)
    )).scalar_one_or_none()
    if wo is None:
        return {"error": f"找不到工單 {wo_no!r}"}
    if wo.status not in ("released", "in_progress"):
        return {
            "error": f"狀態 {wo.status!r} 不可報完工（需 released/in_progress）",
            "wo_no": wo_no,
        }
    if completed_qty <= 0:
        return {"error": f"完工量必須 > 0: {completed_qty}"}

    new_total = (wo.completed_qty or 0) + completed_qty
    will_close = new_total >= wo.ordered_qty

    summary = [
        f"工單：{wo.wo_no}",
        f"產品 ID：{wo.product_id}",
        f"訂單量：{wo.ordered_qty:g}",
        f"已完工：{wo.completed_qty:g} → {new_total:g}",
        f"本次完工：{completed_qty:g}",
    ]
    if will_close:
        summary.append("✅ 累計達訂單量 → 自動結案 + 成品入庫")
    else:
        summary.append(f"進度：{(new_total / wo.ordered_qty * 100):.1f}%")

    card = make_card(
        tool_name="complete_work_order_with_confirm",
        title=f"確認 {wo.wo_no} 報完工 {completed_qty:g}",
        summary=summary,
        slots={
            "wo_id": wo.id, "wo_no": wo.wo_no,
            "completed_qty": completed_qty,
            "current_total": wo.completed_qty,
            "will_close": will_close,
        },
        created_by=(user or {}).get("employee_id"),
    )

    async def execute():
        from app.services.production import complete_production_order
        wo_done = await complete_production_order(
            db, wo.id, float(completed_qty), user=user
        )
        return {
            "wo_no": wo_done.wo_no,
            "id": wo_done.id,
            "completed_qty_total": wo_done.completed_qty,
            "status": wo_done.status,
            "message": (
                f"✅ {wo_done.wo_no} 累計完工 {wo_done.completed_qty:g}"
                + ("，已結案 + 入庫" if wo_done.status == "completed" else "")
            ),
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ============================================================
# v3.25.9 — BOM (做法 / Recipe) 對話式管理：3 個 hard-write tools
# ============================================================

@register_tool(
    name="add_bom_item_with_confirm",
    domain="production",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "新增 BOM (做法 / Recipe) 行：指定產品 + 料件 + 用量 + 耗損率。"
        "AI 會出 ConfirmCard 給使用者確認，確認後才寫入。"
        "範例：「在產品 PROD-001 的做法中加 M6 螺絲 4 個」"
    ),
    slots=[
        Slot("product_no", "string", required=True, description="產品編號（如 PROD-001）"),
        Slot("part_no", "string", required=True, description="料件編號（如 M6-BOLT-20）"),
        Slot("qty_per", "number", required=True, description="每單位產品需要幾個此料件"),
        Slot("scrap_rate", "number", required=False, description="耗損率 0.0-1.0（如 0.05 = 5%）"),
        Slot("sequence_no", "integer", required=False, description="排序順序"),
    ],
    required_permission="production.bom.create",
)
async def _add_bom_item_with_confirm(
    db, user,
    product_no: str, part_no: str, qty_per: float,
    scrap_rate: float = 0.0, sequence_no: int = 0,
):
    from app.models.product import Product, BOMItem
    from app.models.inventory import Part

    product = (await db.execute(
        select(Product).where(Product.product_no == product_no)
    )).scalar_one_or_none()
    if product is None:
        return {"error": f"找不到產品「{product_no}」"}

    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalar_one_or_none()
    if part is None:
        return {"error": f"找不到料件「{part_no}」"}

    # 防呆：同產品同料件已存在
    existing = (await db.execute(
        select(BOMItem).where(
            BOMItem.product_id == product.id,
            BOMItem.part_id == part.id,
            BOMItem.is_active == True,
        )
    )).scalar_one_or_none()
    if existing is not None:
        return {
            "error": f"產品「{product_no}」的做法中已存在料件「{part_no}」",
            "hint": "用 update_bom_item_with_confirm 修改用量",
        }

    summary = [
        f"產品：{product.product_no} ({product.name})",
        f"料件：{part.part_no} ({part.name})",
        f"用量：{qty_per:g} {part.unit} / 1 {product.unit}",
        f"耗損率：{scrap_rate:.1%}" if scrap_rate else "耗損率：0%",
        f"排序：{sequence_no}",
    ]
    card = make_card(
        tool_name="add_bom_item_with_confirm",
        title="確認新增 BOM 行",
        summary=summary,
        slots={
            "product_id": product.id, "product_no": product.product_no,
            "part_id": part.id, "part_no": part.part_no,
            "qty_per": qty_per, "scrap_rate": scrap_rate,
            "sequence_no": sequence_no,
        },
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.production import add_bom_item
        item = await add_bom_item(db, {
            "product_id": product.id,
            "part_id": part.id,
            "qty_per": qty_per,
            "scrap_rate": scrap_rate,
            "sequence_no": sequence_no,
            "level": 1,
            "is_active": True,
        })
        return {
            "bom_item_id": item.id,
            "product_no": product.product_no,
            "part_no": part.part_no,
            "qty_per": item.qty_per,
            "message": f"✅ 已加 {part.part_no} 到 {product.product_no} 的做法",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="update_bom_item_with_confirm",
    domain="production",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "修改 BOM 行的用量或耗損率。"
        "AI 會出 ConfirmCard 給使用者確認，確認後才寫入。"
        "範例：「把產品 PROD-001 的 M6 螺絲用量改成 6 個」"
    ),
    slots=[
        Slot("product_no", "string", required=True, description="產品編號"),
        Slot("part_no", "string", required=True, description="料件編號"),
        Slot("qty_per", "number", required=False, description="新用量（不填則不改）"),
        Slot("scrap_rate", "number", required=False, description="新耗損率（不填則不改）"),
    ],
    required_permission="production.bom.update",
)
async def _update_bom_item_with_confirm(
    db, user,
    product_no: str, part_no: str,
    qty_per: float = None, scrap_rate: float = None,
):
    from app.models.product import Product, BOMItem
    from app.models.inventory import Part

    product = (await db.execute(
        select(Product).where(Product.product_no == product_no)
    )).scalar_one_or_none()
    if product is None:
        return {"error": f"找不到產品「{product_no}」"}
    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalar_one_or_none()
    if part is None:
        return {"error": f"找不到料件「{part_no}」"}

    item = (await db.execute(
        select(BOMItem).where(
            BOMItem.product_id == product.id,
            BOMItem.part_id == part.id,
            BOMItem.is_active == True,
        )
    )).scalar_one_or_none()
    if item is None:
        return {
            "error": f"產品「{product_no}」的做法中沒有料件「{part_no}」",
            "hint": "用 add_bom_item_with_confirm 新增",
        }

    if qty_per is None and scrap_rate is None:
        return {"error": "請至少指定 qty_per 或 scrap_rate 其中一個欄位"}

    changes_summary = []
    update_data = {}
    if qty_per is not None and qty_per != item.qty_per:
        changes_summary.append(f"用量：{item.qty_per:g} → {qty_per:g}")
        update_data["qty_per"] = qty_per
    if scrap_rate is not None and scrap_rate != item.scrap_rate:
        changes_summary.append(f"耗損率：{(item.scrap_rate or 0):.1%} → {scrap_rate:.1%}")
        update_data["scrap_rate"] = scrap_rate
    if not update_data:
        return {"message": "沒有變更", "product_no": product_no, "part_no": part_no}

    summary = [
        f"產品：{product.product_no} ({product.name})",
        f"料件：{part.part_no} ({part.name})",
        *changes_summary,
    ]
    card = make_card(
        tool_name="update_bom_item_with_confirm",
        title="確認修改 BOM 行",
        summary=summary,
        slots={"bom_item_id": item.id, **update_data,
               "product_no": product_no, "part_no": part_no},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.production import update_bom_item
        updated = await update_bom_item(db, item.id, update_data)
        return {
            "bom_item_id": updated.id,
            "product_no": product.product_no,
            "part_no": part.part_no,
            "qty_per": updated.qty_per,
            "scrap_rate": updated.scrap_rate,
            "message": f"✅ 已更新 {product.product_no} 的 {part.part_no} 做法",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="delete_bom_item_with_confirm",
    domain="production",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "從產品的 BOM 中移除一個料件（軟刪除：is_active=False 保留審計）。"
        "AI 會出 ConfirmCard 給使用者確認，確認後才停用。"
        "範例：「從 PROD-001 的做法移除 M6 螺絲」"
    ),
    slots=[
        Slot("product_no", "string", required=True, description="產品編號"),
        Slot("part_no", "string", required=True, description="料件編號"),
        Slot("reason", "string", required=False, description="移除原因（審計用）"),
    ],
    required_permission="production.bom.delete",
)
async def _delete_bom_item_with_confirm(
    db, user,
    product_no: str, part_no: str, reason: str = "",
):
    from app.models.product import Product, BOMItem
    from app.models.inventory import Part

    product = (await db.execute(
        select(Product).where(Product.product_no == product_no)
    )).scalar_one_or_none()
    if product is None:
        return {"error": f"找不到產品「{product_no}」"}
    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalar_one_or_none()
    if part is None:
        return {"error": f"找不到料件「{part_no}」"}

    item = (await db.execute(
        select(BOMItem).where(
            BOMItem.product_id == product.id,
            BOMItem.part_id == part.id,
            BOMItem.is_active == True,
        )
    )).scalar_one_or_none()
    if item is None:
        return {"error": f"產品「{product_no}」的做法中沒有 active 的料件「{part_no}」"}

    summary = [
        f"產品：{product.product_no} ({product.name})",
        f"料件：{part.part_no} ({part.name})",
        f"原用量：{item.qty_per:g}",
        f"移除原因：{reason or '（未填）'}",
        "⚠️ 軟刪除：保留紀錄但停用，未來可重啟用",
    ]
    card = make_card(
        tool_name="delete_bom_item_with_confirm",
        title="確認移除 BOM 行",
        summary=summary,
        slots={"bom_item_id": item.id, "product_no": product_no,
               "part_no": part_no, "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.production import delete_bom_item
        result = await delete_bom_item(db, item.id, user=user)
        return {
            "bom_item_id": result["item_id"],
            "product_no": product.product_no,
            "part_no": part.part_no,
            "message": f"✅ 已從 {product.product_no} 的做法移除 {part.part_no}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ------------------------------------------------------------
# 接到 4 個 domain agent 的 tool_names
# ------------------------------------------------------------

from app.agents.engine import AGENT_REGISTRY as _AGENT_REGISTRY

_DOMAIN_TOOL_MAP = {
    "inventory": [
        "create_part_with_confirm",
        "update_part_safety_stock_with_confirm",
        "add_inventory_transaction_with_confirm",
    ],
    "purchase": [
        "create_supplier_with_confirm",
        "approve_purchase_order_with_confirm",
    ],
    "sales": [
        "create_customer_with_confirm",
        "create_sales_order_with_confirm",
    ],
    "production": [
        "complete_work_order_with_confirm",
        # v3.25.9：BOM (做法) 對話式管理
        "add_bom_item_with_confirm",
        "update_bom_item_with_confirm",
        "delete_bom_item_with_confirm",
    ],
}

for _domain, _tools in _DOMAIN_TOOL_MAP.items():
    if _domain in _AGENT_REGISTRY:
        _tn = _AGENT_REGISTRY[_domain]["tool_names"]
        for _t in _tools:
            if _t not in _tn:
                _tn.append(_t)
