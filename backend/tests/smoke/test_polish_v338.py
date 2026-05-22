"""v3.38 第二輪小白卡關修補 smoke 測試

N1：ConfirmCard TTL 5min → 30min
N2：Generic undo（undo_last_admin_change + push_undo）
N3：query_ai_cost_today / month
N4：backup_database / list_recent_backups
N6：global ValueError handler
N7：resolve_customer_candidates（多筆同名）
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


V338_TOOLS = [
    "query_ai_cost_today",
    "query_ai_cost_this_month",
    "backup_database_with_confirm",
    "list_recent_backups",
    "resolve_customer_candidates",
    "undo_last_admin_change",
]


def test_v338_tools_registered():
    for n in V338_TOOLS:
        assert get_tool(n) is not None, f"{n} 未註冊"


def test_v338_risk_tiers():
    assert get_tool("query_ai_cost_today").risk_tier == RiskTier.READ
    assert get_tool("query_ai_cost_this_month").risk_tier == RiskTier.READ
    assert get_tool("backup_database_with_confirm").risk_tier == RiskTier.HARD_WRITE
    assert get_tool("list_recent_backups").risk_tier == RiskTier.READ
    assert get_tool("resolve_customer_candidates").risk_tier == RiskTier.READ
    assert get_tool("undo_last_admin_change").risk_tier == RiskTier.HARD_WRITE


# ════════════════════════════════════════════════════════════════════
# N1: TTL 改 30 分鐘
# ════════════════════════════════════════════════════════════════════

def test_n1_confirm_card_ttl_is_30_minutes():
    from app.agents.confirm_card import DEFAULT_TTL_SECONDS
    assert DEFAULT_TTL_SECONDS == 1800, (
        f"v3.38 N1: TTL 應為 1800 秒（30 分鐘），實際 {DEFAULT_TTL_SECONDS}"
    )


# ════════════════════════════════════════════════════════════════════
# N3: AI 成本
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_query_ai_cost_today(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_tools import _query_ai_cost_today
    async with AsyncSessionLocal() as db:
        result = await _query_ai_cost_today(db, None)
    assert "summary" in result
    assert "raw" in result
    # 空 DB 時 usd=0
    assert result["raw"]["usd"] == 0 or "error" in result["raw"]


@pytest.mark.asyncio
async def test_query_ai_cost_month(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_tools import _query_ai_cost_this_month
    async with AsyncSessionLocal() as db:
        result = await _query_ai_cost_this_month(db, None)
    assert "summary" in result


# ════════════════════════════════════════════════════════════════════
# N4: Backup
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_backups_empty(seeded_client, tmp_path, monkeypatch):
    from app.agents.domains import polish_tools
    monkeypatch.setattr(polish_tools, "BACKUP_DIR", tmp_path / "backups")
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await polish_tools._list_recent_backups(db, None)
    assert "尚無備份" in result["summary"]
    assert result["raw"]["count"] == 0


@pytest.mark.asyncio
async def test_backup_returns_confirm_card(seeded_client, tmp_path, monkeypatch):
    """SQLite 環境下 → 回 confirm card。"""
    from app.agents.domains import polish_tools
    monkeypatch.setattr(polish_tools, "BACKUP_DIR", tmp_path / "backups")
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await polish_tools._backup_database_with_confirm(
            db, {"user_id": "u1"}, note="test-backup",
        )
    # SQLite path → confirm_card
    assert result.get("type") == "confirm_card"


# ════════════════════════════════════════════════════════════════════
# N7: Customer disambiguation
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_resolve_customer_no_match(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_tools import _resolve_customer_candidates
    async with AsyncSessionLocal() as db:
        result = await _resolve_customer_candidates(db, None, keyword="NOSUCH-XYZ-999")
    assert "找不到" in result["summary"]
    assert result["raw"]["matched"] == "none"


@pytest.mark.asyncio
async def test_resolve_customer_multiple(seeded_client):
    """建 3 個都叫 ABC 的客戶 → 應回 candidates 清單。"""
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from app.agents.domains.polish_tools import _resolve_customer_candidates

    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        for suffix in ("公司", "工業", "商行"):
            db.add(Customer(
                id=str(uuid.uuid4()),
                code=f"AB-{s}-{suffix[0]}",
                name=f"ABC-{s} {suffix}",
            ))
        await db.commit()

        result = await _resolve_customer_candidates(
            db, None, keyword=f"ABC-{s}",
        )
    assert result["raw"]["matched"] == "multiple"
    assert result["raw"]["count"] == 3
    assert len(result["raw"]["candidates"]) == 3


# ════════════════════════════════════════════════════════════════════
# N2: undo 流程
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_undo_no_stack(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_tools import _undo_last_admin_change, _UNDO_STACK
    # 清乾淨
    _UNDO_STACK.clear()
    async with AsyncSessionLocal() as db:
        result = await _undo_last_admin_change(db, {"user_id": "u-empty"})
    assert "沒有可撤銷" in result["summary"]
    assert result["raw"]["undoable"] is False


@pytest.mark.asyncio
async def test_undo_after_push(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_tools import (
        _undo_last_admin_change, push_undo, _UNDO_STACK,
    )
    _UNDO_STACK.clear()
    push_undo("u-push", {
        "kind": "set_company_info",
        "before": {"name": "舊公司", "settings": {"name": "舊公司"}},
    })
    async with AsyncSessionLocal() as db:
        result = await _undo_last_admin_change(db, {"user_id": "u-push"})
    # 應該回 confirm_card
    assert result["type"] == "confirm_card"


# ════════════════════════════════════════════════════════════════════
# N6: Global ValueError handler — 透過 client 觸發
# ════════════════════════════════════════════════════════════════════

def test_n6_value_error_returns_friendly_chinese(seeded_client, admin_headers):
    """傳一個 422 / 400 的請求，看 detail 是否含中文。"""
    # 故意送 invalid quote_id 給 print endpoint → service 應拋 ValueError
    r = seeded_client.get("/api/print/quotation/nosuch-id-xyz.pdf", headers=admin_headers)
    # 期望 404（找不到報價單）→ raise HTTPException 走 friendly_msg
    assert r.status_code in (400, 404)
    payload = r.json()
    detail = str(payload.get("detail", ""))
    # 應包含中文
    has_chinese = any('一' <= c <= '鿿' for c in detail)
    assert has_chinese, f"detail 應為中文：{payload}"
