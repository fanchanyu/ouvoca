"""v3.64 tests — 批號/序號追溯、RFQ、標籤、掃描、MFA、AV 掛鉤。"""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.database import AsyncSessionLocal
    from app.core.tenant_context import set_current_tenant
    set_current_tenant("HQ")
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_batch_trace(db):
    """批號：建立 → 登記動向 → 正反向追溯。"""
    from app.models.inventory import Part, InventoryTransaction
    from app.models.documents_m3 import GoodsReceiptNote
    from app.services.traceability import assign_batch, trace_batch
    from app.services.m3_documents import create_grn
    from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier

    part = Part(id=str(uuid.uuid4()), part_no="TR-PART-1", name="追溯料件",
                category="raw", unit_cost=5)
    sup = Supplier(id=str(uuid.uuid4()), code="SUP-TR", name="追溯供應商", tier="T2", is_approved=True)
    db.add_all([part, sup,
               __import__("app.models.inventory", fromlist=["Inventory"]).Inventory(
                   id=str(uuid.uuid4()), part_id=part.id, qty_on_hand=0, qty_available=0)])
    await db.commit()
    lot = await assign_batch(db, part.id, "LOT-TRACE-1", qty=100)
    assert lot.lot_no == "LOT-TRACE-1"

    # 收貨時帶批號（直接在 txn 上標記）
    po = PurchaseOrder(id=str(uuid.uuid4()), po_no="PO-TR-001", supplier_id=sup.id, status="approved")
    db.add(po)
    await db.commit()
    poi = PurchaseOrderItem(id=str(uuid.uuid4()), po_id=po.id, line_no=1, part_id=part.id,
                            ordered_qty=100, received_qty=0, unit_price=5, line_total=500)
    db.add(poi)
    await db.commit()
    grn = await create_grn(db, po.id, [{"item_id": poi.id, "received_qty": 100}],
                           {"employee_id": "e-tr"})
    # 標記批次動向
    txn = (await db.execute(
        __import__("sqlalchemy").select(InventoryTransaction).where(
            InventoryTransaction.reference_type == "goods_receipt_note",
            InventoryTransaction.reference_id == grn.id,
        )
    )).scalar_one()
    txn.batch_no = "LOT-TRACE-1"
    await db.commit()

    result = await trace_batch(db, "LOT-TRACE-1")
    assert result["lots"][0]["qty"] == 100
    assert any("GRN" in (m["document_no"] or "") for m in result["movements"]), \
        f"應找到 GRN 動向：{result['movements']}"


@pytest.mark.asyncio
async def test_serial_trace(db):
    from app.models.inventory import Part
    from app.services.traceability import record_serials, trace_serial
    part = Part(id=str(uuid.uuid4()), part_no="SN-PART-1", name="序號料件",
                category="finished", unit_cost=100)
    db.add(part)
    await db.commit()
    rows = await record_serials(db, part.id, ["SN-0001", "SN-0002"])
    assert len(rows) == 2
    info = await trace_serial(db, "SN-0001")
    assert info["serial_no"] == "SN-0001"
    assert info["status"] == "in_stock"


@pytest.mark.asyncio
async def test_rfq_flow(db):
    """RFQ：建立 → 送出 → 兩家報價 → 比價 → 決標轉 PO。"""
    from app.models.inventory import Part
    from app.models.purchase import Supplier, PurchaseOrder
    from app.services.rfq import (
        create_rfq, send_rfq, receive_quote, compare_quotes, award_rfq,
    )
    from sqlalchemy import select

    part = Part(id=str(uuid.uuid4()), part_no="RFQ-PART-1", name="詢價料件",
                category="component", unit_cost=8)
    s1 = Supplier(id=str(uuid.uuid4()), code="SUP-RFQ1", name="詢價供應商一", tier="T2", is_approved=True)
    s2 = Supplier(id=str(uuid.uuid4()), code="SUP-RFQ2", name="詢價供應商二", tier="T2", is_approved=True)
    db.add_all([part, s1, s2])
    await db.commit()

    rfq = await create_rfq(db, {"items": [{"part_id": part.id, "qty": 1000}]})
    assert rfq.rfq_no.startswith("RFQ-")
    await send_rfq(db, rfq.id)

    q1 = await receive_quote(db, {
        "rfq_id": rfq.id, "supplier_id": s1.id,
        "items": [{"part_id": part.id, "qty": 1000, "unit_price": 5}],
        "lead_time_days": 7,
    })
    q2 = await receive_quote(db, {
        "rfq_id": rfq.id, "supplier_id": s2.id,
        "items": [{"part_id": part.id, "qty": 1000, "unit_price": 4.5}],
        "lead_time_days": 10,
    })
    comparison = await compare_quotes(db, rfq.id)
    assert comparison["quotes"][0]["quote_id"] == q2.id  # 最便宜排第一
    assert comparison["best_per_part"][0]["unit_price"] == 4.5

    result = await award_rfq(db, rfq.id, q2.id)
    assert result["po_no"].startswith("PO-")
    po = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == result["po_id"])
    )).scalar_one()
    assert po.supplier_id == s2.id


def test_part_label_pdf():
    from app.services.print_service import render_part_label_pdf
    pdf = render_part_label_pdf("M6-BOLT-20", name="M6 螺絲", qty="100")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500


def test_scan_api_part(seeded_client, admin_headers, db):
    """條碼槍掃描：料號 → 庫存資訊。"""
    from app.models.inventory import Part, Inventory
    asyncio.run(_seed_part(db, "SCAN-PART-1", "掃描料件", 50))
    r = seeded_client.post("/api/warehouse/scan", headers=admin_headers,
                           json={"barcode": "SCAN-PART-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["match"] == "part"
    assert body["part_no"] == "SCAN-PART-1"
    assert body["qty_on_hand"] == 50


async def _seed_part(db, part_no, name, qty):
    from app.models.inventory import Part, Inventory
    from sqlalchemy import select
    part = (await db.execute(select(Part).where(Part.part_no == part_no))).scalar_one_or_none()
    if part is None:
        part = Part(id=str(uuid.uuid4()), part_no=part_no, name=name,
                    category="component", unit_cost=10)
        db.add(part)
        await db.commit()
    inv = (await db.execute(select(Inventory).where(Inventory.part_id == part.id))).scalar_one_or_none()
    if inv is None:
        db.add(Inventory(id=str(uuid.uuid4()), part_id=part.id,
                         qty_on_hand=qty, qty_available=qty))
        await db.commit()


def test_mfa_setup_verify_login(seeded_client, admin_headers):
    """MFA：setup → pyotp 驗證碼 → enable → 登入兩階段。"""
    import pyotp
    from app.models.organization import User
    from app.services.auth import hash_password
    from sqlalchemy import select
    from app.database import AsyncSessionLocal

    async def _create_mfa_user():
        from app.models.organization import Employee, Department
        from datetime import datetime
        async with AsyncSessionLocal() as session:
            dept = Department(id=str(uuid.uuid4()), code="D-MFA", name="MFA 部門")
            session.add(dept)
            await session.flush()
            emp = Employee(id=str(uuid.uuid4()), employee_no="E-MFA-1", name="mfa_user",
                           email="mfa@test.local", department_id=dept.id,
                           hire_date=datetime.utcnow())
            session.add(emp)
            await session.flush()
            session.add(User(id=str(uuid.uuid4()), username="mfa_user",
                             hashed_password=hash_password("MfaPass123!"),
                             employee_id=emp.id, is_superuser=True, is_active=True))
            await session.commit()
    asyncio.run(_create_mfa_user())

    # 登入拿 MFA token（未啟用 MFA 前先拿正式 token 做 setup）
    r = seeded_client.post("/api/auth/login", json={
        "username": "mfa_user", "password": "MfaPass123!",
    })
    assert r.status_code == 200
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    setup = seeded_client.post("/api/auth/mfa/setup", headers=h)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()

    enable = seeded_client.post("/api/auth/mfa/enable", headers=h, json={"code": code})
    assert enable.status_code == 200

    # 啟用後登入 → 回 mfa_required + mfa_token
    r2 = seeded_client.post("/api/auth/login", json={
        "username": "mfa_user", "password": "MfaPass123!",
    })
    assert r2.status_code == 200
    assert r2.json().get("mfa_required") is True
    mfa_token = r2.json()["mfa_token"]

    # 錯 code 被拒
    r3 = seeded_client.post("/api/auth/mfa/verify", json={
        "mfa_token": mfa_token, "code": "000000",
    })
    assert r3.status_code == 401

    # 對 code 換正式 token
    code2 = pyotp.TOTP(secret).now()
    r4 = seeded_client.post("/api/auth/mfa/verify", json={
        "mfa_token": mfa_token, "code": code2,
    })
    assert r4.status_code == 200
    assert r4.json()["access_token"]


def test_av_hook_noop_when_unset(seeded_client, admin_headers, monkeypatch):
    """未設定 AV_SCAN_URL → 上傳不被掃描服務阻擋。"""
    from app.config import settings
    monkeypatch.setattr(settings, "AV_SCAN_URL", "")
    r = seeded_client.post(
        "/api/files/upload",
        headers=admin_headers,
        data={"category": "general"},
        files={"file": ("ok.txt", b"plain text content", "text/plain")},
    )
    assert r.status_code in (200, 201), f"應可上傳：{r.status_code} {r.text[:200]}"


def test_v364_apis_and_tools_registered(seeded_client):
    """v3.64 endpoints + tools + migration（grep smoke）。"""
    from pathlib import Path
    tools_src = (Path(__file__).resolve().parents[2] / "app" / "agents" / "domains" /
                 "v364_tools.py").read_text(encoding="utf-8")
    for tool in ("assign_batch_with_confirm", "trace_batch", "trace_serial",
                 "create_rfq_with_confirm", "receive_quote_with_confirm",
                 "compare_quotes", "award_rfq_with_confirm", "print_part_label"):
        assert f'name="{tool}"' in tools_src

    mig = (Path(__file__).resolve().parents[2] / "alembic" / "versions" /
           "v014_traceability_rfq_mfa.py").read_text(encoding="utf-8")
    for table in ("batch_lots", "serial_numbers", "rfqs", "supplier_quotes"):
        assert table in mig
    assert "mfa_secret" in mig

    api_src = (Path(__file__).resolve().parents[2] / "app" / "api" / "auth.py").read_text(encoding="utf-8")
    assert "/mfa/verify" in api_src and "/mfa/setup" in api_src


def test_mfa_pending_token_rejected_on_protected_api(seeded_client, admin_headers):
    """健檢 #1：mfa_pending token 不得當正式 token 使用（GET + 寫入都 401）。"""
    from app.services.auth import mfa_challenge_token
    from app.models.organization import User
    from app.database import AsyncSessionLocal
    from sqlalchemy import select

    async def _get_user():
        async with AsyncSessionLocal() as session:
            return (await session.execute(
                select(User).where(User.username == "testadmin")
            )).scalar_one()
    user = asyncio.run(_get_user())
    mfa_tok = mfa_challenge_token(user)
    h = {"Authorization": f"Bearer {mfa_tok}"}
    assert seeded_client.get("/api/inventory/parts", headers=h).status_code in (401, 403)
    assert seeded_client.post(
        "/api/inventory/parts", headers=h,
        json={"part_no": "MFA-BLOCK", "name": "x", "category": "raw"},
    ).status_code in (401, 403)


def test_rfq_list_http_no_lazy_error(seeded_client, admin_headers, db):
    """健檢 #3：GET /api/purchase/rfqs 在獨立 HTTP session 不得 500（lazy-load）。"""
    from app.models.inventory import Part
    from app.services.rfq import create_rfq, send_rfq
    from app.models.rfq import RFQ
    from sqlalchemy import select

    async def _seed():
        part = Part(id=str(uuid.uuid4()), part_no="HTTP-RFQ-PART", name="HTTP 詢價料件",
                    category="component", unit_cost=5)
        db.add(part)
        await db.commit()
        rfq = await create_rfq(db, {"items": [{"part_id": part.id, "qty": 10}]})
        await send_rfq(db, rfq.id)
        return rfq.id
    asyncio.run(_seed())

    r = seeded_client.get("/api/purchase/rfqs", headers=admin_headers)
    assert r.status_code == 200, f"RFQ list 不應 500：{r.status_code} {r.text[:200]}"
    assert any(x["rfq_no"].startswith("RFQ-") for x in r.json())
