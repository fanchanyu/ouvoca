"""Audit middleware.

Captures request body (≤2 KB), latency, response status, user, IP.
Writes asynchronously via fire-and-forget task so it doesn't block responses,
and never blocks the request even if the audit_logs write fails.

Important: `user_id` in AuditLog is a logical reference. We do NOT enforce a
DB FK on it (could be 'demo-admin', 'anon', or a real users.id), so it tolerates
any string. AuditLog model uses ForeignKey to users; here we write the user_id
as text (no DB FK enforcement at write time — SQLite is lenient and PG with
`ondelete=SET NULL` is preferable). To keep portability we silently skip on FK
violation.
"""
import time
import uuid
import asyncio
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_SKIP_PATHS: set[str] = set()


def _skip(path: str) -> bool:
    global _SKIP_PATHS
    if not _SKIP_PATHS:
        _SKIP_PATHS = set(settings.AUDIT_LOG_SKIP_PATHS)
    return path in _SKIP_PATHS or path.startswith("/api/events/")


async def _write_log(payload: dict) -> None:
    """Background writer — runs in a fresh session, isolated from request flow."""
    try:
        from app.database import AsyncSessionLocal
        from app.models.ai_governance import AuditLog

        async with AsyncSessionLocal() as db:
            row = AuditLog(
                id=str(uuid.uuid4()),
                user_id=payload.get("user_id") if payload.get("user_id") not in (None, "anon", "demo-admin") else None,
                action=payload["action"],
                entity_type=payload["entity_type"],
                params=payload.get("params"),
                result=payload.get("result"),
                ip_address=payload.get("ip"),
                user_agent=payload.get("ua"),
                duration_ms=payload.get("duration_ms", 0),
            )
            db.add(row)
            await db.commit()
    except Exception as exc:  # never let audit kill a request
        log.debug("Audit write failed: %s", exc)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.AUDIT_LOG_ENABLED or _skip(request.url.path):
            return await call_next(request)

        start = time.perf_counter()
        body_preview = None

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                raw = await request.body()
                # Re-inject body so downstream can still read it
                async def receive():
                    return {"type": "http.request", "body": raw, "more_body": False}
                request._receive = receive  # type: ignore[attr-defined]
                body_preview = raw[:2048].decode("utf-8", errors="replace")
            except Exception:
                body_preview = "[unreadable]"

        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        try:
            user = getattr(request.state, "user", None) or {}
            parts = request.url.path.strip("/").split("/")
            entity_type = parts[1] if len(parts) > 1 else "root"
            params = None
            if body_preview:
                try:
                    parsed = json.loads(body_preview)
                    # redact secrets
                    if isinstance(parsed, dict):
                        for k in ("password", "hashed_password", "secret", "api_key"):
                            if k in parsed:
                                parsed[k] = "***"
                    params = {"body": parsed}
                except Exception:
                    params = {"body": body_preview[:512]}

            payload = {
                "user_id": user.get("employee_id"),
                "action": f"{request.method} {request.url.path}",
                "entity_type": entity_type,
                "params": params,
                "result": {"status": response.status_code},
                "ip": request.client.host if request.client else None,
                "ua": request.headers.get("user-agent", "")[:500],
                "duration_ms": duration_ms,
            }
            # Fire-and-forget: don't await — log writes happen out-of-band
            asyncio.create_task(_write_log(payload))
        except Exception as exc:
            log.debug("Audit prepare failed: %s", exc)

        return response
