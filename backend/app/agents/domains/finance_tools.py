"""Finance closure tools（Phase B1）— AP / 付款 / 收款 / 銀行帳戶。

讓金流閉環也能「用講的」操作（Ouvoca 對話式 DNA）：
  - query_payables / query_bank_accounts（read）
  - create_bank_account_with_confirm / record_payment_with_confirm /
    record_receipt_with_confirm（hard-write → ConfirmCard）
"""
from __future__ import annotations

from sqlalchemy import select

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import RiskTier, Slot, register_tool
from app.models.finance import AccountsPayable, BankAccount, Payment, Receipt

# ============================================================
# Read tools
# ============================================================

@register_tool(
    name="query_payables",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="查詢應付帳款（AP）清單：未付、逾期、或全部。範例：「我們欠供應商多少錢？」",
    slots=[
        Slot("status", "string", required=False,
             description="過濾狀態：unpaid / partial / paid / void（預設全部）"),
    ],
    required_permission="accounting.ap.read",
)
async def _query_payables(db, user, status: str | None = None):
    q = select(AccountsPayable).order_by(AccountsPayable.due_date)
    if status:
        q = q.where(AccountsPayable.status == status)
    rows = list((await db.execute(q)).scalars().all())
    return {
        "total": len(rows),
        "payables": [
            {
                "id": r.id,
                "supplier_id": r.supplier_id,
                "invoice_no": r.invoice_no,
                "due_date": r.due_date.isoformat() if r.due_date else None,
                "amount": r.amount,
                "paid_amount": r.paid_amount,
                "balance": round((r.amount or 0) - (r.paid_amount or 0), 2),
                "status": r.status,
                "aging_days": r.aging_days,
            }
            for r in rows
        ],
    }


@register_tool(
    name="query_bank_accounts",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="查詢銀行帳戶與餘額。範例：「銀行還有多少錢？」",
    slots=[],
    required_permission="accounting.bank.read",
)
async def _query_bank_accounts(db, user):
    rows = list((await db.execute(
        select(BankAccount).order_by(BankAccount.code)
    )).scalars().all())
    return {
        "total": len(rows),
        "accounts": [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "bank_name": r.bank_name,
                "account_no": r.account_no,
                "currency": r.currency,
                "current_balance": r.current_balance,
                "is_active": r.is_active,
            }
            for r in rows
        ],
    }


@register_tool(
    name="query_payments",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="查詢付款單與收款單。範例：「上個月付了哪些錢？」",
    slots=[
        Slot("kind", "string", required=False,
             description="payment（付款）/ receipt（收款），預設兩者都回"),
        Slot("limit", "integer", required=False, description="回傳筆數上限（預設 50）"),
    ],
    required_permission="accounting.payment.read",
)
async def _query_payments(db, user, kind: str | None = None, limit: int = 50):
    out = {}
    if kind in (None, "payment"):
        pays = list((await db.execute(
            select(Payment).order_by(Payment.payment_date.desc()).limit(limit)
        )).scalars().all())
        out["payments"] = [
            {"payment_no": p.payment_no, "supplier_id": p.supplier_id,
             "amount": p.amount, "payment_date": p.payment_date.isoformat() if p.payment_date else None,
             "method": p.method, "status": p.status}
            for p in pays
        ]
    if kind in (None, "receipt"):
        recs = list((await db.execute(
            select(Receipt).order_by(Receipt.receipt_date.desc()).limit(limit)
        )).scalars().all())
        out["receipts"] = [
            {"receipt_no": r.receipt_no, "customer_id": r.customer_id,
             "amount": r.amount, "receipt_date": r.receipt_date.isoformat() if r.receipt_date else None,
             "method": r.method, "status": r.status}
            for r in recs
        ]
    return out


# ============================================================
# Hard-write tools
# ============================================================

@register_tool(
    name="create_bank_account_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description="新增銀行帳戶主檔。範例：「新增台銀帳戶 台灣銀行 大安分行 1234-5678」",
    slots=[
        Slot("name", "string", required=True, description="帳戶名稱"),
        Slot("bank_name", "string", required=False, description="銀行名稱"),
        Slot("branch_name", "string", required=False, description="分行名稱"),
        Slot("account_no", "string", required=False, description="帳號"),
        Slot("opening_balance", "number", required=False, description="期初餘額（預設 0）"),
        Slot("currency", "string", required=False, description="幣別（預設 TWD）"),
    ],
    required_permission="accounting.bank.write",
)
async def _create_bank_account_with_confirm(db, user, name, bank_name="", branch_name="", account_no="", opening_balance=0, currency="TWD"):
    from app.services.finance import create_bank_account
    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="create_bank_account_with_confirm",
        title=f"新增銀行帳戶「{name}」",
        summary=[
            f"帳戶名稱：{name}",
            f"銀行：{bank_name or '—'} {branch_name or ''}".rstrip(),
            f"帳號：{account_no or '—'}",
            f"幣別：{currency} | 期初餘額：{opening_balance:g}",
        ],
        slots={"name": name, "bank_name": bank_name, "branch_name": branch_name,
               "account_no": account_no, "opening_balance": opening_balance, "currency": currency},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        acc = await create_bank_account(db, {
            "name": name, "bank_name": bank_name, "branch_name": branch_name,
            "account_no": account_no, "opening_balance": opening_balance, "currency": currency,
        }, user=user)
        return {"created": True, "id": acc.id, "code": acc.code, "name": acc.name}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="record_payment_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description="記錄一筆付款（給供應商）。範例：「付長江 5/15 那張發票 50,000 元，從台銀帳戶」",
    slots=[
        Slot("supplier_keyword", "string", required=True, description="供應商名稱或編號"),
        Slot("amount", "number", required=True, description="付款金額"),
        Slot("payable_invoice_no", "string", required=False, description="要沖的 AP 發票號（可省略，先全額付款）"),
        Slot("bank_account_keyword", "string", required=False, description="銀行帳戶名稱或代碼"),
        Slot("method", "string", required=False, description="cash / transfer / check（預設 transfer）"),
        Slot("reference", "string", required=False, description="備註/參考"),
    ],
    required_permission="accounting.payment.create",
)
async def _record_payment_with_confirm(
    db, user, supplier_keyword, amount,
    payable_invoice_no="", bank_account_keyword="", method="transfer", reference="",
):
    from app.models.purchase import Supplier
    from app.services.finance import create_payment

    supplier = (await db.execute(
        select(Supplier).where(
            (Supplier.code == supplier_keyword) | (Supplier.name.like(f"%{supplier_keyword}%"))
        )
    )).scalars().first()
    if supplier is None:
        return {"error": f"找不到供應商「{supplier_keyword}」"}

    payable_id = None
    ap = None
    if payable_invoice_no:
        ap = (await db.execute(
            select(AccountsPayable).where(AccountsPayable.invoice_no == payable_invoice_no)
        )).scalars().first()
        if ap is None or ap.supplier_id != supplier.id:
            return {"error": f"找不到供應商 {supplier.name} 的發票 {payable_invoice_no!r}"}
        payable_id = ap.id

    bank_account_id = None
    if bank_account_keyword:
        bank = (await db.execute(
            select(BankAccount).where(
                (BankAccount.code == bank_account_keyword) | (BankAccount.name.like(f"%{bank_account_keyword}%"))
            )
        )).scalars().first()
        if bank is None:
            return {"error": f"找不到銀行帳戶「{bank_account_keyword}」"}
        bank_account_id = bank.id

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="record_payment_with_confirm",
        title=f"付款 {amount:g} 給 {supplier.name}",
        summary=[
            f"供應商：{supplier.name}（{supplier.code}）",
            f"金額：{amount:g}",
            f"方式：{method}",
            f"沖應付：{payable_invoice_no or '（不指定）'}",
            f"銀行帳戶：{bank_account_keyword or '（不指定）'}",
        ],
        slots={"supplier_id": supplier.id, "amount": amount, "payable_id": payable_id,
               "bank_account_id": bank_account_id, "method": method, "reference": reference},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        pay = await create_payment(db, {
            "supplier_id": supplier.id, "amount": amount, "payable_id": payable_id,
            "bank_account_id": bank_account_id, "method": method, "reference": reference,
        }, user=user)
        return {"payment_no": pay.payment_no, "amount": pay.amount, "status": pay.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="record_receipt_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description="記錄一筆收款（客戶付款）。範例：「收到富士康 30,000 元，存台銀」",
    slots=[
        Slot("customer_keyword", "string", required=True, description="客戶名稱或編號"),
        Slot("amount", "number", required=True, description="收款金額"),
        Slot("receivable_invoice_no", "string", required=False, description="要沖的 AR 發票號（可省略）"),
        Slot("bank_account_keyword", "string", required=False, description="銀行帳戶名稱或代碼"),
        Slot("method", "string", required=False, description="cash / transfer / check（預設 transfer）"),
        Slot("reference", "string", required=False, description="備註/參考"),
    ],
    required_permission="accounting.receipt.create",
)
async def _record_receipt_with_confirm(
    db, user, customer_keyword, amount,
    receivable_invoice_no="", bank_account_keyword="", method="transfer", reference="",
):
    from app.models.accounting import AccountsReceivable
    from app.models.crm_sales import Customer
    from app.services.finance import create_receipt

    customer = (await db.execute(
        select(Customer).where(
            (Customer.code == customer_keyword) | (Customer.name.like(f"%{customer_keyword}%"))
        )
    )).scalars().first()
    if customer is None:
        return {"error": f"找不到客戶「{customer_keyword}」"}

    receivable_id = None
    if receivable_invoice_no:
        ar = (await db.execute(
            select(AccountsReceivable).where(AccountsReceivable.invoice_no == receivable_invoice_no)
        )).scalars().first()
        if ar is None or ar.customer_id != customer.id:
            return {"error": f"找不到客戶 {customer.name} 的發票 {receivable_invoice_no!r}"}
        receivable_id = ar.id

    bank_account_id = None
    if bank_account_keyword:
        bank = (await db.execute(
            select(BankAccount).where(
                (BankAccount.code == bank_account_keyword) | (BankAccount.name.like(f"%{bank_account_keyword}%"))
            )
        )).scalars().first()
        if bank is None:
            return {"error": f"找不到銀行帳戶「{bank_account_keyword}」"}
        bank_account_id = bank.id

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="record_receipt_with_confirm",
        title=f"收款 {amount:g} 來自 {customer.name}",
        summary=[
            f"客戶：{customer.name}（{customer.code}）",
            f"金額：{amount:g}",
            f"方式：{method}",
            f"沖應收：{receivable_invoice_no or '（不指定）'}",
            f"銀行帳戶：{bank_account_keyword or '（不指定）'}",
        ],
        slots={"customer_id": customer.id, "amount": amount, "receivable_id": receivable_id,
               "bank_account_id": bank_account_id, "method": method, "reference": reference},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        rec = await create_receipt(db, {
            "customer_id": customer.id, "amount": amount, "receivable_id": receivable_id,
            "bank_account_id": bank_account_id, "method": method, "reference": reference,
        }, user=user)
        return {"receipt_no": rec.receipt_no, "amount": rec.amount, "status": rec.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


# ============================================================
# M2 — 財務閉環 tools（三大報表 / 401-405 / 3-Way Match / 票據 / 固定資產）
# ============================================================

@register_tool(
    name="query_financial_statements",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description=(
        "產出三大報表：試算表 / 損益表 / 資產負債表。"
        "範例：「上個月的損益表」「202608 資產負債表」「試算表平不平衡」"
    ),
    slots=[
        Slot("statement", "string", required=True,
             description="trial_balance / income_statement / balance_sheet"),
        Slot("period", "string", required=False,
             description="期間 YYYYMM（預設全部期間）"),
    ],
    required_permission="accounting.statement.read",
)
async def _query_financial_statements(db, user, statement: str, period: str | None = None):
    from app.services.financial_statements import (
        balance_sheet,
        income_statement,
        trial_balance,
    )
    if statement == "trial_balance":
        return await trial_balance(db, period)
    if statement == "income_statement":
        return await income_statement(db, period)
    if statement == "balance_sheet":
        return await balance_sheet(db, period)
    return {"error": f"未知報表類型 {statement!r}",
            "allowed": ["trial_balance", "income_statement", "balance_sheet"]}


@register_tool(
    name="query_tax_report_401_405",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="產出台灣 401/405 營業稅申報表（銷項/進項/應納稅額）。範例：「6 月的 401 405」",
    slots=[
        Slot("period", "string", required=True, description="期間 YYYYMM（如 202606）"),
    ],
    required_permission="accounting.tax_report",
)
async def _query_tax_report_401_405(db, user, period: str):
    from app.services.tax_report_tw import tax_report_401_405
    return await tax_report_401_405(db, period)


@register_tool(
    name="query_supplier_invoice_matches",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="列出供應商發票與 3-Way Match 狀態。範例：「哪些發票數量對不上」",
    slots=[
        Slot("status", "string", required=False,
             description="過濾：matched / qty_variance / price_variance / unmatched / received"),
    ],
    required_permission="accounting.supplier_invoice.read",
)
async def _query_supplier_invoice_matches(db, user, status: str | None = None):
    from app.services.three_way_match import list_invoice_matches
    return {"total": len(await list_invoice_matches(db, status)),
            "invoices": await list_invoice_matches(db, status)}


@register_tool(
    name="record_supplier_invoice_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "建立供應商發票並執行 3-Way Match（PO ↔ 收貨 ↔ 發票勾稽）。"
        "範例：「記錄長江的發票 INV-100 十萬元，對應 PO-...」"
    ),
    slots=[
        Slot("supplier_keyword", "string", required=True, description="供應商名稱或編號"),
        Slot("invoice_no", "string", required=True, description="供應商發票號碼"),
        Slot("po_no", "string", required=False, description="關聯 PO 單號（可省略）"),
        Slot("items", "array", required=True,
             description='發票行清單：[{"part_no": "...", "qty": 100, "unit_price": 5}]（可含 po_item_id）'),
        Slot("tax_amount", "number", required=False, description="稅額（預設 5% 由銷售額計算）"),
    ],
    required_permission="accounting.supplier_invoice.create",
)
async def _record_supplier_invoice_with_confirm(
    db, user, supplier_keyword, invoice_no, items, po_no="", tax_amount=None,
):
    from app.agents.confirm_card import make_card, stash_card
    from app.models.inventory import Part
    from app.models.purchase import PurchaseOrder, Supplier
    from app.services.three_way_match import create_supplier_invoice

    supplier = (await db.execute(
        select(Supplier).where(
            (Supplier.code == supplier_keyword) | (Supplier.name.like(f"%{supplier_keyword}%"))
        )
    )).scalars().first()
    if supplier is None:
        return {"error": f"找不到供應商「{supplier_keyword}」"}

    po = None
    if po_no:
        po = (await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.po_no == po_no)
        )).scalars().first()
        if po is None or po.supplier_id != supplier.id:
            return {"error": f"找不到供應商 {supplier.name} 的 PO {po_no!r}"}

    resolved_items = []
    for raw in items:
        part = None
        if raw.get("part_id"):
            part = (await db.execute(
                select(Part).where(Part.id == raw["part_id"])
            )).scalars().first()
        elif raw.get("part_no"):
            part = (await db.execute(
                select(Part).where(Part.part_no == raw["part_no"])
            )).scalars().first()
        if part is None:
            return {"error": f"找不到料件 {raw.get('part_no') or raw.get('part_id')!r}"}
        resolved_items.append({
            "part_id": part.id,
            "qty": float(raw["qty"]),
            "unit_price": float(raw.get("unit_price", 0)),
        })

    sales = round(sum(i["qty"] * i["unit_price"] for i in resolved_items), 2)
    tax = float(tax_amount) if tax_amount is not None else round(sales * 0.05, 2)
    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="record_supplier_invoice_with_confirm",
        title=f"記錄供應商發票 {invoice_no}（{supplier.name}）",
        summary=[
            f"供應商：{supplier.name}（{supplier.code}）",
            f"發票：{invoice_no} | 銷售額 {sales:g} | 稅 {tax:g}",
            f"行數：{len(resolved_items)}",
            f"關聯 PO：{po.po_no if po else '（未關聯，將標 unmatched）'}",
            "建立後自動執行 3-Way Match 勾稽",
        ],
        slots={"invoice_no": invoice_no, "supplier_id": supplier.id, "po_id": po.id if po else None,
               "items": resolved_items, "sales_amount": sales, "tax_amount": tax},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        inv = await create_supplier_invoice(db, {
            "invoice_no": invoice_no,
            "supplier_id": supplier.id,
            "po_id": po.id if po else None,
            "invoice_date": None,
            "items": resolved_items,
            "sales_amount": sales,
            "tax_amount": tax,
        }, user=user)
        return {"invoice_id": inv.id, "invoice_no": inv.invoice_no, "status": inv.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="query_fixed_assets",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="查詢固定資產與累計折舊。範例：「機器設備現在帳面價值多少」",
    slots=[],
    required_permission="accounting.fixed_asset.read",
)
async def _query_fixed_assets(db, user):
    from app.services.fixed_assets import list_fixed_assets
    rows = await list_fixed_assets(db)
    return {"total": len(rows), "assets": rows}


@register_tool(
    name="create_fixed_asset_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description="新增固定資產（成本/殘值/耐用月數，自動算月折舊）。範例：「新增 CNC 車床 100 萬，耐用 60 個月」",
    slots=[
        Slot("name", "string", required=True, description="資產名稱"),
        Slot("cost", "number", required=True, description="取得成本"),
        Slot("useful_life_months", "integer", required=True, description="耐用月數"),
        Slot("category", "string", required=False,
             description="machinery / building / vehicle / furniture（預設 machinery）"),
        Slot("salvage_value", "number", required=False, description="殘值（預設 0）"),
        Slot("acquisition_date", "string", required=False, description="取得日期 YYYY-MM-DD"),
    ],
    required_permission="accounting.fixed_asset.create",
)
async def _create_fixed_asset_with_confirm(
    db, user, name, cost, useful_life_months,
    category="machinery", salvage_value=0, acquisition_date=None,
):

    from app.agents.confirm_card import make_card, stash_card
    from app.services.fixed_assets import create_fixed_asset

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="create_fixed_asset_with_confirm",
        title=f"新增固定資產「{name}」",
        summary=[
            f"名稱：{name}",
            f"成本：{cost:g} | 殘值：{salvage_value:g} | 耐用：{useful_life_months} 個月",
            f"類別：{category}",
        ],
        slots={"name": name, "cost": cost, "useful_life_months": useful_life_months,
               "category": category, "salvage_value": salvage_value},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        asset = await create_fixed_asset(db, {
            "name": name, "cost": cost, "useful_life_months": useful_life_months,
            "category": category, "salvage_value": salvage_value,
            "acquisition_date": acquisition_date,
        }, user=user)
        return {"id": asset.id, "code": asset.code, "monthly_depreciation": asset.monthly_depreciation}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="post_depreciation_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description="過帳某固定資產一個月的折舊傳票（DR 折舊費用 / CR 累計折舊）。範例：「幫 CNC 車床提 8 月折舊」",
    slots=[
        Slot("asset_keyword", "string", required=True, description="資產代碼或名稱"),
        Slot("period", "string", required=True, description="折舊期間 YYYYMM"),
    ],
    required_permission="accounting.fixed_asset.depreciate",
)
async def _post_depreciation_with_confirm(db, user, asset_keyword: str, period: str):
    from app.agents.confirm_card import make_card, stash_card
    from app.models.finance import FixedAsset
    from app.services.fixed_assets import post_monthly_depreciation

    asset = (await db.execute(
        select(FixedAsset).where(
            (FixedAsset.code == asset_keyword) | (FixedAsset.name.like(f"%{asset_keyword}%"))
        )
    )).scalars().first()
    if asset is None:
        return {"error": f"找不到固定資產「{asset_keyword}」"}

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="post_depreciation_with_confirm",
        title=f"過帳折舊 {asset.code} {asset.name}（{period}）",
        summary=[
            f"資產：{asset.code} {asset.name}",
            f"期間：{period} | 月折舊：{asset.monthly_depreciation:g}",
            f"累計折舊（目前）：{asset.accumulated_depreciation:g}",
            "產生傳票：DR 折舊費用 / CR 累計折舊",
        ],
        slots={"asset_id": asset.id, "period": period},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        updated = await post_monthly_depreciation(db, asset.id, period, user)
        return {
            "asset_code": updated.code,
            "accumulated_depreciation": updated.accumulated_depreciation,
            "status": updated.status,
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="query_promissory_notes",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description="查詢票據（應收/應付票據、到期提示）。範例：「這個月到期的票有哪些」",
    slots=[
        Slot("status", "string", required=False,
             description="on_hand / endorsed / deposited / cleared / returned / void"),
    ],
    required_permission="accounting.note.read",
)
async def _query_promissory_notes(db, user, status: str | None = None):
    from app.models.finance import PromissoryNote
    q = select(PromissoryNote).order_by(PromissoryNote.due_date)
    if status:
        q = q.where(PromissoryNote.status == status)
    rows = list((await db.execute(q)).scalars().all())
    return {
        "total": len(rows),
        "notes": [
            {
                "id": r.id, "note_type": r.note_type, "party_name": r.party_name,
                "bank_name": r.bank_name, "check_no": r.check_no, "amount": r.amount,
                "issue_date": r.issue_date.isoformat() if r.issue_date else None,
                "due_date": r.due_date.isoformat() if r.due_date else None,
                "status": r.status,
            }
            for r in rows
        ],
    }


@register_tool(
    name="record_promissory_note_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "記錄一張票據（應收票據=客戶開的票 / 應付票據=我們開的票）。"
        "範例：「記錄客戶開的 5 萬元支票，10/1 到期」"
    ),
    slots=[
        Slot("note_type", "string", required=True, description="receivable / payable"),
        Slot("party_name", "string", required=True, description="對方名稱（客戶/供應商）"),
        Slot("amount", "number", required=True, description="票面金額"),
        Slot("due_date", "string", required=True, description="到期日 YYYY-MM-DD"),
        Slot("bank_name", "string", required=False, description="付款銀行"),
        Slot("check_no", "string", required=False, description="票號"),
        Slot("issue_date", "string", required=False, description="發票日 YYYY-MM-DD"),
    ],
    required_permission="accounting.note.create",
)
async def _record_promissory_note_with_confirm(
    db, user, note_type, party_name, amount, due_date,
    bank_name="", check_no="", issue_date=None,
):
    from datetime import datetime

    from app.agents.confirm_card import make_card, stash_card
    from app.models.finance import PromissoryNote

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="record_promissory_note_with_confirm",
        title=f"記錄{'應收' if note_type == 'receivable' else '應付'}票據 {check_no or party_name}",
        summary=[
            f"類型：{'應收' if note_type == 'receivable' else '應付'}票據",
            f"對方：{party_name} | 金額：{amount:g}",
            f"到期日：{due_date}",
            f"銀行：{bank_name or '—'} | 票號：{check_no or '—'}",
        ],
        slots={"note_type": note_type, "party_name": party_name, "amount": amount,
               "due_date": due_date, "bank_name": bank_name, "check_no": check_no},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        note = PromissoryNote(
            note_type=note_type,
            party_id="",
            party_name=party_name,
            bank_name=bank_name or None,
            check_no=check_no or None,
            amount=amount,
            issue_date=datetime.fromisoformat(issue_date) if issue_date else datetime.utcnow(),
            due_date=datetime.fromisoformat(due_date),
            status="on_hand",
            created_by=employee_id,
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return {"id": note.id, "check_no": note.check_no, "amount": note.amount, "status": note.status}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="query_wo_cost",
    domain="production",
    risk_tier=RiskTier.READ,
    description="彙總單張工單成本（材料 + 人工 + 製造費用）。範例：「WO-001 這張單是賺是賠」",
    slots=[
        Slot("wo_keyword", "string", required=True, description="工單號碼或關鍵字"),
    ],
    required_permission="production.work_order.cost",
)
async def _query_wo_cost(db, user, wo_keyword: str):
    from app.models.production import ProductionOrder
    from app.services.production_cost import aggregate_wo_cost

    wo = (await db.execute(
        select(ProductionOrder).where(
            (ProductionOrder.wo_no == wo_keyword) | (ProductionOrder.wo_no.like(f"%{wo_keyword}%"))
        )
    )).scalars().first()
    if wo is None:
        return {"error": f"找不到工單「{wo_keyword}」"}
    return await aggregate_wo_cost(db, wo.id)


@register_tool(
    name="settle_cogs_with_confirm",
    domain="accounting",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "月結銷貨成本：期間內出貨 × 成本 → 傳票（DR 銷貨成本 / CR 製成品）。"
        "範例：「結 8 月銷貨成本」"
    ),
    slots=[
        Slot("period", "string", required=True, description="期間 YYYY-MM（如 2026-08）"),
    ],
    required_permission="accounting.cost_settle.execute",
)
async def _settle_cogs_with_confirm(db, user, period: str):
    from app.services.production_cost import settle_cogs
    from app.agents.confirm_card import make_card, stash_card

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="settle_cogs_with_confirm",
        title=f"結轉 {period} 銷貨成本",
        summary=[
            f"期間：{period}",
            "計算方式：期間內出貨明細 × Part.unit_cost",
            "產生傳票：DR 5100 銷貨成本 / CR 1340 製成品",
            "⚠️ 重複執行會產生多張結轉傳票（結帳前請確認）",
        ],
        slots={"period": period},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        return await settle_cogs(db, period, user)

    await stash_card(card, execute)
    return card.to_chat_payload()
