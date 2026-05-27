"""Seed the database with a representative dataset.

Usage (from backend/):
    python -m scripts.seed
    # or:  python scripts/seed.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta

# Allow running as both `python -m scripts.seed` and `python scripts/seed.py`
if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.models.organization import Department, Employee, User, Role
from app.models.inventory import Part, Inventory
from app.models.product import Product, BOMItem
from app.models.purchase import Supplier
from app.models.crm_sales import Customer
from app.models.production import WorkCenter
from app.models.accounting import Account
from app.services.auth import hash_password


async def get_or_create(db, model, lookup: dict, defaults: dict | None = None):
    stmt = select(model)
    for k, v in lookup.items():
        stmt = stmt.where(getattr(model, k) == v)
    obj = (await db.execute(stmt)).scalar_one_or_none()
    if obj:
        return obj, False
    obj = model(id=str(uuid.uuid4()), **lookup, **(defaults or {}))
    db.add(obj)
    await db.flush()
    return obj, True


async def seed():
    await init_db()

    # Seed RBAC first (tenants / permissions / roles)
    from scripts.seed_permissions import seed_permissions
    await seed_permissions()

    async with AsyncSessionLocal() as db:
        # --- Departments + Employees + User ---
        dept_it, _ = await get_or_create(db, Department,
            {"code": "IT"}, {"name": "資訊部"})
        dept_ops, _ = await get_or_create(db, Department,
            {"code": "OPS"}, {"name": "營運部"})
        dept_qc, _ = await get_or_create(db, Department,
            {"code": "QC"}, {"name": "品保部"})

        emp_admin, _ = await get_or_create(db, Employee,
            {"employee_no": "E0001"},
            {"name": "系統管理員", "email": "admin@llm-erp.local",
             "department_id": dept_it.id, "title": "Admin",
             "hire_date": datetime.utcnow()})

        emp_planner, _ = await get_or_create(db, Employee,
            {"employee_no": "E0002"},
            {"name": "規劃員 王小明", "email": "planner@llm-erp.local",
             "department_id": dept_ops.id, "title": "Planner"})

        # Admin user
        existing_user = (await db.execute(
            select(User).where(User.username == settings.SEED_ADMIN_USERNAME)
        )).scalar_one_or_none()
        if not existing_user:
            db.add(User(
                id=str(uuid.uuid4()),
                username=settings.SEED_ADMIN_USERNAME,
                hashed_password=hash_password(settings.SEED_ADMIN_PASSWORD),
                employee_id=emp_admin.id,
                is_superuser=True,
            ))

        # Roles
        for code, name in [
            ("admin", "系統管理員"), ("manager", "經理"),
            ("supervisor", "主管"), ("operator", "作業員"),
            ("inspector", "品檢員"), ("planner", "規劃員"),
            ("sales", "業務員"), ("purchaser", "採購員"),
            ("inventory_manager", "倉管"), ("quality_manager", "品保主管"),
            ("accounting", "會計"), ("warehouse_operator", "倉儲作業員"),
            ("warehouse_supervisor", "倉儲主管"), ("production_manager", "生產主管"),
            ("sales_manager", "業務主管"),
        ]:
            await get_or_create(db, Role, {"name": code}, {"description": name})

        # --- Parts ---
        parts_spec = [
            ("M6-BOLT-20", "M6 不銹鋼螺絲 20mm", "raw_material", "pcs", 500, 5000, 1000, 7, 1.5),
            ("M6-NUT", "M6 不銹鋼螺帽", "raw_material", "pcs", 500, 5000, 1000, 7, 0.8),
            ("BEARING-6204", "深溝滾珠軸承 6204", "component", "pcs", 100, 2000, 500, 14, 45.0),
            ("SEAL-O-25", "O 型環 25mm", "consumable", "pcs", 200, 3000, 1000, 5, 2.5),
            ("STEEL-S45C-10", "S45C 鋼材 10mm", "raw_material", "kg", 50, 1000, 200, 21, 80.0),
            ("PCB-MAIN-V2", "主控板 V2", "semi_finished", "pcs", 30, 300, 100, 30, 320.0),
            ("ALUM-CASE-A", "鋁殼 A 型", "component", "pcs", 80, 800, 200, 14, 110.0),
            ("CABLE-USB-1M", "USB 線材 1m", "consumable", "pcs", 100, 2000, 500, 10, 8.0),
            ("LED-RED-5MM", "5mm 紅色 LED", "consumable", "pcs", 500, 10000, 2000, 7, 0.3),
            ("BOX-CARTON-S", "小型紙箱", "packaging", "pcs", 300, 5000, 1000, 7, 5.0),
        ]
        parts_by_no: dict[str, Part] = {}
        for pn, name, cat, unit, mn, mx, ss, lt, cost in parts_spec:
            p, created = await get_or_create(db, Part,
                {"part_no": pn},
                {"name": name, "category": cat, "unit": unit,
                 "min_stock": mn, "max_stock": mx, "safety_stock": ss,
                 "lead_time_days": lt, "unit_cost": cost})
            parts_by_no[pn] = p
            if created:
                # seed inventory with some starting qty (above safety for most)
                qty_on_hand = ss * 1.5 if pn != "M6-BOLT-20" else ss * 0.3  # one below-safety for demo
                db.add(Inventory(
                    id=str(uuid.uuid4()), part_id=p.id,
                    qty_on_hand=qty_on_hand, qty_allocated=0,
                    qty_available=qty_on_hand, qty_in_transit=0,
                ))

        # --- Products & BOM ---
        prod_a, prod_created = await get_or_create(db, Product,
            {"product_no": "PRD-GEAR-A"},
            {"name": "變速齒輪組 A", "category": "成品", "unit": "set",
             "selling_price": 4500, "standard_cost": 2200, "lead_time_days": 14})

        if prod_created:
            for seq, part_no, qty_per in [
                (1, "BEARING-6204", 4),
                (2, "STEEL-S45C-10", 0.8),
                (3, "M6-BOLT-20", 16),
                (4, "M6-NUT", 16),
                (5, "SEAL-O-25", 4),
            ]:
                db.add(BOMItem(
                    id=str(uuid.uuid4()),
                    product_id=prod_a.id,
                    part_id=parts_by_no[part_no].id,
                    level=1, sequence_no=seq, qty_per=qty_per, scrap_rate=0.02,
                ))

        prod_b, prod_b_created = await get_or_create(db, Product,
            {"product_no": "PRD-IOT-B"},
            {"name": "智慧 IoT 模組 B", "category": "成品", "unit": "pcs",
             "selling_price": 1800, "standard_cost": 800, "lead_time_days": 7})
        if prod_b_created:
            for seq, part_no, qty_per in [
                (1, "PCB-MAIN-V2", 1),
                (2, "ALUM-CASE-A", 1),
                (3, "CABLE-USB-1M", 1),
                (4, "LED-RED-5MM", 2),
                (5, "BOX-CARTON-S", 1),
            ]:
                db.add(BOMItem(
                    id=str(uuid.uuid4()),
                    product_id=prod_b.id,
                    part_id=parts_by_no[part_no].id,
                    level=1, sequence_no=seq, qty_per=qty_per, scrap_rate=0.01,
                ))

        # --- Suppliers ---
        for code, name, tier, lt, approved in [
            ("SUP-001", "大華精密工業", "T1", 7, True),
            ("SUP-002", "建興五金", "T2", 5, True),
            ("SUP-003", "達美電子", "T1", 10, True),
            ("SUP-004", "新光包材", "T3", 3, False),
        ]:
            await get_or_create(db, Supplier,
                {"code": code},
                {"name": name, "tier": tier, "lead_time_days": lt,
                 "is_approved": approved, "is_active": True,
                 "contact_email": f"{code.lower()}@suppliers.example"})

        # --- Customers ---
        for code, name, grade, credit in [
            ("CUST-A001", "鴻海科技集團", "A", 5_000_000),
            ("CUST-A002", "台積電精密", "A", 8_000_000),
            ("CUST-B001", "大同電機", "B", 2_000_000),
            ("CUST-C001", "永信工業社", "C", 500_000),
        ]:
            await get_or_create(db, Customer,
                {"code": code},
                {"name": name, "grade": grade, "credit_limit": credit,
                 "contact_email": f"{code.lower()}@customers.example",
                 "payment_terms": "Net 30"})

        # --- Work Centers ---
        for code, name, cap in [
            ("WC-CNC-01", "CNC 加工中心 #1", 120),
            ("WC-CNC-02", "CNC 加工中心 #2", 120),
            ("WC-ASSY", "組裝線", 200),
            ("WC-QC", "品檢站", 300),
        ]:
            await get_or_create(db, WorkCenter,
                {"code": code},
                {"name": name, "capacity_per_day": cap, "efficiency": 0.9,
                 "hourly_rate": 800})

        # --- Chart of Accounts ---
        for code, name, atype, normal in [
            ("1100", "現金", "asset", True),
            ("1200", "應收帳款", "asset", True),
            ("1300", "存貨", "asset", True),
            ("2100", "應付帳款", "liability", False),
            ("2200", "銷項稅額", "liability", False),  # v3.55 — O2C 鏈 5% VAT
            ("3100", "資本", "equity", False),
            ("4100", "銷售收入", "revenue", False),
            ("5100", "銷貨成本", "expense", True),
            ("6100", "管銷費用", "expense", True),
        ]:
            await get_or_create(db, Account,
                {"code": code},
                {"name": name, "account_type": atype, "is_debit_normal": normal})

        await db.commit()
        print("✓ Seed completed.")
        print(f"  Admin login: username='{settings.SEED_ADMIN_USERNAME}' password='{settings.SEED_ADMIN_PASSWORD}'")
        print(f"  Parts: {len(parts_spec)}  Products: 2  Suppliers: 4  Customers: 4")
        print("  Tip: M6-BOLT-20 is intentionally seeded BELOW safety stock so the dashboard shows alerts.")


if __name__ == "__main__":
    asyncio.run(seed())
