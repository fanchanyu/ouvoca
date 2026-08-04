"""v3.60 Phase C2 tests — 狀態機框架。"""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError
from app.core.status_machine import (
    TRANSITIONS,
    allowed_next,
    assert_transition,
    can_transition,
)


def test_valid_transition_allowed():
    assert can_transition("SO", "draft", "confirmed")
    assert can_transition("SO", "confirmed", "shipped")
    assert can_transition("PO", "approved", "received")
    assert can_transition("JE", "draft", "posted")
    assert can_transition("WO", "released", "completed")


def test_invalid_transition_blocked():
    assert not can_transition("SO", "draft", "shipped")  # 未確認直接出貨 → 擋
    assert not can_transition("SO", "cancelled", "confirmed")  # 已取消不能復活
    assert not can_transition("JE", "posted", "posted")
    assert not can_transition("PO", "received", "approved")


def test_assert_transition_raises():
    with pytest.raises(BusinessRuleError):
        assert_transition("SO", "draft", "shipped", "SO-001")
    # 合法不拋
    assert_transition("SO", "draft", "confirmed", "SO-001")


def test_allowed_next():
    assert "confirmed" in allowed_next("SO", "draft")
    assert "shipped" in allowed_next("SO", "confirmed")
    assert allowed_next("SO", "closed") == []  # 終結狀態


def test_all_doc_types_have_transitions():
    for doc_type in ("SO", "PO", "WO", "DN", "JE", "STOCK_COUNT", "INSPECTION", "QUOTATION"):
        assert doc_type in TRANSITIONS, f"{doc_type} 未定義狀態機"


def test_services_use_status_machine(seeded_client):
    """關鍵 service 應呼叫 assert_transition（grep smoke）。"""
    from pathlib import Path
    checks = [
        ("app/services/sales.py", 'assert_transition("SO"'),
        ("app/services/purchase.py", 'assert_transition("PO"'),
        ("app/services/accounting.py", 'assert_transition("JE"'),
    ]
    for rel, needle in checks:
        src = (Path(__file__).resolve().parents[2] / rel).read_text(encoding="utf-8")
        assert needle in src, f"{rel} 未接入狀態機"
