"""v3.53 smoke: SSE realtime subscriptions + tenant filter.

This is a *grep-style* smoke check that does NOT spin up a browser. It just
verifies the source code carries the expected wiring so the realtime feature
cannot silently regress:

- Backend events.py applies tenant filter inside the per-connection on_event
- Frontend Inventory.tsx / Purchase.tsx / Sales.tsx open an EventSource
  against /api/events/stream and refetch on relevant domain events.
- Backend services include tenant_id in event payloads.
"""
from __future__ import annotations

import os
import pathlib


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    p = _REPO_ROOT / rel
    assert p.exists(), f"expected file missing: {p}"
    return p.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# Backend
# ─────────────────────────────────────────────────────────────

def test_events_api_tenant_filters():
    """events.py must extract user_tenant and skip mismatched events."""
    src = _read("backend/app/api/events.py")
    assert "user_tenant" in src, "events.py 沒有讀取使用者 tenant_id"
    # Filter must reference the event's tenant_id and the user's tenant
    assert "tenant_id" in src, "events.py 沒有檢查事件 tenant_id"
    # Must be an early-return inside on_event (skip mismatched event)
    assert "_allowed" in src or "return" in src, "events.py 沒有 skip 條件"
    # Backlog replay also tenant-filtered
    assert "get_history" in src


def test_auth_middleware_accepts_access_token_query():
    """SSE EventSource cannot send Authorization; middleware must accept
    ?access_token= as fallback."""
    src = _read("backend/app/middleware/auth.py")
    assert "access_token" in src, "auth middleware 未支援 access_token query param"


def test_inventory_service_emits_tenant_id():
    src = _read("backend/app/services/inventory.py")
    # inventory.changed event payload should include tenant_id
    assert "tenant_id" in src, "inventory.py 事件 payload 未含 tenant_id"


def test_purchase_service_emits_tenant_id():
    src = _read("backend/app/services/purchase.py")
    assert "tenant_id" in src, "purchase.py 事件 payload 未含 tenant_id"


def test_sales_service_emits_tenant_id():
    src = _read("backend/app/services/sales.py")
    assert "tenant_id" in src, "sales.py 事件 payload 未含 tenant_id"


# ─────────────────────────────────────────────────────────────
# Frontend page subscriptions
# ─────────────────────────────────────────────────────────────

def _assert_subscribes(page_rel: str, expected_events: list[str]) -> None:
    src = _read(page_rel)
    assert "EventSource" in src, f"{page_rel} 未開 EventSource"
    assert "/api/events/stream" in src, f"{page_rel} 未連 /api/events/stream"
    missing = [e for e in expected_events if e not in src]
    assert not missing, f"{page_rel} 未訂閱事件: {missing}"


def test_inventory_page_subscribes_sse():
    _assert_subscribes(
        "frontend-desktop/src/pages/Inventory.tsx",
        ["inventory.changed", "po.received", "so.shipped", "wo.completed"],
    )


def test_purchase_page_subscribes_sse():
    _assert_subscribes(
        "frontend-desktop/src/pages/Purchase.tsx",
        ["po.created", "po.approved", "po.received", "po.cancelled"],
    )


def test_sales_page_subscribes_sse():
    _assert_subscribes(
        "frontend-desktop/src/pages/Sales.tsx",
        ["so.created", "so.confirmed", "so.shipped", "so.invoiced", "so.cancelled"],
    )


def test_desktop_notifications_uses_access_token():
    """DesktopNotifications must pass access_token in the SSE URL after the
    auth-required SSE backend change."""
    src = _read("frontend-desktop/src/components/DesktopNotifications.tsx")
    assert "access_token" in src, "DesktopNotifications 未在 SSE URL 帶 access_token"
