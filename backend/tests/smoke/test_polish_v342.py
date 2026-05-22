"""v3.42 第六輪小白卡關修補 smoke 測試

R1: create_user / deactivate_user — 使用者帳號管理
R2: global_search — 跨表搜尋
R3: attach_file_to_entity — 附件 LLM
R4: ai_rate_limit middleware（in-memory counter）
R5: add_business_days_tw — 工作天 + 台灣假日
R6: export_chat_session — transcript 匯出
R7: set_timezone + get_tenant_timezone + format_dt_local
R8: Dashboard 手機 responsive class（不寫 test，frontend 已調）
"""
from __future__ import annotations

import base64
import uuid
from datetime import date
import pytest

from app.agents.registry import RiskTier, get_tool


V342_TOOLS = [
    "set_timezone_with_confirm",
    "create_user_with_confirm",
    "deactivate_user_with_confirm",
    "global_search",
    "attach_file_to_entity_with_confirm",
    "add_business_days_tw",
    "export_chat_session",
]


def test_v342_tools_registered():
    for n in V342_TOOLS:
        assert get_tool(n) is not None, f"{n} 未註冊"


def test_v342_risk_tiers():
    for n in ["set_timezone_with_confirm", "create_user_with_confirm",
              "deactivate_user_with_confirm", "attach_file_to_entity_with_confirm"]:
        assert get_tool(n).risk_tier == RiskTier.HARD_WRITE
    for n in ["global_search", "add_business_days_tw", "export_chat_session"]:
        assert get_tool(n).risk_tier == RiskTier.READ


# ════════════════════════════════════════════════════════════════════
# R7: 時區
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_r7_invalid_timezone(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _set_timezone_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _set_timezone_with_confirm(
            db, {"user_id": "u1"}, timezone="Mars/Olympus",
        )
    assert "error" in r


@pytest.mark.asyncio
async def test_r7_valid_tz_returns_card(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _set_timezone_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _set_timezone_with_confirm(
            db, {"user_id": "u1"}, timezone="Asia/Tokyo",
        )
    assert r.get("type") == "confirm_card"


def test_r7_format_dt_local():
    from app.agents.domains.polish_v342_tools import format_dt_local
    from datetime import datetime, UTC
    dt = datetime(2026, 5, 21, 15, 30, tzinfo=UTC)  # 15:30 UTC
    s = format_dt_local(dt, "Asia/Taipei")
    # UTC 15:30 = Taipei 23:30
    assert "23:30" in s
    assert s.startswith("2026-05-21")


# ════════════════════════════════════════════════════════════════════
# R1: 使用者帳號
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_r1_create_user_bad_username(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _create_user_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _create_user_with_confirm(
            db, {"user_id": "u1"},
            username="ab",  # 太短
            password="MyP@ss12",
        )
    assert "error" in r
    assert "格式" in r["error"]


@pytest.mark.asyncio
async def test_r1_create_user_weak_password(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _create_user_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _create_user_with_confirm(
            db, {"user_id": "u1"},
            username="newuser",
            password="abc",  # 太短
        )
    assert "error" in r


@pytest.mark.asyncio
async def test_r1_create_user_returns_card(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _create_user_with_confirm
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        r = await _create_user_with_confirm(
            db, {"user_id": "u1"},
            username=f"hua_{s}",
            password="MyN3wP@ss",
        )
    assert r.get("type") == "confirm_card"


@pytest.mark.asyncio
async def test_r1_deactivate_user_not_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _deactivate_user_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _deactivate_user_with_confirm(
            db, {"user_id": "u1"}, username_keyword="nosuchuser-xyz",
        )
    assert "error" in r


# ════════════════════════════════════════════════════════════════════
# R2: 全域搜尋
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_r2_global_search_too_short(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _global_search
    async with AsyncSessionLocal() as db:
        r = await _global_search(db, None, keyword="A")
    assert "error" in r


@pytest.mark.asyncio
async def test_r2_global_search_no_match(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _global_search
    async with AsyncSessionLocal() as db:
        r = await _global_search(db, None, keyword="NOSUCH-XYZ-99")
    assert r["raw"]["count"] == 0


@pytest.mark.asyncio
async def test_r2_global_search_cross_table(seeded_client):
    """建客戶 + 料件 同名「Acme」→ 應在兩表都找到。"""
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from app.models.inventory import Part
    from app.agents.domains.polish_v342_tools import _global_search
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        db.add(Customer(id=str(uuid.uuid4()), code=f"AC-{s}",
                         name=f"Acme-{s} 公司"))
        db.add(Part(id=str(uuid.uuid4()), part_no=f"AC-{s}-001",
                     name=f"Acme-{s} 螺絲"))
        await db.commit()

        r = await _global_search(db, None, keyword=f"acme-{s}")
    assert r["raw"]["count"] >= 2
    assert len(r["raw"]["matches"]["customers"]) >= 1
    assert len(r["raw"]["matches"]["parts"]) >= 1


# ════════════════════════════════════════════════════════════════════
# R3: 附件
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_r3_attach_invalid_entity_type(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _attach_file_to_entity_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _attach_file_to_entity_with_confirm(
            db, {"user_id": "u1"},
            file_id="x", entity_type="invalid", entity_no="X",
        )
    assert "error" in r


@pytest.mark.asyncio
async def test_r3_attach_file_not_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _attach_file_to_entity_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _attach_file_to_entity_with_confirm(
            db, {"user_id": "u1"},
            file_id="nosuch-file-id", entity_type="sales_order", entity_no="SO-X",
        )
    assert "error" in r


# ════════════════════════════════════════════════════════════════════
# R5: 工作天
# ════════════════════════════════════════════════════════════════════

def test_r5_business_days_skip_weekend():
    from app.agents.domains.polish_v342_tools import add_business_days_tw
    # 2026-05-22 是週五 → +1 應該到下週一 5/25
    assert add_business_days_tw(date(2026, 5, 22), 1) == date(2026, 5, 25)


def test_r5_business_days_skip_taiwan_holiday():
    from app.agents.domains.polish_v342_tools import add_business_days_tw
    # 2026-02-14 是週六，但春節 2/15-2/20 全部跳過
    # +1 工作天 → 應該跳到 2/23 (週一)
    assert add_business_days_tw(date(2026, 2, 14), 1) == date(2026, 2, 23)


def test_r5_business_days_negative():
    from app.agents.domains.polish_v342_tools import add_business_days_tw
    # 倒推 3 個工作天
    # 2026-05-25 (週一) - 3 = 2026-05-20 (週三)
    assert add_business_days_tw(date(2026, 5, 25), -3) == date(2026, 5, 20)


def test_r5_is_business_day():
    from app.agents.domains.polish_v342_tools import is_business_day_tw
    assert is_business_day_tw(date(2026, 5, 21))  # 週四 OK
    assert not is_business_day_tw(date(2026, 5, 23))  # 週六
    assert not is_business_day_tw(date(2026, 1, 1))  # 元旦
    assert not is_business_day_tw(date(2026, 2, 16))  # 春節初一


@pytest.mark.asyncio
async def test_r5_llm_tool_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _add_business_days_tw
    async with AsyncSessionLocal() as db:
        r = await _add_business_days_tw(db, None, n_days=3, start_date="2026-05-20")
    assert r["raw"]["end_date"] == "2026-05-25"


# ════════════════════════════════════════════════════════════════════
# R6: 對話 transcript
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_r6_export_empty(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v342_tools import _export_chat_session
    async with AsyncSessionLocal() as db:
        r = await _export_chat_session(db, {"user_id": "nosuch-user"}, days_back=1)
    assert r["raw"]["count"] == 0


@pytest.mark.asyncio
async def test_r6_export_after_inserting_logs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.ai_governance import ConversationLog
    from app.agents.domains.polish_v342_tools import _export_chat_session

    sid = f"sess-r6-{uuid.uuid4().hex[:5]}"
    async with AsyncSessionLocal() as db:
        for role, msg in [("user", "hello"), ("assistant", "hi there")]:
            db.add(ConversationLog(
                id=str(uuid.uuid4()), session_id=sid,
                role=role, message=msg,
            ))
        await db.commit()

        r = await _export_chat_session(db, None, session_id=sid, days_back=1)

    assert r["raw"]["count"] == 2
    md = base64.b64decode(r["raw"]["markdown_base64"]).decode("utf-8")
    assert "hello" in md
    assert "hi there" in md


# ════════════════════════════════════════════════════════════════════
# R4: Rate limit middleware (in-memory counter)
# ════════════════════════════════════════════════════════════════════

def test_r4_get_user_usage():
    from app.core.ai_rate_limit import get_user_usage, _USER_COUNTERS
    _USER_COUNTERS.clear()
    u = get_user_usage("u:test")
    assert u["used"] == 0
    assert u["limit"] > 0


@pytest.mark.asyncio
async def test_r4_middleware_blocks_after_limit():
    """設超低 limit，呼叫 N 次後第 N+1 次應 429。"""
    from fastapi import FastAPI
    from app.core.ai_rate_limit import AiRateLimitMiddleware, _USER_COUNTERS
    from httpx import AsyncClient, ASGITransport
    from app import config as cfg
    _USER_COUNTERS.clear()
    original = cfg.settings.AI_DAILY_LIMIT_PER_USER
    cfg.settings.AI_DAILY_LIMIT_PER_USER = 2
    try:
        app = FastAPI()
        app.add_middleware(AiRateLimitMiddleware)

        @app.get("/api/chat-v2/test")
        async def _t():
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test",
        ) as ac:
            r1 = await ac.get("/api/chat-v2/test")
            r2 = await ac.get("/api/chat-v2/test")
            r3 = await ac.get("/api/chat-v2/test")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
        body = r3.json()
        assert body["code"] == "ai_rate_limit_exceeded"
        assert "限" in body["detail"] or "上限" in body["detail"]
    finally:
        cfg.settings.AI_DAILY_LIMIT_PER_USER = original
        _USER_COUNTERS.clear()
