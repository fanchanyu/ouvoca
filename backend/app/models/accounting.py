import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.base import Base
from app.models._mixins import TenantMixin


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    account_type = Column(String(30), nullable=False)
    parent_id = Column(String(36), ForeignKey("accounts.id"), nullable=True)
    is_debit_normal = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("Account", remote_side=[id], backref="children")
    journal_lines = relationship("JournalLine", back_populates="account")


class JournalEntry(Base, TenantMixin):
    __tablename__ = "journal_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entry_no = Column(String(50), unique=True, nullable=False)
    entry_date = Column(DateTime, nullable=False)
    source_type = Column(String(50))
    source_id = Column(String(36))
    description = Column(Text)
    period = Column(String(10))
    status = Column(String(20), default="draft")
    created_by = Column(String(36), ForeignKey("employees.id"))
    posted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("Employee")
    lines = relationship("JournalLine", back_populates="journal_entry", cascade="all, delete-orphan")


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    journal_entry_id = Column(String(36), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    line_no = Column(Integer, nullable=False)
    description = Column(Text)
    debit = Column(Float, default=0)
    credit = Column(Float, default=0)
    reference = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")


class AccountsReceivable(Base, TenantMixin):
    __tablename__ = "accounts_receivable"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    invoice_no = Column(String(50), nullable=False)
    invoice_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0)
    status = Column(String(20), default="unpaid")
    aging_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="receivables")


class MonthEndClose(Base):
    __tablename__ = "month_end_closes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    period = Column(String(10), unique=True, nullable=False)
    status = Column(String(20), default="open")
    closed_by = Column(String(36), ForeignKey("employees.id"))
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    closer = relationship("Employee")
