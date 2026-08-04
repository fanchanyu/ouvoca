"""v3.64 AI tools — 批號/序號追溯、RFQ 詢價比價、標籤列印。"""
from __future__ import annotations

import base64

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.inventory import Part
from sqlalchemy import select


# ════════════════════════════════════════════════════════════
# 批號 / 序號
# ════════════════════════════════════════════════════════════

@register_tool(
    name="assign_batch_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description="建立批號主檔（料件 + 批號 + 數量 + 效期）。範例：「料件 A 建批號 LOT-20260801，100 個，10/1 到期」",
    slots=[
        Slot("part_keyword", "string", required=True, description="料號或名稱"),
        Slot("lot_no", "string", required=True, description="批號"),
        Slot("qty", "number", required=False, description="數量"),
        Slot("expiry_date", "string", required=False, description="效期 YYYY-MM-DD"),
    ],
    required_permission="inventory.batch.create",
)
async def _assign_batch_with_confirm(db, user, part_keyword, lot_no, qty=0, expiry_date=None):
    from app.services.traceability import assign_batch
    from datetime import datetime

    part = (await db.execute(
        select(Part).where(
            (Part.part_no == part_keyword) | (Part.name.like(f"%{part_keyword}%"))
        )
    )).scalars().first()
    if part is None:
        return {"error": f"找不到料件「{part_keyword}」"}

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="assign_batch_with_confirm",
        title=f"建立批號 {lot_no}",
        summary=[
            f"料件：{part.part_no} {part.name}",
            f"批號：{lot_no} | 數量：{qty:g}",
            f"效期：{expiry_date or '無'}",
        ],
        slots={"part_id": part.id, "lot_no": lot_no, "qty": qty, "expiry_date": expiry_date},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        lot = await assign_batch(
            db, part.id, lot_no, qty,
            expiry_date=datetime.fromisoformat(expiry_date) if expiry_date else None,
            user=user,
        )
        return {"batch_id": lot.id, "lot_no": lot.lot_no, "status": lot.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="trace_batch",
    domain="inventory",
    risk_tier=RiskTier.READ,
    description="批次追溯：某批號從哪進、被哪些單據消耗（正反向）。範例：「追溯 LOT-20260801」",
    slots=[
        Slot("lot_no", "string", required=True, description="批號"),
    ],
    required_permission="inventory.batch.read",
)
async def _trace_batch(db, user, lot_no: str):
    from app.services.traceability import trace_batch
    return await trace_batch(db, lot_no)


@register_tool(
    name="trace_serial",
    domain="inventory",
    risk_tier=RiskTier.READ,
    description="序號追溯：查序號狀態與最近文件。範例：「查序號 SN-000123」",
    slots=[
        Slot("serial_no", "string", required=True, description="序號"),
    ],
    required_permission="inventory.serial.read",
)
async def _trace_serial(db, user, serial_no: str):
    from app.services.traceability import trace_serial
    return await trace_serial(db, serial_no)


@register_tool(
    name="record_serials_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description="批量登記序號。範例：「登記 SN-0001~SN-0010 到批號 LOT-...」",
    slots=[
        Slot("part_keyword", "string", required=True, description="料號或名稱"),
        Slot("serials", "array", required=True, description='序號清單 ["SN-0001", ...]'),
        Slot("lot_no", "string", required=False, description="批號（可省略）"),
    ],
    required_permission="inventory.serial.create",
)
async def _record_serials_with_confirm(db, user, part_keyword, serials, lot_no=""):
    from app.models.traceability import BatchLot
    from app.services.traceability import record_serials

    part = (await db.execute(
        select(Part).where(
            (Part.part_no == part_keyword) | (Part.name.like(f"%{part_keyword}%"))
        )
    )).scalars().first()
    if part is None:
        return {"error": f"找不到料件「{part_keyword}」"}
    batch = None
    if lot_no:
        batch = (await db.execute(
            select(BatchLot).where(BatchLot.lot_no == lot_no)
        )).scalars().first()
        if batch is None:
            return {"error": f"找不到批號「{lot_no}」"}

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="record_serials_with_confirm",
        title=f"登記 {len(serials)} 個序號",
        summary=[
            f"料件：{part.part_no} {part.name}",
            f"序號數：{len(serials)}",
            f"批號：{lot_no or '（未指定）'}",
        ],
        slots={"part_id": part.id, "serials": serials, "batch_id": batch.id if batch else None},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        rows = await record_serials(db, part.id, serials, batch.id if batch else None, user)
        return {"created": len(rows), "serials": [r.serial_no for r in rows]}

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════
# RFQ 詢價比價
# ════════════════════════════════════════════════════════════

@register_tool(
    name="create_rfq_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description="建立詢價單（RFQ）。範例：「針對 M6 螺絲 1000 個發詢價」",
    slots=[
        Slot("items", "array", required=True,
             description='詢價項目：[{"part_no": "M6-BOLT-20", "qty": 1000}]'),
        Slot("need_date", "string", required=False, description="需求日期"),
        Slot("remark", "string", required=False, description="備註"),
    ],
    required_permission="purchase.rfq.create",
)
async def _create_rfq_with_confirm(db, user, items, need_date=None, remark=""):
    from app.services.rfq import create_rfq

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
        tool_name="create_rfq_with_confirm",
        title="建立詢價單",
        summary=[
            f"項目數：{len(resolved)}",
            *[f"  • {i['part_no']} {i['name']} × {i['qty']:g}" for i in resolved],
        ],
        slots={"items": [{"part_id": i["part_id"], "qty": i["qty"]} for i in resolved],
               "need_date": need_date, "remark": remark},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        rfq = await create_rfq(db, {
            "items": [{"part_id": i["part_id"], "qty": i["qty"]} for i in resolved],
            "need_date": need_date, "remark": remark,
        }, user=user)
        return {"rfq_id": rfq.id, "rfq_no": rfq.rfq_no, "status": rfq.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="receive_quote_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description="登錄供應商報價（RFQ 送出後）。範例：「長江報 M6 螺絲 1000 個 5000 元」",
    slots=[
        Slot("rfq_keyword", "string", required=True, description="詢價單號"),
        Slot("supplier_keyword", "string", required=True, description="供應商名稱或編號"),
        Slot("items", "array", required=True,
             description='報價明細：[{"part_no": "M6-BOLT-20", "qty": 1000, "unit_price": 5}]'),
        Slot("lead_time_days", "integer", required=False, description="交期天數"),
    ],
    required_permission="purchase.rfq.create",
)
async def _receive_quote_with_confirm(db, user, rfq_keyword, supplier_keyword, items, lead_time_days=0):
    from app.models.rfq import RFQ
    from app.models.purchase import Supplier
    from app.services.rfq import receive_quote

    rfq = (await db.execute(
        select(RFQ).where(RFQ.rfq_no == rfq_keyword)
    )).scalars().first()
    if rfq is None:
        return {"error": f"找不到詢價單「{rfq_keyword}」"}
    supplier = (await db.execute(
        select(Supplier).where(
            (Supplier.code == supplier_keyword) | (Supplier.name.like(f"%{supplier_keyword}%"))
        )
    )).scalars().first()
    if supplier is None:
        return {"error": f"找不到供應商「{supplier_keyword}」"}
    resolved = []
    for raw in items:
        part = (await db.execute(
            select(Part).where(Part.part_no == raw["part_no"])
        )).scalars().first()
        if part is None:
            return {"error": f"找不到料件「{raw.get('part_no')}」"}
        resolved.append({"part_id": part.id, "qty": float(raw["qty"]),
                         "unit_price": float(raw.get("unit_price", 0)),
                         "part_no": part.part_no, "name": part.name})

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="receive_quote_with_confirm",
        title=f"登錄報價（{supplier.name}）",
        summary=[
            f"詢價單：{rfq.rfq_no} | 供應商：{supplier.name}",
            *[f"  • {i['part_no']} × {i['qty']:g} @ {i['unit_price']:g}" for i in resolved],
            f"交期：{lead_time_days} 天",
        ],
        slots={"rfq_id": rfq.id, "supplier_id": supplier.id,
               "items": [{"part_id": i["part_id"], "qty": i["qty"], "unit_price": i["unit_price"]}
                         for i in resolved],
               "lead_time_days": lead_time_days},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        quote = await receive_quote(db, {
            "rfq_id": rfq.id, "supplier_id": supplier.id,
            "items": [{"part_id": i["part_id"], "qty": i["qty"], "unit_price": i["unit_price"]}
                      for i in resolved],
            "lead_time_days": lead_time_days,
        }, user=user)
        return {"quote_id": quote.id, "amount": quote.amount, "status": quote.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="compare_quotes",
    domain="purchase",
    risk_tier=RiskTier.READ,
    description="RFQ 比價：列出所有報價 + 每料件最低價。範例：「RFQ-... 誰最便宜」",
    slots=[
        Slot("rfq_keyword", "string", required=True, description="詢價單號"),
    ],
    required_permission="purchase.rfq.read",
)
async def _compare_quotes(db, user, rfq_keyword: str):
    from app.models.rfq import RFQ
    from app.services.rfq import compare_quotes
    rfq = (await db.execute(
        select(RFQ).where(RFQ.rfq_no == rfq_keyword)
    )).scalars().first()
    if rfq is None:
        return {"error": f"找不到詢價單「{rfq_keyword}」"}
    return await compare_quotes(db, rfq.id)


@register_tool(
    name="award_rfq_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description="RFQ 決標：指定報價得標並轉採購單。範例：「RFQ-... 給長江得標」",
    slots=[
        Slot("rfq_keyword", "string", required=True, description="詢價單號"),
        Slot("quote_id", "string", required=True, description="得標報價 id（compare_quotes 查）"),
    ],
    required_permission="purchase.rfq.award",
)
async def _award_rfq_with_confirm(db, user, rfq_keyword: str, quote_id: str):
    from app.models.rfq import RFQ
    from app.services.rfq import award_rfq
    rfq = (await db.execute(
        select(RFQ).where(RFQ.rfq_no == rfq_keyword)
    )).scalars().first()
    if rfq is None:
        return {"error": f"找不到詢價單「{rfq_keyword}」"}

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="award_rfq_with_confirm",
        title=f"決標 {rfq.rfq_no}",
        summary=[
            f"詢價單：{rfq.rfq_no}",
            f"得標報價：{quote_id}",
            "決標後自動依得標報價轉成採購單",
        ],
        slots={"rfq_id": rfq.id, "quote_id": quote_id},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        return await award_rfq(db, rfq.id, quote_id, user)

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════
# 標籤列印
# ════════════════════════════════════════════════════════════

@register_tool(
    name="print_part_label",
    domain="inventory",
    risk_tier=RiskTier.READ,
    description="產生料件 QR 標籤 PDF（回 base64 供前端下載列印）。範例：「印 M6-BOLT-20 標籤」",
    slots=[
        Slot("part_no", "string", required=True, description="料號"),
        Slot("qty", "string", required=False, description="標籤上的數量文字"),
    ],
    required_permission="print.label",
)
async def _print_part_label(db, user, part_no: str, qty: str = ""):
    from app.services.print_service import render_part_label_pdf
    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalars().first()
    name = part.name if part else ""
    pdf = render_part_label_pdf(part_no, name, qty)
    return {
        "part_no": part_no,
        "pdf_base64": base64.b64encode(pdf).decode("ascii"),
        "bytes": len(pdf),
        "hint": "前端可用 data:application/pdf;base64,... 直接下載/列印",
    }
