"""Inventory service — Part/Inventory/InventoryTransaction/Transfer business logic.

Emits domain events on every state-changing operation so the event engine
can apply constraints, send notifications and broadcast SSE.
"""
import uuid
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select, update as sql_update, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.inventory import Part, Inventory, InventoryTransaction, InventoryTransfer
from app.events import EventBus, DomainEvent
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.logging import get_logger

log = get_logger(__name__)

# -------- Part --------

async def get_part(db: AsyncSession, part_id: str) -> Optional[Part]:
    result = await db.execute(select(Part).where(Part.id == part_id))
    return result.scalar_one_or_none()


async def get_part_by_no(db: AsyncSession, part_no: str) -> Optional[Part]:
    result = await db.execute(select(Part).where(Part.part_no == part_no))
    return result.scalar_one_or_none()


async def list_parts(db: AsyncSession, skip: int = 0, limit: int = 100, category: Optional[str] = None) -> List[Part]:
    query = select(Part)
    if category:
        query = query.where(Part.category == category)
    query = query.offset(skip).limit(limit).order_by(Part.part_no)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_part(db: AsyncSession, data: dict) -> Part:
    part = Part(id=str(uuid.uuid4()), **data)
    db.add(part)
    inv = Inventory(id=str(uuid.uuid4()), part_id=part.id)
    db.add(inv)
    await db.commit()
    await db.refresh(part)
    await EventBus.emit(DomainEvent(
        name="part.created", domain="inventory",
        entity_type="Part", entity_id=part.id,
        data={"part_no": part.part_no, "name": part.name},
    ))
    return part


# -------- Inventory --------

async def get_inventory(db: AsyncSession, part_id: str) -> Optional[Inventory]:
    result = await db.execute(
        select(Inventory).options(joinedload(Inventory.part)).where(Inventory.part_id == part_id)
    )
    return result.scalar_one_or_none()


async def list_inventory_below_safety(db: AsyncSession, limit: int = 100):
    """Return inventory rows where qty_available < part.safety_stock."""
    result = await db.execute(
        select(Inventory, Part)
        .join(Part, Inventory.part_id == Part.id)
        .where(Inventory.qty_available < Part.safety_stock)
        .where(Part.safety_stock > 0)
        .limit(limit)
    )
    return [(inv, p) for inv, p in result.all()]


# -------- Transactions --------

VALID_INBOUND = {"inbound", "receipt", "return_to_stock", "adjustment_in"}
VALID_OUTBOUND = {"outbound", "issue", "consumption", "adjustment_out"}
VALID_ALLOCATION = {"allocate", "deallocate"}
ALL_VALID_TXN_TYPES = VALID_INBOUND | VALID_OUTBOUND | VALID_ALLOCATION


async def add_inventory_transaction(db: AsyncSession, data: dict, user: Optional[dict] = None) -> InventoryTransaction:
    """記一筆庫存異動 + 同步更新 Inventory 餘額（race-safe atomic UPDATE）。

    重要：
    - v3.53 改為以 SQL 算術 (Inventory.qty_on_hand + delta) 做原子更新，
      取代舊的 Python read-modify-write（並行下會 lost update）。
    - 本函式 **只 flush 不 commit**：交易邊界由呼叫端負責，以利多行操作
      （如 PO 收貨、SO 出貨、WO 完工）整批原子化。
    """
    part_id = data["part_id"]
    qty = float(data["qty"])
    txn_type = data["transaction_type"]

    if qty <= 0:
        raise BusinessRuleError("數量必須大於 0", qty=qty)

    # 防呆：拒絕未知的 transaction_type，避免靜默不更新庫存
    # (早期 bug: type='in'/'out' 不報錯但不改庫存 → 沉默資料毀損)
    if txn_type not in ALL_VALID_TXN_TYPES:
        raise BusinessRuleError(
            f"無效的 transaction_type: {txn_type!r}。"
            f"合法值：{sorted(ALL_VALID_TXN_TYPES)}",
            transaction_type=txn_type,
        )

    # 先讀一次（用於：① 存在性檢查 ② outbound 可用量檢查）。
    # 注意：這個讀只用來檢查與 emit 事件用的快照值，真正的數量更新
    #      由下方 atomic SQL UPDATE 完成 → 不會 lost update。
    inv_q = await db.execute(select(Inventory).where(Inventory.part_id == part_id))
    inv = inv_q.scalar_one_or_none()
    if not inv:
        raise NotFoundError(f"零件 {part_id} 沒有庫存記錄", part_id=part_id)

    # Outbound: check available qty（盡力檢查；最終仍由 DB 的並行寫入決定）
    if txn_type in VALID_OUTBOUND and inv.qty_available < qty:
        raise BusinessRuleError(
            "庫存不足",
            part_id=part_id, requested=qty, available=inv.qty_available,
        )

    txn = InventoryTransaction(
        id=str(uuid.uuid4()),
        operator_id=(user or {}).get("employee_id") if user else None,
        **data,
    )
    db.add(txn)

    now = datetime.now(UTC).replace(tzinfo=None)

    # ---- Atomic SQL UPDATE（race-safe；取代 Python +=） ----
    # qty_allocated 用 SQL case() 模擬 max(0, x-qty)，SQLite/PostgreSQL 皆通用。
    if txn_type in VALID_INBOUND:
        new_allocated_expr = Inventory.qty_allocated
        new_on_hand_expr = Inventory.qty_on_hand + qty
    elif txn_type in VALID_OUTBOUND:
        new_allocated_expr = case(
            (Inventory.qty_allocated - qty < 0, 0.0),
            else_=Inventory.qty_allocated - qty,
        )
        new_on_hand_expr = Inventory.qty_on_hand - qty
    elif txn_type == "allocate":
        new_allocated_expr = Inventory.qty_allocated + qty
        new_on_hand_expr = Inventory.qty_on_hand
    elif txn_type == "deallocate":
        new_allocated_expr = case(
            (Inventory.qty_allocated - qty < 0, 0.0),
            else_=Inventory.qty_allocated - qty,
        )
        new_on_hand_expr = Inventory.qty_on_hand
    else:  # pragma: no cover — 上方已驗 type
        new_allocated_expr = Inventory.qty_allocated
        new_on_hand_expr = Inventory.qty_on_hand

    stmt = (
        sql_update(Inventory)
        .where(Inventory.part_id == part_id)
        .values(
            qty_on_hand=new_on_hand_expr,
            qty_allocated=new_allocated_expr,
            qty_available=new_on_hand_expr - new_allocated_expr,
            updated_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    await db.execute(stmt)
    await db.flush()
    # 把已被 SQL UPDATE 改動的 inv ORM 物件刷新成最新值
    await db.refresh(inv)

    # v3.53: include tenant_id so SSE can do per-tenant filtering
    _tenant = getattr(inv, "tenant_id", None) or (user or {}).get("tenant_id")
    await EventBus.emit(DomainEvent(
        name="inventory.changed", domain="inventory",
        entity_type="InventoryTransaction", entity_id=txn.id,
        data={"part_id": part_id, "qty": qty, "type": txn_type,
              "qty_on_hand": inv.qty_on_hand, "qty_available": inv.qty_available,
              "tenant_id": _tenant},
    ))

    # Check safety stock breach
    part = (await db.execute(select(Part).where(Part.id == part_id))).scalar_one_or_none()
    if part and part.safety_stock > 0 and inv.qty_available < part.safety_stock:
        await EventBus.emit(DomainEvent(
            name="stock.below_safety", domain="inventory",
            entity_type="Part", entity_id=part_id,
            data={"part_no": part.part_no, "qty_available": inv.qty_available,
                  "safety_stock": part.safety_stock,
                  "tenant_id": getattr(part, "tenant_id", None) or _tenant},
        ))

    return txn


# -------- Transfers --------

async def create_transfer(db: AsyncSession, data: dict, user: Optional[dict] = None) -> InventoryTransfer:
    transfer = InventoryTransfer(
        id=str(uuid.uuid4()),
        transfer_no=f"TRF-{datetime.now(UTC).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        requested_by=(user or {}).get("employee_id") if user else None,
        **{k: v for k, v in data.items() if k != "requested_by"},
    )
    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)
    await EventBus.emit(DomainEvent(
        name="transfer.requested", domain="inventory",
        entity_type="InventoryTransfer", entity_id=transfer.id,
        data={"transfer_no": transfer.transfer_no, "part_id": transfer.part_id, "qty": transfer.qty},
    ))
    return transfer


# ============================================================
# v3.10 — Update / Delete (修補 root cause：UI 沒 Edit/Delete 是因為 service 沒有)
# ============================================================

# Fields that can be safely updated via PATCH (white-list, 不允許改 part_no/id)
PART_UPDATABLE_FIELDS = {
    "name", "description", "category", "unit", "specification", "drawing_no",
    "min_stock", "max_stock", "safety_stock", "lead_time_days",
    "unit_cost", "is_active", "is_critical",
}


async def update_part(db: AsyncSession, part_id: str, data: dict, user: Optional[dict] = None) -> Part:
    """更新 Part — 白名單欄位，emit part.updated event。"""
    p = (await db.execute(select(Part).where(Part.id == part_id))).scalar_one_or_none()
    if not p:
        raise NotFoundError("零件不存在", part_id=part_id)
    changes = {}
    for k, v in data.items():
        if k not in PART_UPDATABLE_FIELDS:
            continue
        if getattr(p, k) != v:
            changes[k] = {"from": getattr(p, k), "to": v}
            setattr(p, k, v)
    if not changes:
        return p
    await db.commit()
    await db.refresh(p)
    await EventBus.emit(DomainEvent(
        name="part.updated", domain="inventory",
        entity_type="Part", entity_id=p.id,
        data={"part_no": p.part_no, "changes": changes},
    ))
    return p


async def delete_part(db: AsyncSession, part_id: str, user: Optional[dict] = None) -> dict:
    """刪除 Part — FK guard：有交易紀錄 / 庫存 > 0 / BOM 引用 不准刪。"""
    p = (await db.execute(select(Part).where(Part.id == part_id))).scalar_one_or_none()
    if not p:
        raise NotFoundError("零件不存在", part_id=part_id)

    txn_count = (await db.execute(
        select(InventoryTransaction).where(InventoryTransaction.part_id == part_id).limit(1)
    )).scalar_one_or_none()
    if txn_count is not None:
        raise BusinessRuleError(
            "此料件已有交易紀錄，不可刪除（改用 is_active=False 停用）",
            part_id=part_id,
        )
    inv = (await db.execute(select(Inventory).where(Inventory.part_id == part_id))).scalar_one_or_none()
    if inv and (inv.qty_on_hand > 0 or inv.qty_allocated > 0):
        raise BusinessRuleError(
            "庫存未歸零，不可刪除",
            part_id=part_id, qty_on_hand=inv.qty_on_hand,
        )

    # BOM 引用檢查
    from app.models.product import BOMItem
    bom_ref = (await db.execute(
        select(BOMItem).where(BOMItem.part_id == part_id).limit(1)
    )).scalar_one_or_none()
    if bom_ref is not None:
        raise BusinessRuleError("此料件被 BOM 引用，不可刪除", part_id=part_id)

    part_no = p.part_no
    if inv:
        await db.delete(inv)
    await db.delete(p)
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="part.deleted", domain="inventory",
        entity_type="Part", entity_id=part_id,
        data={"part_no": part_no},
    ))
    return {"deleted": True, "part_id": part_id, "part_no": part_no}
