"""Sales service — Customer / SalesOrder business logic."""
import uuid
from datetime import datetime, UTC, timedelta
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.crm_sales import Customer, SalesOrder, SalesOrderItem
from app.events import EventBus, DomainEvent
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.core.logging import get_logger

log = get_logger(__name__)


async def create_customer(db: AsyncSession, data: dict) -> Customer:
    c = Customer(id=str(uuid.uuid4()), **data)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def list_customers(db: AsyncSession, skip: int = 0, limit: int = 100,
                         grade: Optional[str] = None, keyword: Optional[str] = None) -> List[Customer]:
    q = select(Customer)
    if grade:
        q = q.where(Customer.grade == grade)
    if keyword:
        like = f"%{keyword}%"
        q = q.where((Customer.name.like(like)) | (Customer.code.like(like)))
    q = q.offset(skip).limit(limit).order_by(Customer.code)
    return list((await db.execute(q)).scalars().all())


async def create_sales_order(db: AsyncSession, data: dict, user: Optional[dict] = None) -> SalesOrder:
    items_data = data.pop("items", [])
    if not items_data:
        raise BusinessRuleError("銷售訂單必須至少包含 1 個項目")

    so = SalesOrder(
        id=str(uuid.uuid4()),
        so_no=f"SO-{datetime.now(UTC).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        created_by=(user or {}).get("employee_id"),
        **data,
    )
    db.add(so)
    total = 0.0
    for i, item in enumerate(items_data):
        line_total = float(item.get("ordered_qty", 0)) * float(item.get("unit_price", 0))
        soi = SalesOrderItem(
            id=str(uuid.uuid4()),
            so_id=so.id, line_no=i + 1, line_total=line_total, **item,
        )
        db.add(soi)
        total += line_total
    so.total_amount = total
    await db.commit()
    # 預載 customer 關聯，避免 SalesOrderResponse 觸發 async lazy-load (MissingGreenlet)
    await db.refresh(so, attribute_names=["customer"])
    await EventBus.emit(DomainEvent(
        name="so.created", domain="sales",
        entity_type="SalesOrder", entity_id=so.id,
        data={"so_no": so.so_no, "customer_id": so.customer_id, "total": total,
              "tenant_id": getattr(so, "tenant_id", None)},
    ))
    return so


async def confirm_sales_order(db: AsyncSession, so_id: str, user: dict) -> SalesOrder:
    so = await get_sales_order(db, so_id)
    if not so:
        raise NotFoundError("銷售訂單不存在", so_id=so_id)
    if so.status != "draft":
        raise BusinessRuleError(f"狀態 '{so.status}' 不可確認")
    so.status = "confirmed"
    so.approved_by = user.get("employee_id")
    await db.commit()
    await db.refresh(so, attribute_names=["customer"])
    await EventBus.emit(DomainEvent(
        name="so.confirmed", domain="sales",
        entity_type="SalesOrder", entity_id=so.id,
        data={"so_no": so.so_no, "customer_id": so.customer_id, "total": so.total_amount,
              "tenant_id": getattr(so, "tenant_id", None)},
    ))
    return so


# ============================================================
# v3.55 — O2C 鏈：ship_sales_order 全自動串接
# ============================================================
#
# 王董痛點：「出貨單沒對應傳票及發票號碼，進銷存三者沒有同步會很麻煩」
#
# v3.54 之前：ship 只改 so.status + 扣庫存，沒生 DN / 發票 / 傳票 / AR
# v3.55：ship 原子化建立整條鏈：
#   1. DeliveryNote + DeliveryNoteItem（出貨單實體 — 商業會計法 §33）
#   2. inventory_transaction（v3.53 atomic UPDATE pattern）
#   3. EInvoiceRecord（若 customer.tax_id 存在 — B2B；B2C skip 並警告）
#   4. JournalEntry：DR 1200 AR / CR 4100 Revenue / CR 2200 Output Tax
#   5. AccountsReceivable（DR AR 對應 AR 表 row）
#   6. SO 反寫 delivery_note_no / invoice_no / ar_id
#
# 全部在一個 transaction：失敗 rollback，不留斷鏈憑證。
# ============================================================

# 會計科目代碼（與 scripts/seed.py 對齊）
_ACCOUNT_AR = "1200"          # 應收帳款
_ACCOUNT_REVENUE = "4100"     # 銷售收入
_ACCOUNT_OUTPUT_TAX = "2200"  # 銷項稅額（v3.55 補入 seed.py）

_TAX_RATE = 0.05  # Taiwan 5% VAT


async def _gen_dn_no(db: AsyncSession) -> str:
    """產生 DN-YYYYMMDD-NNNN 格式單號（當日序號）。"""
    from app.models.delivery import DeliveryNote
    today = datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%d")
    prefix = f"DN-{today}-"
    cnt = (await db.execute(
        select(func.count(DeliveryNote.id)).where(DeliveryNote.dn_no.like(f"{prefix}%"))
    )).scalar() or 0
    return f"{prefix}{cnt + 1:04d}"


async def _gen_invoice_no(db: AsyncSession) -> str:
    """產生 AB + 8 碼數字之 mock 發票號（生產環境由加值中心配發）。"""
    from app.models.tax_tw import EInvoiceRecord
    cnt = (await db.execute(select(func.count(EInvoiceRecord.id)))).scalar() or 0
    return f"AB{(cnt + 1) % 100000000:08d}"


async def ship_sales_order(
    db: AsyncSession,
    so_id: str,
    qty_to_ship: Optional[dict[str, float]] = None,  # {so_item_id: qty}; None = ship all remaining
    user: Optional[dict] = None,
    *,
    auto_invoice: bool = True,
    auto_journal: bool = True,
    carrier: Optional[str] = None,
    tracking_no: Optional[str] = None,
) -> dict:
    """v3.55: O2C 全鏈原子化出貨。

    Args:
        db: AsyncSession
        so_id: SalesOrder.id
        qty_to_ship: {so_item_id: qty}；None 表示全部剩餘
        user: {"employee_id": ..., "tenant_id": ...}
        auto_invoice: 自動開立電子發票（需 customer.tax_id；B2C 自動 skip）
        auto_journal: 自動建立會計傳票（DR AR / CR Revenue / CR Output Tax）+ AR
        carrier: 貨運商
        tracking_no: 貨運單號

    Returns:
        {
            "delivery_note": {"id", "dn_no"},
            "invoice": {"invoice_no"} or None,
            "journal_entry": {"id", "entry_no"} or None,
            "ar": {"id"} or None,
            "so_id": ..., "so_status": "shipped",
            "total_amount": ..., "tax_amount": ..., "sales_amount": ...,
        }

    Raises:
        NotFoundError / BusinessRuleError — 全部 rollback。
    """
    from app.models.inventory import Part
    from app.models.product import Product
    from app.models.delivery import DeliveryNote, DeliveryNoteItem
    from app.models.tax_tw import EInvoiceRecord
    from app.models.accounting import (
        Account, JournalEntry, JournalLine, AccountsReceivable,
    )
    from app.services.inventory import add_inventory_transaction
    from app.integrations.einvoice_tw import default_provider, EInvoice, InvoiceLineItem

    so = await get_sales_order(db, so_id)
    if not so:
        raise NotFoundError("銷售訂單不存在", so_id=so_id)
    if so.status not in ("confirmed", "production", "ready_to_ship"):
        raise BusinessRuleError(f"狀態 '{so.status}' 不可出貨")

    raw_user = user or {}
    tenant_id = raw_user.get("tenant_id") or getattr(so, "tenant_id", None) or "HQ"
    emp_id = raw_user.get("employee_id")
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        # ─── 1. 建立 DeliveryNote + items ──────────────────
        dn_no = await _gen_dn_no(db)
        dn = DeliveryNote(
            id=str(uuid.uuid4()),
            dn_no=dn_no,
            so_id=so.id,
            ship_date=now,
            carrier=carrier,
            tracking_no=tracking_no,
            status="shipped",
            tenant_id=tenant_id,
            created_at=now,
            created_by=emp_id,
        )
        db.add(dn)
        await db.flush()  # 拿 dn.id

        # 為每個 so item 建 DN item + 扣庫存
        shipped_items_event = []
        total_amount = 0.0
        for item in (so.items or []):
            # 決定要出多少
            if qty_to_ship is not None:
                qty = float(qty_to_ship.get(item.id, 0))
                if qty <= 0:
                    continue
            else:
                remaining = float(item.ordered_qty or 0) - float(item.shipped_qty or 0)
                qty = remaining
                if qty <= 0:
                    continue

            # 找對應的 part（約定 product.product_no == part.part_no）
            prod = (await db.execute(
                select(Product).where(Product.id == item.product_id)
            )).scalar_one_or_none()
            if prod is None:
                continue
            part = (await db.execute(
                select(Part).where(Part.part_no == prod.product_no)
            )).scalar_one_or_none()
            if part is None:
                # 沒對應的 part：保留 DN line 但 skip 庫存異動（warn）
                log.warning("ship_sales_order: no part for product_no=%s, skip inventory", prod.product_no)
                part_id_for_line = None
            else:
                part_id_for_line = part.id

            unit_price = float(item.unit_price or 0)
            line_amount = qty * unit_price
            total_amount += line_amount

            # part_id 是 NOT NULL — 沒對應 part 則整個 line skip（早期失敗）
            if part_id_for_line is None:
                continue

            dn_item = DeliveryNoteItem(
                id=str(uuid.uuid4()),
                dn_id=dn.id,
                so_item_id=item.id,
                part_id=part_id_for_line,
                qty_shipped=qty,
                unit_price=unit_price,
                line_amount=line_amount,
                tenant_id=tenant_id,
            )
            db.add(dn_item)

            # ─── 2. 庫存異動（v3.53 atomic pattern）───────
            await add_inventory_transaction(db, {
                "part_id": part.id,
                "transaction_type": "outbound",
                "qty": qty,
                "reference_type": "delivery_note",
                "reference_id": dn.id,
                "remark": f"出貨 / Ship SO {so.so_no} DN {dn_no}",
            }, user=user)

            # 回寫 so item shipped_qty
            item.shipped_qty = float(item.shipped_qty or 0) + qty
            shipped_items_event.append({"part_id": part.id, "qty": qty})

        # 若 SO 沒任何 item 或全部 qty_to_ship 為 0 → fail
        # （但若是「找不到對應 part」導致 skip：仍建 DN 主檔以保合規鏈，不擋出貨）
        if not (so.items or []):
            raise BusinessRuleError("SO 無 item，無法出貨", so_id=so_id)
        if qty_to_ship is not None and not shipped_items_event:
            raise BusinessRuleError("qty_to_ship 全為 0，無可出貨明細", so_id=so_id)

        # 5% Taiwan VAT — 假設 SO 單價為含稅價
        sales_amount = round(total_amount / (1.0 + _TAX_RATE), 2)
        tax_amount = round(total_amount - sales_amount, 2)

        # ─── 3. 電子發票（若 customer 有 tax_id）──────────
        einvoice_rec = None
        customer = None
        if so.customer_id:
            customer = (await db.execute(
                select(Customer).where(Customer.id == so.customer_id)
            )).scalar_one_or_none()

        buyer_tax_id = getattr(customer, "tax_id", None) if customer else None

        if auto_invoice and customer is not None:
            if not buyer_tax_id:
                # B2C：customer 無統編 → skip einvoice 但保留 DN/JE/AR
                log.warning(
                    "ship_sales_order: customer %s has no tax_id (B2C) — skipping einvoice",
                    customer.code if customer else "?",
                )
            else:
                invoice_no = await _gen_invoice_no(db)
                # 直接落 DB（不走 provider mock，避免外部依賴）
                seller_tax_id = "00000000"  # TODO: 取 tenant 設定
                einvoice_rec = EInvoiceRecord(
                    id=str(uuid.uuid4()),
                    invoice_no=invoice_no,
                    invoice_date=now.strftime("%Y%m%d"),
                    invoice_time=now.strftime("%H:%M:%S"),
                    seller_tax_id=seller_tax_id,
                    buyer_tax_id=buyer_tax_id,
                    buyer_name=customer.name,
                    sales_amount=sales_amount,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    tax_rate=_TAX_RATE,
                    so_id=so.id,
                    status="issued",
                    tracking_no=f"AUTO-{uuid.uuid4().hex[:10].upper()}",
                    tenant_id=tenant_id,
                    created_at=now,
                    created_by=emp_id,
                )
                db.add(einvoice_rec)
                await db.flush()
                # 反寫 SO + DN 的 invoice_no
                so.invoice_no = invoice_no
                dn.invoice_no = invoice_no

        # ─── 4. 會計傳票 + AR ─────────────────────────────
        je = None
        ar = None
        ar_acc = rev_acc = tax_acc = None
        if auto_journal and total_amount > 0:
            # 取會計科目
            ar_acc = (await db.execute(
                select(Account).where(Account.code == _ACCOUNT_AR)
            )).scalar_one_or_none()
            rev_acc = (await db.execute(
                select(Account).where(Account.code == _ACCOUNT_REVENUE)
            )).scalar_one_or_none()
            tax_acc = (await db.execute(
                select(Account).where(Account.code == _ACCOUNT_OUTPUT_TAX)
            )).scalar_one_or_none()

            missing = [
                code for code, acc in [
                    (_ACCOUNT_AR, ar_acc),
                    (_ACCOUNT_REVENUE, rev_acc),
                    (_ACCOUNT_OUTPUT_TAX, tax_acc),
                ] if acc is None
            ]
            if missing:
                # 容錯：未建 chart of accounts 之系統 → skip JE 並 warn
                # （避免阻擋出貨主流程；warning 提醒管理員補 seed.py）
                log.warning(
                    "ship_sales_order: missing accounts %s — skipping auto-JE/AR. "
                    "請執行 scripts/seed.py 建立完整 chart of accounts。",
                    missing,
                )
                ar_acc = rev_acc = tax_acc = None  # 觸發下方 skip

        if auto_journal and total_amount > 0 and ar_acc and rev_acc and tax_acc:

            # 建 JE（不走 service create_journal_entry — 因為它有自己的 commit）
            entry_no = f"JE-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
            je = JournalEntry(
                id=str(uuid.uuid4()),
                entry_no=entry_no,
                entry_date=now,
                source_type="SalesOrder",  # v3.54 GAP-5
                source_id=so.id,
                description=f"出貨開立 SO {so.so_no} / DN {dn_no}",
                period=now.strftime("%Y-%m"),
                status="posted",
                created_by=emp_id,
                created_at=now,
                posted_at=now,
                tenant_id=tenant_id,
            )
            db.add(je)
            await db.flush()

            # 借：應收帳款 (含稅)；貸：銷售收入 (未稅) + 銷項稅額
            db.add(JournalLine(
                id=str(uuid.uuid4()),
                journal_entry_id=je.id, account_id=ar_acc.id,
                line_no=1, description=f"應收-{customer.name if customer else ''}",
                debit=total_amount, credit=0,
                reference=so.so_no,
            ))
            db.add(JournalLine(
                id=str(uuid.uuid4()),
                journal_entry_id=je.id, account_id=rev_acc.id,
                line_no=2, description=f"銷售收入-SO {so.so_no}",
                debit=0, credit=sales_amount,
                reference=so.so_no,
            ))
            db.add(JournalLine(
                id=str(uuid.uuid4()),
                journal_entry_id=je.id, account_id=tax_acc.id,
                line_no=3, description="銷項稅額 5%",
                debit=0, credit=tax_amount,
                reference=so.so_no,
            ))
            await db.flush()

            # 回寫 DN.journal_entry_id 與 einvoice.journal_entry_id
            dn.journal_entry_id = je.id
            if einvoice_rec is not None:
                einvoice_rec.journal_entry_id = je.id

            # AR 表 row（追溯鏈最末節）
            if so.customer_id:
                due = now + timedelta(days=30)  # TODO: 取 customer.payment_terms
                ar = AccountsReceivable(
                    id=str(uuid.uuid4()),
                    customer_id=so.customer_id,
                    invoice_no=so.invoice_no or dn_no,  # B2C 用 DN 號當憑證
                    invoice_date=now,
                    due_date=due,
                    amount=total_amount,
                    paid_amount=0,
                    status="unpaid",
                    tenant_id=tenant_id,
                )
                db.add(ar)
                await db.flush()
                so.ar_id = ar.id

        # ─── 5. SO 反寫 + 狀態 ────────────────────────────
        so.delivery_note_no = dn_no
        so.status = "shipped"
        so.actual_delivery_date = now

        # 單一 commit — 全鏈原子化
        await db.commit()

        # 預載關聯避免 lazy-load
        await db.refresh(so, attribute_names=["customer"])

        # ─── EventBus emit ───────────────────────────────
        await EventBus.emit(DomainEvent(
            name="so.shipped", domain="sales",
            entity_type="SalesOrder", entity_id=so.id,
            data={
                "so_no": so.so_no,
                "dn_no": dn_no,
                "invoice_no": so.invoice_no,
                "je_id": je.id if je else None,
                "ar_id": so.ar_id,
                "shipped_at": now.isoformat(),
                "items": shipped_items_event,
                "total_amount": total_amount,
                "sales_amount": sales_amount,
                "tax_amount": tax_amount,
                "customer_id": so.customer_id,
                "tenant_id": tenant_id,
            },
        ))

        return {
            "delivery_note": {"id": dn.id, "dn_no": dn_no},
            "invoice": {"invoice_no": einvoice_rec.invoice_no} if einvoice_rec else None,
            "journal_entry": {"id": je.id, "entry_no": je.entry_no} if je else None,
            "ar": {"id": ar.id} if ar else None,
            "so_id": so.id,
            "so_no": so.so_no,
            "so_status": so.status,
            # 向後相容（既有 test 與 LLM tool 仍讀 .status）
            "status": so.status,
            "total_amount": total_amount,
            "sales_amount": sales_amount,
            "tax_amount": tax_amount,
        }

    except Exception:
        await db.rollback()
        raise


async def get_sales_order(db: AsyncSession, so_id: str) -> Optional[SalesOrder]:
    result = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.items), joinedload(SalesOrder.customer))
        .where(SalesOrder.id == so_id)
    )
    return result.unique().scalar_one_or_none()


async def list_sales_orders(db: AsyncSession, status: Optional[str] = None,
                            skip: int = 0, limit: int = 100) -> List[SalesOrder]:
    q = select(SalesOrder).options(joinedload(SalesOrder.customer))
    if status:
        q = q.where(SalesOrder.status == status)
    q = q.offset(skip).limit(limit).order_by(SalesOrder.created_at.desc())
    return list((await db.execute(q)).unique().scalars().all())


# ============================================================
# v3.10 — Update / Delete
# ============================================================

CUSTOMER_UPDATABLE_FIELDS = {
    "name", "grade", "contact_person", "contact_email", "contact_phone",
    "address", "payment_terms", "credit_limit", "is_active",
}


async def update_customer(db: AsyncSession, customer_id: str, data: dict, user: Optional[dict] = None) -> Customer:
    c = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not c:
        raise NotFoundError("客戶不存在", customer_id=customer_id)
    changes = {}
    for k, v in data.items():
        if k not in CUSTOMER_UPDATABLE_FIELDS:
            continue
        if getattr(c, k) != v:
            changes[k] = {"from": getattr(c, k), "to": v}
            setattr(c, k, v)
    if not changes:
        return c
    await db.commit()
    await db.refresh(c)
    await EventBus.emit(DomainEvent(
        name="customer.updated", domain="sales",
        entity_type="Customer", entity_id=c.id,
        data={"code": c.code, "changes": changes},
    ))
    return c


async def delete_customer(db: AsyncSession, customer_id: str, user: Optional[dict] = None) -> dict:
    c = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not c:
        raise NotFoundError("客戶不存在", customer_id=customer_id)
    has_so = (await db.execute(
        select(SalesOrder).where(SalesOrder.customer_id == customer_id).limit(1)
    )).scalar_one_or_none()
    if has_so is not None:
        raise BusinessRuleError("此客戶已有銷售訂單，不可刪除（改用 is_active=False 停用）", customer_id=customer_id)
    code = c.code
    await db.delete(c)
    await db.commit()
    await EventBus.emit(DomainEvent(
        name="customer.deleted", domain="sales",
        entity_type="Customer", entity_id=customer_id,
        data={"code": code},
    ))
    return {"deleted": True, "customer_id": customer_id, "code": code}


async def cancel_sales_order(db: AsyncSession, so_id: str, user: dict, reason: str = "") -> SalesOrder:
    so = await get_sales_order(db, so_id)
    if not so:
        raise NotFoundError("銷售訂單不存在", so_id=so_id)
    if so.status in ("shipped", "delivered", "closed", "cancelled"):
        raise BusinessRuleError(f"狀態 {so.status!r} 不可取消", so_id=so_id)
    old = so.status
    so.status = "cancelled"
    if reason:
        so.remark = (so.remark or "") + f"\n[Cancel] {reason}"
    await db.commit()
    await db.refresh(so, attribute_names=["customer"])
    await EventBus.emit(DomainEvent(
        name="so.cancelled", domain="sales",
        entity_type="SalesOrder", entity_id=so.id,
        data={"so_no": so.so_no, "previous_status": old, "reason": reason,
              "tenant_id": getattr(so, "tenant_id", None)},
    ))
    return so
