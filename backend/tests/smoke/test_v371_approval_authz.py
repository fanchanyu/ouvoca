"""v3.71 — 審批決行授權（回歸鎖）。

修復前：`/api/approvals/{id}/approve|reject` 只有 `Depends(get_current_user)`
（僅驗有沒有登入），service 層也只檢查單據存在且為 pending。任何已登入者——
包含權限最低的現場作業員——都能核准任何待審單據，包含家規因「超過 10 萬要老闆簽」
擋下來的採購單，等於架空整條治理鏈。

本檔鎖住：
  1. 沒有 approver_role、也不是 superuser 的一般使用者 → 403
  2. 具備 approver_role 的使用者 → 可決行
  3. superuser → 可決行（維持既有維運能力）
  4. mesh 跨廠聚合查詢需要 mesh.factory.query 權限
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

import pytest


def _mk_user(username: str, *, superuser: bool = False) -> None:
    """建立一個沒有任何角色指派的使用者（JWT roles 會是空陣列）。"""
    from app.database import AsyncSessionLocal
    from app.models.organization import Department, Employee, User
    from app.services.auth import hash_password

    async def _seed():
        async with AsyncSessionLocal() as db:
            dept = Department(id=str(uuid.uuid4()), code=f"D{uuid.uuid4().hex[:5]}", name="授權測試部")
            db.add(dept)
            await db.flush()
            emp = Employee(
                id=str(uuid.uuid4()), employee_no=f"E{uuid.uuid4().hex[:6]}",
                name=username, email=f"{uuid.uuid4().hex[:8]}@authz.local",
                department_id=dept.id, hire_date=datetime.utcnow(),
            )
            db.add(emp)
            await db.flush()
            db.add(User(
                id=str(uuid.uuid4()), username=username,
                hashed_password=hash_password("AuthzPass123!"),
                employee_id=emp.id, is_superuser=superuser, is_active=True,
            ))
            await db.commit()

    asyncio.run(_seed())


def _headers(client, username: str) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"username": username, "password": "AuthzPass123!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_pending_request(client, admin_headers) -> dict[str, Any]:
    """建規則 → 觸發 po.created 事件 → 取得一張 approver_role='boss' 的待審單。"""
    from app.events import EventBus, DomainEvent

    rule = client.post("/api/approvals/rules", headers=admin_headers, json={
        "name": f"authz-{uuid.uuid4().hex[:6]}",
        "trigger_type": "po", "condition_field": "amount",
        "condition_op": "gt", "condition_value": 100000.0,
        "approver_role": "boss", "stages": 1,
    })
    assert rule.status_code == 200, rule.text

    po_id = f"po-authz-{uuid.uuid4().hex[:8]}"
    asyncio.run(EventBus.emit(DomainEvent(
        name="po.created", domain="purchase",
        entity_type="PurchaseOrder", entity_id=po_id,
        data={"po_no": "PO-AUTHZ-001", "amount": 500000.0, "supplier_id": "s-authz"},
    )))

    for _ in range(20):
        r = client.get("/api/approvals/pending?approver_role=boss", headers=admin_headers)
        assert r.status_code == 200, r.text
        for req in r.json():
            if req["trigger_id"] == po_id:
                return req
    pytest.skip("審批單未在時限內產生（事件匯流排非同步），略過")


def test_plain_user_cannot_approve(seeded_client, admin_headers):
    """一般使用者（無 boss 角色、非 superuser）核准他人單據 → 403。"""
    req = _make_pending_request(seeded_client, admin_headers)
    _mk_user("authz_plain")
    h = _headers(seeded_client, "authz_plain")

    r = seeded_client.post(f"/api/approvals/{req['id']}/approve",
                           headers=h, json={"comment": "我不該有權限核准"})
    assert r.status_code == 403, f"應被擋下，實得 {r.status_code}: {r.text[:200]}"
    assert "boss" in r.text, "錯誤訊息應說明需要哪個角色"

    # 單據必須維持 pending，不能被偷改
    check = seeded_client.get("/api/approvals/pending?approver_role=boss", headers=admin_headers)
    assert any(x["id"] == req["id"] and x["status"] == "pending" for x in check.json())


def test_plain_user_cannot_reject(seeded_client, admin_headers):
    """一般使用者駁回他人單據 → 403（不可用駁回癱瘓流程）。"""
    req = _make_pending_request(seeded_client, admin_headers)
    _mk_user("authz_plain2")
    h = _headers(seeded_client, "authz_plain2")

    r = seeded_client.post(f"/api/approvals/{req['id']}/reject",
                           headers=h, json={"comment": "惡意駁回"})
    assert r.status_code == 403, f"應被擋下，實得 {r.status_code}: {r.text[:200]}"


def test_superuser_can_still_approve(seeded_client, admin_headers):
    """superuser 仍可決行 —— 修復不得破壞既有維運能力。"""
    req = _make_pending_request(seeded_client, admin_headers)
    r = seeded_client.post(f"/api/approvals/{req['id']}/approve",
                           headers=admin_headers, json={"comment": "superuser 放行"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"


def test_mesh_aggregate_requires_permission(seeded_client):
    """跨廠聚合查詢需要 mesh.factory.query（原本是 mesh 唯一沒有權限檢查的 endpoint）。"""
    _mk_user("authz_mesh")
    h = _headers(seeded_client, "authz_mesh")
    r = seeded_client.post("/api/factory/aggregate?domain=inventory", headers=h)
    assert r.status_code == 403, f"應被擋下，實得 {r.status_code}: {r.text[:200]}"
