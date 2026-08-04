"""金流閉環基礎模型（Phase B1）— AP / 收付款 / 銀行帳戶。

對應審計缺口：
  - 無 AP（只有 AR）→ 付款鏈（採購→發票→AP→付款）是斷的
  - 無 Payment/Receipt 實體、無銀行帳戶主檔 → 金流無法對帳

Phase B 後續（4-6 週）：
  - SupplierInvoice + 3-Way Match（PO ↔ 收貨 ↔ 供應商發票）
  - 票據管理（應收/應付票據 + 託收）
  - 現金流表 / 三大報表
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.base import Base
from app.models._mixins import TenantMixin


class BankAccount(Base, TenantMixin):
    """銀行帳戶主檔 — 收付款的資金歸屬。"""
    __tablename__ = "bank_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False)  # 健檢 #19：租戶域唯一（非全域）
    name = Column(String(200), nullable=False)
    bank_name = Column(String(100))
    branch_name = Column(String(100))
    account_no = Column(String(50))
    currency = Column(String(10), default="TWD")
    opening_balance = Column(Float, default=0)
    current_balance = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payments = relationship("Payment", back_populates="bank_account")
    receipts = relationship("Receipt", back_populates="bank_account")


class AccountsPayable(Base, TenantMixin):
    """應付帳款 — 採購付款鏈的核心（對應 AccountsReceivable）。"""
    __tablename__ = "accounts_payable"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    invoice_no = Column(String(50), nullable=False)
    invoice_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    # M2-3：進項稅額拆分（401/405 與 3-Way Match 用；舊資料可為 NULL）
    sales_amount = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    paid_amount = Column(Float, default=0)
    status = Column(String(20), default="unpaid")  # unpaid / partial / paid / void
    aging_days = Column(Integer, default=0)
    source_type = Column(String(30))  # supplier_invoice / purchase_order ...
    source_id = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier")
    payments = relationship("Payment", back_populates="payable")


class Payment(Base, TenantMixin):
    """付款單 — 付錢給供應商（沖 AP）。"""
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_no = Column(String(50), unique=True, nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    payable_id = Column(String(36), ForeignKey("accounts_payable.id"), nullable=True)
    bank_account_id = Column(String(36), ForeignKey("bank_accounts.id"), nullable=True)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    method = Column(String(20), default="transfer")  # cash / transfer / check
    reference = Column(String(100))
    status = Column(String(20), default="draft")     # draft / posted / void
    created_by = Column(String(36), ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier")
    payable = relationship("AccountsPayable", back_populates="payments")
    bank_account = relationship("BankAccount", back_populates="payments")


class Receipt(Base, TenantMixin):
    """收款單 — 客戶付錢（沖 AR）。"""
    __tablename__ = "receipts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    receipt_no = Column(String(50), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    receivable_id = Column(String(36), ForeignKey("accounts_receivable.id"), nullable=True)
    bank_account_id = Column(String(36), ForeignKey("bank_accounts.id"), nullable=True)
    amount = Column(Float, nullable=False)
    receipt_date = Column(DateTime, nullable=False)
    method = Column(String(20), default="transfer")  # cash / transfer / check
    reference = Column(String(100))
    status = Column(String(20), default="draft")     # draft / posted / void
    created_by = Column(String(36), ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer")
    receivable = relationship("AccountsReceivable")
    bank_account = relationship("BankAccount", back_populates="receipts")


class SupplierInvoice(Base, TenantMixin):
    """供應商發票 — 3-Way Match（PO ↔ 收貨 ↔ 發票）的核心。

    關聯 PO（可選）；對應 Supplier 與一組 SupplierInvoiceItem。
    """
    __tablename__ = "supplier_invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_no = Column(String(50), nullable=False, index=True)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    po_id = Column(String(36), ForeignKey("purchase_orders.id"), nullable=True)
    invoice_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime)
    sales_amount = Column(Float, default=0)   # 未稅
    tax_amount = Column(Float, default=0)     # 稅額
    total_amount = Column(Float, default=0)   # 含稅
    status = Column(String(20), default="received")  # received / matched / qty_variance / price_variance / unmatched
    remark = Column(Text)
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier")
    purchase_order = relationship("PurchaseOrder")
    items = relationship("SupplierInvoiceItem", back_populates="invoice",
                         cascade="all, delete-orphan")


class SupplierInvoiceItem(Base, TenantMixin):
    """供應商發票行 — 對應 PO 行（po_item_id 可選）。"""
    __tablename__ = "supplier_invoice_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String(36), ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False)
    po_item_id = Column(String(36), ForeignKey("purchase_order_items.id"), nullable=True)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    line_no = Column(Integer, default=1)
    qty = Column(Float, nullable=False)
    unit_price = Column(Float, default=0)
    line_total = Column(Float, default=0)

    invoice = relationship("SupplierInvoice", back_populates="items")
    po_item = relationship("PurchaseOrderItem")
    part = relationship("Part")


class PromissoryNote(Base, TenantMixin):
    """票據管理（M2-4）— 應收/應付票據 + 託收。"""
    __tablename__ = "promissory_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    note_type = Column(String(20), nullable=False)   # receivable / payable
    party_id = Column(String(36), nullable=False)    # customer_id / supplier_id
    party_name = Column(String(200))
    bank_name = Column(String(100))
    check_no = Column(String(50))
    amount = Column(Float, nullable=False)
    issue_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="on_hand")   # on_hand / endorsed / deposited / cleared / returned / void
    deposit_bank_account_id = Column(String(36), ForeignKey("bank_accounts.id"), nullable=True)
    remark = Column(Text)
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deposit_bank = relationship("BankAccount")


class FixedAsset(Base, TenantMixin):
    """固定資產 + 折舊（M2-5）— 直線法。"""
    __tablename__ = "fixed_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False)  # 健檢 #19：租戶域唯一（非全域）
    name = Column(String(200), nullable=False)
    category = Column(String(50))                   # machinery / equipment / vehicle / furniture ...
    cost = Column(Float, nullable=False)            # 取得成本
    salvage_value = Column(Float, default=0)        # 殘值
    useful_life_months = Column(Integer, nullable=False)
    acquisition_date = Column(DateTime, nullable=False)
    depreciation_method = Column(String(20), default="straight_line")
    accumulated_depreciation = Column(Float, default=0)
    monthly_depreciation = Column(Float, default=0)
    status = Column(String(20), default="active")   # active / fully_depreciated / disposed
    journal_entry_id = Column(String(36), ForeignKey("journal_entries.id"), nullable=True)
    remark = Column(Text)
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
