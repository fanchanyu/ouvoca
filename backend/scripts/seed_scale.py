"""Scalability seed - 10x the demo dataset.

Generates 100 suppliers, 1000 parts, 100 customers, 50 products on top of the
standard demo seed, so the benchmark can be re-run at a representative SMM
scale (a 50-employee factory typically has hundreds of suppliers and parts).

Usage:
    python -m scripts.seed_scale         # additive: keeps demo data, adds scale
    python -m scripts.seed_scale --fresh # drops db, re-seeds at scale

Output is reported as a JSON summary so the manuscript can quote exact counts.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
import uuid
from datetime import datetime
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func

from app.database import AsyncSessionLocal, init_db
from app.models.inventory import Part, Inventory
from app.models.purchase import Supplier
from app.models.crm_sales import Customer
from app.models.product import Product


PART_TYPES = ["raw_material", "semi_finished", "component", "consumable", "packaging"]
UOMS = ["pcs", "kg", "m", "L", "set"]
GRADES = ["A", "B", "C"]


async def seed_scale(n_suppliers: int = 100, n_parts: int = 1000,
                      n_customers: int = 100, n_products: int = 50,
                      tenant_id: str | None = None) -> dict:
    rng = random.Random(20260523)
    counts = {"added_suppliers": 0, "added_parts": 0,
              "added_customers": 0, "added_products": 0,
              "added_inventory": 0}

    await init_db()

    async with AsyncSessionLocal() as db:
        # Resolve tenant_id (use HQ)
        from app.models.permission import Tenant
        if tenant_id is None:
            hq = (await db.execute(
                select(Tenant).where(Tenant.code == "HQ")
            )).scalar_one_or_none()
            tenant_id = hq.id if hq else None

        # ---- Suppliers ----
        existing_codes = set((await db.execute(
            select(Supplier.code).where(Supplier.code.like("SUP-%"))
        )).scalars().all())

        for i in range(1, n_suppliers + 1):
            code = f"SUP-{1000 + i:04d}"
            if code in existing_codes:
                continue
            tier = rng.choice(["T1", "T2", "T3"])
            lead = rng.randint(2, 30)
            obj = Supplier(
                id=str(uuid.uuid4()),
                code=code,
                name=f"Supplier {i:03d} Industrial Co.",
                tier=tier,
                lead_time_days=lead,
                payment_terms=rng.choice(["NET30", "NET45", "NET60"]),
                is_approved=rng.random() > 0.1,
                tenant_id=tenant_id,
            )
            db.add(obj)
            counts["added_suppliers"] += 1

        await db.commit()

        # ---- Parts + Inventory ----
        existing_part_nos = set((await db.execute(
            select(Part.part_no).where(Part.part_no.like("P-%"))
        )).scalars().all())

        for i in range(1, n_parts + 1):
            pno = f"P-{10000 + i:05d}"
            if pno in existing_part_nos:
                continue
            ptype = rng.choice(PART_TYPES)
            uom = rng.choice(UOMS)
            safety = rng.choice([10, 50, 100, 200, 500, 1000])
            cost = round(rng.uniform(0.5, 500.0), 2)
            obj = Part(
                id=str(uuid.uuid4()),
                part_no=pno,
                name=f"Part {pno}",
                category=ptype,
                unit=uom,
                unit_cost=cost,
                safety_stock=safety,
                lead_time_days=rng.randint(3, 21),
                tenant_id=tenant_id,
            )
            db.add(obj)
            await db.flush()
            qty = rng.choice([0, safety // 2, safety, safety * 2, safety * 5])
            inv = Inventory(
                id=str(uuid.uuid4()),
                part_id=obj.id,
                qty_on_hand=qty,
                qty_allocated=0,
                qty_available=qty,
                tenant_id=tenant_id,
            )
            db.add(inv)
            counts["added_parts"] += 1
            counts["added_inventory"] += 1
        await db.commit()

        # ---- Customers ----
        existing_customer_codes = set((await db.execute(
            select(Customer.code).where(Customer.code.like("C-%"))
        )).scalars().all())

        for i in range(1, n_customers + 1):
            code = f"C-{1000 + i:04d}"
            if code in existing_customer_codes:
                continue
            obj = Customer(
                id=str(uuid.uuid4()),
                code=code,
                name=f"Customer {i:03d} Trading Co.",
                grade=rng.choice(GRADES),
                credit_limit=rng.choice([100000, 500000, 1000000, 5000000]),
                contact_phone=f"02-{rng.randint(20000000, 99999999)}",
                tenant_id=tenant_id,
            )
            db.add(obj)
            counts["added_customers"] += 1
        await db.commit()

        # ---- Products (a subset of parts that are 'semi_finished') ----
        existing_product_nos = set((await db.execute(
            select(Product.product_no).where(Product.product_no.like("PRD-%"))
        )).scalars().all())

        for i in range(1, n_products + 1):
            pno = f"PRD-{1000 + i:04d}"
            if pno in existing_product_nos:
                continue
            obj = Product(
                id=str(uuid.uuid4()),
                product_no=pno,
                name=f"Product {pno}",
                selling_price=round(rng.uniform(100, 50000), 2),
                standard_cost=round(rng.uniform(50, 30000), 2),
                tenant_id=tenant_id,
            )
            db.add(obj)
            counts["added_products"] += 1
        await db.commit()

        # ---- Final tallies ----
        n_suppliers_total = (await db.execute(select(func.count(Supplier.id)))).scalar_one()
        n_parts_total = (await db.execute(select(func.count(Part.id)))).scalar_one()
        n_customers_total = (await db.execute(select(func.count(Customer.id)))).scalar_one()
        n_products_total = (await db.execute(select(func.count(Product.id)))).scalar_one()

    summary = {
        "added": counts,
        "totals_after_seed": {
            "suppliers": n_suppliers_total,
            "parts": n_parts_total,
            "customers": n_customers_total,
            "products": n_products_total,
        },
        "rng_seed": 20260523,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # Write the totals to a JSON for the manuscript
    out = Path(__file__).resolve().parents[3] / "ISF_Q2_投稿" / "eval"
    out.mkdir(parents=True, exist_ok=True)
    (out / "scalability_seed_state.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--suppliers", type=int, default=100)
    p.add_argument("--parts", type=int, default=1000)
    p.add_argument("--customers", type=int, default=100)
    p.add_argument("--products", type=int, default=50)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(seed_scale(args.suppliers, args.parts, args.customers, args.products))
