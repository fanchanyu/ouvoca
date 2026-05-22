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
    """
    queue: asyncio.Queue[DomainEvent] = asyncio.Queue(maxsize=256)

    async def on_event(event: DomainEvent):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            log.debug("SSE queue full, dropping event %s", event.name)

    # Subscribe to all known events via a wildcard subscription
    EventBus.subscribe_all(on_event)

    async def generator() -> AsyncGenerator[dict, None]:
        try:
            # Replay last 20 events as backlog
            for e in EventBus.get_history(limit=20):
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
