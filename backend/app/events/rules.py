"""Constraint rules executed by ConstraintChecker before write operations.

A rule returns one of:
  {"rule": <name>, "status": "PASS" | "WARN" | "BLOCK", "message": "..."}
or None to skip.

BLOCK results raise BusinessRuleError in callers that opt in.
"""
from datetime import datetime, timedelta, UTC

from sqlalchemy import select

from app.events.engine import ConstraintChecker


# ============================================================
# INVENTORY
# ============================================================

async def check_inventory_positive(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "inventory" or action not in ("deduct", "allocate", "issue", "consumption"):
        return None
    from app.database import AsyncSessionLocal
    from app.models.inventory import Inventory

    qty_needed = float(data.get("qty", 0))
    part_id = data.get("part_id")
    if not part_id or qty_needed <= 0:
        return {"rule": "check_inventory_positive", "status": "PASS"}

    async with AsyncSessionLocal() as db:
        inv = (await db.execute(select(Inventory).where(Inventory.part_id == part_id))).scalar_one_or_none()
        if inv and inv.qty_available < qty_needed:
            return {"rule": "check_inventory_positive", "status": "BLOCK",
                    "message": f"庫存不足: 需要 {qty_needed}, 可用 {inv.qty_available}"}
    return {"rule": "check_inventory_positive", "status": "PASS"}


async def check_safety_stock(domain: str, action: str, data: dict, user: dict | None = None):
    """Warn (not block) if action will drop stock below safety level."""
    if domain != "inventory" or action not in ("deduct", "issue"):
        return None
    from app.database import AsyncSessionLocal
    from app.models.inventory import Inventory, Part

    part_id = data.get("part_id")
    qty = float(data.get("qty", 0))
    async with AsyncSessionLocal() as db:
        inv = (await db.execute(select(Inventory).where(Inventory.part_id == part_id))).scalar_one_or_none()
        part = (await db.execute(select(Part).where(Part.id == part_id))).scalar_one_or_none()
        if inv and part and (inv.qty_available - qty) < part.safety_stock:
            return {"rule": "check_safety_stock", "status": "WARN",
                    "message": f"扣帳後庫存 {inv.qty_available - qty} 將低於安全庫存 {part.safety_stock}"}


# ============================================================
# ACCOUNTING
# ============================================================

async def check_month_not_closed(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "accounting" or action not in ("create_journal_entry", "post_journal"):
        return None
    from app.database import AsyncSessionLocal
    from app.models.accounting import MonthEndClose

    period = data.get("period") or datetime.now(UTC).replace(tzinfo=None).strftime("%Y-%m")
    async with AsyncSessionLocal() as db:
        closed = (await db.execute(
            select(MonthEndClose).where(MonthEndClose.period == period, MonthEndClose.status == "closed")
        )).scalar_one_or_none()
        if closed:
            return {"rule": "check_month_not_closed", "status": "BLOCK",
                    "message": f"月結 {period} 已鎖定，無法新增傳票"}


def check_journal_balanced(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "accounting" or action != "create_journal_entry":
        return None
    lines = data.get("lines") or []
    debit = sum(float(l.get("debit", 0)) for l in lines)
    credit = sum(float(l.get("credit", 0)) for l in lines)
    if round(debit, 2) != round(credit, 2):
        return {"rule": "check_journal_balanced", "status": "BLOCK",
                "message": f"借貸不平衡: 借 {debit} ≠ 貸 {credit}"}


# ============================================================
# PURCHASE
# ============================================================

def check_po_has_items(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "purchase" or action != "create":
        return None
    items = data.get("items") or []
    if not items:
        return {"rule": "check_po_has_items", "status": "BLOCK",
                "message": "採購單必須至少包含 1 個項目"}


async def check_po_supplier_approved(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "purchase" or action != "create":
        return None
    from app.database import AsyncSessionLocal
    from app.models.purchase import Supplier

    sid = data.get("supplier_id")
    if not sid:
        return None
    async with AsyncSessionLocal() as db:
        s = (await db.execute(select(Supplier).where(Supplier.id == sid))).scalar_one_or_none()
        if s and not s.is_approved:
            return {"rule": "check_po_supplier_approved", "status": "WARN",
                    "message": f"供應商 {s.name} 尚未核准"}


async def check_po_not_overdue(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "purchase" or action != "receive":
        return None
    from app.database import AsyncSessionLocal
    from app.models.purchase import PurchaseOrder

    po_id = data.get("po_id")
    if not po_id:
        return None
    async with AsyncSessionLocal() as db:
        po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))).scalar_one_or_none()
        if po and po.expected_delivery_date and po.expected_delivery_date < datetime.now(UTC).replace(tzinfo=None):
            days_late = (datetime.now(UTC).replace(tzinfo=None) - po.expected_delivery_date).days
            return {"rule": "check_po_not_overdue", "status": "WARN",
                    "message": f"PO {po.po_no} 已逾期 {days_late} 天"}


# ============================================================
# PRODUCTION
# ============================================================

async def check_bom_exists(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "production" or action != "release":
        return None
    from app.database import AsyncSessionLocal
    from app.models.product import BOMItem

    product_id = data.get("product_id")
    if not product_id:
        return None
    async with AsyncSessionLocal() as db:
        bom = (await db.execute(
            select(BOMItem).where(BOMItem.product_id == product_id, BOMItem.is_active == True).limit(1)
        )).scalar_one_or_none()
        if not bom:
            return {"rule": "check_bom_exists", "status": "BLOCK",
                    "message": "尚未維護 BOM，無法釋放工單"}


def check_wo_qty_positive(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "production" or action != "create":
        return None
    if float(data.get("ordered_qty", 0)) <= 0:
        return {"rule": "check_wo_qty_positive", "status": "BLOCK",
                "message": "工單訂單量必須大於 0"}


async def check_wo_material_available(domain: str, action: str, data: dict, user: dict | None = None):
    """Pre-flight materials availability against BOM."""
    if domain != "production" or action != "release":
        return None
    from app.database import AsyncSessionLocal
    from app.models.product import BOMItem
    from app.models.inventory import Inventory

    product_id = data.get("product_id")
    qty = float(data.get("ordered_qty", 0))
    if not product_id or qty <= 0:
        return None
    shortages = []
    async with AsyncSessionLocal() as db:
        bom = (await db.execute(
            select(BOMItem).where(BOMItem.product_id == product_id, BOMItem.is_active == True)
        )).scalars().all()
        for b in bom:
            inv = (await db.execute(select(Inventory).where(Inventory.part_id == b.part_id))).scalar_one_or_none()
            required = qty * b.qty_per * (1 + b.scrap_rate)
            if not inv or inv.qty_available < required:
                shortages.append({"part_id": b.part_id, "required": required,
                                   "available": inv.qty_available if inv else 0})
    if shortages:
        return {"rule": "check_wo_material_available", "status": "WARN",
                "message": f"釋放後 {len(shortages)} 項物料庫存不足，建議先 MRP", "shortages": shortages}


# ============================================================
# SALES / CRM
# ============================================================

async def check_customer_credit(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "sales" or action not in ("create", "confirm"):
        return None
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from app.models.accounting import AccountsReceivable

    cust_id = data.get("customer_id")
    if not cust_id:
        return None
    new_amount = float(data.get("total_amount", 0))
    async with AsyncSessionLocal() as db:
        cust = (await db.execute(select(Customer).where(Customer.id == cust_id))).scalar_one_or_none()
        if not cust or not cust.credit_limit:
            return None
        ar_q = await db.execute(
            select(AccountsReceivable.amount).where(
                AccountsReceivable.customer_id == cust_id,
                AccountsReceivable.status != "paid",
            )
        )
        outstanding = sum(row[0] for row in ar_q.all() if row[0])
        if outstanding + new_amount > cust.credit_limit:
            return {"rule": "check_customer_credit", "status": "BLOCK",
                    "message": f"客戶 {cust.name} 信用額度不足: 已用 {outstanding} + 本單 {new_amount} > 額度 {cust.credit_limit}"}


def check_so_has_items(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "sales" or action != "create":
        return None
    if not data.get("items"):
        return {"rule": "check_so_has_items", "status": "BLOCK",
                "message": "銷售訂單必須至少包含 1 個項目"}


async def check_payment_terms(domain: str, action: str, data: dict, user: dict | None = None):
    """Warn if AR is significantly overdue when creating a new SO."""
    if domain != "sales" or action != "create":
        return None
    from app.database import AsyncSessionLocal
    from app.models.accounting import AccountsReceivable

    cust_id = data.get("customer_id")
    if not cust_id:
        return None
    async with AsyncSessionLocal() as db:
        overdue = (await db.execute(
            select(AccountsReceivable).where(
                AccountsReceivable.customer_id == cust_id,
                AccountsReceivable.due_date < datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30),
                AccountsReceivable.status != "paid",
            )
        )).scalars().all()
        if overdue:
            return {"rule": "check_payment_terms", "status": "WARN",
                    "message": f"客戶有 {len(overdue)} 筆應收逾期 30 天以上"}


# ============================================================
# QUALITY
# ============================================================

def check_inspection_qty(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "quality" or action != "complete":
        return None
    accepted = float(data.get("accepted_qty", 0))
    rejected = float(data.get("rejected_qty", 0))
    if accepted < 0 or rejected < 0:
        return {"rule": "check_inspection_qty", "status": "BLOCK",
                "message": "檢驗數量不能為負"}


# ============================================================
# WAREHOUSE
# ============================================================

async def check_bin_capacity(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "warehouse" or action != "put_away":
        return None
    from app.database import AsyncSessionLocal
    from app.models.warehouse import BinLocation

    bin_id = data.get("bin_location_id")
    qty = float(data.get("qty", 0))
    if not bin_id:
        return None
    async with AsyncSessionLocal() as db:
        b = (await db.execute(select(BinLocation).where(BinLocation.id == bin_id))).scalar_one_or_none()
        if b and b.capacity > 0 and (b.qty + qty) > b.capacity:
            return {"rule": "check_bin_capacity", "status": "WARN",
                    "message": f"儲位 {b.bin_code} 容量不足 (容量 {b.capacity}, 現有 {b.qty}, 入庫 {qty})"}


# ============================================================
# Org / Approval
# ============================================================

def check_approval_step_valid(domain: str, action: str, data: dict, user: dict | None = None):
    if domain != "approval" or action != "advance":
        return None
    step = data.get("step", -1)
    total = data.get("total_steps", 0)
    if step < 0 or step >= total:
        return {"rule": "check_approval_step_valid", "status": "BLOCK",
                "message": f"審核步驟 {step} 超出範圍 (0..{total - 1})"}


# ============================================================
# Registration
# ============================================================

def register_all_rules() -> None:
    rules = [
        # inventory
        check_inventory_positive, check_safety_stock,
        # accounting
        check_month_not_closed, check_journal_balanced,
        # purchase
        check_po_has_items, check_po_supplier_approved, check_po_not_overdue,
        # production
        check_bom_exists, check_wo_qty_positive, check_wo_material_available,
        # sales / CRM
        check_customer_credit, check_so_has_items, check_payment_terms,
        # quality
        check_inspection_qty,
        # warehouse
        check_bin_capacity,
        # approval
        check_approval_step_valid,
    ]
    for r in rules:
        ConstraintChecker.register(r)


register_all_rules()
