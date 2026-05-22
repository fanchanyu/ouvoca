"""v3.40 第四輪小白卡關修補 smoke 測試

M1: parse_relative_date_zh — 中文相對日期解析
M2: query_customer_aging — 應收帳齡
M3: case-insensitive 搜尋（client.search "abc" 應找到「ABC」）
M4: Delete 三件套加 push_undo（snapshot 復原）
M5: toggle_hard_write_freeze_with_confirm — 凍結 / 解凍 + engine 攔截
M6: query_audit_log_search — 跨人搜尋
M7: compare_orders
"""
from __future__ import annotations

import json
import uuid
from datetime import date
import pytest

from app.agents.registry import RiskTier, get_tool


V340_TOOLS = [
    "parse_relative_date_zh_tool",
    "query_customer_aging",
    "toggle_hard_write_freeze_with_confirm",
    "query_audit_log_search",
    "compare_orders",
]


def test_v340_tools_registered():
    for n in V340_TOOLS:
        assert get_tool(n) is not None, f"{n} 未註冊"


def test_v340_risk_tiers():
    assert get_tool("toggle_hard_write_freeze_with_confirm").risk_tier == RiskTier.HARD_WRITE
    for n in ["parse_relative_date_zh_tool", "query_customer_aging",
              "query_audit_log_search", "compare_orders"]:
        assert get_tool(n).risk_tier == RiskTier.READ


# ════════════════════════════════════════════════════════════════════
# M1: 中文相對日期解析
# ════════════════════════════════════════════════════════════════════

def test_m1_today():
    from app.agents.domains.polish_v340_tools import parse_relative_date_zh
    today = date(2026, 5, 21)
    assert parse_relative_date_zh("今天", today) == (today, today)
    assert parse_relative_date_zh("今日", today) == (today, today)


def test_m1_yesterday_and_tomorrow():
    from app.agents.domains.polish_v340_tools import parse_relative_date_zh
    today = date(2026, 5, 21)
    assert parse_relative_date_zh("昨天", today) == (date(2026, 5, 20), date(2026, 5, 20))
    assert parse_relative_date_zh("明天", today) == (date(2026, 5, 22), date(2026, 5, 22))
    assert parse_relative_date_zh("前天", today) == (date(2026, 5, 19), date(2026, 5, 19))


def test_m1_week():
    from app.agents.domains.polish_v340_tools import parse_relative_date_zh
    # 2026-05-21 是星期四（weekday=3）→ 本週週一 = 5/18
    today = date(2026, 5, 21)
    assert parse_relative_date_zh("本週", today) == (date(2026, 5, 18), date(2026, 5, 24))
    assert parse_relative_date_zh("上週", today) == (date(2026, 5, 11), date(2026, 5, 17))


def test_m1_month():
    from app.agents.domains.polish_v340_tools import parse_relative_date_zh
    today = date(2026, 5, 21)
    assert parse_relative_date_zh("本月", today) == (date(2026, 5, 1), date(2026, 5, 31))
    assert parse_relative_date_zh("上月", today) == (date(2026, 4, 1), date(2026, 4, 30))


def test_m1_past_n_days():
    from app.agents.domains.polish_v340_tools import parse_relative_date_zh
    today = date(2026, 5, 21)
    assert parse_relative_date_zh("過去 30 天", today) == (date(2026, 4, 21), today)
    assert parse_relative_date_zh("近 7 天", today) == (date(2026, 5, 14), today)
    # 中文數字
    assert parse_relative_date_zh("過去三天", today) == (date(2026, 5, 18), today)


def test_m1_quarter():
    from app.agents.domains.polish_v340_tools import parse_relative_date_zh
    today = date(2026, 5, 21)
    assert parse_relative_date_zh("Q1", today) == (date(2026, 1, 1), date(2026, 3, 31))
    assert parse_relative_date_zh("第二季", today) == (date(2026, 4, 1), date(2026, 6, 30))


def test_m1_unknown_returns_none():
    from app.agents.domains.polish_v340_tools import parse_relative_date_zh
    assert parse_relative_date_zh("foobar") is None
    assert parse_relative_date_zh("2026-05-21") is None  # 不是相對日期


@pytest.mark.asyncio
async def test_m1_llm_tool_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v340_tools import _parse_relative_date_zh
    async with AsyncSessionLocal() as db:
        r = await _parse_relative_date_zh(db, None, text="上週")
    assert r["raw"]["parsed"] is True
    assert "start_date" in r["raw"]


# ════════════════════════════════════════════════════════════════════
# M2: 客戶帳齡
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_m2_aging_no_data_or_no_table(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v340_tools import _query_customer_aging
    async with AsyncSessionLocal() as db:
        r = await _query_customer_aging(db, None)
    # 空 DB → "沒有應收帳款"；無表 → error
    assert "summary" in r or "error" in r


# ════════════════════════════════════════════════════════════════════
# M3: case-insensitive search
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_m3_resolve_candidates_case_insensitive(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from app.agents.domains.polish_tools import _resolve_customer_candidates
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"M3-{s}", name=f"AcmeCorp-{s}")
        db.add(cu)
        await db.commit()

        # 用小寫查
        r = await _resolve_customer_candidates(db, None, keyword=f"acmecorp-{s}")
    # case-insensitive 應該找得到
    assert r["raw"]["matched"] != "none"


# ════════════════════════════════════════════════════════════════════
# M5: 凍結 / 解凍 + engine 攔截
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_m5_freeze_invalid_action(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v340_tools import _toggle_hard_write_freeze_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _toggle_hard_write_freeze_with_confirm(
            db, {"user_id": "u1"}, action="invalid"
        )
    assert "error" in r


@pytest.mark.asyncio
async def test_m5_freeze_returns_confirm_card(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.permission import Tenant
    from sqlalchemy import select
    from app.agents.domains.polish_v340_tools import _toggle_hard_write_freeze_with_confirm
    async with AsyncSessionLocal() as db:
        # 確保 HQ tenant 存在
        t = (await db.execute(select(Tenant).where(Tenant.code == "HQ"))).scalar_one_or_none()
        if t is None:
            t = Tenant(id=str(uuid.uuid4()), code="HQ", name="Test HQ",
                       tenant_type="hq", is_active=True, settings={})
            db.add(t)
            await db.commit()
        r = await _toggle_hard_write_freeze_with_confirm(
            db, {"user_id": "u1"}, action="freeze", days=14, reason="老闆出國"
        )
    assert r.get("type") == "confirm_card", f"got {r}"


@pytest.mark.asyncio
async def test_m5_engine_blocks_hard_write_when_frozen(seeded_client):
    """凍結後執行任一 hard-write tool → 應回 frozen=true。"""
    from app.database import AsyncSessionLocal
    from app.models.permission import Tenant
    from datetime import datetime, timedelta, UTC
    from sqlalchemy import select
    from app.agents.engine import execute_tool

    async with AsyncSessionLocal() as db:
        t = (await db.execute(select(Tenant).where(Tenant.code == "HQ"))).scalar_one_or_none()
        if t is None:
            t = Tenant(id=str(uuid.uuid4()), code="HQ", name="Test HQ",
                       tenant_type="hq", is_active=True, settings={})
            db.add(t)
            await db.commit()
        # 強制凍結
        settings = dict(t.settings or {})
        settings["hard_write_frozen_until"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        settings["hard_write_freeze_reason"] = "test"
        t.settings = settings
        await db.commit()

        # 嘗試執行 hard-write tool（用 set_company_info）→ 應被攔截
        result = await execute_tool(
            "set_company_info_with_confirm",
            {"name": "X"}, db=db, user={"user_id": "u-test"},
        )
        parsed = json.loads(result)
        assert parsed.get("frozen") is True, f"應被凍結攔截：{parsed}"

        # toggle_hard_write_freeze_with_confirm 本身不應被攔
        result2 = await execute_tool(
            "toggle_hard_write_freeze_with_confirm",
            {"action": "unfreeze"}, db=db, user={"user_id": "u-test"},
        )
        parsed2 = json.loads(result2)
        assert parsed2.get("frozen") is not True, "解凍工具不應被攔"

        # 清乾淨
        settings = dict(t.settings or {})
        settings.pop("hard_write_frozen_until", None)
        settings.pop("hard_write_freeze_reason", None)
        t.settings = settings
        await db.commit()


# ════════════════════════════════════════════════════════════════════
# M6: Audit log 搜尋
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_m6_audit_search_empty(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v340_tools import _query_audit_log_search
    async with AsyncSessionLocal() as db:
        r = await _query_audit_log_search(
            db, None, actor_keyword="nosuch-user-xxx", days_back=30
        )
    assert "summary" in r
    assert r["raw"]["count"] == 0


# ════════════════════════════════════════════════════════════════════
# M7: 比較訂單
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_m7_compare_orders_invalid_doc_type(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v340_tools import _compare_orders
    async with AsyncSessionLocal() as db:
        r = await _compare_orders(db, None, doc_type="invalid", no_a="A", no_b="B")
    assert "error" in r


@pytest.mark.asyncio
async def test_m7_compare_orders_both_not_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v340_tools import _compare_orders
    async with AsyncSessionLocal() as db:
        r = await _compare_orders(db, None, doc_type="so",
                                   no_a="NOSUCH-1", no_b="NOSUCH-2")
    assert "error" in r


@pytest.mark.asyncio
async def test_m7_compare_orders_real(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder
    from app.agents.domains.polish_v340_tools import _compare_orders
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"CMP-{s}", name=f"Compare {s}")
        db.add(cu)
        await db.flush()
        a = SalesOrder(id=str(uuid.uuid4()), so_no=f"SO-A-{s}",
                       customer_id=cu.id, total_amount=1000, status="draft")
        b = SalesOrder(id=str(uuid.uuid4()), so_no=f"SO-B-{s}",
                       customer_id=cu.id, total_amount=2000, status="confirmed")
        db.add(a); db.add(b)
        await db.commit()

        r = await _compare_orders(db, None, doc_type="so",
                                   no_a=f"SO-A-{s}", no_b=f"SO-B-{s}")
    assert "summary" in r
    assert r["raw"]["total_amount"]["a"] == 1000
    assert r["raw"]["total_amount"]["b"] == 2000


# ════════════════════════════════════════════════════════════════════
# M4: Delete + undo
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_m4_delete_customer_pushes_undo(seeded_client):
    """刪除後 undo stack 應有一筆 delete_customer。"""
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from app.agents.domains.polish_v339_tools import _delete_customer_with_confirm
    from app.agents.domains.polish_tools import _UNDO_STACK
    from app.agents.confirm_card import consume_card

    s = uuid.uuid4().hex[:5]
    user_id = f"u-m4-{s}"
    _UNDO_STACK.pop(user_id, None)

    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"DEL-M4-{s}", name=f"Delete M4 {s}")
        db.add(cu)
        await db.commit()

        # 走確認流程
        r = await _delete_customer_with_confirm(
            db, {"user_id": user_id, "employee_id": user_id},
            customer_keyword=f"DEL-M4-{s}",
        )
        assert r["type"] == "confirm_card"
        card_id = r["card"]["id"]

        # 模擬確認執行
        entry = await consume_card(card_id)
        assert entry is not None
        exec_result = await entry["executor"]()
        # 成功訊息含「90 秒內可撤銷」
        assert "撤銷" in (exec_result.get("message") or "")

    # undo stack 應有一筆
    stack = _UNDO_STACK.get(user_id, [])
    assert len(stack) >= 1
    assert stack[-1]["kind"] == "delete_customer"
    assert "snapshot" in stack[-1]["before"]
