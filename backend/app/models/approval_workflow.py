"""Approval Workflow models (v3.22 — 多階審批工作流)。

對標鼎新 / SAP B1：把「規則」「申請單」「決議紀錄」三段分清楚。

設計重點
--------
- **ApprovalRule**：條件式自動觸發。例：PO > 10 萬要老闆審。
- **ApprovalRequestV2**：由事件 / 規則命中自動建單。狀態機 pending → approved/rejected。
- **ApprovalStep**：每一階的決議紀錄（審核人、動作、原因）。

為什麼新建（不 reuse organization.py 的 ApprovalFlow/Request/Record）？
----------------------------------------------------------------------
舊三表是「人工建 flow → 人工提請」的模式，沒有「條件自動觸發」概念，
且 step 結構是預定 steps JSON。新需求是 rule-based + 自動 evaluate，
資料模型差異太大，沿用會迫使既有欄位變雙重含義 → 維護惡夢。
新建 + 不同表名 (`approval_rules` / `approval_workflow_requests` /
`approval_workflow_steps`) 完全避開衝突。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.base import Base
from app.models._mixins import TenantMixin


# ── 規則 ────────────────────────────────────────────────────
class ApprovalRule(Base, TenantMixin):
    """什麼條件需要審 + 誰審。

    範例
    ----
    name="高額採購單", trigger_type="po",
    condition_field="amount", condition_op="gt", condition_value=100000,
    approver_role="boss", stages=1
    """
    __tablename__ = "approval_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False)
    trigger_type = Column(String(20), nullable=False, index=True)  # 'po' | 'so' | 'payment'
    condition_field = Column(String(40), nullable=False)            # 'amount' | 'discount_pct'
    condition_op = Column(String(8), nullable=False)                # 'gt' | 'gte' | 'lt' | 'lte' | 'eq'
    condition_value = Column(Float, nullable=False)
    approver_role = Column(String(40), nullable=False)              # 'boss' | 'manager' | ...
    stages = Column(Integer, nullable=False, default=1)             # 幾階審
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── 申請單 ─────────────────────────────────────────────────
class ApprovalRequestV2(Base, TenantMixin):
    """規則命中後自動產生的申請單。"""
    __tablename__ = "approval_workflow_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String(36), ForeignKey("approval_rules.id"), nullable=False, index=True)
    trigger_type = Column(String(20), nullable=False, index=True)
    trigger_id = Column(String(36), nullable=False, index=True)   # PO / SO / payment id
    trigger_summary = Column(String(255), nullable=False)         # 「PO-2026-0042 NT$150,000」

    requested_by = Column(String(36), nullable=True)              # employee_id; nullable for system
    approver_role = Column(String(40), nullable=False)            # 從 rule 複製，方便 list_pending

    current_stage = Column(Integer, nullable=False, default=1)
    total_stages = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="pending", index=True)
    # 'pending' | 'approved' | 'rejected' | 'cancelled'

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rule = relationship("ApprovalRule")
    steps = relationship(
        "ApprovalStepV2", back_populates="request",
        cascade="all, delete-orphan", order_by="ApprovalStepV2.stage",
    )


# ── 決議紀錄 ────────────────────────────────────────────────
class ApprovalStepV2(Base):
    """每一階的決議紀錄。"""
    __tablename__ = "approval_workflow_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(
        String(36),
        ForeignKey("approval_workflow_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage = Column(Integer, nullable=False)
    approver_id = Column(String(36), nullable=True)   # employee_id
    approver_username = Column(String(80), nullable=True)
    action = Column(String(20), nullable=False)       # 'approved' | 'rejected'
    comment = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("ApprovalRequestV2", back_populates="steps")


__all__ = ["ApprovalRule", "ApprovalRequestV2", "ApprovalStepV2"]
