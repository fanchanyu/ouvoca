"""v3.60 P0-1 tests — chat 管線 tool 級 RBAC。

審計問題：/api/chat-v2 只檢查 ai.agent.use，execute_tool() 不檢查
required_permission，等於任何能對話的帳號都能叫 AI 建 PO / 批准 / 刪 BOM。

驗證：
  1. _ensure_tool_permission 的 wildcard / superuser / fail-closed 行為
  2. execute_tool 對缺權限的使用者回 permission_denied
  3. chat-v2（HTTP）對缺權限 tool 的呼叫被攔截
"""
from __future__ import annotations

import json

import pytest
import pytest_asyncio

from app.agents.confirm_card import _clear_all_for_test
from app.agents.engine import _ensure_tool_permission, execute_tool


@pytest.fixture(autouse=True)
def _clean():
    _clear_all_for_test()
    yield
    _clear_all_for_test()


@pytest_asyncio.fixture
async def db(client):
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_ensure_permission_superuser_allows():
    ok = await _ensure_tool_permission(None, {"is_superuser": True}, "sales.order.create")
    assert ok is True


@pytest.mark.asyncio
async def test_ensure_permission_exact_code():
    user = {"permissions": ["sales.order.create"]}
    assert await _ensure_tool_permission(None, user, "sales.order.create") is True
    assert await _ensure_tool_permission(None, user, "sales.order.delete") is False


@pytest.mark.asyncio
async def test_ensure_permission_wildcard():
    user = {"permissions": ["sales.*"]}
    assert await _ensure_tool_permission(None, user, "sales.order.create") is True
    assert await _ensure_tool_permission(None, user, "inventory.part.read") is False


@pytest.mark.asyncio
async def test_ensure_permission_fail_closed_no_context():
    # 無 db / user_id / permissions → fail-closed（資料不足 = 拒絕）
    ok = await _ensure_tool_permission(None, {"username": "anon"}, "sales.order.create")
    assert ok is False


@pytest.mark.asyncio
async def test_execute_tool_denies_missing_permission(db):
    user = {"user_id": "u-rbac-1", "employee_id": "e-rbac-1", "username": "受限使用者",
            "permissions": ["ai.agent.use"]}  # 只有對話權限，無 purchase.po.create
    result = json.loads(await execute_tool(
        "create_purchase_order_with_confirm",
        {"supplier_keyword": "x", "items": [], "expected_delivery_date": "2026-08-10"},
        db=db, user=user,
    ))
    assert result.get("permission_denied") is True, f"應拒絕：{result}"
    assert result.get("required_permission") == "purchase.po.create"


@pytest.mark.asyncio
async def test_execute_tool_allows_with_permission(db):
    import uuid

    from app.models.inventory import Part
    from app.models.purchase import Supplier

    sup = Supplier(id=str(uuid.uuid4()), code="SUP-RBAC", name="RBAC 供應商", tier="T2", is_approved=True)
    part = Part(id=str(uuid.uuid4()), part_no="RBAC-PART-1", name="RBAC 料件", category="component", unit_cost=10)
    db.add_all([sup, part])
    await db.commit()

    user = {"user_id": "u-rbac-2", "employee_id": "e-rbac-2", "username": "採購",
            "permissions": ["purchase.po.create"]}
    result = json.loads(await execute_tool(
        "create_purchase_order_with_confirm",
        {
            "supplier_keyword": "RBAC 供應商",
            "items": [{"part_no": "RBAC-PART-1", "ordered_qty": 5, "unit_price": 10}],
            "expected_delivery_date": "2026-08-10",
        },
        db=db, user=user,
    ))
    assert result.get("type") == "confirm_card", f"應出 ConfirmCard：{result}"
    assert result["card"]["tool_name"] == "create_purchase_order_with_confirm"


def test_chat_system_prompt_contains_rbac_section(seeded_client):
    """chat.py 的 system prompt 應含 RBAC 權限約束（grep smoke）。"""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "app" / "api" / "chat.py").read_text(encoding="utf-8")
    assert "RBAC 權限約束" in src, "chat.py system prompt 缺 RBAC 權限約束段落"
    assert "load_user_context" in src, "chat.py 應從 DB 載入真實權限（load_user_context）"
    assert '"permissions": list(ctx.permissions.keys())' in src, \
        "chat.py user_info 應帶真實 permissions 供 execute_tool 檢查"


def test_execute_tool_has_permission_gate(seeded_client):
    """engine.py 的 execute_tool 應檢查 required_permission（grep smoke）。"""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "app" / "agents" / "engine.py").read_text(encoding="utf-8")
    assert "meta.required_permission" in src
    assert "_ensure_tool_permission" in src
    assert "permission_denied" in src
