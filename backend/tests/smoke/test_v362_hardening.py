"""v3.62 資安硬化 tests — 登入鎖定 / session 撤銷 / 上傳驗證 / 發票號 / 信用額度 / 備份。"""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.database import AsyncSessionLocal
    from app.core.tenant_context import set_current_tenant
    set_current_tenant("HQ")
    async with AsyncSessionLocal() as session:
        yield session


def _make_user_sync(username: str, password: str = "Passw0rd!x"):
    """用獨立 session 建測試使用者（sync wrapper）。"""
    from app.models.organization import User, Employee, Department
    from app.services.auth import hash_password
    from datetime import datetime
    from app.database import AsyncSessionLocal

    async def _create():
        async with AsyncSessionLocal() as session:
            dept = Department(id=str(uuid.uuid4()), code=f"D-{username[:8]}", name=f"{username} 部門")
            session.add(dept)
            await session.flush()
            emp = Employee(id=str(uuid.uuid4()), employee_no=f"E-{username[:10]}", name=username,
                           email=f"{username}@test.local",
                           department_id=dept.id, hire_date=datetime.utcnow())
            session.add(emp)
            await session.flush()
            user = User(id=str(uuid.uuid4()), username=username,
                        hashed_password=hash_password(password),
                        employee_id=emp.id, is_superuser=True, is_active=True)
            session.add(user)
            await session.commit()
    asyncio.run(_create())


def _bump_token_version_sync(username: str):
    from app.models.organization import User
    from sqlalchemy import select
    from app.database import AsyncSessionLocal

    async def _bump():
        async with AsyncSessionLocal() as session:
            u = (await session.execute(
                select(User).where(User.username == username)
            )).scalar_one()
            u.token_version = (u.token_version or 0) + 1
            await session.commit()
    asyncio.run(_bump())


def test_login_lockout_after_failures(seeded_client):
    """連續失敗 ≥ 閾值 → 鎖定 15 分鐘（連正確密碼也 429）。"""
    _make_user_sync("lockout_user")

    for _ in range(5):
        r = seeded_client.post("/api/auth/login", json={
            "username": "lockout_user", "password": "wrong-pass",
        })
        assert r.status_code == 401

    # 鎖定後正確密碼也被擋
    r = seeded_client.post("/api/auth/login", json={
        "username": "lockout_user", "password": "Passw0rd!x",
    })
    assert r.status_code == 429
    assert "鎖定" in r.json()["detail"]


def test_token_version_revocation(seeded_client):
    """改密碼（token_version+1）後，舊 token 立即失效。"""
    _make_user_sync("revoke_user")
    r = seeded_client.post("/api/auth/login", json={
        "username": "revoke_user", "password": "Passw0rd!x",
    })
    assert r.status_code == 200
    old_token = r.json()["access_token"]

    # 舊 token 可用
    r = seeded_client.get("/api/inventory/parts", headers={
        "Authorization": f"Bearer {old_token}",
    })
    assert r.status_code == 200

    # 模擬改密碼：token_version +1
    _bump_token_version_sync("revoke_user")

    # 舊 token 失效
    r = seeded_client.get("/api/inventory/parts", headers={
        "Authorization": f"Bearer {old_token}",
    })
    assert r.status_code in (401, 403), f"舊 token 應失效：{r.status_code}"


def test_upload_rejects_fake_extension(seeded_client, admin_headers):
    """.txt 改名 .pdf → magic bytes 檢查拒絕。"""
    r = seeded_client.post(
        "/api/files/upload",
        headers=admin_headers,
        data={"category": "general"},
        files={"file": ("fake.pdf", b"this is actually plain text not a pdf", "application/pdf")},
    )
    assert r.status_code == 400
    assert "內容簽名" in r.json()["detail"]


def test_upload_accepts_real_pdf(seeded_client, admin_headers):
    """真 PDF 檔頭 → 通過。"""
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
    r = seeded_client.post(
        "/api/files/upload",
        headers=admin_headers,
        data={"category": "general"},
        files={"file": ("real.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code in (200, 201), f"真 PDF 應通過：{r.status_code} {r.text[:200]}"


@pytest.mark.asyncio
async def test_invoice_numbers_unique_sequential(db):
    """集中計數器：連續兩張發票號不重複且遞增。"""
    from app.services.sales import _gen_invoice_no
    n1 = await _gen_invoice_no(db)
    n2 = await _gen_invoice_no(db)
    assert n1.startswith("AB") and len(n1) == 10
    assert n1 != n2
    assert int(n1[2:]) + 1 == int(n2[2:])


@pytest.mark.asyncio
async def test_credit_limit_blocks_so(db):
    """客戶信用額度不足 → SO 建立被擋（審計 P1-6）。"""
    from app.models.crm_sales import Customer
    from app.services.sales import create_sales_order
    from app.core.exceptions import BusinessRuleError

    cust = Customer(id=str(uuid.uuid4()), code="CL-001", name="額度客戶", credit_limit=1000)
    db.add(cust)
    await db.commit()

    with pytest.raises(BusinessRuleError, match="信用額度不足"):
        await create_sales_order(db, {
            "customer_id": cust.id,
            "items": [{"product_id": str(uuid.uuid4()), "ordered_qty": 1, "unit_price": 5000}],
        })


def test_backup_lifecycle(seeded_client, admin_headers, tmp_path, monkeypatch):
    """建立備份 → 列出 → 刪除（API 走 mem 目錄，不碰真 DB）。"""
    from app.services import backup as backup_svc
    monkeypatch.setattr(backup_svc, "BACKUP_DIR", tmp_path)
    backup_svc.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    r = seeded_client.post("/api/system/backups", headers=admin_headers)
    if r.status_code == 200:
        name = r.json()["name"]
        lst = seeded_client.get("/api/system/backups", headers=admin_headers)
        assert any(b["name"] == name for b in lst.json()["backups"])
        d = seeded_client.delete(f"/api/system/backups/{name}", headers=admin_headers)
        assert d.status_code == 200
    else:
        # PostgreSQL / 非 SQLite 環境 → 應回明確 reason
        assert r.status_code == 400


def test_hardening_apis_and_tools_registered(seeded_client):
    """登入鎖定 / 撤銷 / 上傳驗證 / 備份 API+tool（grep smoke）。"""
    from pathlib import Path
    auth_src = (Path(__file__).resolve().parents[2] / "app" / "api" / "auth.py").read_text(encoding="utf-8")
    assert "is_login_locked" in auth_src
    assert "record_failed_login" in auth_src
    assert '"ver": user.token_version' in auth_src

    files_src = (Path(__file__).resolve().parents[2] / "app" / "api" / "files.py").read_text(encoding="utf-8")
    assert "_validate_content" in files_src
    assert "magic" in files_src

    tools_src = (Path(__file__).resolve().parents[2] / "app" / "agents" / "domains" /
                 "backup_tools.py").read_text(encoding="utf-8")
    for tool in ("list_backups", "create_backup_with_confirm", "restore_backup_with_confirm"):
        assert f'name="{tool}"' in tools_src
