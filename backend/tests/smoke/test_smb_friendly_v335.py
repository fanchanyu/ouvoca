"""v3.35 電腦小白友善：8 LLM tools + 錯誤中文化 middleware

回答客戶第一天會問的問題：
  「我是誰？」「erpilot 好嗎？」「我能對 AI 講什麼？」
  「我做過什麼？」「上週問過什麼？」「客戶 X 全部資料」
  「給阿玲採購權限」「拿掉阿明的會計權限」
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


V335_TOOLS = [
    "whoami", "system_health", "list_what_can_i_do",
    "query_my_recent_actions", "search_chat_history",
    "query_customer_360",
    "grant_role_with_confirm", "revoke_role_with_confirm",
]


def test_v335_tools_registered():
    for n in V335_TOOLS:
        assert get_tool(n) is not None, f"{n} 未註冊"


def test_v335_creates_system_and_permission_agents():
    from app.agents.engine import AGENT_REGISTRY
    assert "system" in AGENT_REGISTRY
    assert "permission" in AGENT_REGISTRY


def test_grant_revoke_role_are_hard_write():
    for n in ["grant_role_with_confirm", "revoke_role_with_confirm"]:
        meta = get_tool(n)
        assert meta.risk_tier == RiskTier.HARD_WRITE


# ════════════════════════════════════════════════════════════════════
# whoami / system_health 不會 crash
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_whoami_no_user(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.smb_friendly_tools import _whoami
    async with AsyncSessionLocal() as db:
        result = await _whoami(db, None)
    assert result["raw"]["logged_in"] is False


@pytest.mark.asyncio
async def test_system_health_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.smb_friendly_tools import _system_health
    async with AsyncSessionLocal() as db:
        result = await _system_health(db, None)
    assert "summary" in result
    assert "raw" in result
    assert "db_ok" in result["raw"]


@pytest.mark.asyncio
async def test_list_what_can_i_do_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.smb_friendly_tools import _list_what_can_i_do
    async with AsyncSessionLocal() as db:
        result = await _list_what_can_i_do(db, None)
    assert "summary" in result
    # 應該列出多個 category
    assert "業務" in result["summary"] or "採購" in result["summary"]


@pytest.mark.asyncio
async def test_list_what_can_i_do_with_category(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.smb_friendly_tools import _list_what_can_i_do
    async with AsyncSessionLocal() as db:
        result = await _list_what_can_i_do(db, None, category="sales")
    assert "summary" in result


# ════════════════════════════════════════════════════════════════════
# query_customer_360 / search_chat_history
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_customer_360_missing(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.smb_friendly_tools import _query_customer_360
    async with AsyncSessionLocal() as db:
        result = await _query_customer_360(db, None, customer_keyword="NOSUCH-XYZ")
    assert "error" in result


@pytest.mark.asyncio
async def test_customer_360_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from app.agents.domains.smb_friendly_tools import _query_customer_360

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        cu = Customer(
            id=str(uuid.uuid4()), code=f"CC-360-{s}",
            name=f"Cust 360 {s}", credit_limit=50000,
        )
        db.add(cu)
        await db.commit()

        result = await _query_customer_360(db, None, customer_keyword=f"CC-360-{s}")
    assert "summary" in result
    assert result["raw"]["customer_no"] == f"CC-360-{s}"


@pytest.mark.asyncio
async def test_search_chat_history_no_match(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.smb_friendly_tools import _search_chat_history
    async with AsyncSessionLocal() as db:
        result = await _search_chat_history(
            db, {"user_id": "test"}, keyword="never_in_history_zzz", days=30,
        )
    assert "summary" in result


# ════════════════════════════════════════════════════════════════════
# grant / revoke role graceful errors
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_grant_role_missing_employee(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.smb_friendly_tools import _grant_role_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _grant_role_with_confirm(
            db, {"employee_id": "x"},
            employee_keyword="NOSUCH-EMP", role_code="any",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_revoke_role_missing_employee(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.smb_friendly_tools import _revoke_role_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _revoke_role_with_confirm(
            db, {"employee_id": "x"},
            employee_keyword="NOSUCH-EMP", role_code="any",
        )
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# 錯誤中文化 middleware
# ════════════════════════════════════════════════════════════════════

def test_error_middleware_translates_403_to_chinese(seeded_client):
    """訪問需要權限的 endpoint 但無權限 → 應回友善中文。"""
    # /api/permissions 需 permission 管理權限；以無 token 訪問會 401
    r = seeded_client.get("/api/permissions/roles")
    # 401 or 403
    assert r.status_code in (401, 403)
    payload = r.json()
    # 必有 detail 與 hint（中文）
    assert "detail" in payload
    # 中文檢查 — detail 應包含中文字
    has_chinese = any('一' <= c <= '鿿' for c in str(payload.get("detail", "")))
    has_hint_chinese = any('一' <= c <= '鿿' for c in str(payload.get("hint", "") or ""))
    assert has_chinese or has_hint_chinese, \
        f"錯誤訊息應含中文：{payload}"


def test_error_middleware_returns_chinese(seeded_client, admin_headers):
    """訪問不存在路徑（已 login）→ 友善中文 404。"""
    r = seeded_client.get("/api/no-such-endpoint-xyz", headers=admin_headers)
    assert r.status_code == 404
    payload = r.json()
    # detail 可能仍是英文（FastAPI 預設），但 hint 應是中文
    hint = payload.get("hint") or ""
    has_chinese = any('一' <= c <= '鿿' for c in hint)
    assert has_chinese, f"hint 應為中文：{payload}"
