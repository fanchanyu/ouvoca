"""Accounting API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import require_permission, UserContext
from app.schemas.accounting import (
    AccountCreate, AccountUpdate, AccountResponse,
    JournalEntryCreate, JournalEntryResponse,
    ARCreate, ARResponse,
)
from app.services import accounting as svc

router = APIRouter(prefix="/api/accounting", tags=["Accounting"])


@router.post("/accounts", response_model=AccountResponse)
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.account.create")),
):
    a = await svc.create_account(db, data.model_dump())
    return AccountResponse.model_validate(a)


@router.put("/accounts/{code}", response_model=AccountResponse)
async def update_account(
    code: str,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.account.update")),
):
    a = await svc.update_account(db, code, data.model_dump(exclude_unset=True))
    return AccountResponse.model_validate(a)


@router.delete("/accounts/{code}")
async def delete_account(
    code: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.account.delete")),
):
    await svc.delete_account(db, code)
    return {"ok": True}


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
    user: UserContext = Depends(require_permission("accounting.ar.create")),
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


# ═══════════════════════════════════════════════════════════
# M2 — 財務閉環：三大報表 / 401-405 / 3-Way Match / 票據 / 固定資產
# ═══════════════════════════════════════════════════════════

# --- 三大報表（M2-1） ---

@router.get("/statements/trial-balance")
async def get_trial_balance(
    period: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.statement.read")),
):
    from app.services.financial_statements import trial_balance
    return await trial_balance(db, period)


@router.get("/statements/income-statement")
async def get_income_statement(
    period: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.statement.read")),
):
    from app.services.financial_statements import income_statement
    return await income_statement(db, period)


@router.get("/statements/balance-sheet")
async def get_balance_sheet(
    period: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.statement.read")),
):
    from app.services.financial_statements import balance_sheet
    return await balance_sheet(db, period)


# --- 401/405 營業稅申報（M2-2） ---

@router.get("/tax/401-405")
async def get_tax_report_401_405(
    period: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.tax_report")),
):
    from app.services.tax_report_tw import tax_report_401_405
    return await tax_report_401_405(db, period)


# --- 供應商發票 + 3-Way Match（M2-3） ---

@router.post("/supplier-invoices")
async def create_supplier_invoice(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.supplier_invoice.create")),
):
    from app.services.three_way_match import create_supplier_invoice
    inv = await create_supplier_invoice(db, data, {"employee_id": user.employee_id})
    return {
        "id": inv.id, "invoice_no": inv.invoice_no, "status": inv.status,
        "total_amount": inv.total_amount,
    }


@router.get("/supplier-invoices")
async def list_supplier_invoices(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.supplier_invoice.read")),
):
    from app.services.three_way_match import list_invoice_matches
    return await list_invoice_matches(db, status)


@router.post("/supplier-invoices/{invoice_id}/match")
async def match_supplier_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.supplier_invoice.match")),
):
    from app.services.three_way_match import match_supplier_invoice
    return await match_supplier_invoice(db, invoice_id)


# --- 票據管理（M2-4） ---

@router.get("/promissory-notes")
async def list_promissory_notes(
    note_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.note.read")),
):
    from sqlalchemy import select
    from app.models.finance import PromissoryNote
    q = select(PromissoryNote).order_by(PromissoryNote.due_date)
    if note_type:
        q = q.where(PromissoryNote.note_type == note_type)
    if status:
        q = q.where(PromissoryNote.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": r.id, "note_type": r.note_type, "party_name": r.party_name,
            "bank_name": r.bank_name, "check_no": r.check_no, "amount": r.amount,
            "issue_date": r.issue_date.isoformat() if r.issue_date else None,
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "status": r.status,
        }
        for r in rows
    ]


@router.post("/promissory-notes")
async def create_promissory_note(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.note.create")),
):
    from app.models.finance import PromissoryNote
    note = PromissoryNote(**data, created_by=user.employee_id)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return {"id": note.id, "check_no": note.check_no, "amount": note.amount, "status": note.status}


# --- 固定資產 + 折舊（M2-5） ---

@router.get("/fixed-assets")
async def list_fixed_assets(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.fixed_asset.read")),
):
    from app.services.fixed_assets import list_fixed_assets
    return await list_fixed_assets(db, status)


@router.post("/fixed-assets")
async def create_fixed_asset(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.fixed_asset.create")),
):
    from app.services.fixed_assets import create_fixed_asset
    asset = await create_fixed_asset(db, data, {"employee_id": user.employee_id})
    return {
        "id": asset.id, "code": asset.code, "name": asset.name,
        "monthly_depreciation": asset.monthly_depreciation,
    }


@router.post("/fixed-assets/{asset_id}/depreciate")
async def post_fixed_asset_depreciation(
    asset_id: str,
    period: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.fixed_asset.depreciate")),
):
    from app.services.fixed_assets import post_monthly_depreciation
    asset = await post_monthly_depreciation(
        db, asset_id, period, {"employee_id": user.employee_id},
    )
    return {
        "id": asset.id, "code": asset.code,
        "accumulated_depreciation": asset.accumulated_depreciation,
        "status": asset.status,
    }


@router.post("/cogs/settle")
async def settle_cogs(
    period: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("accounting.cost_settle.execute")),
):
    """M2-6：月結銷貨成本（期間內出貨 × 成本 → DR 5100 / CR 1340）。"""
    from app.services.production_cost import settle_cogs
    return await settle_cogs(db, period, {"employee_id": user.employee_id})
