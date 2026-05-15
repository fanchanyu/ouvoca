"""Smoke tests for v3.5 Email digest service + API + AI tools。"""
from __future__ import annotations

import pytest
import pytest_asyncio

from app.agents.confirm_card import _clear_all_for_test, consume_card


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


@pytest.fixture
def demo_user():
    return {"employee_id": "emp-digest-001", "username": "tester", "roles": ["admin"]}


# ============================================================
# Service 層
# ============================================================

class TestBuildDigest:
    @pytest.mark.asyncio
    async def test_build_digest_basic(self, db):
        """空 DB 也應該 build 得出 digest（不炸）。"""
        from app.services.email_digest import build_digest
        d = await build_digest(db, recipient="boss@example.com", period_hours=24)
        assert d.generated_at
        assert d.period_label
        assert len(d.sections) == 3  # alerts + events + KPI
        assert d.summary_line

    @pytest.mark.asyncio
    async def test_digest_to_markdown(self, db):
        from app.services.email_digest import build_digest
        d = await build_digest(db, period_hours=24)
        md = d.to_markdown()
        assert "# 老闆儀表板" in md
        assert "關鍵警示" in md
        assert "KPI 快照" in md

    @pytest.mark.asyncio
    async def test_digest_to_html(self, db):
        from app.services.email_digest import build_digest
        d = await build_digest(db, period_hours=24)
        html = d.to_html()
        assert "<!DOCTYPE html>" in html
        assert "老闆儀表板" in html
        assert "</body>" in html

    @pytest.mark.asyncio
    async def test_digest_to_dict_serializable(self, db):
        """to_dict 結果必須能 JSON 序列化。"""
        import json
        from app.services.email_digest import build_digest
        d = await build_digest(db, period_hours=24)
        s = json.dumps(d.to_dict(), ensure_ascii=False)
        assert "sections" in s

    @pytest.mark.asyncio
    async def test_digest_clamps_period(self, db):
        """period_hours 太小應該不炸。"""
        from app.services.email_digest import build_digest
        d = await build_digest(db, period_hours=1)
        assert d.period_label

    @pytest.mark.asyncio
    async def test_digest_includes_low_stock_alerts(self, db):
        """有低於安全庫存的料件時，alerts 應該列出。"""
        from app.services.email_digest import build_digest
        from app.models.inventory import Inventory, Part
        import uuid

        # 造一個低於安全的料件
        p = Part(
            id=str(uuid.uuid4()), part_no="DIGEST-LOW-1", name="測試料件",
            category="component", safety_stock=100, unit_cost=10,
        )
        db.add(p)
        await db.flush()
        inv = Inventory(
            id=str(uuid.uuid4()), part_id=p.id,
            qty_on_hand=30, qty_available=30, qty_allocated=0,
        )
        db.add(inv)
        await db.commit()

        d = await build_digest(db)
        alerts = d.sections[0]
        # 應該有警示 item
        types = {i.get("type") for i in alerts.items}
        assert "low_stock" in types

        # cleanup
        from sqlalchemy import delete
        await db.execute(delete(Inventory).where(Inventory.part_id == p.id))
        await db.execute(delete(Part).where(Part.id == p.id))
        await db.commit()


# ============================================================
# SMTP send (dry-run)
# ============================================================

class TestSendEmail:
    def test_send_email_dry_run_without_smtp(self):
        """SMTP_HOST 沒設時，回 dry_run。settings 沒這個欄位，getattr fallback "" → dry_run."""
        from app.services.email_digest import send_email
        result = send_email("test@example.com", "test subject", "<p>hi</p>")
        assert result["sent"] is False
        assert result["dry_run"] is True

    def test_send_email_includes_preview(self):
        from app.services.email_digest import send_email
        result = send_email("test@example.com", "hello", "<p>x</p>")
        assert "preview" in result
        assert result["preview"]["to"] == "test@example.com"


# ============================================================
# API endpoints
# ============================================================

class TestEmailDigestAPI:
    def test_preview_endpoint(self, seeded_client, admin_headers):
        r = seeded_client.get("/api/email-digest/preview", headers=admin_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "summary_line" in data
        assert "sections" in data
        assert len(data["sections"]) == 3

    def test_preview_html_endpoint(self, seeded_client, admin_headers):
        r = seeded_client.get("/api/email-digest/preview.html", headers=admin_headers)
        assert r.status_code == 200
        assert "<!DOCTYPE html>" in r.text
        assert "老闆儀表板" in r.text

    def test_send_endpoint_invalid_email(self, seeded_client, admin_headers):
        r = seeded_client.post(
            "/api/email-digest/send?to=not_an_email",
            headers=admin_headers,
        )
        assert r.status_code == 400

    def test_send_endpoint_dry_run(self, seeded_client, admin_headers):
        """SMTP 沒設 → dry_run，仍回 200。"""
        r = seeded_client.post(
            "/api/email-digest/send?to=wang@example.com",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("dry_run") is True or data.get("sent") is False


# ============================================================
# AI tools
# ============================================================

class TestEmailDigestTools:
    @pytest.mark.asyncio
    async def test_preview_email_digest_tool(self, db, demo_user):
        from app.agents.domains.email_digest_tools import _preview_digest
        result = await _preview_digest(db=db, user=demo_user)
        assert "summary_line" in result
        assert len(result["sections"]) == 3

    @pytest.mark.asyncio
    async def test_send_digest_tool_emits_confirm_card(self, db, demo_user):
        from app.agents.domains.email_digest_tools import _send_digest_with_confirm
        result = await _send_digest_with_confirm(
            db=db, user=demo_user, to="wang@example.com",
        )
        assert result.get("type") == "confirm_card"
        assert "wang@example.com" in " ".join(result["card"]["summary"])

    @pytest.mark.asyncio
    async def test_send_digest_invalid_email_no_card(self, db, demo_user):
        from app.agents.domains.email_digest_tools import _send_digest_with_confirm
        result = await _send_digest_with_confirm(
            db=db, user=demo_user, to="not_an_email",
        )
        assert "error" in result
        assert result.get("type") != "confirm_card"

    @pytest.mark.asyncio
    async def test_send_digest_confirm_dry_run(self, db, demo_user):
        """confirm 後執行：SMTP 沒設 → dry_run，不炸。"""
        from app.agents.domains.email_digest_tools import _send_digest_with_confirm
        result = await _send_digest_with_confirm(
            db=db, user=demo_user, to="wang@example.com",
        )
        card_id = result["card"]["id"]
        entry = await consume_card(card_id)
        exec_result = await entry["executor"]()
        # dry_run 或 sent，不應該炸
        assert "to" in exec_result
        assert "message" in exec_result


# ============================================================
# Registry sanity
# ============================================================

def test_v35_tools_registered():
    from app.agents import TOOL_FUNCTIONS, AGENT_REGISTRY
    assert "preview_email_digest" in TOOL_FUNCTIONS
    assert "send_email_digest_with_confirm" in TOOL_FUNCTIONS

    # 接到 general / purchase / sales / production agents
    for ag in ("general", "purchase", "sales", "production"):
        tools = AGENT_REGISTRY[ag]["tool_names"]
        assert "preview_email_digest" in tools, f"missing in {ag}"
        assert "send_email_digest_with_confirm" in tools, f"missing in {ag}"


def test_send_digest_is_hard_write():
    from app.agents.registry import get_tool, RiskTier
    meta = get_tool("send_email_digest_with_confirm")
    assert meta.risk_tier == RiskTier.HARD_WRITE
    assert meta.required_permission is not None
