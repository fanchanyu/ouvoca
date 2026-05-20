"""Agent tool 直接執行 endpoint（v3.10 Track B — 給 UI Edit/Delete 按鈕用）。

讓前端不必走 LLM round-trip 也能呼叫 hard-write tools：
  POST /api/agents/exec/{tool_name}  body: {args...}
  → 回 ConfirmCard payload（同 chat-v2 hard-write 結果）
  → 前端用相同 ConfirmCard.tsx 渲染
  → 點確認 → /api/agents/confirm/{card_id}（既有 endpoint）

設計：
  - 只允許新 registry 內的 tool（防呼叫不存在/敏感函式）
  - Permission 透過 require_permission(tool.required_permission) 強制
  - read tier 也支援（同步回 raw result）
  - 失敗回 400 + JSON error
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.deps import get_db
from app.core.security import UserContext, require_permission
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/agents", tags=["AgentExec"])


@router.get("/exec/_list")
async def list_executable_tools(
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """列出新 registry 內可直接執行的 tool（給前端動態 form generator 用）。"""
    from app.agents.registry import _REGISTRY
    return {
        "total": len(_REGISTRY),
        "tools": [
            {
                "name": meta.name,
                "domain": meta.domain,
                "risk_tier": meta.risk_tier.value,
                "description": meta.description,
                "required_permission": meta.required_permission,
                "slots": [
                    {
                        "name": s.name, "type": s.type,
                        "required": s.required, "description": s.description,
                    }
                    for s in meta.slots
                ],
            }
            for meta in _REGISTRY.values()
        ],
    }


@router.post("/exec/{tool_name}")
async def exec_tool(
    tool_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """直接執行 tool。read 直接拿 result；hard-write 拿 ConfirmCard。

    Body: JSON dict 直接 unpack 成 tool 的 args。
    """
    from app.agents.registry import get_tool
    from app.agents.engine import execute_tool

    meta = get_tool(tool_name)
    if meta is None:
        raise HTTPException(404, f"Tool {tool_name!r} 不存在或未註冊")

    # 額外權限驗證：tool 自己宣告的 required_permission 也要過
    if meta.required_permission and not user.has(meta.required_permission):
        raise HTTPException(
            403,
            f"缺少權限 {meta.required_permission}（tool {tool_name} 需要）",
        )

    # 解析 body
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        raise HTTPException(400, "body 必須是 JSON object")

    # v3.25.9 修 pre-existing bug：UserContext 沒有 .roles 屬性（有 permissions dict）
    # 之前 user.roles 會直接 AttributeError 讓整個 endpoint 500。
    user_dict = {
        "employee_id": user.employee_id,
        "username": user.username,
        "user_id": user.user_id,
        "is_superuser": user.is_superuser,
        "tenant_id": user.tenant_id,
        # 給 tool 看：擁有的權限清單（從 UserContext.permissions dict 抽 keys）
        "permissions": list(user.permissions.keys()),
    }

    # 走 engine.execute_tool（含 slot validation）
    result_str = await execute_tool(tool_name, body, db=db, user=user_dict)
    try:
        result = json.loads(result_str)
    except Exception:
        result = {"raw": result_str}
    return result
