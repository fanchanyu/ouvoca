"""Chat / AI Agent API."""
import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_db, get_optional_user
from app.core.security import require_permission, UserContext
from app.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, ConversationLogResponse
from app.models.organization import User
from app.models.ai_governance import ConversationLog
from app.agents import classify_intent, get_agent, get_tool_definitions, execute_tool, chat_completion
from app.core.logging import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["Chat"])


async def _resolve_user_id_for_log(db: AsyncSession, user_info: dict) -> Optional[str]:
    """
    ConversationLog.user_id is FK -> users.id (not employees.id).
    We accept employee_id from the JWT, then look up the matching User row.
    Returns None if not resolvable (e.g. demo user) — log row will have NULL user_id.
    """
    emp_id = user_info.get("employee_id")
    if not emp_id or emp_id == "demo-admin":
        return None
    result = await db.execute(select(User).where(User.employee_id == emp_id))
    user = result.scalar_one_or_none()
    return user.id if user else None


@router.post("/chat-v2", response_model=ChatResponse)
async def chat_v2(
    request: Request,
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_permission("ai.agent.use")),
):
    user_info = getattr(request.state, "user", None) or {"employee_id": "demo-admin", "username": "demo", "roles": ["admin"]}
    session_id = data.session_id or str(uuid.uuid4())
    message = data.message
    user_id_for_log = await _resolve_user_id_for_log(db, user_info)

    # 1) Load recent history (10 messages)
    history_q = await db.execute(
        select(ConversationLog)
        .where(ConversationLog.session_id == session_id)
        .order_by(ConversationLog.created_at.desc())
        .limit(10)
    )
    history = list(history_q.scalars().all())

    # 2) Persist user message
    user_log = ConversationLog(
        id=str(uuid.uuid4()), session_id=session_id,
        user_id=user_id_for_log, role="user", message=message,
    )
    db.add(user_log)
    await db.commit()

    # 3) Classify + pick agent
    intent = classify_intent(message)
    agent = get_agent(intent) or get_agent("general")
    if not agent:
        return ChatResponse(
            reply="尚未註冊任何 agent，請檢查後端設定。",
            agent="none", session_id=session_id,
        )

    system_msg = {
        "role": "system",
        "content": (
            agent["system_prompt"]
            + f"\n\n當前使用者: {user_info.get('username', '匿名')} "
            + f"| 角色: {user_info.get('roles', [])}"
        ),
    }
    messages = [system_msg]
    for h in reversed(history):
        messages.append({"role": h.role, "content": h.message})
    messages.append({"role": "user", "content": message})

    # 4) Tool calling loop
    tools = get_tool_definitions(agent["tool_names"]) if agent.get("tool_names") else None
    tool_calls_log: List[dict] = []
    assistant_reply = ""
    max_rounds = settings.LLM_MAX_TOOL_ROUNDS

    if not settings.LLM_API_KEY and settings.LLM_PROVIDER != "ollama":
        # No API key — return structured flag so frontend can render setup guide card.
        # 不直接回錯字串，避免電腦小白看到 raw text 不知道怎辦。
        setup_reply = (
            "🤖 AI 助手還沒啟用\n\n"
            f"我偵測到你想做：**{intent}**\n\n"
            "但目前系統還沒有 LLM API key，所以我沒辦法幫你執行。\n"
            "好消息是申請只要 3 分鐘 + 完全免費試用額度（DeepSeek 推薦）。\n\n"
            "請點下面的「立刻申請 API Key」按鈕，跟著步驟做。"
        )
        # v3.43 P1-2：persist assistant reply 以便 session reload 後仍看得到 setup 提示
        db.add(ConversationLog(
            id=str(uuid.uuid4()), session_id=session_id,
            user_id=user_id_for_log, role="assistant",
            message=setup_reply, agent=intent,
            tool_calls={"setup_required": True, "reason": "no_api_key"},
        ))
        await db.commit()
        return ChatResponse(
            reply=setup_reply,
            agent=intent,
            session_id=session_id,
            tool_calls=None,
            setup_required=True,
            setup_reason="no_api_key",
        )
    else:
        for round_idx in range(max_rounds):
            try:
                response = await chat_completion(messages, tools)
            except Exception as exc:
                log.exception("LLM call failed: %s", exc)
                assistant_reply = "AI 服務暫時無法連線，請稍後再試。"
                break

            tc_list = response.get("tool_calls", []) or []
            if not tc_list:
                assistant_reply = response.get("content", "") or "(無回應)"
                break

            for tc in tc_list:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                fn_args_str = fn.get("arguments", "{}")
                try:
                    fn_args = json.loads(fn_args_str) if isinstance(fn_args_str, str) else fn_args_str
                except Exception:
                    fn_args = {}
                result = await execute_tool(fn_name, fn_args, db=db, user=user_info)
                tool_calls_log.append({"tool": fn_name, "args": fn_args, "result": result})
                messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", fn_name),
                    "content": result,
                })
        else:
            assistant_reply = "處理超過最大工具呼叫回合，請簡化您的查詢。"

    # 5) Detect slot-filling needs_input from tool results
    needs_slot_input = False
    slot_ask: Optional[str] = None
    for tc in tool_calls_log:
        raw = tc.get("result", "")
        if isinstance(raw, str) and raw.startswith("{"):
            try:
                parsed = json.loads(raw)
                if parsed.get("needs_input") is True:
                    needs_slot_input = True
                    slot_ask = parsed.get("ask")
                    # 若 LLM 沒產生文字回覆，直接用 ask 文字讓使用者看到問題
                    if not assistant_reply.strip():
                        assistant_reply = slot_ask or "請補充必要資訊。"
                    break
            except Exception:
                pass

    # 6) Persist assistant reply
    db.add(ConversationLog(
        id=str(uuid.uuid4()), session_id=session_id,
        user_id=user_id_for_log, role="assistant",
        message=assistant_reply, agent=intent,
        tool_calls={"calls": tool_calls_log} if tool_calls_log else None,
    ))
    await db.commit()

    return ChatResponse(
        reply=assistant_reply, agent=intent, session_id=session_id,
        tool_calls=tool_calls_log if tool_calls_log else None,
        needs_slot_input=needs_slot_input or None,
        slot_ask=slot_ask,
    )


@router.get("/chat/sessions/{session_id}/history", response_model=List[ConversationLogResponse])
async def session_history(
    session_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    result = await db.execute(
        select(ConversationLog)
        .where(ConversationLog.session_id == session_id)
        .order_by(ConversationLog.created_at.asc())
        .limit(limit)
    )
    return [ConversationLogResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/health")
async def health(_user: dict = Depends(get_optional_user)):
    """Public health check — no auth required."""
    from app.database import engine
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "db": "ok" if db_ok else "fail",
        "llm_provider": settings.LLM_PROVIDER,
        "demo_bypass": settings.demo_bypass_active,
    }
