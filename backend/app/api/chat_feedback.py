"""Chat feedback API (v3.41 P7) — 👍 / 👎 collection

電腦小白 UX：AI 回了一段，老闆覺得不對，按 👎 把訊息標記。
存到 AuditLog（action="chat.feedback"），未來可分析 hallucination 模式。

POST /api/chat/feedback
  {message_id, session_id, score: 1 | -1, comment?}
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import UserContext, require_permission
from app.models.ai_governance import AuditLog


router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatFeedbackRequest(BaseModel):
    message_id: str = Field(..., max_length=64, description="前端為訊息產生的 id")
    session_id: str = Field("", max_length=100)
    score: int = Field(..., description="1 = 讚 / -1 = 倒讚")
    comment: str = Field("", max_length=500, description="（可選）使用者註解")


class ChatFeedbackResponse(BaseModel):
    saved: bool
    message: str


@router.post("/feedback", response_model=ChatFeedbackResponse)
async def submit_chat_feedback(
    req: ChatFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """記錄使用者對 AI 訊息的 thumbs up / down feedback。"""
    if req.score not in (1, -1):
        return ChatFeedbackResponse(saved=False, message="score 應為 1 或 -1")

    entry = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user.id if hasattr(user, "id") else None,
        action="chat.feedback",
        entity_type="ChatMessage",
        entity_id=req.message_id,
        params={
            "session_id": req.session_id,
            "score": req.score,
            "comment": req.comment[:500] if req.comment else "",
        },
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(entry)
    await db.commit()
    return ChatFeedbackResponse(
        saved=True,
        message=f"已記錄 {'👍 讚' if req.score == 1 else '👎 不讚'}",
    )
