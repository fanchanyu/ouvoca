"""v3.42 R4：per-user AI 用量限制 middleware

老闆怕「員工亂用 AI，月底 cost 爆」— 限每人每天最多 N 次 LLM call。

設計：
  • in-memory counter（每日重置；多 worker 不共享 — v3.x 改 Redis）
  • 攔截 /api/chat-v2 + 任何 chat endpoint
  • 預設 200 次 / day / user（可由 settings.AI_DAILY_LIMIT_PER_USER 改）
  • Reset：UTC 每日 00:00 自動

LEGAL：
  rate limit 屬於「服務水準限制」（SLA），不取代正式之資安政策。
  客戶若需更嚴格控管（如每小時計、IP 計），須自行於 nginx / API gateway 加。
"""
from __future__ import annotations

import asyncio
from datetime import datetime, UTC, timedelta
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


# in-memory counter：{ user_key: {"count": N, "reset_at": dt} }
_USER_COUNTERS: dict[str, dict] = {}
_LOCK = asyncio.Lock()


def _get_user_id(request: Request) -> Optional[str]:
    """從 JWT 取 user_id；無 token 用 IP."""
    # 簡化：用 Authorization header 的最後 16 字元作 hash key
    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer ") and len(auth) > 30:
        return f"u:{hash(auth[7:]) & 0xFFFFFFFF:x}"
    # 無 token → 用 IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


class AiRateLimitMiddleware(BaseHTTPMiddleware):
    """攔截 /api/chat-v2 等 LLM 入口，每人每日上限。"""

    async def dispatch(self, request: Request, call_next):
        # 只攔 LLM 相關 endpoints
        path = request.url.path
        if not (path.startswith("/api/chat-v2") or path.startswith("/api/agents")):
            return await call_next(request)

        user_key = _get_user_id(request)
        if user_key is None:
            return await call_next(request)

        limit = int(getattr(settings, "AI_DAILY_LIMIT_PER_USER", 200) or 200)
        now = datetime.now(UTC)

        async with _LOCK:
            entry = _USER_COUNTERS.get(user_key)
            if entry is None or now >= entry["reset_at"]:
                # 新一天 reset
                next_reset = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                entry = {"count": 0, "reset_at": next_reset}
                _USER_COUNTERS[user_key] = entry

            if entry["count"] >= limit:
                hours_left = max(0, int((entry["reset_at"] - now).total_seconds() / 3600))
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": "ai_rate_limit_exceeded",
                        "detail": (
                            f"您今日 AI 用量已達上限 {limit} 次。"
                            f"明日 UTC 00:00 自動重置（約 {hours_left} 小時後）。"
                            "如需提升上限，請洽公司負責人調整 AI_DAILY_LIMIT_PER_USER。"
                        ),
                        "hint": "節省用量小撇步：問句一次帶完整資訊（不要分多次問）。",
                        "limit": limit,
                        "used": entry["count"],
                        "reset_at": entry["reset_at"].isoformat(),
                    },
                )

            entry["count"] += 1

        return await call_next(request)


def get_user_usage(user_key: str) -> dict:
    """查使用者當前用量（給 LLM tool 用）。"""
    entry = _USER_COUNTERS.get(user_key, {})
    return {
        "used": entry.get("count", 0),
        "reset_at": entry["reset_at"].isoformat() if entry.get("reset_at") else None,
        "limit": int(getattr(settings, "AI_DAILY_LIMIT_PER_USER", 200) or 200),
    }
