"""出貨單 (Delivery Note) - v3.55 O2C compliance chain.

商業會計法第 33 條：出貨為銷貨原始憑證之一，必須與 SO/Invoice 互為憑證。
原本只有 SO.status='shipped' 不夠 — 需有可獨立保存、編號、簽收的出貨單實體。

本表為 v3.55 O2C 鏈核心：SO -> DeliveryNote -> EInvoice -> JournalEntry -> AR。
ship_sales_order 觸發時，原子化建立 DN + items + 庫存異動 + 發票 + 傳票 + AR。
"""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class DeliveryNote(Base, TenantMixin):
    """出貨單 — 對應一次出貨事件，可能與一張 SO 部分對應。"""
    __tablename__ = "delivery_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dn_no = Column(String(50), nullable=False, unique=True, index=True)  # DN-YYYYMMDD-NNNN
    so_id = Column(String(36), ForeignKey("sales_orders.id"), nullable=False, index=True)

    # 出貨資訊
    ship_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    carrier = Column(String(100))           # 貨運商
    tracking_no = Column(String(100))       # 貨運單號

    # 簽收
    signed_by = Column(String(100))         # 客戶簽收人
    signed_at = Column(DateTime)            # 簽收時間

    # 狀態
    status = Column(String(20), default="shipped", nullable=False)  # shipped / signed / returned

    # 後鏈關聯（denormalize 方便查詢）
    invoice_no = Column(String(20))         # 對應發票號（issue_einvoice 後回寫）
    journal_entry_id = Column(String(36), ForeignKey("journal_entries.id"))

    # 備註 + 稽核
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(36))         # employee_id

    items = relationship("DeliveryNoteItem", back_populates="dn", cascade="all, delete-orphan")


class DeliveryNoteItem(Base, TenantMixin):
    """出貨單明細行。"""
    __tablename__ = "delivery_note_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dn_id = Column(String(36), ForeignKey("delivery_notes.id"), nullable=False, index=True)
    so_item_id = Column(String(36), ForeignKey("sales_order_items.id"))

    part_id = Column(String(36), ForeignKey("parts.id"), nullable=False)
    qty_shipped = Column(Float, nullable=False)
    unit_price = Column(Float, default=0)   # 出貨時單價快照
    line_amount = Column(Float, default=0)

    dn = relationship("DeliveryNote", back_populates="items")
