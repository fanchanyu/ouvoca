"""
Shared pytest fixtures for LLM-ERP backend tests.

設計原則：
1. 用獨立的 sqlite 檔案（不是 :memory:）— 因為 aiosqlite + NullPool 跨連線不共享 :memory:
2. 每個測試 session 一個 DB，session 結束清掉
3. 用 FastAPI TestClient 直接呼叫 ASGI，不需起 uvicorn
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# 必須在 import app 之前設好環境變數
_TMP_DIR = Path(tempfile.mkdtemp(prefix="llmerp-test-"))
_DB_PATH = _TMP_DIR / "test.db"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "test-jwt-secret-" + "x" * 48  # 觸發非 demo 模式
os.environ["DEBUG"] = "true"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["DATABASE_DRIVER"] = "sqlite"
os.environ["RATE_LIMIT_ENABLED"] = "false"  # 測試時關閉 rate limit

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def _app():
    """Import app once per session（會跑 init_db 建 schema）。"""
    from app.main import app
    return app


@pytest.fixture(scope="session")
def client(_app):
    """跨 session 共用 TestClient — startup/shutdown 只跑一次。"""
    with TestClient(_app) as c:
        yield c
    # 清檔
    try:
        if _DB_PATH.exists():
            _DB_PATH.unlink()
        _TMP_DIR.rmdir()
    except Exception:
        pass


@pytest.fixture(scope="session")
def seeded_client(client):
    """確保 testadmin user 存在的 client（透過直接 DB insert，繞過 RBAC）。"""
    import asyncio
    import uuid as _uuid
    from datetime import datetime as _dt
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.organization import User, Employee, Department
    from app.services.auth import hash_password

    async def _seed():
        async with AsyncSessionLocal() as db:
            # 已存在就跳過
            existing = (await db.execute(
                select(User).where(User.username == "testadmin")
            )).scalar_one_or_none()
            if existing:
                return

            # Dept → Emp → User
            dept = (await db.execute(
                select(Department).where(Department.code == "TEST")
            )).scalar_one_or_none()
            if not dept:
                dept = Department(
                    id=str(_uuid.uuid4()), code="TEST", name="Test Dept",
                )
                db.add(dept)
                await db.flush()

            emp = Employee(
                id=str(_uuid.uuid4()),
                employee_no="TEST-001",
                name="Test Admin",
                email="testadmin@llm-erp.test",
                department_id=dept.id,
                title="Admin",
                hire_date=_dt.utcnow(),
            )
            db.add(emp)
            await db.flush()

            user = User(
                id=str(_uuid.uuid4()),
                username="testadmin",
                hashed_password=hash_password("TestPass123!"),
                employee_id=emp.id,
                is_superuser=True,
                is_active=True,
            )
            db.add(user)
            await db.commit()

    asyncio.run(_seed())
    return client


@pytest.fixture(scope="session")
def admin_token(seeded_client):
    """登入 testadmin 拿 JWT token。"""
    r = seeded_client.post("/api/auth/login", json={
        "username": "testadmin", "password": "TestPass123!",
    })
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
