"""v3.39 第三輪小白卡關修補 smoke 測試

K1：upload_company_logo_with_confirm + PDF 渲染 LOGO
K2：delete_customer/part/supplier_with_confirm（含預檢查）
K3：list_customers_paginated（分頁 + offset）
K4：engine.py slot-filling 3-strike fallback
K6：trigger_daily_digest_now
K7：print_multiple_orders_with_confirm（zip 打包）
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


V339_TOOLS = [
    "upload_company_logo_with_confirm",
    "delete_customer_with_confirm",
    "delete_supplier_with_confirm",
    "delete_part_with_confirm",
    "print_multiple_orders_with_confirm",
    "trigger_daily_digest_now",
    "list_customers_paginated",
]


def test_v339_tools_registered():
    for n in V339_TOOLS:
        assert get_tool(n) is not None, f"{n} 未註冊"


def test_v339_risk_tiers():
    # hard-write
    for n in ["upload_company_logo_with_confirm",
              "delete_customer_with_confirm", "delete_supplier_with_confirm",
              "delete_part_with_confirm",
              "print_multiple_orders_with_confirm"]:
        assert get_tool(n).risk_tier == RiskTier.HARD_WRITE
    # read
    for n in ["trigger_daily_digest_now", "list_customers_paginated"]:
        assert get_tool(n).risk_tier == RiskTier.READ


# ════════════════════════════════════════════════════════════════════
# K2: Delete 三件套 — 預檢查（有訂單 → 拒絕）
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_delete_customer_not_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _delete_customer_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _delete_customer_with_confirm(
            db, {"user_id": "u1"}, customer_keyword="NOSUCH-XYZ-999",
        )
    assert "error" in result
    assert "找不到" in result["error"]


@pytest.mark.asyncio
async def test_delete_customer_with_sales_order_blocked(seeded_client):
    """有 SO 的客戶 → 預檢查應拒絕。"""
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder
    from app.agents.domains.polish_v339_tools import _delete_customer_with_confirm

    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"DEL-{s}", name=f"Delete Test {s}")
        db.add(cu)
        await db.flush()
        so = SalesOrder(
            id=str(uuid.uuid4()), so_no=f"SO-DEL-{s}",
            customer_id=cu.id, status="draft",
        )
        db.add(so)
        await db.commit()

        result = await _delete_customer_with_confirm(
            db, {"user_id": "u1"}, customer_keyword=f"DEL-{s}",
        )
    assert "error" in result
    assert "不可刪除" in result["error"]


@pytest.mark.asyncio
async def test_delete_customer_clean_returns_confirm_card(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from app.agents.domains.polish_v339_tools import _delete_customer_with_confirm

    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"DCLE-{s}", name=f"Clean Delete {s}")
        db.add(cu)
        await db.commit()

        result = await _delete_customer_with_confirm(
            db, {"user_id": "u1"}, customer_keyword=f"DCLE-{s}",
        )
    assert result["type"] == "confirm_card"


@pytest.mark.asyncio
async def test_delete_supplier_not_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _delete_supplier_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _delete_supplier_with_confirm(
            db, {"user_id": "u1"}, supplier_keyword="NOSUCH-SUP-999",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_delete_part_not_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _delete_part_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _delete_part_with_confirm(
            db, {"user_id": "u1"}, part_keyword="NOSUCH-PART-999",
        )
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# K3: 分頁
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_customers_paginated(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _list_customers_paginated
    async with AsyncSessionLocal() as db:
        result = await _list_customers_paginated(db, None, page=1, page_size=5)
    assert "summary" in result
    assert result["raw"]["page"] == 1
    assert result["raw"]["page_size"] == 5
    assert "total" in result["raw"]
    assert "items" in result["raw"]


@pytest.mark.asyncio
async def test_list_customers_paginated_page_size_clamped(seeded_client):
    """page_size 超過 50 應 clamp 到 50。"""
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _list_customers_paginated
    async with AsyncSessionLocal() as db:
        result = await _list_customers_paginated(db, None, page=1, page_size=500)
    assert result["raw"]["page_size"] == 50


# ════════════════════════════════════════════════════════════════════
# K4: Slot-filling 3-strike fallback
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_k4_slot_retry_counter_increases():
    from app.agents.engine import _bump_slot_retry, _reset_slot_retry, _SLOT_RETRY
    _SLOT_RETRY.clear()
    user = {"user_id": "test-k4"}
    assert _bump_slot_retry(user, "some_tool") == 1
    assert _bump_slot_retry(user, "some_tool") == 2
    assert _bump_slot_retry(user, "some_tool") == 3
    _reset_slot_retry(user, "some_tool")
    assert _bump_slot_retry(user, "some_tool") == 1


@pytest.mark.asyncio
async def test_k4_slot_retry_three_strikes(seeded_client):
    """連續 3 次缺欄位 → 第 3 次回 retry_exceeded。"""
    import json
    from app.agents.engine import execute_tool, _SLOT_RETRY
    _SLOT_RETRY.clear()
    user = {"user_id": "test-3strike"}

    # 用一個有 required slot 的 tool（create_customer_with_confirm 之 name 必填）
    # 第 1, 2 次 should be needs_input
    for i in range(2):
        result = await execute_tool(
            "create_customer_with_confirm", {}, db=None, user=user,
        )
        parsed = json.loads(result)
        assert parsed.get("needs_input") is True, f"第 {i+1} 次應 needs_input"

    # 第 3 次 should be retry_exceeded
    result = await execute_tool(
        "create_customer_with_confirm", {}, db=None, user=user,
    )
    parsed = json.loads(result)
    assert parsed.get("retry_exceeded") is True
    assert "3 次" in parsed.get("error", "")


# ════════════════════════════════════════════════════════════════════
# K7: 批次列印
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_print_multiple_invalid_doc_type(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _print_multiple_orders_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _print_multiple_orders_with_confirm(
            db, {"user_id": "u1"}, doc_type="invalid", doc_nos="A,B",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_print_multiple_too_many(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _print_multiple_orders_with_confirm
    nos = ",".join(f"SO-{i:04d}" for i in range(60))
    async with AsyncSessionLocal() as db:
        result = await _print_multiple_orders_with_confirm(
            db, {"user_id": "u1"}, doc_type="so", doc_nos=nos,
        )
    assert "error" in result
    assert "50" in result["error"]


@pytest.mark.asyncio
async def test_print_multiple_returns_confirm_card(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _print_multiple_orders_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _print_multiple_orders_with_confirm(
            db, {"user_id": "u1"}, doc_type="so", doc_nos="SO-001,SO-002,SO-003",
        )
    assert result["type"] == "confirm_card"


# ════════════════════════════════════════════════════════════════════
# K1: LOGO upload — 找不到 file
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_upload_logo_file_not_found(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _upload_company_logo_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _upload_company_logo_with_confirm(
            db, {"user_id": "u1"}, file_id="nosuch-file-id",
        )
    assert "error" in result


# ════════════════════════════════════════════════════════════════════
# K6: digest 觸發
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_trigger_daily_digest_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.polish_v339_tools import _trigger_daily_digest_now
    async with AsyncSessionLocal() as db:
        result = await _trigger_daily_digest_now(db, None, period_hours=24)
    assert "summary" in result
    assert "Daily Digest" in result["summary"]


# ════════════════════════════════════════════════════════════════════
# K1: LOGO 渲染 — PDF 偵測 logo_b64 不會 fail
# ════════════════════════════════════════════════════════════════════

def test_print_service_company_header_with_logo():
    """直接呼叫 _company_header 確保 logo_b64 不會 crash。"""
    from app.services.print_service import _company_header, _styles
    s = _styles()
    # 假 base64（合法 PNG header 但實際不是 image）→ 應 silent fallback
    fake_b64 = "aGVsbG8="  # "hello" base64
    result = _company_header(s, "Test Co", "12345678", "Taipei", "02-1234", fake_b64)
    assert isinstance(result, list)
    assert len(result) > 0  # 至少有 title
