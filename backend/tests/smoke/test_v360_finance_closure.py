"""v3.60 Phase B1 tests — 金流閉環基礎（AP / 付款 / 收款 / 銀行帳戶）。"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.core.tenant_context import set_current_tenant
    from app.database import AsyncSessionLocal
    set_current_tenant("HQ")
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_bank_account_create_and_balance(db):
    from app.services.finance import create_bank_account
    acc = await create_bank_account(db, {
        "code": "BK-001", "name": "台灣銀行 大安分行",
        "bank_name": "台灣銀行", "branch_name": "大安分行",
        "account_no": "1234-5678", "opening_balance": 100000,
    })
    assert acc.id
    assert acc.current_balance == 100000
    assert acc.tenant_id == "HQ"


@pytest.mark.asyncio
async def test_payment_reduces_bank_and_ap(db):
    from datetime import UTC, datetime, timedelta

    from app.models.purchase import Supplier
    from app.services.finance import (
        create_accounts_payable,
        create_bank_account,
        create_payment,
    )

    sup = Supplier(id=str(uuid.uuid4()), code="SUP-FIN", name="金流供應商", tier="T2", is_approved=True)
    db.add(sup)
    await db.commit()

    bank = await create_bank_account(db, {
        "code": "BK-002", "name": "測試銀行", "opening_balance": 50000,
    })
    ap = await create_accounts_payable(db, {
        "supplier_id": sup.id,
        "invoice_no": "SUP-INV-2026-001",
        "due_date": datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30),
        "amount": 10000,
    })

    pay = await create_payment(db, {
        "supplier_id": sup.id,
        "payable_id": ap.id,
        "bank_account_id": bank.id,
        "amount": 6000,
    })
    assert pay.payment_no.startswith("PY-")
    assert pay.status == "posted"

    # 銀行餘額減少 + AP 部分沖銷
    from sqlalchemy import select

    from app.models.finance import AccountsPayable, BankAccount
    bank_after = (await db.execute(select(BankAccount).where(BankAccount.id == bank.id))).scalar_one()
    ap_after = (await db.execute(select(AccountsPayable).where(AccountsPayable.id == ap.id))).scalar_one()
    assert bank_after.current_balance == 44000
    assert ap_after.paid_amount == 6000
    assert ap_after.status == "partial"


@pytest.mark.asyncio
async def test_receipt_increases_bank_and_ar(db):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.models.accounting import AccountsReceivable
    from app.models.crm_sales import Customer
    from app.models.finance import BankAccount
    from app.services.finance import create_bank_account, create_receipt

    cust = Customer(id=str(uuid.uuid4()), code="CUST-FIN", name="金流客戶")
    db.add(cust)
    await db.commit()

    bank = await create_bank_account(db, {"code": "BK-003", "name": "收款銀行", "opening_balance": 0})
    ar = AccountsReceivable(
        id=str(uuid.uuid4()),
        customer_id=cust.id,
        invoice_no="AR-INV-2026-001",
        invoice_date=datetime.now(UTC).replace(tzinfo=None),
        due_date=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30),
        amount=8000, paid_amount=0, status="unpaid",
    )
    db.add(ar)
    await db.commit()

    rec = await create_receipt(db, {
        "customer_id": cust.id,
        "receivable_id": ar.id,
        "bank_account_id": bank.id,
        "amount": 8000,
    })
    assert rec.receipt_no.startswith("RC-")

    bank_after = (await db.execute(select(BankAccount).where(BankAccount.id == bank.id))).scalar_one()
    ar_after = (await db.execute(select(AccountsReceivable).where(AccountsReceivable.id == ar.id))).scalar_one()
    assert bank_after.current_balance == 8000
    assert ar_after.status == "paid"


def test_finance_tools_registered(seeded_client):
    """金流 AI tools 應已註冊（grep smoke）。"""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "app" / "agents" / "domains" /
           "finance_tools.py").read_text(encoding="utf-8")
    for tool in ("query_payables", "create_bank_account_with_confirm",
                 "record_payment_with_confirm", "record_receipt_with_confirm"):
        assert f'name="{tool}"' in src, f"finance_tools.py 缺 {tool}"
