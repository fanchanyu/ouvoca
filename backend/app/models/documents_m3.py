"""M3 表單工程 — 請購單 / 收料單 / 領料單 / 退貨單（RMA）。

對應審計缺口：
  - 請購單→採購流程（採購內控第一道防線）
  - 收料單 GRN（收貨與 PO 的獨立驗收單據）
  - 領料單/退料單（現場實際用料，WO 成本才準）
  - 客訴 RMA / 退貨折讓（出貨後反向流程）
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from app.core.base import Base
from app.models._mixins import TenantMixin


class PurchaseRequisition(Base, TenantMixin):
    """請購單（PR）— 採購內控第一道防線。"""
    __tablename__ = "purchase_requisitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pr_no = Column(String(50), unique=True, nullable=False)
    requester_id = Column(String(36), ForeignKey("employees.id"))
    department_id = Column(String(36), ForeignKey("departments.id"))
    status = Column(String(20), default="draft")  # draft / approved / converted / cancelled
    need_date = Column(DateTime)
    remark = Column(Text)
    converted_po_id = Column(String(36), ForeignKey("purchase_orders.id"))
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("PurchaseRequisitionItem", back_populates="pr",
                         cascade="all, delete-orphan")


class PurchaseRequisitionItem(Base, TenantMixin):
    __tablename__ = "purchase_requisition_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pr_id = Column(String(36), ForeignKey("purchase_requisitions.id", ondelete="CASCADE"), nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    line_no = Column(Integer, default=1)
    qty = Column(Float, nullable=False)
    need_date = Column(DateTime)
    remark = Column(Text)

    pr = relationship("PurchaseRequisition", back_populates="items")
    part = relationship("Part")


class GoodsReceiptNote(Base, TenantMixin):
    """收料單（GRN）— 收貨的獨立驗收單據。"""
    __tablename__ = "goods_receipt_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    grn_no = Column(String(50), unique=True, nullable=False)
    po_id = Column(String(36), ForeignKey("purchase_orders.id"), nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    received_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="posted")  # draft / posted / void
    remark = Column(Text)
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("GoodsReceiptNoteItem", back_populates="grn",
                         cascade="all, delete-orphan")
    po = relationship("PurchaseOrder")
    supplier = relationship("Supplier")


class GoodsReceiptNoteItem(Base, TenantMixin):
    __tablename__ = "goods_receipt_note_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    grn_id = Column(String(36), ForeignKey("goods_receipt_notes.id", ondelete="CASCADE"), nullable=False)
    po_item_id = Column(String(36), ForeignKey("purchase_order_items.id"), nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    qty_received = Column(Float, nullable=False)
    unit_price = Column(Float, default=0)

    grn = relationship("GoodsReceiptNote", back_populates="items")
    po_item = relationship("PurchaseOrderItem")
    part = relationship("Part")


class MaterialIssue(Base, TenantMixin):
    """領料單 — 工單領用原料（現場實際用料）。"""
    __tablename__ = "material_issues"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_no = Column(String(50), unique=True, nullable=False)
    wo_id = Column(String(36), ForeignKey("production_orders.id"), nullable=False)
    issued_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="posted")  # draft / posted / void
    remark = Column(Text)
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("MaterialIssueItem", back_populates="issue",
                         cascade="all, delete-orphan")
    wo = relationship("ProductionOrder")


class MaterialIssueItem(Base, TenantMixin):
    __tablename__ = "material_issue_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id = Column(String(36), ForeignKey("material_issues.id", ondelete="CASCADE"), nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    qty = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0)   # 成本快照

    issue = relationship("MaterialIssue", back_populates="items")
    part = relationship("Part")


class ReturnNote(Base, TenantMixin):
    """退貨單（RMA）— 客訴/退貨/折讓的反向流程。"""
    __tablename__ = "return_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    return_no = Column(String(50), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    so_id = Column(String(36), ForeignKey("sales_orders.id"), nullable=True)
    return_date = Column(DateTime, nullable=False)
    reason = Column(Text)
    status = Column(String(20), default="draft")  # draft / approved / processed / void
    created_by = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("ReturnNoteItem", back_populates="return_note",
                         cascade="all, delete-orphan")
    customer = relationship("Customer")


class ReturnNoteItem(Base, TenantMixin):
    __tablename__ = "return_note_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    return_id = Column(String(36), ForeignKey("return_notes.id", ondelete="CASCADE"), nullable=False)
    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    qty = Column(Float, nullable=False)
    unit_price = Column(Float, default=0)
    reason = Column(Text)

    return_note = relationship("ReturnNote", back_populates="items")
    part = relationship("Part")
