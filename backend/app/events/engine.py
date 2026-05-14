"""Event Engine — EventBus + ConstraintChecker + NotificationDispatcher.

- EventBus: pub/sub for domain events, plus wildcard subscribers for SSE.
- ConstraintChecker: pre-write business rules (PASS/WARN/BLOCK).
- NotificationDispatcher: maps events → recipient roles for notification.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Awaitable, Union
import asyncio
import inspect
from collections import deque

from app.core.logging import get_logger

log = get_logger(__name__)

Handler = Callable[..., Union[Awaitable[Any], Any]]


@dataclass
class DomainEvent:
    name: str
    domain: str
    entity_type: str
    entity_id: str
    data: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class EventBus:
    _listeners: dict[str, list[Handler]] = {}
    _wildcard: list[Handler] = []
    _event_log: deque = deque(maxlen=500)

    @classmethod
    def subscribe(cls, event_name: str, handler: Handler) -> None:
        cls._listeners.setdefault(event_name, []).append(handler)

    @classmethod
    def subscribe_all(cls, handler: Handler) -> None:
        """Subscribe to ALL events (used by SSE stream)."""
        cls._wildcard.append(handler)

    @classmethod
    def unsubscribe_all(cls, handler: Handler) -> None:
        try:
            cls._wildcard.remove(handler)
        except ValueError:
            pass

    @classmethod
    async def emit(cls, event: DomainEvent) -> None:
        cls._event_log.append(event)
        log.debug("emit %s | entity=%s/%s", event.name, event.entity_type, event.entity_id)

        # Dispatch notification routing (always)
        try:
            await NotificationDispatcher.dispatch(event)
        except Exception as exc:
            log.warning("Notification dispatch failed: %s", exc)

        # Specific listeners + wildcard
        handlers = cls._listeners.get(event.name, []) + cls._wildcard

        async def _run(h: Handler):
            try:
                if inspect.iscoroutinefunction(h):
                    await h(event)
                else:
                    h(event)
            except Exception as exc:
                log.warning("Event handler %s failed for %s: %s", h.__name__, event.name, exc)

        if handlers:
            await asyncio.gather(*(_run(h) for h in handlers), return_exceptions=True)

    @classmethod
    def get_history(cls, name: str | None = None, limit: int = 50) -> list[DomainEvent]:
        events = list(cls._event_log)
        if name:
            events = [e for e in events if e.name == name]
        return events[-limit:]


class ConstraintChecker:
    rules: list[Callable] = []

    @classmethod
    def register(cls, rule: Callable) -> None:
        cls.rules.append(rule)

    @classmethod
    async def check(cls, domain: str, action: str, data: dict, user: dict | None = None) -> dict:
        results: list[dict] = []
        for rule in cls.rules:
            try:
                if inspect.iscoroutinefunction(rule):
                    result = await rule(domain, action, data, user)
                else:
                    result = rule(domain, action, data, user)
                if result:
                    results.append(result)
            except Exception as exc:
                results.append({"rule": rule.__name__, "status": "ERROR", "message": str(exc)})

        blocked = [r for r in results if r.get("status") == "BLOCK"]
        warnings = [r for r in results if r.get("status") == "WARN"]
        if blocked:
            return {"status": "BLOCK", "blocked": blocked, "warnings": warnings}
        return {"status": "PASS" if not warnings else "WARN", "warnings": warnings}


class NotificationDispatcher:
    role_routes: dict[str, list[str]] = {
        # Inventory
        "stock.below_safety": ["inventory_manager", "purchaser"],
        "inventory.changed": [],
        "transfer.requested": ["inventory_manager"],
        # Purchase
        "po.created": ["manager"],
        "po.approved": ["purchaser", "inventory_manager"],
        "po.received": ["purchaser", "inventory_manager"],
        # Production
        "wo.created": ["planner"],
        "wo.released": ["supervisor", "operator"],
        "wo.completed": ["planner", "supervisor"],
        "dispatch.created": ["operator"],
        # Quality
        "inspection.created": ["inspector"],
        "quality.inspected": ["quality_manager"],
        "nc.created": ["quality_manager", "purchaser"],
        "capa.created": ["quality_manager"],
        # Sales / CRM
        "so.created": ["sales"],
        "so.confirmed": ["planner", "production_manager"],
        "so.shipped": ["sales", "accounting"],
        "lead.converted": ["sales"],
        "opportunity.stage_changed": ["sales_manager"],
        # Accounting
        "journal.created": ["accounting"],
        "journal.posted": ["accounting"],
        "month.end_close": ["accounting", "manager"],
        "payment.overdue": ["accounting", "sales"],
        # MRP
        "mrp.generated": ["planner", "purchaser"],
        # Warehouse
        "pick.created": ["warehouse_operator"],
        "pick.completed": ["warehouse_supervisor"],
        "cycle_count.created": ["inventory_manager"],
        # Replenish
        "replenish.suggested": ["purchaser"],
    }

    @classmethod
    def get_recipients(cls, event: DomainEvent) -> list[str]:
        return cls.role_routes.get(event.name, [])

    @classmethod
    async def dispatch(cls, event: DomainEvent) -> dict:
        roles = cls.get_recipients(event)
        # In production this would push to a notification queue / WebSocket / email.
        # For now we just attach to event metadata.
        event.metadata["notified_roles"] = roles
        return {"event": event.name, "notified_roles": roles}
