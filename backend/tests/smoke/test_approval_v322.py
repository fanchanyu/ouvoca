"""Smoke: 多階審批工作流（v3.22）

驗收：
1. 建規則「PO > 10 萬要審」
2. 建 5 萬的 PO → **不**產 ApprovalRequest（< 10 萬）
3. 建 11 萬的 PO → 產 ApprovalRequest（pending）
4. list_pending 看得到
5. approve → request 變 approved
6. reject 必填 comment → 拒絕 status
7. 多階審：stages=2 → 第一階 approve 後仍 pending 但 current_stage=2
8. SO 折扣規則：discount_pct > 5 觸發
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any


def _post_rule(client, headers, **kwargs: Any):
    payload = {
        "name": "高額採購單",
        "trigger_type": "po",
        "condition_field": "amount",
        "condition_op": "gt",
        "condition_value": 100000.0,
        "approver_role": "boss",
        "stages": 1,
        "is_active": True,
    }
    payload.update(kwargs)
    r = client.post("/api/approvals/rules", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _emit_po_event(po_id: str, amount: float, po_no: str = "PO-TEST"):
    """直接打 EventBus event，模擬 PO service 在 create_purchase_order 結尾的 emit。"""
    from app.events.engine import EventBus, DomainEvent
    asyncio.run(EventBus.emit(DomainEvent(
        name="po.created", domain="purchase",
        entity_type="PurchaseOrder", entity_id=po_id,
        data={"po_no": po_no, "supplier_id": "fake", "total": amount},
    )))


def _emit_so_event(so_id: str, amount: float, discount_pct: float, so_no: str = "SO-TEST"):
    from app.events.engine import EventBus, DomainEvent
    asyncio.run(EventBus.emit(DomainEvent(
        name="so.created", domain="sales",
        entity_type="SalesOrder", entity_id=so_id,
        data={"so_no": so_no, "customer_id": "fake", "total": amount, "discount_pct": discount_pct},
    )))


def _wait_for_pending(client, headers, trigger_id: str, timeout_s: float = 3.0):
    """等背景 listener 把 ApprovalRequest 寫好。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = client.get("/api/approvals/pending", headers=headers)
        if r.status_code == 200:
            matches = [x for x in r.json() if x["trigger_id"] == trigger_id]
            if matches:
                return matches[0]
        time.sleep(0.1)
    return None


def test_create_rule_high_value_po(seeded_client, admin_headers):
    """T1：建一條規則「PO > 10 萬要審」。"""
    rule = _post_rule(
        seeded_client, admin_headers,
        name=f"高額採購-{uuid.uuid4().hex[:6]}",
    )
    assert rule["trigger_type"] == "po"
    assert rule["condition_value"] == 100000.0
    assert rule["approver_role"] == "boss"


def test_po_below_threshold_no_request(seeded_client, admin_headers):
    """T2：5 萬的 PO 不命中規則，不應該產生 ApprovalRequest。"""
    _post_rule(
        seeded_client, admin_headers,
        name=f"T2-{uuid.uuid4().hex[:6]}",
    )
    po_id = f"po-below-{uuid.uuid4().hex[:8]}"
    _emit_po_event(po_id, amount=50000.0, po_no="PO-LOW-001")

    # 給 listener 一點時間（雖然不該產，仍要等一拍以確認）
    time.sleep(0.3)
    r = seeded_client.get("/api/approvals/pending", headers=admin_headers)
    assert r.status_code == 200
    matches = [x for x in r.json() if x["trigger_id"] == po_id]
    assert matches == [], f"低於門檻不該產審批單，但拿到：{matches}"


def test_po_above_threshold_creates_request(seeded_client, admin_headers):
    """T3：11 萬的 PO 命中規則，產 pending ApprovalRequest。"""
    _post_rule(
        seeded_client, admin_headers,
        name=f"T3-{uuid.uuid4().hex[:6]}",
    )
    po_id = f"po-high-{uuid.uuid4().hex[:8]}"
    _emit_po_event(po_id, amount=110000.0, po_no="PO-HIGH-001")

    req = _wait_for_pending(seeded_client, admin_headers, po_id)
    assert req is not None, "高於門檻應產審批單，卻找不到"
    assert req["status"] == "pending"
    assert req["approver_role"] == "boss"
    assert req["current_stage"] == 1
    assert req["total_stages"] == 1
    assert "110,000" in req["trigger_summary"]


def test_list_pending_sees_request(seeded_client, admin_headers):
    """T4：list_pending 應該看得到（重點：approver_role filter 可選）。"""
    _post_rule(
        seeded_client, admin_headers,
        name=f"T4-{uuid.uuid4().hex[:6]}",
        approver_role="manager",
    )
    po_id = f"po-mgr-{uuid.uuid4().hex[:8]}"
    _emit_po_event(po_id, amount=200000.0, po_no="PO-MGR-001")

    req = _wait_for_pending(seeded_client, admin_headers, po_id)
    assert req is not None

    # 用 approver_role filter（只看 manager 的）
    r = seeded_client.get("/api/approvals/pending?approver_role=manager", headers=admin_headers)
    assert r.status_code == 200
    matches = [x for x in r.json() if x["trigger_id"] == po_id]
    assert len(matches) == 1

    # 用錯角色 filter 應該看不到
    r = seeded_client.get("/api/approvals/pending?approver_role=ceo", headers=admin_headers)
    assert all(x["trigger_id"] != po_id for x in r.json())


def test_approve_request_marks_approved(seeded_client, admin_headers):
    """T5：approve 後 status = approved。"""
    _post_rule(
        seeded_client, admin_headers,
        name=f"T5-{uuid.uuid4().hex[:6]}",
    )
    po_id = f"po-app-{uuid.uuid4().hex[:8]}"
    _emit_po_event(po_id, amount=300000.0, po_no="PO-APP-001")

    req = _wait_for_pending(seeded_client, admin_headers, po_id)
    assert req is not None

    r = seeded_client.post(
        f"/api/approvals/{req['id']}/approve",
        headers=admin_headers,
        json={"comment": "金額合理，准了"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "approved"
    assert len(body["steps"]) == 1
    assert body["steps"][0]["action"] == "approved"
    assert body["steps"][0]["comment"] == "金額合理，准了"


def test_reject_requires_comment(seeded_client, admin_headers):
    """T6：拒絕必填 comment。空字串 / None 應被擋下。"""
    _post_rule(
        seeded_client, admin_headers,
        name=f"T6-{uuid.uuid4().hex[:6]}",
    )
    po_id = f"po-rej-{uuid.uuid4().hex[:8]}"
    _emit_po_event(po_id, amount=500000.0, po_no="PO-REJ-001")

    req = _wait_for_pending(seeded_client, admin_headers, po_id)
    assert req is not None

    # 空 comment 應該被擋
    r = seeded_client.post(
        f"/api/approvals/{req['id']}/reject",
        headers=admin_headers,
        json={"comment": ""},
    )
    assert r.status_code >= 400, f"空 comment 不該過：{r.text}"

    r = seeded_client.post(
        f"/api/approvals/{req['id']}/reject",
        headers=admin_headers,
        json={},
    )
    assert r.status_code >= 400

    # 有 comment 應該成功
    r = seeded_client.post(
        f"/api/approvals/{req['id']}/reject",
        headers=admin_headers,
        json={"comment": "金額破表，不行"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "rejected"
    assert body["steps"][-1]["comment"] == "金額破表，不行"


def test_multi_stage_approval(seeded_client, admin_headers):
    """T7：stages=2 → 第一階 approve 後仍 pending，current_stage 推到 2。"""
    _post_rule(
        seeded_client, admin_headers,
        name=f"T7-雙簽-{uuid.uuid4().hex[:6]}",
        trigger_type="payment",
        condition_field="amount",
        condition_value=50000.0,
        approver_role="manager",
        stages=2,
    )
    pay_id = f"pay-{uuid.uuid4().hex[:8]}"
    # 模擬付款事件
    from app.events.engine import EventBus, DomainEvent
    asyncio.run(EventBus.emit(DomainEvent(
        name="payment.created", domain="accounting",
        entity_type="Payment", entity_id=pay_id,
        data={"payment_no": "PAY-001", "amount": 80000.0},
    )))

    req = _wait_for_pending(seeded_client, admin_headers, pay_id)
    assert req is not None
    assert req["total_stages"] == 2
    assert req["current_stage"] == 1

    # 第一階 approve
    r = seeded_client.post(
        f"/api/approvals/{req['id']}/approve",
        headers=admin_headers,
        json={"comment": "一簽"},
    )
    body = r.json()
    assert body["status"] == "pending", f"雙簽第一階後仍應 pending：{body}"
    assert body["current_stage"] == 2

    # 第二階 approve → 才結案
    r = seeded_client.post(
        f"/api/approvals/{req['id']}/approve",
        headers=admin_headers,
        json={"comment": "二簽"},
    )
    body = r.json()
    assert body["status"] == "approved"
    assert len(body["steps"]) == 2


def test_so_discount_rule(seeded_client, admin_headers):
    """T8：SO 折扣 > 5% 觸發。"""
    _post_rule(
        seeded_client, admin_headers,
        name=f"折扣-{uuid.uuid4().hex[:6]}",
        trigger_type="so",
        condition_field="discount_pct",
        condition_op="gt",
        condition_value=5.0,
        approver_role="manager",
    )
    so_id = f"so-{uuid.uuid4().hex[:8]}"
    _emit_so_event(so_id, amount=300000.0, discount_pct=8.5, so_no="SO-DISC-001")

    req = _wait_for_pending(seeded_client, admin_headers, so_id)
    assert req is not None
    assert req["trigger_type"] == "so"
    assert "8.5%" in req["trigger_summary"]


def test_history_lists_decided(seeded_client, admin_headers):
    """補：歷史列表可以按 status filter 撈到已決議的單。"""
    r = seeded_client.get("/api/approvals/history?status=approved", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    # 前面 T5/T7 各 approve 一張，T7 還是兩階
    assert any(x["status"] == "approved" for x in data)
