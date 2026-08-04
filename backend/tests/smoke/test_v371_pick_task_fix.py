"""v3.71 — 揀貨任務對話工具修復（回歸鎖）。

修復前這條路完全跑不起來，而且沒有任何測試守著：

  1. `create_pick_task(db, {...})` 的實作是
     `PickTask(id=…, pick_no=…, assigned_to=…, **data)`，
     呼叫端只要在 data 裡帶 `pick_no` 就是「重複的關鍵字引數」TypeError。
  2. 呼叫端傳 `requested_qty` / `operator_id`，但 model 的欄位叫
     `qty_to_pick` / `assigned_to` → TypeError: unexpected keyword。
  3. `bin_location_id` 是 NOT NULL，呼叫端完全沒給。
  4. SO 行是「產品」（products），但 `PickTask.part_id` 指向 parts，
     直接把 product_id 塞進去在 production（FK 強制開啟）會違反外鍵。
  5. 查待揀與完成揀貨兩處讀 `r.requested_qty` → AttributeError。

本檔鎖住整條 建立 → 查詢 → 完成 的流程。
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(client):
    from app.core.tenant_context import set_current_tenant
    from app.database import AsyncSessionLocal
    set_current_tenant("HQ")
    async with AsyncSessionLocal() as session:
        yield session


async def _seed_pickable_so(db):
    """建立一張可揀貨的 SO：產品 + 同名料件 + 儲位 + 庫存。"""
    from app.models.crm_sales import Customer, SalesOrder, SalesOrderItem
    from app.models.inventory import Inventory, Part
    from app.models.product import Product
    from app.models.warehouse import BinLocation, WarehouseZone

    tag = uuid.uuid4().hex[:6]
    # 依既有約定：product.product_no == part.part_no
    no = f"PK-{tag}"
    product = Product(id=str(uuid.uuid4()), product_no=no, name="揀貨測試產品")
    part = Part(id=str(uuid.uuid4()), part_no=no, name="揀貨測試料件",
                category="finished", unit_cost=100)
    cust = Customer(id=str(uuid.uuid4()), code=f"C-{tag}", name="揀貨測試客戶")
    zone = WarehouseZone(id=str(uuid.uuid4()), code=f"Z-{tag}", name="測試倉區")
    db.add_all([product, part, cust, zone])
    await db.commit()

    db.add_all([
        Inventory(id=str(uuid.uuid4()), part_id=part.id, qty_on_hand=100, qty_available=100),
        BinLocation(id=str(uuid.uuid4()), zone_id=zone.id, bin_code=f"B-{tag}",
                    part_id=part.id, qty=100, is_active=True),
    ])
    await db.commit()

    so = SalesOrder(id=str(uuid.uuid4()), so_no=f"SO-PK-{tag}",
                    customer_id=cust.id, status="confirmed", total_amount=1000)
    db.add(so)
    await db.commit()
    db.add(SalesOrderItem(id=str(uuid.uuid4()), so_id=so.id, line_no=1,
                          product_id=product.id, ordered_qty=10, unit_price=100))
    await db.commit()
    return so, part


@pytest.mark.asyncio
async def test_pick_task_create_query_complete(db):
    """建立 → 查待揀 → 完成，整條走通且欄位對得上 model。"""
    from app.services.warehouse import complete_pick, create_pick_task
    from app.models.warehouse import PickTask
    from sqlalchemy import select

    so, part = await _seed_pickable_so(db)
    bin_loc = (await db.execute(
        select(__import__("app.models.warehouse", fromlist=["BinLocation"]).BinLocation)
        .where(__import__("app.models.warehouse", fromlist=["BinLocation"]).BinLocation.part_id == part.id)
    )).scalar_one()

    # 建立 —— 呼叫端帶 pick_no 與 assigned_to，不可再 TypeError
    task = await create_pick_task(db, {
        "pick_no": f"PICK-CUSTOM-{uuid.uuid4().hex[:6]}",
        "so_id": so.id,
        "part_id": part.id,
        "bin_location_id": bin_loc.id,
        "qty_to_pick": 10,
        "assigned_to": "emp-pick-1",
        "status": "pending",
    }, user={"employee_id": "emp-other"})

    assert task.pick_no.startswith("PICK-CUSTOM-"), "呼叫端指定的 pick_no 應可覆寫預設"
    assert task.qty_to_pick == 10
    assert task.assigned_to == "emp-pick-1", "呼叫端指定的 assigned_to 應可覆寫 user 預設"
    assert not hasattr(task, "requested_qty"), "model 上不該有 requested_qty"

    # 查待揀 —— 修復前讀 r.requested_qty 會 AttributeError
    rows = (await db.execute(
        select(PickTask).where(PickTask.status == "pending")
    )).scalars().all()
    assert any(f"{r.qty_to_pick or 0:g}" for r in rows)

    # 完成
    done = await complete_pick(db, task.id, 10, {"employee_id": "emp-pick-1"})
    assert done.status == "completed"
    assert done.qty_picked == 10


@pytest.mark.asyncio
async def test_pick_task_tool_resolves_product_to_part(db):
    """AI 工具版：SO 的產品要正確解析成料件，不能把 product_id 塞進 part_id。"""
    from app.agents.registry import _REGISTRY
    from app.models.warehouse import PickTask
    from sqlalchemy import select

    so, part = await _seed_pickable_so(db)
    entry = _REGISTRY.get("create_pick_task_with_confirm")
    assert entry is not None, "工具未註冊"

    payload = await entry.func(db, {"employee_id": "emp-1"}, so_no=so.so_no)

    # 工具回 ConfirmCard；取出 card 並執行
    from app.agents.confirm_card import _PENDING
    card_id = (payload.get("card") or {}).get("id") if isinstance(payload, dict) else None
    assert card_id, f"應回 ConfirmCard，實得：{str(payload)[:200]}"
    result = await _PENDING[card_id]["executor"]()

    assert result["tasks_created"] == 1, f"應建立 1 筆，實得 {result}"
    task = (await db.execute(
        select(PickTask).where(PickTask.so_id == so.id)
    )).scalars().first()
    assert task.part_id == part.id, "part_id 必須是料件 id，不是產品 id"
    assert task.bin_location_id is not None, "bin_location_id 是 NOT NULL，必須有值"
    assert task.qty_to_pick == 10
