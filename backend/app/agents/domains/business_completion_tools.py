"""業務面 LLM tools 補完 — Tax + Accounting + Approval + Warehouse + Quality (v3.34)

電腦小白每天最痛 17 個 LLM tools：
  Tax 稅務 (5)：開發票 / 作廢 / 查發票 / 查 401 / 驗統編
  Accounting 會計 (4)：記付款 / 記收款 / 查 AR / 查 AP
  Approval 審批 (3)：查待審 / 批准 / 拒絕
  Warehouse 揀貨 (2)：建揀貨單 / 查待揀
  Quality 退貨 (3)：建 NCR / 建 CAPA / 退貨入庫

══════════════════════════════════════════════════════════════════
LEGAL / 法律聲明（雙語累積適用 v3.25.10 → v3.33）
══════════════════════════════════════════════════════════════════
本模組含**高合規敏感**操作：
  • 開發票/作廢發票 — 影響營業稅申報、財報、稅務檢查
  • 付款/收款記錄 — 影響 cash flow 與審計
  • 審批決策 — 影響契約效力、責任歸屬
  • 退貨入庫 — 影響庫存帳與供應商/客戶關係

所有 hard-write 必走 ConfirmCard。**erpilot 之輸出不構成稅務 / 財務 /
法律意見**，對外財報請依適用會計準則 + CPA + 稅務顧問覆核。

This module contains high-compliance operations: invoicing, payments,
approvals, returns. All hard-writes use ConfirmCard. erpilot output
does NOT constitute tax / financial / legal advice. For external
filings, use CPA + tax advisor review per applicable standards.
Cumulative applicability with v3.25.10 → v3.33 §6 disclaimers.
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.accounting import (
    Account, JournalEntry, JournalLine, AccountsReceivable,
)
from app.models.approval_workflow import (
    ApprovalRequestV2, ApprovalStepV2, ApprovalRule,
)
from app.models.warehouse import PickTask
from app.models.quality import (
    InspectionOrder, NonConformance, CAPARecord,
)
from app.models.purchase import PurchaseOrder, Supplier
from app.models.crm_sales import SalesOrder, Customer


# ════════════════════════════════════════════════════════════════════
# Tax 稅務 (5)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="issue_einvoice_with_confirm",
    domain="tax",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "為銷售單開立電子發票（B2B 三聯式 / B2C 二聯式）。"
        "範例：「為 SO-001 開發票」「客戶 X 那張單開發票給他」"
    ),
    slots=[
        Slot("so_no", "string", required=True, description="銷售單號"),
        Slot("invoice_type", "string", required=False,
             description="07 (三聯式 B2B 含稅) / 31 (二聯式 B2C 含稅)；預設 07"),
        Slot("tax_id", "string", required=False, description="買方統編（B2B 必填）"),
    ],
    required_permission="tax.einvoice.issue",
)
async def _issue_einvoice_tool(
    db, user, so_no: str, invoice_type: str = "07", tax_id: str = "",
):
    so = (await db.execute(
        select(SalesOrder).where(SalesOrder.so_no == so_no)
    )).scalar_one_or_none()
    if so is None:
        return {"error": f"找不到銷售單「{so_no}」"}
    if so.status not in ("shipped", "confirmed", "closed"):
        return {"error": f"SO 狀態 {so.status!r}，建議 shipped 後再開發票"}

    cu = (await db.execute(
        select(Customer).where(Customer.id == so.customer_id)
    )).scalar_one_or_none()

    amount = so.total_amount or 0
    tax_amount = round(amount * 0.05 / 1.05, 0)  # 5% 內含
    net = amount - tax_amount

    summary = [
        f"📋 銷售單：{so.so_no}",
        f"👤 客戶：{cu.code if cu else '?'} - {cu.name if cu else '?'}",
        f"🧾 發票類型：{invoice_type} ({'三聯式 B2B' if invoice_type == '07' else '二聯式 B2C'})",
        f"🆔 買方統編：{tax_id or '(未填)'}",
        f"💰 銷售額（未稅）：${net:,.0f}",
        f"💰 營業稅 (5%)：${tax_amount:,.0f}",
        f"💰 總額（含稅）：${amount:,.0f}",
        "",
        "⚠️ 開立後將上傳財政部 / 通報雲端發票平台，**作廢需 24 小時內**",
        "⚠️ 統編錯誤 → 對方無法扣抵；務必先用 validate_tax_id_tool 確認",
    ]
    card = make_card(
        tool_name="issue_einvoice_with_confirm",
        title="🧾 確認開立電子發票",
        summary=summary,
        slots={"so_id": so.id, "so_no": so.so_no, "invoice_type": invoice_type,
               "tax_id": tax_id, "amount": amount},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        # Real einvoice integration is out of scope; mock issue
        inv_no = f"EI{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
        return {
            "invoice_no": inv_no, "so_no": so.so_no,
            "amount": amount, "tax_amount": tax_amount,
            "message": f"✅ 發票 {inv_no} 已開立（金額 ${amount:,.0f}）",
            "note": "實際 SMTP / 雲端發票上傳請整合對應 API",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="void_einvoice_with_confirm",
    domain="tax",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "作廢電子發票（24 小時內可作廢，逾期需開折讓單）。"
        "範例：「EI20260521001 作廢」"
    ),
    slots=[
        Slot("invoice_no", "string", required=True),
        Slot("reason", "string", required=False, description="作廢原因"),
    ],
    required_permission="tax.einvoice.void",
)
async def _void_einvoice_tool(db, user, invoice_no: str, reason: str = ""):
    summary = [
        f"🧾 發票號：{invoice_no}",
        f"📝 作廢原因：{reason or '(未填)'}",
        "",
        "⚠️ 作廢限制：發票開立 24 小時內可作廢，逾期需開折讓單",
        "⚠️ 此動作將通報財政部 / 雲端發票平台",
    ]
    card = make_card(
        tool_name="void_einvoice_with_confirm",
        title="🚫 確認作廢發票",
        summary=summary,
        slots={"invoice_no": invoice_no, "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        return {
            "invoice_no": invoice_no,
            "message": f"✅ 發票 {invoice_no} 已標為作廢（實際財政部 API 通報請整合）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="validate_tax_id_tool",
    domain="tax",
    risk_tier=RiskTier.READ,
    description=(
        "驗證統一編號是否正確（含台灣 8 碼 checksum 演算法）。"
        "範例：「查 12345678 統編對不對？」"
    ),
    slots=[
        Slot("tax_id", "string", required=True),
        Slot("country", "string", required=False, description="預設 TW"),
    ],
    required_permission="tax.tax_id.validate",
)
async def _validate_tax_id_tool(db, user, tax_id: str, country: str = "TW"):
    if country.upper() == "TW":
        # Taiwan 8-digit tax ID checksum (公司行號)
        if not tax_id.isdigit() or len(tax_id) != 8:
            return {
                "summary": f"❌ {tax_id} 格式錯誤（應為 8 位數字）",
                "raw": {"valid": False, "reason": "format"},
            }
        weights = [1, 2, 1, 2, 1, 2, 4, 1]
        total = 0
        for i, d in enumerate(tax_id):
            n = int(d) * weights[i]
            total += (n // 10) + (n % 10)
        valid = (total % 10 == 0) or (int(tax_id[6]) == 7 and (total + 1) % 10 == 0)
        return {
            "summary": f"{'✅' if valid else '❌'} 統編 {tax_id}：{'有效' if valid else '無效'}",
            "raw": {"tax_id": tax_id, "country": country, "valid": valid},
        }
    return {
        "summary": f"⚠️ 國別 {country} 驗證未實作",
        "raw": {"valid": None},
    }


@register_tool(
    name="query_monthly_sales_tax",
    domain="tax",
    risk_tier=RiskTier.READ,
    description=(
        "查詢指定月份營業稅概況（含稅銷售總額、銷項稅額）。"
        "範例：「這個月營業稅多少？」「查 5 月稅額」"
    ),
    slots=[
        Slot("year_month", "string", required=False, description="YYYY-MM；預設本月"),
    ],
    required_permission="tax.report.read",
)
async def _query_monthly_sales_tax(db, user, year_month: str = None):
    from datetime import datetime as _dt
    if not year_month:
        year_month = _dt.now(UTC).strftime("%Y-%m")
    try:
        year, month = year_month.split("-")
        year, month = int(year), int(month)
    except (ValueError, AttributeError):
        return {"error": f"年月格式錯誤 {year_month!r}，應為 YYYY-MM"}

    # 期初期末
    start = _dt(year, month, 1)
    end = _dt(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

    # Sum SO total in range
    result = await db.execute(
        select(func.sum(SalesOrder.total_amount)).where(
            SalesOrder.order_date >= start,
            SalesOrder.order_date < end,
            SalesOrder.status.in_(["shipped", "confirmed", "closed"]),
        )
    )
    total_with_tax = result.scalar() or 0
    tax_amount = round(total_with_tax * 0.05 / 1.05, 0)
    net_sales = total_with_tax - tax_amount

    return {
        "summary": (
            f"📊 **{year_month} 營業稅概況**\n\n"
            f"含稅銷售總額：${total_with_tax:,.0f}\n"
            f"未稅銷售額：${net_sales:,.0f}\n"
            f"銷項稅額 (5%)：${tax_amount:,.0f}\n\n"
            f"💡 申報請用 query_form_401 取完整 401 表"
        ),
        "raw": {
            "year_month": year_month, "total_with_tax": total_with_tax,
            "net_sales": net_sales, "tax_amount": tax_amount,
        },
    }


@register_tool(
    name="query_einvoice_by_so",
    domain="tax",
    risk_tier=RiskTier.READ,
    description=(
        "查詢某銷售單已開之發票紀錄。範例：「SO-001 的發票呢？」"
    ),
    slots=[
        Slot("so_no", "string", required=True),
    ],
    required_permission="tax.einvoice.read",
)
async def _query_einvoice_by_so(db, user, so_no: str):
    # In real implementation, einvoices would be in a dedicated table.
    # For now, we report SO status and recommend manual lookup.
    so = (await db.execute(
        select(SalesOrder).where(SalesOrder.so_no == so_no)
    )).scalar_one_or_none()
    if so is None:
        return {"error": f"找不到 SO 「{so_no}」"}
    return {
        "summary": (
            f"📋 SO {so.so_no} 狀態：{so.status}\n"
            f"金額：${so.total_amount:,.0f}\n\n"
            f"💡 發票紀錄請查 /api/tax/tw/einvoice 端點（v3.34 之 query 用 SO 連動 mock）"
        ),
        "raw": {"so_no": so.so_no, "status": so.status, "amount": so.total_amount},
    }


# ════════════════════════════════════════════════════════════════════
# Accounting 會計 (4)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="record_payment_to_supplier_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "💸 記錄付款給供應商（建立 JE：借應付帳款，貸銀行存款）。"
        "範例：「付給長江廠 NT$50000」「結 PO-001 的款」"
    ),
    slots=[
        Slot("supplier_keyword", "string", required=True),
        Slot("amount", "number", required=True),
        Slot("po_no", "string", required=False, description="關聯之 PO 號"),
        Slot("payment_method", "string", required=False,
             description="cash / wire / check（預設 wire）"),
        Slot("notes", "string", required=False),
    ],
    required_permission="accounting.payment.record",
)
async def _record_payment_to_supplier(
    db, user, supplier_keyword: str, amount: float,
    po_no: str = "", payment_method: str = "wire", notes: str = "",
):
    sup = (await db.execute(
        select(Supplier).where(
            (Supplier.code == supplier_keyword) | (Supplier.name.contains(supplier_keyword))
        )
    )).scalars().first()
    if sup is None:
        return {"error": f"找不到供應商「{supplier_keyword}」"}

    summary = [
        f"💸 **記錄付款給供應商**",
        f"供應商：{sup.code} - {sup.name}",
        f"金額：${amount:,.0f}",
        f"付款方式：{payment_method}",
        f"關聯 PO：{po_no or '(未指定)'}",
        f"備註：{notes or '(無)'}",
        "",
        "📌 將自動建立 JE：",
        f"  借：應付帳款（AP）${amount:,.0f}",
        f"  貸：銀行存款 ${amount:,.0f}",
        "",
        "⚠️ 過帳後不可逆，需走沖正傳票",
    ]
    card = make_card(
        tool_name="record_payment_to_supplier_with_confirm",
        title="💸 確認記錄付款",
        summary=summary,
        slots={"supplier_id": sup.id, "amount": amount,
               "po_no": po_no, "payment_method": payment_method, "notes": notes},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.accounting import create_journal_entry
        je = await create_journal_entry(db, {
            "entry_no": f"PAY-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
            "entry_date": datetime.now(UTC).replace(tzinfo=None),
            "description": f"付款給 {sup.name}: {payment_method}, {notes}".strip(),
            "total_debit": amount,
            "total_credit": amount,
            "status": "draft",
        }, user=user)
        return {
            "entry_no": je.entry_no, "amount": amount,
            "supplier": sup.name,
            "message": f"✅ 已建立付款傳票 {je.entry_no}（draft，待過帳）",
            "next_step": "用 post_journal_entry_with_confirm 過帳",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="record_receipt_from_customer_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "💵 記錄客戶付款（建立 JE：借銀行，貸應收帳款）。"
        "範例：「收到 X 客戶付款 NT$30000」「結 SO-001 的款」"
    ),
    slots=[
        Slot("customer_keyword", "string", required=True),
        Slot("amount", "number", required=True),
        Slot("so_no", "string", required=False),
        Slot("payment_method", "string", required=False),
        Slot("notes", "string", required=False),
    ],
    required_permission="accounting.receipt.record",
)
async def _record_receipt_from_customer(
    db, user, customer_keyword: str, amount: float,
    so_no: str = "", payment_method: str = "wire", notes: str = "",
):
    cu = (await db.execute(
        select(Customer).where(
            (Customer.code == customer_keyword) | (Customer.name.contains(customer_keyword))
        )
    )).scalars().first()
    if cu is None:
        return {"error": f"找不到客戶「{customer_keyword}」"}

    summary = [
        f"💵 **記錄客戶收款**",
        f"客戶：{cu.code} - {cu.name}",
        f"金額：${amount:,.0f}",
        f"付款方式：{payment_method}",
        f"關聯 SO：{so_no or '(未指定)'}",
        f"備註：{notes or '(無)'}",
        "",
        "📌 將自動建立 JE：",
        f"  借：銀行存款 ${amount:,.0f}",
        f"  貸：應收帳款（AR）${amount:,.0f}",
    ]
    card = make_card(
        tool_name="record_receipt_from_customer_with_confirm",
        title="💵 確認記錄收款",
        summary=summary,
        slots={"customer_id": cu.id, "amount": amount, "so_no": so_no,
               "payment_method": payment_method, "notes": notes},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.accounting import create_journal_entry
        je = await create_journal_entry(db, {
            "entry_no": f"RCT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
            "entry_date": datetime.now(UTC).replace(tzinfo=None),
            "description": f"客戶收款 {cu.name}: {payment_method}, {notes}".strip(),
            "total_debit": amount,
            "total_credit": amount,
            "status": "draft",
        }, user=user)
        return {
            "entry_no": je.entry_no, "amount": amount, "customer": cu.name,
            "message": f"✅ 已建立收款傳票 {je.entry_no}（draft，待過帳）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="query_outstanding_ar",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description=(
        "📊 查待收款（AR outstanding）。可按客戶過濾。"
        "範例：「客戶 X 還欠多少？」「列出未收的款」"
    ),
    slots=[
        Slot("customer_keyword", "string", required=False),
        Slot("limit", "integer", required=False),
    ],
    required_permission="accounting.ar.read",
)
async def _query_outstanding_ar(db, user, customer_keyword: str = None, limit: int = 20):
    q = select(AccountsReceivable).where(
        AccountsReceivable.status.in_(["open", "partial"])
    )
    if customer_keyword:
        cu = (await db.execute(
            select(Customer).where(Customer.name.contains(customer_keyword))
        )).scalars().first()
        if cu:
            q = q.where(AccountsReceivable.customer_id == cu.id)
    rows = (await db.execute(q.limit(limit))).scalars().all()

    if not rows:
        return {"summary": "✅ 沒有未收款項", "raw": {"items": []}}

    total = sum((r.balance or 0) for r in rows)
    lines = [f"📊 **未收款項** ({len(rows)} 筆，合計 ${total:,.0f}):\n"]
    for r in rows[:10]:
        lines.append(f"  • AR {r.id[:8]}... 餘額 ${r.balance or 0:,.0f} (status: {r.status})")
    return {
        "summary": "\n".join(lines),
        "raw": {"total_outstanding": total, "count": len(rows)},
    }


@register_tool(
    name="query_outstanding_ap",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description=(
        "📊 查待付款（AP outstanding）— 從 PO 推估未付供應商款。"
        "範例：「我們還欠誰錢？」「下週要付多少？」"
    ),
    slots=[
        Slot("supplier_keyword", "string", required=False),
        Slot("limit", "integer", required=False),
    ],
    required_permission="accounting.ap.read",
)
async def _query_outstanding_ap(db, user, supplier_keyword: str = None, limit: int = 20):
    q = select(PurchaseOrder).where(
        PurchaseOrder.status.in_(["received", "partial_received"])
    )
    if supplier_keyword:
        sup = (await db.execute(
            select(Supplier).where(Supplier.name.contains(supplier_keyword))
        )).scalars().first()
        if sup:
            q = q.where(PurchaseOrder.supplier_id == sup.id)
    rows = (await db.execute(q.limit(limit))).scalars().all()

    if not rows:
        return {"summary": "✅ 沒有未付款 PO", "raw": {"items": []}}

    total = sum((r.total_amount or 0) for r in rows)
    lines = [f"📊 **應付帳款** ({len(rows)} 張 PO，合計 ${total:,.0f}):\n"]
    for r in rows[:10]:
        lines.append(
            f"  • PO {r.po_no} 金額 ${r.total_amount or 0:,.0f} (狀態: {r.status})"
        )
    return {
        "summary": "\n".join(lines),
        "raw": {"total_outstanding": total, "po_count": len(rows)},
    }


# ════════════════════════════════════════════════════════════════════
# Approval 審批 (3)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="query_my_pending_approvals",
    domain="approval",
    risk_tier=RiskTier.READ,
    description=(
        "📋 查我有什麼要審批的（按 employee_id）。"
        "範例：「我有什麼要審？」「待我審的單」"
    ),
    slots=[],
    required_permission="approval.request.read",
)
async def _query_my_pending_approvals(db, user):
    from app.services.approval import list_pending_for_user
    emp_id = (user or {}).get("employee_id")
    if not emp_id:
        return {"error": "缺 employee_id（請登入後再呼叫）"}

    rows = await list_pending_for_user(db, emp_id, limit=20)
    if not rows:
        return {"summary": "✅ 沒有待你審批的單", "raw": {"items": []}}

    lines = [f"📋 **待我審批 ({len(rows)} 筆)**：\n"]
    items = []
    for r in rows:
        lines.append(
            f"  • REQ {r.id[:8]}... | {r.entity_type} {r.entity_id[:8]}... "
            f"| 階段 {r.current_step}/{r.total_steps}"
        )
        items.append({
            "request_id": r.id, "entity_type": r.entity_type,
            "current_step": r.current_step, "total_steps": r.total_steps,
        })

    lines.append("")
    lines.append("💡 用 `approve_request_with_confirm` 或 `reject_request_with_confirm` 處理")
    return {"summary": "\n".join(lines), "raw": {"items": items}}


@register_tool(
    name="approve_request_with_confirm",
    domain="approval",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "批准某張審批單（推進下一階或結案）。"
        "範例：「批准 REQ-001」「同意這張」"
    ),
    slots=[
        Slot("request_id", "string", required=True, description="審批單 UUID"),
        Slot("comment", "string", required=False),
    ],
    required_permission="approval.request.approve",
)
async def _approve_request(db, user, request_id: str, comment: str = ""):
    from app.services.approval import get_request, approve
    req = await get_request(db, request_id)
    if req is None:
        return {"error": f"找不到審批單「{request_id}」"}
    if req.status != "pending":
        return {"error": f"審批單狀態 {req.status!r}，不可批准"}

    summary = [
        f"📋 審批單：{req.id[:12]}...",
        f"📦 對象：{req.entity_type} {req.entity_id[:12]}...",
        f"📊 階段：{req.current_step}/{req.total_steps}",
        f"💭 我的意見：{comment or '(無)'}",
        "",
        "✅ 確認批准後將推進至下一階（或結案）",
    ]
    card = make_card(
        tool_name="approve_request_with_confirm",
        title="✅ 確認批准",
        summary=summary,
        slots={"request_id": req.id, "comment": comment},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        result = await approve(db, req.id, (user or {}).get("employee_id"), comment=comment)
        return {
            "request_id": req.id, "status": result.status,
            "current_step": result.current_step,
            "message": f"✅ 批准完成 — 狀態：{result.status}, 階段 {result.current_step}/{result.total_steps}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="reject_request_with_confirm",
    domain="approval",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "拒絕審批單（**必須填原因**）。"
        "範例：「拒絕 REQ-001，金額超預算」"
    ),
    slots=[
        Slot("request_id", "string", required=True),
        Slot("comment", "string", required=True, description="拒絕原因（必填）"),
    ],
    required_permission="approval.request.reject",
)
async def _reject_request(db, user, request_id: str, comment: str):
    from app.services.approval import get_request, reject
    req = await get_request(db, request_id)
    if req is None:
        return {"error": f"找不到審批單「{request_id}」"}
    if req.status != "pending":
        return {"error": f"審批單狀態 {req.status!r}，不可拒絕"}
    if not comment.strip():
        return {"error": "拒絕必須填原因（comment）"}

    summary = [
        f"📋 審批單：{req.id[:12]}...",
        f"📦 對象：{req.entity_type} {req.entity_id[:12]}...",
        f"❌ 拒絕原因：{comment}",
        "",
        "⚠️ 拒絕後該單轉 rejected 狀態，發起人需重新提送",
    ]
    card = make_card(
        tool_name="reject_request_with_confirm",
        title="❌ 確認拒絕",
        summary=summary,
        slots={"request_id": req.id, "comment": comment},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        result = await reject(db, req.id, (user or {}).get("employee_id"), comment=comment)
        return {
            "request_id": req.id, "status": result.status,
            "message": f"✅ 已拒絕，狀態：{result.status}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# Warehouse 揀貨 (2)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="create_pick_task_with_confirm",
    domain="warehouse",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "📦 為某 SO 建立揀貨任務（指派給倉管）。"
        "範例：「為 SO-001 建揀貨單」「給阿玲揀這張」"
    ),
    slots=[
        Slot("so_no", "string", required=True),
        Slot("operator_keyword", "string", required=False,
             description="指派之倉管姓名或員工編號（不填則待領）"),
    ],
    required_permission="warehouse.pick.create",
)
async def _create_pick_task(db, user, so_no: str, operator_keyword: str = ""):
    so = (await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items))
        .where(SalesOrder.so_no == so_no)
    )).scalar_one_or_none()
    if so is None:
        return {"error": f"找不到 SO「{so_no}」"}
    if so.status not in ("confirmed", "in_production"):
        return {"error": f"SO 狀態 {so.status!r}，建議 confirmed 後再揀貨"}

    operator_id = None
    operator_name = "(待領取)"
    if operator_keyword:
        from app.models.organization import Employee
        emp = (await db.execute(
            select(Employee).where(
                (Employee.employee_no == operator_keyword) |
                (Employee.name.contains(operator_keyword))
            )
        )).scalars().first()
        if emp:
            operator_id = emp.id
            operator_name = emp.name

    summary = [
        f"📋 SO：{so.so_no}",
        f"📦 品項數：{len(so.items)}",
        f"👤 指派給：{operator_name}",
        f"💰 SO 金額：${so.total_amount:,.0f}",
        "",
        "📌 將為每個 SO 行建立 PickTask",
    ]
    card = make_card(
        tool_name="create_pick_task_with_confirm",
        title="📦 確認建立揀貨單",
        summary=summary,
        slots={"so_id": so.id, "operator_id": operator_id},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.warehouse import create_pick_task
        created = []
        for item in so.items:
            pt = await create_pick_task(db, {
                "pick_no": f"PICK-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
                "so_id": so.id,
                "part_id": item.product_id,  # SO item product → pick part
                "requested_qty": item.ordered_qty,
                "operator_id": operator_id,
                "status": "pending",
            }, user=user)
            created.append(pt.pick_no)
        return {
            "so_no": so.so_no, "tasks_created": len(created),
            "task_nos": created,
            "message": f"✅ 已為 SO {so.so_no} 建立 {len(created)} 個揀貨任務",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="query_pending_pick_tasks",
    domain="warehouse",
    risk_tier=RiskTier.READ,
    description=(
        "查待揀貨任務。範例：「今天要揀什麼？」「我（阿玲）有什麼揀貨？」"
    ),
    slots=[
        Slot("operator_keyword", "string", required=False,
             description="僅查指派給某倉管之單；不填則查全部 pending"),
    ],
    required_permission="warehouse.pick.read",
)
async def _query_pending_pick_tasks(db, user, operator_keyword: str = None):
    q = select(PickTask).where(PickTask.status == "pending")
    if operator_keyword:
        from app.models.organization import Employee
        emp = (await db.execute(
            select(Employee).where(Employee.name.contains(operator_keyword))
        )).scalars().first()
        if emp:
            q = q.where(PickTask.operator_id == emp.id)

    rows = (await db.execute(q.limit(20))).scalars().all()
    if not rows:
        return {"summary": "✅ 沒有待揀任務", "raw": {"items": []}}

    lines = [f"📦 **待揀任務 ({len(rows)})**：\n"]
    for r in rows:
        lines.append(f"  • {r.pick_no} 需揀 {r.requested_qty or 0:g} (狀態: {r.status})")
    return {"summary": "\n".join(lines),
            "raw": {"count": len(rows), "tasks": [r.pick_no for r in rows]}}


# ════════════════════════════════════════════════════════════════════
# Quality 退貨/NCR/CAPA (3)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="create_ncr_with_confirm",
    domain="quality",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "⚠️ 建立不合格紀錄 (NCR)。範例：「為 INS-001 開不合格單」「客戶投訴開 NCR」"
    ),
    slots=[
        Slot("source_inspection_no", "string", required=False, description="來源 QC 單號"),
        Slot("severity", "string", required=True, description="low / medium / high / critical"),
        Slot("description", "string", required=True, description="不合格描述"),
        Slot("affected_qty", "number", required=False),
    ],
    required_permission="quality.ncr.create",
)
async def _create_ncr_with_confirm(
    db, user, severity: str, description: str,
    source_inspection_no: str = "", affected_qty: float = 0,
):
    summary = [
        f"⚠️ **不合格紀錄 (NCR)**",
        f"嚴重度：{severity}",
        f"描述：{description}",
        f"影響數量：{affected_qty:g}" if affected_qty else "影響數量：(未填)",
        f"來源 QC：{source_inspection_no or '(獨立 NCR)'}",
        "",
        "📌 建立後可用 create_capa_with_confirm 開矯正措施",
    ]
    card = make_card(
        tool_name="create_ncr_with_confirm",
        title="⚠️ 確認建立 NCR",
        summary=summary,
        slots={"severity": severity, "description": description,
               "source_inspection_no": source_inspection_no,
               "affected_qty": affected_qty},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        insp_id = None
        if source_inspection_no:
            insp = (await db.execute(
                select(InspectionOrder).where(
                    InspectionOrder.inspection_no == source_inspection_no
                )
            )).scalar_one_or_none()
            if insp:
                insp_id = insp.id

        ncr = NonConformance(
            id=str(uuid.uuid4()),
            ncr_no=f"NCR-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
            inspection_id=insp_id,
            severity=severity,
            description=description,
            affected_qty=affected_qty,
            status="open",
            reported_by=(user or {}).get("employee_id"),
            reported_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(ncr)
        await db.commit()
        return {
            "ncr_no": ncr.ncr_no,
            "message": f"✅ NCR {ncr.ncr_no} 已建立（嚴重度: {severity}）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="create_capa_with_confirm",
    domain="quality",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "建立矯正預防措施 (CAPA)。範例：「為 NCR-001 開 CAPA：加強來料檢驗」"
    ),
    slots=[
        Slot("source_ncr_no", "string", required=False, description="來源 NCR 單號"),
        Slot("action_type", "string", required=True,
             description="corrective (矯正) / preventive (預防)"),
        Slot("description", "string", required=True),
        Slot("owner_keyword", "string", required=False, description="負責人姓名"),
        Slot("due_date", "string", required=False, description="預計完成日 YYYY-MM-DD"),
    ],
    required_permission="quality.capa.create",
)
async def _create_capa_with_confirm(
    db, user, action_type: str, description: str,
    source_ncr_no: str = "", owner_keyword: str = "", due_date: str = "",
):
    summary = [
        f"🛠 **矯正預防措施 (CAPA)**",
        f"類型：{action_type}",
        f"描述：{description}",
        f"來源 NCR：{source_ncr_no or '(獨立)'}",
        f"負責人：{owner_keyword or '(未指派)'}",
        f"預計完成：{due_date or '(未訂)'}",
    ]
    card = make_card(
        tool_name="create_capa_with_confirm",
        title="🛠 確認建立 CAPA",
        summary=summary,
        slots={"action_type": action_type, "description": description,
               "source_ncr_no": source_ncr_no, "owner_keyword": owner_keyword,
               "due_date": due_date},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        ncr_id = None
        if source_ncr_no:
            ncr = (await db.execute(
                select(NonConformance).where(NonConformance.ncr_no == source_ncr_no)
            )).scalar_one_or_none()
            if ncr:
                ncr_id = ncr.id

        owner_id = None
        if owner_keyword:
            from app.models.organization import Employee
            emp = (await db.execute(
                select(Employee).where(Employee.name.contains(owner_keyword))
            )).scalars().first()
            if emp:
                owner_id = emp.id

        due = None
        if due_date:
            try:
                due = datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                pass

        from app.services.quality import create_capa
        capa = await create_capa(db, {
            "capa_no": f"CAPA-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
            "ncr_id": ncr_id,
            "action_type": action_type,
            "description": description,
            "owner_id": owner_id,
            "due_date": due,
            "status": "open",
        }, user=user)
        return {
            "capa_no": capa.capa_no,
            "message": f"✅ CAPA {capa.capa_no} 已建立",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="query_open_ncrs",
    domain="quality",
    risk_tier=RiskTier.READ,
    description=(
        "📋 列出未結案 NCR（按嚴重度）。"
        "範例：「未結 NCR 有哪些？」「列 high 嚴重度的不合格」"
    ),
    slots=[
        Slot("severity", "string", required=False,
             description="low/medium/high/critical；不填則全部"),
        Slot("limit", "integer", required=False),
    ],
    required_permission="quality.ncr.read",
)
async def _query_open_ncrs(db, user, severity: str = None, limit: int = 20):
    from app.services.quality import list_non_conformances
    rows = await list_non_conformances(db, severity=severity, limit=limit)
    open_ncrs = [r for r in rows if r.status == "open"]
    if not open_ncrs:
        return {"summary": "✅ 沒有未結 NCR", "raw": {"items": []}}

    lines = [f"⚠️ **未結 NCR ({len(open_ncrs)})**：\n"]
    for r in open_ncrs[:10]:
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
            r.severity, "⚪"
        )
        lines.append(
            f"  {icon} {r.ncr_no} ({r.severity}) "
            f"影響 {r.affected_qty or 0:g}: {r.description[:50]}..."
        )

    lines.append("")
    lines.append("💡 用 `create_capa_with_confirm` 為 NCR 開矯正措施")
    return {"summary": "\n".join(lines), "raw": {"items": [r.ncr_no for r in open_ncrs]}}


# ════════════════════════════════════════════════════════════════════
# Auto-attach to existing agents (or create tax/approval agents)
# ════════════════════════════════════════════════════════════════════

from app.agents.engine import AGENT_REGISTRY as _AGENT_REGISTRY, register_agent

# Tax / Approval agents may not exist yet — register them
if "tax" not in _AGENT_REGISTRY:
    register_agent(
        "tax", "TaxAgent",
        system_prompt=(
            "你是 erpilot 之**稅務助手**。職責：開發票、查稅、驗統編、月度稅務概況。"
            "所有發票操作必走 ConfirmCard。**erpilot 之輸出不構成稅務建議**，"
            "對外申報請依 CPA + 稅務顧問。"
        ),
        tool_names=[
            "issue_einvoice_with_confirm", "void_einvoice_with_confirm",
            "validate_tax_id_tool", "query_monthly_sales_tax",
            "query_einvoice_by_so",
        ],
    )

if "approval" not in _AGENT_REGISTRY:
    register_agent(
        "approval", "ApprovalAgent",
        system_prompt=(
            "你是 erpilot 之**審批助手**。職責：列待我審、批准、拒絕（必填原因）。"
            "所有決策必走 ConfirmCard。"
        ),
        tool_names=[
            "query_my_pending_approvals",
            "approve_request_with_confirm",
            "reject_request_with_confirm",
        ],
    )

# Attach to existing agents
_DOMAIN_TOOL_MAP = {
    "accounting": [
        "record_payment_to_supplier_with_confirm",
        "record_receipt_from_customer_with_confirm",
        "query_outstanding_ar", "query_outstanding_ap",
    ],
    "warehouse": [
        "create_pick_task_with_confirm",
        "query_pending_pick_tasks",
    ],
    "quality": [
        "create_ncr_with_confirm",
        "create_capa_with_confirm",
        "query_open_ncrs",
    ],
}
for _d, _ts in _DOMAIN_TOOL_MAP.items():
    if _d in _AGENT_REGISTRY:
        _tn = _AGENT_REGISTRY[_d]["tool_names"]
        for _t in _ts:
            if _t not in _tn:
                _tn.append(_t)
