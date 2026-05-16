"""Onboarding API（v3.10 Track D）— 中小企業快速上手。

  POST /api/onboarding/seed-demo  — 一鍵載入 demo 資料（5 客戶 / 3 供應商 / 10 料件）
  GET  /api/onboarding/status     — 看當前 tenant 是否已 seed 過 demo

設計：
  - 純後端 endpoint，前端 wizard 觸發
  - 每個 demo 實體用 `DEMO-` 前綴，方便批次清理
  - 已存在則跳過（idempotent）
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, UTC
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.logging import get_logger
from app.core.security import UserContext, require_permission
from app.models.crm_sales import Customer
from app.models.inventory import Inventory, Part
from app.models.purchase import Supplier

log = get_logger(__name__)
router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


DEMO_PREFIX = "DEMO-"


class OnboardingStatusResponse(BaseModel):
    has_demo_data: bool
    demo_customers: int
    demo_suppliers: int
    demo_parts: int
    total_customers: int
    total_suppliers: int
    total_parts: int


@router.get("/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """看當前 tenant 是否已 seed demo（DEMO- 前綴計數）。"""
    demo_c = (await db.execute(
        select(func.count(Customer.id)).where(Customer.code.like(f"{DEMO_PREFIX}%"))
    )).scalar() or 0
    demo_s = (await db.execute(
        select(func.count(Supplier.id)).where(Supplier.code.like(f"{DEMO_PREFIX}%"))
    )).scalar() or 0
    demo_p = (await db.execute(
        select(func.count(Part.id)).where(Part.part_no.like(f"{DEMO_PREFIX}%"))
    )).scalar() or 0
    total_c = (await db.execute(select(func.count(Customer.id)))).scalar() or 0
    total_s = (await db.execute(select(func.count(Supplier.id)))).scalar() or 0
    total_p = (await db.execute(select(func.count(Part.id)))).scalar() or 0
    return OnboardingStatusResponse(
        has_demo_data=(demo_c + demo_s + demo_p) > 0,
        demo_customers=demo_c, demo_suppliers=demo_s, demo_parts=demo_p,
        total_customers=total_c, total_suppliers=total_s, total_parts=total_p,
    )


class SeedDemoResponse(BaseModel):
    inserted_customers: int
    inserted_suppliers: int
    inserted_parts: int
    skipped: int
    message: str


# ─── Demo data 模板 ────────────────────────────────────────

_DEMO_CUSTOMERS = [
    ("DEMO-CUST-A001", "示範客戶 A（電子）", "A", 500000),
    ("DEMO-CUST-A002", "示範客戶 B（汽車）", "A", 800000),
    ("DEMO-CUST-B001", "示範客戶 C（自行車）", "B", 200000),
    ("DEMO-CUST-B002", "示範客戶 D（家電）", "B", 300000),
    ("DEMO-CUST-C001", "示範客戶 E（小型工廠）", "C", 80000),
]

_DEMO_SUPPLIERS = [
    ("DEMO-SUP-001", "示範供應商 - 長江五金", "T1", 7),
    ("DEMO-SUP-002", "示範供應商 - 大華實業", "T2", 14),
    ("DEMO-SUP-003", "示範供應商 - 中華電子", "T2", 10),
]

_DEMO_PARTS = [
    # part_no, name, category, unit, safety_stock, unit_cost, qty_on_hand
    ("DEMO-M6-BOLT", "M6 螺絲 × 20mm", "component", "pcs", 500, 5.0, 1200),
    ("DEMO-M8-NUT",  "M8 螺帽", "component", "pcs", 300, 3.0, 800),
    ("DEMO-RIVET-4", "鉚釘 4mm", "component", "pcs", 200, 2.0, 100),  # 低於安全
    ("DEMO-PCB-A1",  "PCB 板 A1", "raw_material", "pcs", 50, 250.0, 80),
    ("DEMO-CASING",  "外殼 ABS 250", "semi_finished", "pcs", 100, 80.0, 150),
    ("DEMO-PACK-S",  "包裝盒 S", "packaging", "pcs", 200, 8.0, 350),
    ("DEMO-PACK-M",  "包裝盒 M", "packaging", "pcs", 150, 12.0, 60),  # 低於安全
    ("DEMO-MOTOR-A", "馬達模組 A", "component", "pcs", 30, 450.0, 45),
    ("DEMO-WIRE-2M", "電線 2 米", "consumable", "pcs", 100, 15.0, 250),
    ("DEMO-LABEL",   "標籤紙", "consumable", "rolls", 20, 100.0, 28),
]


@router.post("/seed-demo", response_model=SeedDemoResponse)
async def seed_demo(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """一鍵載入 demo 資料 — idempotent（已存在跳過）。"""
    inserted_c = inserted_s = inserted_p = skipped = 0

    # Customers
    for code, name, grade, credit in _DEMO_CUSTOMERS:
        existing = (await db.execute(
            select(Customer).where(Customer.code == code)
        )).scalar_one_or_none()
        if existing is not None:
            skipped += 1
            continue
        db.add(Customer(
            id=str(uuid.uuid4()), code=code, name=name,
            grade=grade, credit_limit=credit,
        ))
        inserted_c += 1

    # Suppliers
    for code, name, tier, lead in _DEMO_SUPPLIERS:
        existing = (await db.execute(
            select(Supplier).where(Supplier.code == code)
        )).scalar_one_or_none()
        if existing is not None:
            skipped += 1
            continue
        db.add(Supplier(
            id=str(uuid.uuid4()), code=code, name=name, tier=tier,
            lead_time_days=lead, is_approved=True,
        ))
        inserted_s += 1

    # Parts + Inventory
    for part_no, name, cat, unit, safety, cost, on_hand in _DEMO_PARTS:
        existing = (await db.execute(
            select(Part).where(Part.part_no == part_no)
        )).scalar_one_or_none()
        if existing is not None:
            skipped += 1
            continue
        p = Part(
            id=str(uuid.uuid4()), part_no=part_no, name=name,
            category=cat, unit=unit, safety_stock=safety, unit_cost=cost,
        )
        db.add(p)
        await db.flush()  # 取 p.id
        db.add(Inventory(
            id=str(uuid.uuid4()), part_id=p.id,
            qty_on_hand=on_hand, qty_available=on_hand, qty_allocated=0,
        ))
        inserted_p += 1

    await db.commit()

    return SeedDemoResponse(
        inserted_customers=inserted_c,
        inserted_suppliers=inserted_s,
        inserted_parts=inserted_p,
        skipped=skipped,
        message=(
            f"✅ Demo 資料已準備：客戶 {inserted_c} / 供應商 {inserted_s} / 料件 {inserted_p}"
            + (f"（跳過 {skipped} 筆已存在）" if skipped > 0 else "")
        ),
    )


@router.delete("/clear-demo")
async def clear_demo(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.config.update")),
):
    """清除所有 DEMO- 前綴資料（給結束試用清場用）。"""
    from sqlalchemy import delete
    # 清順序很重要：先 Inventory（有 FK 到 Part）
    parts = (await db.execute(
        select(Part).where(Part.part_no.like(f"{DEMO_PREFIX}%"))
    )).scalars().all()
    deleted_inv = 0
    for p in parts:
        r = await db.execute(delete(Inventory).where(Inventory.part_id == p.id))
        deleted_inv += r.rowcount or 0
    deleted_p = (await db.execute(
        delete(Part).where(Part.part_no.like(f"{DEMO_PREFIX}%"))
    )).rowcount or 0
    deleted_c = (await db.execute(
        delete(Customer).where(Customer.code.like(f"{DEMO_PREFIX}%"))
    )).rowcount or 0
    deleted_s = (await db.execute(
        delete(Supplier).where(Supplier.code.like(f"{DEMO_PREFIX}%"))
    )).rowcount or 0
    await db.commit()
    return {
        "deleted_customers": deleted_c,
        "deleted_suppliers": deleted_s,
        "deleted_parts": deleted_p,
        "deleted_inventory_rows": deleted_inv,
        "message": "✅ Demo 資料已清空",
    }
