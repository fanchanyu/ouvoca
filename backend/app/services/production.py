"""Production service — Product / BOM / WO / Operation / Dispatch."""
import uuid
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, BOMItem
from app.models.production import ProductionOrder, WorkCenter, Operation, DispatchLog
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError, BusinessRuleError


# -------- Product --------

async def create_product(db: AsyncSession, data: dict) -> Product:
    p = Product(id=str(uuid.uuid4()), **data)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def list_products(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Product]:
    result = await db.execute(select(Product).offset(skip).limit(limit).order_by(Product.product_no))
    return list(result.scalars().all())


async def get_product(db: AsyncSession, product_id: str) -> Optional[Product]:
    return (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()


# -------- BOM --------

async def add_bom_item(db: AsyncSession, data: dict) -> BOMItem:
    item = BOMItem(id=str(uuid.uuid4()), **data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def get_bom_tree(db: AsyncSession, product_id: str) -> List[BOMItem]:
    result = await db.execute(
        select(BOMItem)
        .where(BOMItem.product_id == product_id, BOMItem.is_active == True)
        .order_by(BOMItem.level, BOMItem.sequence_no)
    )
    return list(result.scalars().all())


# v3.25.9：多階 BOM 遞迴爆破
# 規則：BOMItem.part_id → Part.part_no；若 Part.part_no 對應到某個 Product.product_no，
#       則該 part 為「半成品 / 次組件」，需再爆破它自己的 BOM。
async def explode_bom_recursive(
    db: AsyncSession,
    product_id: str,
    qty: float = 1.0,
    *,
    level: int = 1,
    visited: Optional[set] = None,
) -> List[dict]:
    """遞迴展開多階 BOM，回傳所有葉節點（不再有子 BOM 的 part）累計用量。

    回傳格式：[{"part_id": ..., "qty": float, "level": int, "scrap_rate": float, "path": [...]}, ...]

    循環依賴保護：若 product_id 已在 visited set 中，直接 return []（防止 A→B→A 無窮遞迴）。

    用量計算：父階 qty × 子階 qty_per × (1 + scrap_rate)
    """
    if visited is None:
        visited = set()
    if product_id in visited:
        # 循環依賴：A 用了 B，B 又用了 A → 截斷
        return []
    visited = visited | {product_id}  # 不直接修改傳入的 set

    rows = (await db.execute(
        select(BOMItem)
        .where(BOMItem.product_id == product_id, BOMItem.is_active == True)
        .order_by(BOMItem.level, BOMItem.sequence_no)
    )).scalars().all()

    # 用 Part / Product 兩張表批次查 part_no 對應的子 product_id
    # （效能：先一次抓所有 part_no，避免每階 N+1 query）
    from app.models.inventory import Part
    part_ids = [r.part_id for r in rows]
    if not part_ids:
        return []

    parts = (await db.execute(
        select(Part).where(Part.id.in_(part_ids))
    )).scalars().all()
    part_by_id = {p.id: p for p in parts}

    # 反查：哪些 part_no 對應到 product（是半成品）
    part_nos = [p.part_no for p in parts]
    sub_products = (await db.execute(
        select(Product).where(Product.product_no.in_(part_nos))
    )).scalars().all()
    subprod_by_part_no = {p.product_no: p for p in sub_products}

    result: List[dict] = []
    for bom in rows:
        part = part_by_id.get(bom.part_id)
        if part is None:
            continue
        # 本階需求 = 父階 qty × 用量 × (1 + 耗損)
        line_qty = qty * bom.qty_per * (1 + (bom.scrap_rate or 0))

        sub_product = subprod_by_part_no.get(part.part_no)
        if sub_product is not None:
            # 半成品 → 再遞迴展子階；本階自己不算「葉節點需求」
            sub_explosion = await explode_bom_recursive(
                db, sub_product.id, line_qty,
                level=level + 1, visited=visited,
            )
            result.extend(sub_explosion)
        else:
            # 葉節點（純料件）→ 累計用量
            result.append({
                "part_id": bom.part_id,
                "part_no": part.part_no,
                "qty": line_qty,
                "level": level,
                "scrap_rate": bom.scrap_rate or 0,
                "is_critical": bom.is_critical or False,
            })

    return result


# v3.25.9：where-used 反查（哪些產品的 BOM 用到這個料件）
async def where_used(db: AsyncSession, part_id: str) -> List[dict]:
    """回傳所有「BOM 中用到該 part」的產品清單 + 用量。"""
    rows = (await db.execute(
        select(BOMItem, Product)
        .join(Product, Product.id == BOMItem.product_id)
        .where(BOMItem.part_id == part_id, BOMItem.is_active == True)
    )).all()
    return [
        {
            "product_id": prod.id,
            "product_no": prod.product_no,
            "product_name": prod.name,
            "qty_per": bom.qty_per,
            "scrap_rate": bom.scrap_rate,
            "level": bom.level,
        }
        for bom, prod in rows
    ]


# v3.25.9：BOM 行更新 / 刪除（搭 hard-write tools）
BOM_ITEM_UPDATABLE_FIELDS = {
    "qty_per", "scrap_rate", "sequence_no", "level",
    "is_critical", "effective_from", "effective_to", "is_active",
}


async def update_bom_item(db: AsyncSession, item_id: str, data: dict) -> BOMItem:
    item = (await db.execute(
        select(BOMItem).where(BOMItem.id == item_id)
    )).scalar_one_or_none()
    if item is None:
        raise NotFoundError("BOM 項目不存在", item_id=item_id)
    changes = {}
    for k, v in data.items():
        if k not in BOM_ITEM_UPDATABLE_FIELDS:
            continue
        if getattr(item, k) != v:
            changes[k] = {"from": getattr(item, k), "to": v}
            setattr(item, k, v)
    if not changes:
        return item
    await db.commit()
    await db.refresh(item)
    await EventBus.emit(DomainEvent(
        name="bom_item.updated", domain="production",
        entity_type="BOMItem", entity_id=item.id,
        data={"product_id": item.product_id, "part_id": item.part_id, "changes": changes},
    ))
    return item


async def delete_bom_item(db: AsyncSession, item_id: str, user: Optional[dict] = None) -> dict:
    """軟刪除：is_active = False（保留審計軌跡，不真 DELETE）。"""
    item = (await db.execute(
        select(BOMItem).where(BOMItem.id == item_id)
    )).scalar_one_or_none()
    if item is None:
        raise NotFoundError("BOM 項目不存在", item_id=item_id)
    if not item.is_active:
        return {"message": "BOM 項目已停用", "item_id": item_id}
    item.is_active = False
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="bom_item.deactivated", domain="production",
        entity_type="BOMItem", entity_id=item.id,
        data={"product_id": item.product_id, "part_id": item.part_id,
              "deactivated_by": (user or {}).get("employee_id")},
    ))
    return {"message": "✅ BOM 項目已停用", "item_id": item_id}


# -------- Work Order --------

async def create_production_order(db: AsyncSession, data: dict, user: Optional[dict] = None) -> ProductionOrder:
    if float(data.get("ordered_qty", 0)) <= 0:
        raise BusinessRuleError("訂單量必須大於 0")

    wo = ProductionOrder(
        id=str(uuid.uuid4()),
        wo_no=f"WO-{datetime.now(UTC).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        created_by=(user or {}).get("employee_id"),
        **data,
    )
    db.add(wo)
    await db.commit()
    await db.refresh(wo)
    await EventBus.emit(DomainEvent(
        name="wo.created", domain="production",
        entity_type="ProductionOrder", entity_id=wo.id,
        data={"wo_no": wo.wo_no, "product_id": wo.product_id, "qty": wo.ordered_qty},
    ))
    return wo


async def get_production_order(db: AsyncSession, wo_id: str) -> Optional[ProductionOrder]:
    result = await db.execute(
        select(ProductionOrder)
        .options(selectinload(ProductionOrder.operations))
        .where(ProductionOrder.id == wo_id)
    )
    return result.scalar_one_or_none()


async def list_production_orders(db: AsyncSession, status: Optional[str] = None,
                                 skip: int = 0, limit: int = 100) -> List[ProductionOrder]:
    q = select(ProductionOrder)
    if status:
        q = q.where(ProductionOrder.status == status)
    q = q.offset(skip).limit(limit).order_by(ProductionOrder.created_at.desc())
    return list((await db.execute(q)).scalars().all())


async def release_production_order(db: AsyncSession, wo_id: str, user: Optional[dict] = None) -> ProductionOrder:
    wo = (await db.execute(select(ProductionOrder).where(ProductionOrder.id == wo_id))).scalar_one_or_none()
    if not wo:
        raise NotFoundError("工單不存在", wo_id=wo_id)
    if wo.status != "draft":
        raise BusinessRuleError(f"工單狀態 '{wo.status}' 不可釋放", wo_id=wo_id)

    # v3.25：用 PolicyEngine 取代寫死的「需 BOM」檢查
    # 預設家規 "WO 釋放需有做法 (Recipe)" 會自動 evaluate
    # 客戶可在 UI 開關 / 改條件，無需動 code
    from app.services.policy_engine import evaluate_policies
    result = await evaluate_policies(
        db, "wo.release",
        context={"product_id": wo.product_id, "wo_id": wo.id, "wo_no": wo.wo_no},
        user_id=(user or {}).get("employee_id"),
    )
    if result.blocked:
        raise BusinessRuleError(
            result.message,
            product_id=wo.product_id,
            can_override=result.can_override,
            override_role=result.override_role,
            triggered_rule_id=result.triggered_rule_id,
        )
    if result.needs_approval:
        # 進審批流（接 Sprint P 的 approval workflow，這裡簡化為阻擋）
        raise BusinessRuleError(
            f"本動作需要 {result.override_role or '主管'} 審批：{result.message}",
            requires_approval=True,
            triggered_rule_id=result.triggered_rule_id,
        )

    wo.status = "released"
    wo.released_by = (user or {}).get("employee_id")
    wo.actual_start = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="wo.released", domain="production",
        entity_type="ProductionOrder", entity_id=wo.id,
        data={"wo_no": wo.wo_no, "product_id": wo.product_id, "qty": wo.ordered_qty},
    ))
    return wo


async def complete_production_order(db: AsyncSession, wo_id: str,
                                    completed_qty: float, user: Optional[dict] = None) -> ProductionOrder:
    """Mark WO completed and push finished product to inventory."""
    from app.services.inventory import add_inventory_transaction

    wo = await get_production_order(db, wo_id)
    if not wo:
        raise NotFoundError("工單不存在", wo_id=wo_id)
    if wo.status not in ("released", "in_progress"):
        raise BusinessRuleError(f"工單狀態 '{wo.status}' 不可完工")

    wo.completed_qty += completed_qty
    if wo.completed_qty >= wo.ordered_qty:
        wo.status = "completed"
        wo.actual_end = datetime.now(UTC).replace(tzinfo=None)

    # 把成品實際入庫（之前是註解 TODO 沒做 → 完工不會增加庫存的沉默 bug）
    # 約定：product.product_no == part.part_no（同編號對齊）
    from app.models.product import Product
    from app.models.inventory import Part
    prod = (await db.execute(
        select(Product).where(Product.id == wo.product_id)
    )).scalar_one_or_none()
    fg_part = None
    if prod is not None:
        fg_part = (await db.execute(
            select(Part).where(Part.part_no == prod.product_no)
        )).scalar_one_or_none()
    if fg_part is not None and completed_qty > 0:
        await add_inventory_transaction(db, {
            "part_id": fg_part.id,
            "transaction_type": "inbound",
            "qty": float(completed_qty),
            "reference_type": "work_order",
            "reference_id": wo.id,
            "remark": f"WO {wo.wo_no} 完工入庫",
        }, user=user)

    await db.commit()
    await EventBus.emit(DomainEvent(
        name="wo.completed", domain="production",
        entity_type="ProductionOrder", entity_id=wo.id,
        data={
            "wo_no": wo.wo_no, "completed_qty": completed_qty,
            "status": wo.status,
            "fg_inventory_increased": fg_part is not None,
        },
    ))
    return wo


# -------- WorkCenter / Operation / DispatchLog --------

async def create_work_center(db: AsyncSession, data: dict) -> WorkCenter:
    wc = WorkCenter(id=str(uuid.uuid4()), **data)
    db.add(wc)
    await db.commit()
    await db.refresh(wc)
    return wc


async def list_work_centers(db: AsyncSession) -> List[WorkCenter]:
    return list((await db.execute(select(WorkCenter).order_by(WorkCenter.code))).scalars().all())


async def create_operation(db: AsyncSession, data: dict) -> Operation:
    op = Operation(id=str(uuid.uuid4()), **data)
    db.add(op)
    await db.commit()
    await db.refresh(op)
    return op


async def create_dispatch_log(db: AsyncSession, data: dict, user: Optional[dict] = None) -> DispatchLog:
    log = DispatchLog(
        id=str(uuid.uuid4()),
        operator_id=(user or {}).get("employee_id") or data.get("operator_id"),
        started_at=datetime.now(UTC).replace(tzinfo=None),
        **{k: v for k, v in data.items() if k != "operator_id"},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    await EventBus.emit(DomainEvent(
        name="dispatch.created", domain="production",
        entity_type="DispatchLog", entity_id=log.id,
        data={"wo_id": log.production_order_id, "op_id": log.operation_id, "qty": log.dispatched_qty},
    ))
    return log


# ============================================================
# v3.10 — Update / Delete
# ============================================================

PRODUCT_UPDATABLE_FIELDS = {
    "name", "selling_price", "standard_cost", "is_active",
}


async def update_product(db: AsyncSession, product_id: str, data: dict, user: Optional[dict] = None) -> Product:
    p = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if not p:
        raise NotFoundError("產品不存在", product_id=product_id)
    changes = {}
    for k, v in data.items():
        if k not in PRODUCT_UPDATABLE_FIELDS:
            continue
        if getattr(p, k) != v:
            changes[k] = {"from": getattr(p, k), "to": v}
            setattr(p, k, v)
    if not changes:
        return p
    await db.commit()
    await db.refresh(p)
    await EventBus.emit(DomainEvent(
        name="product.updated", domain="production",
        entity_type="Product", entity_id=p.id,
        data={"product_no": p.product_no, "changes": changes},
    ))
    return p


async def cancel_production_order(db: AsyncSession, wo_id: str, user: dict, reason: str = "") -> ProductionOrder:
    wo = (await db.execute(select(ProductionOrder).where(ProductionOrder.id == wo_id))).scalar_one_or_none()
    if not wo:
        raise NotFoundError("工單不存在", wo_id=wo_id)
    if wo.status in ("completed", "cancelled"):
        raise BusinessRuleError(f"狀態 {wo.status!r} 不可取消", wo_id=wo_id)
    old = wo.status
    wo.status = "cancelled"
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="wo.cancelled", domain="production",
        entity_type="ProductionOrder", entity_id=wo.id,
        data={"wo_no": wo.wo_no, "previous_status": old, "reason": reason},
    ))
    return wo
