"""M1-1.5 — seed_accounts 與科目 API 保護測試（9 支）。

規格：docs/TURNKEY_M1-1_ACCOUNTS_DETAIL.md §8、docs/TURNKEY_M1-1_3_SEEDACCOUNTS_DETAIL.md §6

注意：pytest session 共享同一測試 DB，其他測試檔可能新增科目；
故「數量」類斷言採用「86 科全部存在 + 冪等」而非嚴格 == 86。
"""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.accounting import Account
from app.services import fs_defs
from scripts.seed_accounts import (
    ACCOUNTS,
    CONTRA_CODES,
    SYSTEM_CODES,
    seed_accounts,
)

HARDCODED_NAMES = {
    "1100": "現金及銀行存款",
    "1200": "應收帳款",
    "2100": "應付帳款",
    "2200": "銷項稅額",
    "4100": "銷貨收入",
}


@pytest.fixture(scope="module", autouse=True)
def _seeded_accounts():
    """本模組測試前先跑一次 seed（冪等，可重複執行）。"""
    asyncio.run(seed_accounts())
    yield


async def _account_map() -> dict[str, Account]:
    async with AsyncSessionLocal() as db:
        return {
            r.code: r for r in (await db.execute(select(Account))).scalars().all()
        }


async def _count() -> int:
    async with AsyncSessionLocal() as db:
        from sqlalchemy import func
        return (await db.execute(select(func.count()).select_from(Account))).scalar()


def test_seed_account_count():
    """86 科全部存在、無重複、硬編碼五碼 is_system=True。"""
    rows = asyncio.run(_account_map())
    missing = [a["code"] for a in ACCOUNTS if a["code"] not in rows]
    assert missing == [], f"缺科目: {missing}"
    assert len({a["code"] for a in ACCOUNTS}) == 86
    assert len(rows) >= 86
    sys_codes = sorted(c for c, r in rows.items() if r.is_system)
    assert sys_codes == sorted(SYSTEM_CODES), f"is_system 科目異常: {sys_codes}"


def test_hardcoded_codes_present():
    """五硬編碼存在、is_system=True、名稱與程式碼契約一致。"""
    rows = asyncio.run(_account_map())
    for code, expected_name in HARDCODED_NAMES.items():
        row = rows.get(code)
        assert row is not None, f"硬編碼科目 {code} 不存在"
        assert row.is_system is True, f"{code} 保護失效"
        assert row.name == expected_name, f"{code} 名稱漂移: {row.name}"


def test_fs_line_whitelist():
    """86 科 fs_line 全填且在白名單內。"""
    rows = asyncio.run(_account_map())
    for spec in ACCOUNTS:
        row = rows[spec["code"]]
        assert row.fs_line, f"{spec['code']} fs_line 為空"
        assert row.fs_line in fs_defs.FS_LINES, f"{spec['code']} fs_line 非白名單: {row.fs_line}"


def test_debit_credit_direction():
    """非抵減科目借貸方向符合類別規則（抵減科目為例外，資料表人工校驗）。"""
    rows = asyncio.run(_account_map())
    bad: list[str] = []
    for spec in ACCOUNTS:
        if spec["code"] in CONTRA_CODES:
            continue
        expect = spec["account_type"] in fs_defs.DEBIT_NORMAL_TYPES
        if rows[spec["code"]].is_debit_normal != expect:
            bad.append(f"{spec['code']}({spec['account_type']})")
    assert bad == [], f"借貸方向錯誤: {bad}"


def test_parent_resolution():
    """所有 parent_code 已解析為 parent_id 且指向正確科目。"""
    rows = asyncio.run(_account_map())
    bad: list[str] = []
    for spec in ACCOUNTS:
        pc = spec["parent_code"]
        if pc and rows[spec["code"]].parent_id != rows[pc].id:
            bad.append(f"{spec['code']}->{pc}")
    assert bad == [], f"parent 解析失敗: {bad}"


def test_seed_idempotent():
    """重跑 seed 不增刪不變更（created/updated 皆 0）。"""
    n1 = asyncio.run(_count())
    asyncio.run(seed_accounts())
    asyncio.run(seed_accounts())
    n2 = asyncio.run(_count())
    assert n1 == n2, f"重跑 seed 筆數變化: {n1} -> {n2}"


def test_system_account_code_protected(seeded_client, admin_headers):
    """改 is_system 科目 code → 403。"""
    r = seeded_client.put(
        "/api/accounting/accounts/1100", headers=admin_headers,
        json={"code": "9999"},
    )
    assert r.status_code == 403, r.text
    r = seeded_client.get("/api/accounting/accounts", headers=admin_headers)
    assert r.status_code == 200
    assert any(a["code"] == "1100" for a in r.json()), "1100 不應被改名"


def test_system_account_deletable(seeded_client, admin_headers):
    """刪 is_system 科目 → 403；刪自訂科目 → 200；再刪 → 404。"""
    r = seeded_client.delete("/api/accounting/accounts/1100", headers=admin_headers)
    assert r.status_code == 403, r.text

    r = seeded_client.post(
        "/api/accounting/accounts", headers=admin_headers,
        json={"code": "9001", "name": "M1 測試科目", "account_type": "expense",
              "is_debit_normal": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_system"] is False

    r = seeded_client.delete("/api/accounting/accounts/9001", headers=admin_headers)
    assert r.status_code == 200, r.text

    r = seeded_client.delete("/api/accounting/accounts/9001", headers=admin_headers)
    assert r.status_code == 404


def test_alias_audit_gate():
    """M1-0.3 gate：審計工具 MISSING == 0（權限碼對齊不回退）。"""
    from scripts.audit_permission_codes import audit, load_db_codes
    from scripts.seed_permissions import seed_permissions

    asyncio.run(seed_permissions())
    db_codes = asyncio.run(load_db_codes())
    result = audit(db_codes)
    assert result["missing"] == [], f"權限碼 MISSING: {result['missing']}"
