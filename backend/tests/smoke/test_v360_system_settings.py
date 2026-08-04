"""v3.60 M1-3 tests — 系統組態（system_settings）+ M1-2 角色 sync。"""
from __future__ import annotations

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_default_setting_fallback(db):
    from app.services.system_settings import get_setting
    assert await get_setting(db, "currency.default") == "TWD"
    assert await get_setting(db, "tax.vat_rate") == 0.05
    assert await get_setting(db, "nonexistent.key") is None


@pytest.mark.asyncio
async def test_set_and_get_setting(db):
    from app.services.system_settings import get_setting, set_setting
    await set_setting(db, "company.name", "長江精密", group="company", updated_by="test")
    assert await get_setting(db, "company.name") == "長江精密"


@pytest.mark.asyncio
async def test_list_settings_contains_defaults(db):
    from app.services.system_settings import list_settings
    rows = await list_settings(db)
    keys = {r["key"] for r in rows}
    assert "currency.default" in keys
    assert "backup.retention_days" in keys
    assert "tax.vat_rate" in keys


def test_settings_api_registered(seeded_client):
    """GET/PUT /api/system/settings 存在 + 權限保護（grep smoke）。"""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "app" / "api" /
           "system_settings.py").read_text(encoding="utf-8")
    assert 'require_permission("system.config.read")' in src
    assert 'require_permission("system.config.update")' in src
    assert 'PUT' in src or 'put_setting' in src


def test_role_seed_is_upsert_not_skip(seeded_client):
    """M1-2：系統角色必須是 sync 而非 skip-if-exists（grep smoke）。"""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "scripts" /
           "seed_permissions.py").read_text(encoding="utf-8")
    # 角色區段改為全量 sync（RowFilter 的 skip-if-exists 是刻意保留，不受影響）
    assert "重建 permission links" in src
    assert "role.is_system = True" in src
    assert "純自訂角色 → 保留不動" in src


def test_seed_py_wires_accounts_and_settings(seeded_client):
    """M1-4：seed.py 必須串接 seed_accounts + 系統設定（grep smoke）。"""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "scripts" /
           "seed.py").read_text(encoding="utf-8")
    assert "from scripts.seed_accounts import seed_accounts" in src
    assert "await seed_accounts()" in src
    assert "DEFAULT_SETTINGS" in src
