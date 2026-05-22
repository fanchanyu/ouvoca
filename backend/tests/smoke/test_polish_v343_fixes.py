"""v3.43 P0/P1 真實診斷後的修補驗證

P0-1: install.bat / install.sh 加 port 預檢（純 script，無 Python test，只驗存在）
P0-2: Login.tsx 用 err.friendly() — frontend，無 Python test
P0-3: Dashboard wizard 用 localStorage 條件 — frontend
P1-1: AttachmentResponse 多 4 欄位（parsed_status / parsed_target_type / parsed_target_id / parsed_at）
P1-2: chat.py setup_required branch 寫 ConversationLog assistant 記錄
P1-3: .env.example CORS_ORIGINS 加 127.0.0.1
P1-4: engine.py freeze 回傳含 http_equivalent=423 + frozen_reason + tool_blocked
"""
from __future__ import annotations

import json
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]


# ════════════════════════════════════════════════════════════════════
# P0-1: install scripts 加 port 預檢
# ════════════════════════════════════════════════════════════════════

def test_p0_1_install_bat_has_port_precheck():
    bat = (ROOT / "install.bat").read_text(encoding="utf-8", errors="ignore")
    assert "Port" in bat and "8000" in bat and "5173" in bat and "8080" in bat
    assert "netstat" in bat.lower(), "install.bat 缺 port 檢查"
    assert "已被佔用" in bat or "in use" in bat


def test_p0_1_install_sh_has_port_precheck():
    sh = (ROOT / "install.sh").read_text(encoding="utf-8", errors="ignore")
    assert "8000" in sh and "5173" in sh and "8080" in sh
    assert "lsof" in sh or "nc -z" in sh or "netstat" in sh, "install.sh 缺 port 檢查"


# ════════════════════════════════════════════════════════════════════
# P0-2: Login.tsx 用 err.friendly()
# ════════════════════════════════════════════════════════════════════

def test_p0_2_login_calls_friendly():
    login_tsx = (ROOT / "frontend-desktop" / "src" / "pages" / "Login.tsx").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "err.friendly()" in login_tsx, "Login.tsx 仍用 err.message 而非 friendly()"


# ════════════════════════════════════════════════════════════════════
# P0-3: Dashboard wizard 用 localStorage
# ════════════════════════════════════════════════════════════════════

def test_p0_3_dashboard_uses_first_seen_flag():
    db_tsx = (ROOT / "frontend-desktop" / "src" / "pages" / "Dashboard.tsx").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "erpilot_first_seen" in db_tsx, "Dashboard.tsx 缺 first_seen 邏輯"


# ════════════════════════════════════════════════════════════════════
# P1-1: AttachmentResponse 暴露 parsed_target_*
# ════════════════════════════════════════════════════════════════════

def test_p1_1_attachment_response_has_parsed_fields():
    from app.api.files import AttachmentResponse
    fields = AttachmentResponse.model_fields
    assert "parsed_target_type" in fields
    assert "parsed_target_id" in fields
    assert "parsed_status" in fields
    assert "parsed_at" in fields


# ════════════════════════════════════════════════════════════════════
# P1-2: chat.py setup_required 寫 ConversationLog
# ════════════════════════════════════════════════════════════════════

def test_p1_2_chat_setup_required_persists_assistant_log():
    chat_py = (ROOT / "backend" / "app" / "api" / "chat.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    # setup_required branch 應該有兩個 db.add(ConversationLog(...))（user + assistant）
    # 或 setup_reply 變數 + ConversationLog 寫入
    assert "setup_reply" in chat_py
    assert chat_py.count('role="assistant"') >= 2, (
        "chat.py setup_required branch 應該也 persist assistant_log"
    )


# ════════════════════════════════════════════════════════════════════
# P1-3: .env.example CORS_ORIGINS 加 127.0.0.1
# ════════════════════════════════════════════════════════════════════

def test_p1_3_env_example_cors_has_127_0_0_1():
    env_example = (ROOT / "backend" / ".env.example").read_text(
        encoding="utf-8", errors="ignore"
    )
    # 找 CORS_ORIGINS 行
    cors_line = None
    for line in env_example.split("\n"):
        if line.startswith("CORS_ORIGINS"):
            cors_line = line
            break
    assert cors_line is not None
    assert "127.0.0.1" in cors_line, ".env.example CORS_ORIGINS 缺 127.0.0.1"


# ════════════════════════════════════════════════════════════════════
# P1-4: engine.py freeze response 含 http_equivalent
# ════════════════════════════════════════════════════════════════════

def test_p1_4_freeze_response_has_http_equivalent():
    engine_py = (ROOT / "backend" / "app" / "agents" / "engine.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "http_equivalent" in engine_py
    assert "423" in engine_py, "engine.py freeze 缺 http_equivalent=423"
    assert "frozen_reason" in engine_py
    assert "tool_blocked" in engine_py


@pytest.mark.asyncio
async def test_p1_4_freeze_blocks_tool_with_rich_payload(seeded_client):
    """凍結後執行 hard-write tool → 應回含 http_equivalent / frozen_reason / tool_blocked。"""
    import uuid as _uuid
    from app.database import AsyncSessionLocal
    from app.models.permission import Tenant
    from datetime import datetime, timedelta, UTC
    from sqlalchemy import select
    from app.agents.engine import execute_tool

    async with AsyncSessionLocal() as db:
        t = (await db.execute(select(Tenant).where(Tenant.code == "HQ"))).scalar_one_or_none()
        if t is None:
            t = Tenant(id=str(_uuid.uuid4()), code="HQ", name="Test HQ",
                       tenant_type="hq", is_active=True, settings={})
            db.add(t)
            await db.commit()
        settings = dict(t.settings or {})
        settings["hard_write_frozen_until"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        settings["hard_write_freeze_reason"] = "test"
        t.settings = settings
        await db.commit()

        result = await execute_tool(
            "create_customer_with_confirm",
            {"name": "X"}, db=db, user={"user_id": "u-test"},
        )
        parsed = json.loads(result)
        assert parsed.get("frozen") is True
        assert parsed.get("http_equivalent") == 423
        assert parsed.get("frozen_reason") == "test"
        assert parsed.get("tool_blocked") == "create_customer_with_confirm"

        # 清乾淨
        settings = dict(t.settings or {})
        settings.pop("hard_write_frozen_until", None)
        settings.pop("hard_write_freeze_reason", None)
        t.settings = settings
        await db.commit()


# ════════════════════════════════════════════════════════════════════
# P1-4 bonus: undo_last_admin_change 凍結時仍可呼叫
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_p1_4_undo_still_works_when_frozen(seeded_client):
    """凍結期間 undo_last_admin_change 不被攔（讓使用者能還原誤操作）。"""
    import uuid as _uuid
    from app.database import AsyncSessionLocal
    from app.models.permission import Tenant
    from datetime import datetime, timedelta, UTC
    from sqlalchemy import select
    from app.agents.engine import execute_tool

    async with AsyncSessionLocal() as db:
        t = (await db.execute(select(Tenant).where(Tenant.code == "HQ"))).scalar_one_or_none()
        if t is None:
            t = Tenant(id=str(_uuid.uuid4()), code="HQ", name="Test HQ",
                       tenant_type="hq", is_active=True, settings={})
            db.add(t)
            await db.commit()
        settings = dict(t.settings or {})
        settings["hard_write_frozen_until"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        t.settings = settings
        await db.commit()

        result = await execute_tool(
            "undo_last_admin_change",
            {}, db=db, user={"user_id": "u-test"},
        )
        parsed = json.loads(result)
        # 不應該被凍結攔截
        assert parsed.get("frozen") is not True, f"undo 被誤攔：{parsed}"

        # 清乾淨
        settings = dict(t.settings or {})
        settings.pop("hard_write_frozen_until", None)
        t.settings = settings
        await db.commit()
