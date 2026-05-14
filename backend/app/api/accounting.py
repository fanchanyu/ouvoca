"""Accounting API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import require_permission, UserContext
from app.schemas.accounting import (
    AccountCreate, AccountResponse,
    JournalEntryCreate, JournalEntryResponse,
    ARCreate, ARResponse,
)
from app.services import accounting as svc

router = APIRouter(prefix="/api/accounting", tags=["Accounting"])


@router.post("/accounts", response_model=AccountResponse)
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.account.list")),
):
    a = await svc.create_account(db, data.model_dump())
    return AccountResponse.model_validate(a)


@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(
    account_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.account.list")),
):
    rows = await svc.list_accounts(db, account_type)
    return [AccountResponse.model_validate(r) for r in rows]


@router.post("/journals", response_model=JournalEntryResponse)
async def create_journal(
    data: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.journal.create")),
):
    je = await svc.create_journal_entry(db, data.model_dump(), user=user.raw_user)
    return JournalEntryResponse.model_validate(je)


@router.post("/journals/{entry_id}/post", response_model=JournalEntryResponse)
async def post_journal(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.journal.post")),
):
    je = await svc.post_journal(db, entry_id, user.raw_user)
    return JournalEntryResponse.model_validate(je)


@router.get("/journals", response_model=List[JournalEntryResponse])
async def list_journals(
    period: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.journal.list")),
):
    rows = await svc.list_journals(db, period, status, skip, limit)
    return [JournalEntryResponse.model_validate(r) for r in rows]


@router.post("/receivables", response_model=ARResponse)
async def create_ar(
    data: ARCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.ar.list")),
):
    ar = await svc.create_receivable(db, data.model_dump())
    return ARResponse.model_validate(ar)


@router.get("/receivables", response_model=List[ARResponse])
async def list_ar(
    status: Optional[str] = None,
    overdue_only: bool = False,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.ar.list")),
):
    rows = await svc.list_receivables(db, status, overdue_only, limit)
    return [ARResponse.model_validate(r) for r in rows]


@router.post("/close-month/{period}")
async def close_month(
    period: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.month_close.execute")),
):
    rec = await svc.close_month(db, period, user.raw_user)
    return {"period": rec.period, "status": rec.status, "closed_at": rec.closed_at}
