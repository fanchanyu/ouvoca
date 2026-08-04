"""M3 表單工程 AI tools — 請購 / 收料 / 領料 / 退貨。"""
from __future__ import annotations

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot


@register_tool(
    name="create_pr_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "建立請購單（PR）。範例：「請購 100 個 M6 螺絲，8/20 要」"
        "之後可用 convert_pr_to_po 轉成採購單。"
    ),
    slots=[
        Slot("items", "array", required=True,
             description='請購項目：[{"part_no": "M6-BOLT-20", "qty": 100}]'),
        Slot("need_date", "string", required=False, description="需求日期 YYYY-MM-DD"),
        Slot("remark", "string", required=False, description="備註"),
    ],
    required_permission="purchase.pr.create",
)
async def _create_pr_with_confirm(db, user, items, need_date=None, remark=""):
    from app.models.inventory import Part
    from app.services.m3_documents import create_purchase_requisition
    from sqlalchemy import select

    resolved = []
    for raw in items:
        part = None
        if raw.get("part_id"):
            part = (await db.execute(select(Part).where(Part.id == raw["part_id"]))).scalars().first()
        elif raw.get("part_no"):
            part = (await db.execute(select(Part).where(Part.part_no == raw["part_no"]))).scalars().first()
        if part is None:
            return {"error": f"找不到料件 {raw.get('part_no') or raw.get('part_id')!r}"}
        resolved.append({"part_id": part.id, "qty": float(raw["qty"]),
                         "part_no": part.part_no, "name": part.name})

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="create_pr_with_confirm",
        title="建立請購單",
        summary=[
            f"項目數：{len(resolved)}",
            *[f"  • {i['part_no']} {i['name']} × {i['qty']:g}" for i in resolved],
            f"需求日：{need_date or '未指定'}",
        ],
        slots={"items": [{"part_id": i["part_id"], "qty": i["qty"]} for i in resolved],
               "need_date": need_date, "remark": remark},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        pr = await create_purchase_requisition(db, {
            "items": [{"part_id": i["part_id"], "qty": i["qty"]} for i in resolved],
            "need_date": need_date, "remark": remark,
        }, user=user)
        return {"pr_id": pr.id, "pr_no": pr.pr_no, "status": pr.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="convert_pr_to_po_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description="把已核准的請購單轉成採購單。範例：「把 PR-... 轉成給長江的採購單」",
    slots=[
        Slot("pr_keyword", "string", required=True, description="請購單號"),
        Slot("supplier_keyword", "string", required=True, description="供應商名稱或編號"),
    ],
    required_permission="purchase.pr.convert",
)
async def _convert_pr_to_po_with_confirm(db, user, pr_keyword: str, supplier_keyword: str):
    from app.models.documents_m3 import PurchaseRequisition
    from app.models.purchase import Supplier
    from app.services.m3_documents import convert_pr_to_po
    from sqlalchemy import select

    pr = (await db.execute(
        select(PurchaseRequisition).where(PurchaseRequisition.pr_no == pr_keyword)
    )).scalars().first()
    if pr is None:
        return {"error": f"找不到請購單「{pr_keyword}」"}
    supplier = (await db.execute(
        select(Supplier).where(
            (Supplier.code == supplier_keyword) | (Supplier.name.like(f"%{supplier_keyword}%"))
        )
    )).scalars().first()
    if supplier is None:
        return {"error": f"找不到供應商「{supplier_keyword}」"}

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="convert_pr_to_po_with_confirm",
        title=f"請購單 {pr.pr_no} 轉採購單",
        summary=[
            f"請購單：{pr.pr_no}（狀態 {pr.status}）",
            f"供應商：{supplier.name}（{supplier.code}）",
            "品項與數量依請購單帶入，單價以料件成本為預設",
        ],
        slots={"pr_id": pr.id, "supplier_id": supplier.id},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        po = await convert_pr_to_po(db, pr.id, supplier.id, user)
        return {"po_id": po.id, "po_no": po.po_no, "status": po.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="receive_grn_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "收料：對採購單建立收料單（GRN），更新收貨量並入庫。"
        "範例：「收 PO-... 全部到貨」"
    ),
    slots=[
        Slot("po_keyword", "string", required=True, description="採購單號"),
        Slot("receipts", "array", required=False,
             description='收貨清單 [{"po_item_id": "...", "received_qty": 100}]；省略 = 全部收齊'),
    ],
    required_permission="purchase.grn.create",
)
async def _receive_grn_with_confirm(db, user, po_keyword: str, receipts=None):
    from app.models.purchase import PurchaseOrder, PurchaseOrderItem
    from app.services.m3_documents import create_grn
    from sqlalchemy import select

    po = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.po_no == po_keyword)
    )).scalars().first()
    if po is None:
        return {"error": f"找不到採購單「{po_keyword}」"}

    if not receipts:
        items = list((await db.execute(
            select(PurchaseOrderItem).where(PurchaseOrderItem.po_id == po.id)
        )).scalars().all())
        receipts = [
            {"po_item_id": it.id,
             "received_qty": float(it.ordered_qty or 0) - float(it.received_qty or 0)}
            for it in items
        ]

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="receive_grn_with_confirm",
        title=f"收料 {po.po_no}",
        summary=[
            f"採購單：{po.po_no}",
            f"收貨行數：{len(receipts)}",
            "建立 GRN + 更新收貨量 + 入庫（原子）",
        ],
        slots={"po_id": po.id, "receipts": receipts},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        grn = await create_grn(db, po.id, receipts, user)
        return {"grn_id": grn.id, "grn_no": grn.grn_no, "status": grn.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="issue_material_with_confirm",
    domain="production",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "工單領料：從倉庫扣料給工單（記錄成本快照）。"
        "範例：「WO-001 領 100 個 M6 螺絲」"
    ),
    slots=[
        Slot("wo_keyword", "string", required=True, description="工單號碼"),
        Slot("items", "array", required=True,
             description='領料清單：[{"part_no": "M6-BOLT-20", "qty": 100}]'),
    ],
    required_permission="production.material_issue.create",
)
async def _issue_material_with_confirm(db, user, wo_keyword: str, items):
    from app.models.production import ProductionOrder
    from app.models.inventory import Part
    from app.services.m3_documents import issue_material
    from sqlalchemy import select

    wo = (await db.execute(
        select(ProductionOrder).where(ProductionOrder.wo_no == wo_keyword)
    )).scalars().first()
    if wo is None:
        return {"error": f"找不到工單「{wo_keyword}」"}
    resolved = []
    for raw in items:
        part = (await db.execute(
            select(Part).where(Part.part_no == raw["part_no"])
        )).scalars().first()
        if part is None:
            return {"error": f"找不到料件「{raw.get('part_no')}」"}
        resolved.append({"part_id": part.id, "qty": float(raw["qty"]),
                         "part_no": part.part_no, "name": part.name})

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="issue_material_with_confirm",
        title=f"工單領料 {wo.wo_no}",
        summary=[
            f"工單：{wo.wo_no}",
            *[f"  • {i['part_no']} {i['name']} × {i['qty']:g}" for i in resolved],
            "扣原料庫存 + 領料成本快照",
        ],
        slots={"wo_id": wo.id, "items": [{"part_id": i["part_id"], "qty": i["qty"]} for i in resolved]},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        issue = await issue_material(db, wo.id,
                                     [{"part_id": i["part_id"], "qty": i["qty"]} for i in resolved],
                                     user)
        return {"issue_id": issue.id, "issue_no": issue.issue_no, "status": issue.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="create_return_note_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "建立退貨單（RMA）。範例：「客戶退回 10 個 M6 螺絲，品質問題」"
        "核准後可 process 退貨入庫。"
    ),
    slots=[
        Slot("customer_keyword", "string", required=True, description="客戶名稱或編號"),
        Slot("items", "array", required=True,
             description='退貨清單：[{"part_no": "M6-BOLT-20", "qty": 10}]'),
        Slot("reason", "string", required=False, description="退貨原因"),
    ],
    required_permission="sales.return.create",
)
async def _create_return_note_with_confirm(db, user, customer_keyword, items, reason=""):
    from app.models.crm_sales import Customer
    from app.models.inventory import Part
    from app.services.m3_documents import create_return_note
    from sqlalchemy import select

    customer = (await db.execute(
        select(Customer).where(
            (Customer.code == customer_keyword) | (Customer.name.like(f"%{customer_keyword}%"))
        )
    )).scalars().first()
    if customer is None:
        return {"error": f"找不到客戶「{customer_keyword}」"}
    resolved = []
    for raw in items:
        part = (await db.execute(
            select(Part).where(Part.part_no == raw["part_no"])
        )).scalars().first()
        if part is None:
            return {"error": f"找不到料件「{raw.get('part_no')}」"}
        resolved.append({"part_id": part.id, "qty": float(raw["qty"]),
                         "part_no": part.part_no, "name": part.name})

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="create_return_note_with_confirm",
        title=f"退貨單（{customer.name}）",
        summary=[
            f"客戶：{customer.name}（{customer.code}）",
            *[f"  • {i['part_no']} {i['name']} × {i['qty']:g}" for i in resolved],
            f"原因：{reason or '未填'}",
        ],
        slots={"customer_id": customer.id,
               "items": [{"part_id": i["part_id"], "qty": i["qty"]} for i in resolved],
               "reason": reason},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        note = await create_return_note(db, {
            "customer_id": customer.id,
            "items": [{"part_id": i["part_id"], "qty": i["qty"]} for i in resolved],
            "reason": reason,
        }, user=user)
        return {"return_id": note.id, "return_no": note.return_no, "status": note.status}

    await stash_card(card, execute)
    return card.to_chat_payload()
