"""金流服務（Phase B1）— AP / 付款 / 收款 / 銀行帳戶。

設計原則：
  - 付款/收款單號走集中式 document_numbering（Phase C1）
  - post 時原子更新 AP/AR 的 paid_amount + 銀行帳戶 current_balance
  - 狀態機：Payment/Receipt 走 draft → posted → void
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.accounting import AccountsReceivable
from app.models.finance import AccountsPayable, BankAccount, Payment, Receipt


async def create_bank_account(db: AsyncSession, data: dict, user: dict | None = None) -> BankAccount:
    code = data.get("code") or data.get("name", "").strip()[:20].replace(" ", "_")
    account = BankAccount(
        code=code,
        name=data["name"],
        bank_name=data.get("bank_name"),
        branch_name=data.get("branch_name"),
        account_no=data.get("account_no"),
        currency=data.get("currency", "TWD"),
        opening_balance=float(data.get("opening_balance", 0) or 0),
        current_balance=float(data.get("opening_balance", 0) or 0),
        is_active=data.get("is_active", True),
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def create_payment(
    db: AsyncSession,
    data: dict,
    user: dict | None = None,
    *,
    post: bool = True,
) -> Payment:
    """建立付款單；post=True 時同時沖 AP + 扣銀行餘額。"""
    from app.services.document_numbering import next_document_no

    supplier_id = data["supplier_id"]
    amount = float(data["amount"])
    if amount <= 0:
        raise BusinessRuleError("付款金額必須大於 0")

    payable_id = data.get("payable_id")
    if payable_id:
        ap = (await db.execute(
            select(AccountsPayable).where(AccountsPayable.id == payable_id)
        )).scalar_one_or_none()
        if ap is None:
            raise NotFoundError("應付帳款不存在", payable_id=payable_id)
        if ap.supplier_id != supplier_id:
            raise BusinessRuleError("付款供應商與應付帳款供應商不一致")
        if ap.status in ("paid", "void"):
            raise BusinessRuleError(f"此應付帳款狀態 {ap.status!r} 不可再付款")

    bank_account = None
    if data.get("bank_account_id"):
        bank_account = (await db.execute(
            select(BankAccount).where(BankAccount.id == data["bank_account_id"])
        )).scalar_one_or_none()
        if bank_account is None:
            raise NotFoundError("銀行帳戶不存在", bank_account_id=data["bank_account_id"])

    payment_no = await next_document_no(db, "PAYMENT")
    payment = Payment(
        payment_no=payment_no,
        supplier_id=supplier_id,
        payable_id=payable_id,
        bank_account_id=data.get("bank_account_id"),
        amount=amount,
        payment_date=data.get("payment_date") or datetime.now(UTC).replace(tzinfo=None),
        method=data.get("method", "transfer"),
        reference=data.get("reference"),
        status="posted" if post else "draft",
        created_by=(user or {}).get("employee_id"),
    )
    db.add(payment)

    if post:
        # 沖 AP
        if payable_id and ap:
            # 健檢 #11：超付防呆 — 累計付款不可超過 AP 金額
            if (ap.paid_amount or 0) + amount > ap.amount:
                raise BusinessRuleError(
                    f"超付：此應付帳款 {ap.amount:g} 已付 {ap.paid_amount or 0:g}，"
                    f"再加 {amount:g} 會超過",
                    payable_id=payable_id,
                )
            ap.paid_amount = (ap.paid_amount or 0) + amount
            remaining = ap.amount - ap.paid_amount
            ap.status = "paid" if remaining <= 0 else "partial"
        # 扣銀行餘額
        if bank_account:
            bank_account.current_balance = (bank_account.current_balance or 0) - amount

    await db.commit()
    await db.refresh(payment)
    return payment


async def create_receipt(
    db: AsyncSession,
    data: dict,
    user: dict | None = None,
    *,
    post: bool = True,
) -> Receipt:
    """建立收款單；post=True 時同時沖 AR + 加銀行餘額。"""
    from app.services.document_numbering import next_document_no

    customer_id = data["customer_id"]
    amount = float(data["amount"])
    if amount <= 0:
        raise BusinessRuleError("收款金額必須大於 0")

    receivable_id = data.get("receivable_id")
    if receivable_id:
        ar = (await db.execute(
            select(AccountsReceivable).where(AccountsReceivable.id == receivable_id)
        )).scalar_one_or_none()
        if ar is None:
            raise NotFoundError("應收帳款不存在", receivable_id=receivable_id)
        if ar.customer_id != customer_id:
            raise BusinessRuleError("收款客戶與應收帳款客戶不一致")
        if ar.status in ("paid", "void"):
            raise BusinessRuleError(f"此應收帳款狀態 {ar.status!r} 不可再收款")

    bank_account = None
    if data.get("bank_account_id"):
        bank_account = (await db.execute(
            select(BankAccount).where(BankAccount.id == data["bank_account_id"])
        )).scalar_one_or_none()
        if bank_account is None:
            raise NotFoundError("銀行帳戶不存在", bank_account_id=data["bank_account_id"])

    receipt_no = await next_document_no(db, "RECEIPT")
    receipt = Receipt(
        receipt_no=receipt_no,
        customer_id=customer_id,
        receivable_id=receivable_id,
        bank_account_id=data.get("bank_account_id"),
        amount=amount,
        receipt_date=data.get("receipt_date") or datetime.now(UTC).replace(tzinfo=None),
        method=data.get("method", "transfer"),
        reference=data.get("reference"),
        status="posted" if post else "draft",
        created_by=(user or {}).get("employee_id"),
    )
    db.add(receipt)

    if post:
        if receivable_id and ar:
            ar.paid_amount = (ar.paid_amount or 0) + amount
            remaining = ar.amount - ar.paid_amount
            ar.status = "paid" if remaining <= 0 else "partial"
        if bank_account:
            bank_account.current_balance = (bank_account.current_balance or 0) + amount

    await db.commit()
    await db.refresh(receipt)
    return receipt


async def create_accounts_payable(db: AsyncSession, data: dict, user: dict | None = None) -> AccountsPayable:
    """建立一筆應付帳款（供應商發票 / PO 收貨後產生）。"""
    amount = float(data["amount"])
    if amount <= 0:
        raise BusinessRuleError("AP 金額必須大於 0")
    ap = AccountsPayable(
        supplier_id=data["supplier_id"],
        invoice_no=data["invoice_no"],
        invoice_date=data.get("invoice_date") or datetime.now(UTC).replace(tzinfo=None),
        due_date=data["due_date"],
        amount=amount,
        paid_amount=0,
        status="unpaid",
        source_type=data.get("source_type"),
        source_id=data.get("source_id"),
    )
    db.add(ap)
    await db.commit()
    await db.refresh(ap)
    return ap
