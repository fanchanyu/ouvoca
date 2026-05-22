"""v3.41 第五輪小白卡關修補 smoke 測試

P1: query_customer_profitability — 客戶毛利率
P2: trace_order_lifecycle — 訂單跟單
P5: email_pdf_to_customer_with_confirm — 寄 PDF email
P6: ask_faq — FAQ
P7: chat feedback endpoint
P8: run_data_health_check — 資料健康
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


V341_TOOLS = [
    "query_customer_profitability",
    "trace_order_lifecycle",
    "email_pdf_to_customer_with_confirm",
    "ask_faq",
    "run_data_health_check",
]


def test_v341_tools_registered():
    for n in V341_TOOLS:
        assert get_tool(n) is not None, f"{n} 未註冊"


def test_v341_risk_tiers():
    assert get_tool("email_pdf_to_customer_with_confirm").risk_tier == RiskTier.HARD_WRITE
    for n in ["query_customer_profitability", "trace_order_lifecycle",
              "ask_faq", "run_data_health_check"]:
        assert get_tool(n).risk_tier == RiskTier.READ


# ════════════════════════════════════════════════════════════════════
# P1: 客戶毛利率
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_p1_profitability_empty(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v341_tools import _query_customer_profitability
    async with AsyncSessionLocal() as db:
        r = await _query_customer_profitability(
            db, None, customer_keyword="NOSUCH-CUST-XYZ", days_back=30,
        )
    assert "summary" in r
    assert r["raw"]["count"] == 0


@pytest.mark.asyncio
async def test_p1_profitability_real(seeded_client):
    """建客戶 + 產品 + SO + items 驗證毛利率計算。"""
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder, SalesOrderItem
    from app.models.product import Product
    from app.agents.domains.polish_v341_tools import _query_customer_profitability

    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"PROF-{s}",
                       name=f"Prof Test {s}")
        prod = Product(id=str(uuid.uuid4()), product_no=f"P-{s}",
                       name=f"Widget {s}", selling_price=100,
                       standard_cost=60)
        db.add(cu); db.add(prod); await db.flush()
        so = SalesOrder(id=str(uuid.uuid4()), so_no=f"SO-PROF-{s}",
                        customer_id=cu.id, status="confirmed",
                        total_amount=1000)
        db.add(so); await db.flush()
        item = SalesOrderItem(
            id=str(uuid.uuid4()), so_id=so.id, line_no=1,
            product_id=prod.id, ordered_qty=10, unit_price=100, line_total=1000,
        )
        db.add(item); await db.commit()

        r = await _query_customer_profitability(
            db, None, customer_keyword=f"PROF-{s}",
        )

    assert r["raw"]["count"] == 1
    row = r["raw"]["rows"][0]
    assert row["revenue"] == 1000
    assert row["cost"] == 600  # 10 * 60
    assert row["gross_profit"] == 400
    assert abs(row["margin_pct"] - 40.0) < 0.01


# ════════════════════════════════════════════════════════════════════
# P2: 訂單跟單
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_p2_lifecycle_not_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v341_tools import _trace_order_lifecycle
    async with AsyncSessionLocal() as db:
        r = await _trace_order_lifecycle(db, None, doc_no="NOSUCH-XYZ-999")
    assert "error" in r


@pytest.mark.asyncio
async def test_p2_lifecycle_so_only(seeded_client):
    """建 SO 沒有對應 Quote → timeline 只有 SO 段。"""
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder
    from app.agents.domains.polish_v341_tools import _trace_order_lifecycle

    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"LC-{s}", name=f"LC {s}")
        db.add(cu); await db.flush()
        so = SalesOrder(id=str(uuid.uuid4()), so_no=f"SO-LC-{s}",
                        customer_id=cu.id, status="confirmed",
                        total_amount=5000)
        db.add(so); await db.commit()

        r = await _trace_order_lifecycle(db, None, doc_no=f"SO-LC-{s}")

    assert "timeline" in r["raw"]
    assert any(t["stage"].startswith("🤝") for t in r["raw"]["timeline"])


# ════════════════════════════════════════════════════════════════════
# P5: Email PDF
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_p5_invalid_doc_type(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v341_tools import _email_pdf_to_customer_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _email_pdf_to_customer_with_confirm(
            db, {"user_id": "u1"}, doc_type="invalid", doc_no="X",
        )
    assert "error" in r


@pytest.mark.asyncio
async def test_p5_doc_not_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v341_tools import _email_pdf_to_customer_with_confirm
    async with AsyncSessionLocal() as db:
        r = await _email_pdf_to_customer_with_confirm(
            db, {"user_id": "u1"}, doc_type="so", doc_no="NOSUCH-SO-XYZ",
            to_email="test@example.com",
        )
    assert "error" in r


@pytest.mark.asyncio
async def test_p5_no_email_no_default(seeded_client):
    """SO 客戶無 email + 未提供 to_email → 應 error。"""
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder
    from app.agents.domains.polish_v341_tools import _email_pdf_to_customer_with_confirm

    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"E5-{s}", name=f"E5 {s}",
                       contact_email=None)
        db.add(cu); await db.flush()
        so = SalesOrder(id=str(uuid.uuid4()), so_no=f"SO-E5-{s}",
                        customer_id=cu.id, status="draft")
        db.add(so); await db.commit()

        r = await _email_pdf_to_customer_with_confirm(
            db, {"user_id": "u1"}, doc_type="so", doc_no=f"SO-E5-{s}",
        )
    assert "error" in r
    assert "email" in r["error"].lower()


@pytest.mark.asyncio
async def test_p5_returns_confirm_card(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder
    from app.agents.domains.polish_v341_tools import _email_pdf_to_customer_with_confirm

    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"E5C-{s}", name=f"E5C {s}",
                       contact_email="test@example.com")
        db.add(cu); await db.flush()
        so = SalesOrder(id=str(uuid.uuid4()), so_no=f"SO-E5C-{s}",
                        customer_id=cu.id, status="draft")
        db.add(so); await db.commit()

        r = await _email_pdf_to_customer_with_confirm(
            db, {"user_id": "u1"}, doc_type="so", doc_no=f"SO-E5C-{s}",
        )
    assert r.get("type") == "confirm_card"


# ════════════════════════════════════════════════════════════════════
# P6: FAQ
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_p6_faq_list_all(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v341_tools import _ask_faq
    async with AsyncSessionLocal() as db:
        r = await _ask_faq(db, None)
    assert r["raw"]["count"] >= 5


@pytest.mark.asyncio
async def test_p6_faq_price(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v341_tools import _ask_faq
    async with AsyncSessionLocal() as db:
        r = await _ask_faq(db, None, question="erpilot 多少錢")
    assert r["raw"]["matched"] is True
    assert "30 萬" in r["summary"] or "50 萬" in r["summary"]


@pytest.mark.asyncio
async def test_p6_faq_offline(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v341_tools import _ask_faq
    async with AsyncSessionLocal() as db:
        r = await _ask_faq(db, None, question="斷網能用嗎")
    assert r["raw"]["matched"] is True
    assert "斷網" in r["summary"] or "離線" in r["summary"]


# ════════════════════════════════════════════════════════════════════
# P8: 資料健康檢查
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_p8_health_check_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v341_tools import _run_data_health_check
    async with AsyncSessionLocal() as db:
        r = await _run_data_health_check(db, None)
    assert "summary" in r
    assert "raw" in r
    # 6 個 metric 都應存在
    for k in ("duplicate_customer_codes", "duplicate_part_nos",
              "bom_self_reference", "orphan_inventory",
              "customers_without_email", "parts_without_unit_cost"):
        assert k in r["raw"], f"{k} missing"


# ════════════════════════════════════════════════════════════════════
# P7: Chat feedback endpoint
# ════════════════════════════════════════════════════════════════════

def test_p7_feedback_endpoint_thumbs_up(seeded_client, admin_headers):
    r = seeded_client.post("/api/chat/feedback", json={
        "message_id": "test-msg-001",
        "session_id": "test-sess",
        "score": 1,
        "comment": "good",
    }, headers=admin_headers)
    assert r.status_code == 200
    payload = r.json()
    assert payload.get("saved") is True


def test_p7_feedback_endpoint_thumbs_down(seeded_client, admin_headers):
    r = seeded_client.post("/api/chat/feedback", json={
        "message_id": "test-msg-002",
        "session_id": "test-sess",
        "score": -1,
        "comment": "wrong",
    }, headers=admin_headers)
    assert r.status_code == 200
    payload = r.json()
    assert payload.get("saved") is True


def test_p7_feedback_invalid_score(seeded_client, admin_headers):
    r = seeded_client.post("/api/chat/feedback", json={
        "message_id": "test-msg-003",
        "session_id": "test-sess",
        "score": 5,
    }, headers=admin_headers)
    # 422 (pydantic) or 200 with saved=false
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json().get("saved") is False
