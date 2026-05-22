"""PolicyRule — 「家規 (House Rules)」資料化引擎（Sprint S v3.25）。

**Ouvoca 原創詞**：對手叫 "Business Rule / Workflow / Authorization"，
我們叫「家規」— 每家公司有自己的家規，AI 可以幫你加新家規。

對標：
  - SAP B1 Authorization（要顧問改 code）
  - 鼎新業務規則（條件死板）
  - NetSuite SuiteScript / Odoo Server Action（要會寫程式）
  - Ouvoca：規則資料化 + LLM 對話建規則 + ConfirmCard 確認

設計重點：
  - 規則存 DB（PolicyRule table），不是寫死 code
  - condition_type 是 enum-like string，pluggable
  - action: block / warn / require_approval
  - override_role: 哪個角色可以「主管覆寫」這條規則
  - 每家公司可以開關、改條件、刪規則，無需重啟系統

例子：
  - "WO 釋放需有做法 (Recipe)"      → trigger=wo.release, condition=has_bom, action=block, override=manager
  - "PO > NT$10 萬需老闆審"          → trigger=po.approve, condition=amount>100000, action=require_approval
  - "SO 折扣 > 10% 需主管審"          → trigger=so.confirm, condition=discount>0.10, action=require_approval
  - "刪除料件需 admin"                → trigger=inventory.delete, action=require_approval, override=admin
"""
from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, JSON

from app.core.base import Base
from app.models._mixins import TenantMixin


# 觸發點清單（白名單，避免 typo）
POLICY_TRIGGERS = frozenset({
    # Production
    "wo.release", "wo.complete", "wo.cancel",
    # Purchase
    "po.create", "po.approve", "po.receive", "po.cancel",
    # Sales
    "so.create", "so.confirm", "so.ship", "so.cancel",
    # Inventory
    "inventory.delete", "inventory.transfer",
    # Accounting
    "journal.post", "ar.create", "ar.collect",
    # CRM
    "lead.convert", "opportunity.stage_changed",
    # Custom (使用者自定觸發)
    "custom",
})

# 條件類型（pluggable）
POLICY_CONDITION_TYPES = frozenset({
    "always",        # 總是觸發
    "has_bom",       # 產品有 BOM 才通過
    "field_compare", # 比較欄位（amount > 100000 等）
    "count_check",   # 計數檢查（items > 0、attachments >= 1）
    "custom",        # 自定 Python 表達式（謹慎用）
})

# 動作類型
POLICY_ACTIONS = frozenset({
    "allow",              # 允許（記 log，不擋）
    "warn",               # 警告（不擋，UI 顯示提示）
    "block",              # 阻擋（必須符合條件才能繼續）
    "require_approval",   # 走審批流（接 Sprint P 的 approval workflow）
})


class PolicyRule(Base, TenantMixin):
    """家規 — 規則資料化，不寫死 code。"""
    __tablename__ = "policy_rules"

    id              = Column(String(36), primary_key=True)
    name            = Column(String(200), nullable=False)         # "WO 釋放需有做法"
    description     = Column(Text, nullable=True)                  # 給使用者看的詳細說明

    trigger         = Column(String(50), nullable=False, index=True)  # "wo.release" 等
    condition_type  = Column(String(50), nullable=False, default="always")
    condition_params = Column(JSON, nullable=True)                 # {"field": "amount", "op": "gt", "value": 100000}

    action          = Column(String(30), nullable=False, default="block")  # block/warn/require_approval
    message         = Column(Text, nullable=False)                 # 觸發時給使用者看的訊息
    override_role   = Column(String(50), nullable=True)            # 'manager' / 'admin' / null=不能 override

    is_active       = Column(Boolean, nullable=False, default=True, index=True)
    priority        = Column(Integer, nullable=False, default=100)  # 數字小先評估

    created_by      = Column(String(36), nullable=True)
    created_at      = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at      = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))


class PolicyAuditLog(Base, TenantMixin):
    """每次規則 evaluate 的稽核 log（給合規 / debug 用）。"""
    __tablename__ = "policy_audit_logs"

    id              = Column(String(36), primary_key=True)
    rule_id         = Column(String(36), nullable=True, index=True)
    trigger         = Column(String(50), nullable=False, index=True)
    action_taken    = Column(String(30), nullable=False)  # 'allowed' / 'blocked' / 'overridden' / 'warned'
    context         = Column(JSON, nullable=True)         # 完整的觸發脈絡
    user_id         = Column(String(36), nullable=True)
    override_by     = Column(String(36), nullable=True)   # 覆寫者
    override_reason = Column(Text, nullable=True)
    created_at      = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
