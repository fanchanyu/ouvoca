from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    customer_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    agent: str
    session_id: str
    tool_calls: Optional[list] = None
    # v3.14：當 LLM_API_KEY 未設時，前端依此 flag render AI 申請引導卡
    setup_required: Optional[bool] = None
    setup_reason: Optional[str] = None  # 'no_api_key' / 'invalid_key' / 'quota_exceeded'
    # v3.45：槽位填充缺欄位時，前端亮起「輸入提示」UI
    needs_slot_input: Optional[bool] = None
    slot_ask: Optional[str] = None  # 反問語句，前端可顯示為輸入框 placeholder


class ConversationLogResponse(BaseModel):
    id: str
    session_id: str
    role: str
    message: str
    agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FactoryConfigCreate(BaseModel):
    factory_id: str
    factory_name: str
    mode: str = "MTO"
    llm_endpoint: Optional[str] = None
    db_connection: Optional[str] = None


class MeshQueryRequest(BaseModel):
    domain: str
    query_params: dict
    aggregation: Optional[str] = None
    target_factories: Optional[list[str]] = None


class MeshQueryResponse(BaseModel):
    total: Optional[float] = None
    by_site: dict
    success_count: int
    error_count: int
