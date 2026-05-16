"""Inventory API — 全 endpoint RBAC 保護版。"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import get_db
from app.core.security import require_permission, UserContext, apply_row_filter, apply_tenant_filter
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.models.inventory import Part, Inventory, InventoryTransaction
from app.schemas.inventory import (
    PartCreate, PartResponse,
    InventoryResponse, InventoryTransactionCreate, InventoryTransactionResponse,
    InventoryTransferCreate, InventoryTransferResponse,
)
from app.services import inventory as svc

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


@router.post("/parts", response_model=PartResponse)
async def create_part_endpoint(
    data: PartCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.part.create")),
):
    existing = (await db.execute(select(Part).where(Part.part_no == data.part_no))).scalar_one_or_none()
    if existing:
        raise BusinessRuleError("料號已存在", part_no=data.part_no)
    part = await svc.create_part(db, data.model_dump())
    return PartResponse.model_validate(part)


@router.get("/parts", response_model=List[PartResponse])
async def list_parts_endpoint(
    category: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.part.list")),
):
    q = select(Part)
    q = apply_tenant_filter(q, Part, user)   # ★ 第一道：tenant 隔離
    q = apply_row_filter(q, user, "inventory.part")  # 第二道：row-level scope
    if category: q = q.where(Part.category == category)
    q = q.offset(skip).limit(limit).order_by(Part.part_no)
    parts = (await db.execute(q)).scalars().all()
    return [PartResponse.model_validate(p) for p in parts]


@router.get("/parts/{part_no}", response_model=PartResponse)
async def get_part_endpoint(
    part_no: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.part.read")),
):
    part = await svc.get_part_by_no(db, part_no)
    if not part:
        raise NotFoundError("零件不存在", part_no=part_no)
    # Tenant 隔離：別租戶的 part 即使知道 part_no 也不能取（防 ID-guessing）
    if (
        getattr(part, "tenant_id", None)
        and part.tenant_id != user.tenant_id
        and "tenant.cross" not in user.permissions
    ):
        raise NotFoundError("零件不存在", part_no=part_no)  # 故意回 404 不洩漏存在性
    return PartResponse.model_validate(part)


@router.get("/parts/{part_id}/inventory", response_model=InventoryResponse)
async def get_inventory_endpoint(
    part_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.inventory.read")),
):
    inv = await svc.get_inventory(db, part_id)
    if not inv:
        raise NotFoundError("庫存記錄不存在", part_id=part_id)
    return InventoryResponse.model_validate(inv)


@router.get("/below-safety")
async def below_safety(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.inventory.read")),
):
    rows = await svc.list_inventory_below_safety(db, limit)
    return [
        {
            "part_no": p.part_no, "name": p.name,
            "qty_on_hand": inv.qty_on_hand,
            "qty_available": inv.qty_available,
            "safety_stock": p.safety_stock,
            "shortage": p.safety_stock - inv.qty_available,
        }
        for inv, p in rows
    ]


@router.post("/transactions", response_model=InventoryTransactionResponse)
async def create_transaction(
    data: InventoryTransactionCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.transaction.create")),
):
    txn = await svc.add_inventory_transaction(db, data.model_dump(), user=user.raw_user)
    result = await db.execute(
        select(InventoryTransaction)
        .options(joinedload(InventoryTransaction.part))
        .where(InventoryTransaction.id == txn.id)
    )
    return InventoryTransactionResponse.model_validate(result.scalar_one())


@router.get("/transactions", response_model=List[InventoryTransactionResponse])
async def list_transactions(
    part_id: Optional[str] = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.transaction.list")),
):
    # 預載 part 關聯，避免 InventoryTransactionResponse 觸發 async lazy-load
    q = (
        select(InventoryTransaction)
        .options(joinedload(InventoryTransaction.part))
        .order_by(InventoryTransaction.created_at.desc())
        .offset(skip).limit(limit)
    )
    if part_id:
        q = q.where(InventoryTransaction.part_id == part_id)
    result = await db.execute(q)
    return [InventoryTransactionResponse.model_validate(t) for t in result.unique().scalars().all()]


@router.post("/transfers", response_model=InventoryTransferResponse)
async def create_transfer(
    data: InventoryTransferCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.transaction.create")),
):
    t = await svc.create_transfer(db, data.model_dump(), user=user.raw_user)
    return InventoryTransferResponse.model_validate(t)


# ─── v3.10 PATCH/DELETE ───────────────────────────────────

from pydantic import BaseModel


class PartUpdate(BaseModel):
    """白名單欄位 — 不可改 part_no/id。"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    specification: Optional[str] = None
    drawing_no: Optional[str] = None
    min_stock: Optional[float] = None
    max_stock: Optional[float] = None
    safety_stock: Optional[float] = None
    lead_time_days: Optional[int] = None
    unit_cost: Optional[float] = None
    is_active: Optional[bool] = None
    is_critical: Optional[bool] = None


@router.patch("/parts/{part_id}", response_model=PartResponse)
async def update_part_endpoint(
    part_id: str,
    data: PartUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.part.update")),
):
    patch = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    part = await svc.update_part(db, part_id, patch, user=user.raw_user)
    return PartResponse.model_validate(part)


@router.delete("/parts/{part_id}")
async def delete_part_endpoint(
    part_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("inventory.part.update")),
):
    return await svc.delete_part(db, part_id, user=user.raw_user)
