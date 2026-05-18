"""Accounting service — Journal entries (debit/credit balance) + AR + month-end close."""
import uuid
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting import (
    Account, JournalEntry, JournalLine, AccountsReceivable, MonthEndClose,
)
from app.events import EventBus, DomainEvent
from app.core.exceptions import BusinessRuleError, NotFoundError


# -------- Accounts --------

async def create_account(db: AsyncSession, data: dict) -> Account:
    a = Account(id=str(uuid.uuid4()), **data)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def list_accounts(db: AsyncSession, account_type: Optional[str] = None) -> List[Account]:
    q = select(Account).where(Account.is_active == True)
    if account_type:
        q = q.where(Account.account_type == account_type)
    return list((await db.execute(q.order_by(Account.code))).scalars().all())


# -------- Journal Entry --------

async def create_journal_entry(db: AsyncSession, data: dict, user: Optional[dict] = None) -> JournalEntry:
    """Create a balanced journal entry — fails if debit != credit."""
    lines_data = data.pop("lines", [])
    if not lines_data:
        raise BusinessRuleError("傳票必須至少包含 2 個分錄")

    total_debit = sum(float(l.get("debit", 0)) for l in lines_data)
    total_credit = sum(float(l.get("credit", 0)) for l in lines_data)
    if round(total_debit, 2) != round(total_credit, 2):
        raise BusinessRuleError(
            "借貸不平衡", total_debit=total_debit, total_credit=total_credit,
        )

    # Period lock check
    period = data.get("period") or datetime.now(UTC).replace(tzinfo=None).strftime("%Y-%m")
    closed = (await db.execute(
        select(MonthEndClose).where(MonthEndClose.period == period, MonthEndClose.status == "closed")
    )).scalar_one_or_none()
    if closed:
        raise BusinessRuleError(f"會計期間 {period} 已結帳鎖定", period=period)

    je = JournalEntry(
        id=str(uuid.uuid4()),
        entry_no=f"JE-{datetime.now(UTC).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        entry_date=data.get("entry_date", datetime.now(UTC).replace(tzinfo=None)),
        period=period,
        created_by=(user or {}).get("employee_id"),
        **{k: v for k, v in data.items() if k not in ("entry_date", "period")},
    )
    db.add(je)
    for i, ld in enumerate(lines_data):
        line = JournalLine(
            id=str(uuid.uuid4()),
            journal_entry_id=je.id,
            line_no=i + 1,
            **ld,
        )
        db.add(line)
    await db.commit()
    # 預載 lines 關聯，避免 JournalEntryResponse 觸發 async lazy-load (MissingGreenlet)
    await db.refresh(je, attribute_names=["lines"])
    await EventBus.emit(DomainEvent(
        name="journal.created", domain="accounting",
        entity_type="JournalEntry", entity_id=je.id,
        data={"entry_no": je.entry_no, "amount": total_debit, "period": period},
    ))
    return je


async def post_journal(db: AsyncSession, entry_id: str, user: dict) -> JournalEntry:
    # 預載 lines 避免 response schema 觸發 async lazy-load
    je = (await db.execute(
        select(JournalEntry).options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == entry_id)
    )).scalar_one_or_none()
    if not je:
        raise NotFoundError("傳票不存在", entry_id=entry_id)
    if je.status != "draft":
        raise BusinessRuleError(f"傳票狀態 '{je.status}' 不可過帳")
    je.status = "posted"
    je.posted_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="journal.posted", domain="accounting",
        entity_type="JournalEntry", entity_id=je.id,
        data={"entry_no": je.entry_no, "posted_by": user.get("employee_id")},
    ))
    return je


async def list_journals(db: AsyncSession, period: Optional[str] = None,
                        status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[JournalEntry]:
    q = select(JournalEntry).options(selectinload(JournalEntry.lines))
    if period:
        q = q.where(JournalEntry.period == period)
    if status:
        q = q.where(JournalEntry.status == status)
    q = q.offset(skip).limit(limit).order_by(JournalEntry.entry_date.desc())
    return list((await db.execute(q)).scalars().all())


# -------- AR --------

async def create_receivable(db: AsyncSession, data: dict) -> AccountsReceivable:
    ar = AccountsReceivable(id=str(uuid.uuid4()), **data)
    db.add(ar)
    await db.commit()
    await db.refresh(ar)
    return ar


async def list_receivables(db: AsyncSession, status: Optional[str] = None,
                           overdue_only: bool = False, limit: int = 100) -> List[AccountsReceivable]:
    q = select(AccountsReceivable)
    if status:
        q = q.where(AccountsReceivable.status == status)
    if overdue_only:
        q = q.where(AccountsReceivable.due_date < datetime.now(UTC).replace(tzinfo=None),
                    AccountsReceivable.status != "paid")
    return list((await db.execute(q.limit(limit).order_by(AccountsReceivable.due_date))).scalars().all())


# -------- Month-end close --------

async def close_month(db: AsyncSession, period: str, user: dict) -> MonthEndClose:
    existing = (await db.execute(
        select(MonthEndClose).where(MonthEndClose.period == period)
    )).scalar_one_or_none()
    if existing and existing.status == "closed":
        raise BusinessRuleError(f"期間 {period} 已結帳", period=period)
    if existing:
        existing.status = "closed"
        existing.closed_by = user.get("employee_id")
        existing.closed_at = datetime.now(UTC).replace(tzinfo=None)
        rec = existing
    else:
        rec = MonthEndClose(
            id=str(uuid.uuid4()),
            period=period,
            status="closed",
            closed_by=user.get("employee_id"),
            closed_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(rec)
    await db.commit()
    await db.refresh(rec)
    await EventBus.emit(DomainEvent(
        name="month.end_close", domain="accounting",
        entity_type="MonthEndClose", entity_id=rec.id,
        data={"period": period, "closed_by": user.get("employee_id")},
    ))
    return rec
