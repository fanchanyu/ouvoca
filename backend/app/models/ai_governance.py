import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.core.base import Base


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True)
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    agent = Column(String(50))
    tool_calls = Column(JSON)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    customer = relationship("Customer")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36))
    params = Column(JSON)
    result = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(100), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"))
    domain = Column(String(50), nullable=False)
    query = Column(Text, nullable=False)
    decision = Column(Text, nullable=False)
    alternatives = Column(JSON)
    reasoning = Column(Text)
    score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ─── AI Governance fields (Phase γ) ───────────────────────
    agent_name = Column(String(50), index=True)     # 哪個 agent 處理
    model = Column(String(100))                      # LLM model
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    risk_flagged = Column(Boolean, default=False)    # prompt-safety 標記
    human_confirmed = Column(Boolean, default=None)  # 高風險動作確認

    user = relationship("User")


class AfterActionReview(Base):
    __tablename__ = "after_action_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_log_id = Column(String(36), ForeignKey("decision_logs.id"), nullable=False)
    reviewer_id = Column(String(36), ForeignKey("employees.id"))
    assessment = Column(String(20), default="pending")
    lesson_learned = Column(Text)
    improvement_actions = Column(Text)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    decision_log = relationship("DecisionLog")
    reviewer = relationship("Employee")


class FactoryConfig(Base):
    __tablename__ = "factory_config"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    factory_id = Column(String(10), unique=True, nullable=False)
    factory_name = Column(String(200), nullable=False)
    mode = Column(String(10), default="MTO")
    is_active = Column(Boolean, default=True)
    llm_endpoint = Column(String(300))
    db_connection = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
