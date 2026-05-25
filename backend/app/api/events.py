"""Real-time event stream (SSE) + recent event history.

Frontend (war-room, desktop notifications) connects to `/api/events/stream`
and receives DomainEvents as they happen via the SSE protocol.
"""
import asyncio
import json
from datetime import datetime, UTC
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request, Query
from sse_starlette.sse import EventSourceResponse

from app.events.engine import EventBus, DomainEvent
from app.core.deps import get_current_user
from app.core.logging import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get("/recent")
async def recent_events(
    name: str = Query(None),
    limit: int = Query(50, le=500),
    _user: dict = Depends(get_current_user),
):
    """Return the most recent events buffered in memory."""
    events = EventBus.get_history(name=name, limit=limit)
    return [
        {
            "name": e.name,
            "domain": e.domain,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "data": e.data,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/stream")
async def event_stream(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> EventSourceResponse:
    """Server-Sent Events endpoint.

    Sends initial backlog + a hello message, then live events as they fire.
    Clients should reconnect automatically on disconnect.

    v3.53 tenant filter: only deliver events whose payload tenant_id matches
    the caller's tenant. Events with no tenant_id (system events) pass through.
    """
    queue: asyncio.Queue[DomainEvent] = asyncio.Queue(maxsize=256)
    user_tenant = (_user or {}).get("tenant_id")

    def _event_tenant(e: DomainEvent) -> str | None:
        """Pull tenant_id off a DomainEvent (lives in .data)."""
        d = getattr(e, "data", None)
        if isinstance(d, dict):
            tid = d.get("tenant_id")
            if tid is not None:
                return str(tid)
        return None

    def _allowed(e: DomainEvent) -> bool:
        """Tenant filter: pass system events (no tenant_id) and matching tenant.
        Drop events that explicitly carry a different tenant_id.
        """
        evt_tenant = _event_tenant(e)
        if user_tenant and evt_tenant and evt_tenant != user_tenant:
            return False
        return True

    async def on_event(event: DomainEvent):
        if not _allowed(event):
            return
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            log.debug("SSE queue full, dropping event %s", event.name)

    # Subscribe to all known events via a wildcard subscription
    EventBus.subscribe_all(on_event)

    async def generator() -> AsyncGenerator[dict, None]:
        try:
            # Replay last 20 events as backlog (also tenant-filtered)
            for e in EventBus.get_history(limit=20):
                if not _allowed(e):
                    continue
                yield {
                    "event": e.name,
                    "data": json.dumps({
                        "domain": e.domain,
                        "entity_type": e.entity_type,
                        "entity_id": e.entity_id,
                        "data": e.data,
                        "ts": e.created_at.isoformat(),
                    }, default=str, ensure_ascii=False),
                }

            yield {"event": "ready", "data": json.dumps({"ts": datetime.now(UTC).replace(tzinfo=None).isoformat()})}

            while True:
                if await request.is_disconnected():
                    log.debug("SSE client disconnected")
                    break
                try:
                    e = await asyncio.wait_for(queue.get(), timeout=15)
                    yield {
                        "event": e.name,
                        "data": json.dumps({
                            "domain": e.domain,
                            "entity_type": e.entity_type,
                            "entity_id": e.entity_id,
                            "data": e.data,
                            "ts": e.created_at.isoformat(),
                        }, default=str, ensure_ascii=False),
                    }
                except asyncio.TimeoutError:
                    # heartbeat to keep connection alive
                    yield {"event": "ping", "data": json.dumps({"ts": datetime.now(UTC).replace(tzinfo=None).isoformat()})}
        finally:
            EventBus.unsubscribe_all(on_event)

    return EventSourceResponse(generator())
