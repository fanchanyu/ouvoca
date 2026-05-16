"""ConfirmCard — hard-write 操作的「人類確認卡」。

設計目的（對話式 ERP 核心安全機制）：
  - 使用者用對話下令「跟長江廠下 100 個 M6 螺絲」
  - AI 不直接執行；先出 ConfirmCard 給人類點確認
  - 確認後才呼叫 service 真寫入
  - 5 分鐘 TTL，過期自動失效
  - 90 秒內可 Undo（Phase 2）

設計：see docs/CONVERSATIONAL_ERP_DESIGN_ZH.md §5「7 設計原則」#2 + ROADMAP Phase 1。

當前實作（v3.1 PoC）：
  - 暫存：in-memory dict（單 worker OK；Phase 2 改 Redis 支援多 worker）
  - executor：closure capture，呼叫時動態傳入新的 db session
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Any, Awaitable, Callable, Optional

from app.agents.registry import RiskTier
from app.core.logging import get_logger

log = get_logger(__name__)


DEFAULT_TTL_SECONDS = 300  # 5 分鐘


@dataclass
class ConfirmCard:
    """確認卡資料。

    給前端顯示用：title + summary（一行一句的摘要清單）+ 倒數計時。
    給後端執行用：tool_name + slots（已 normalize 的參數）+ executor（closure）。
    """

    id: str
    tool_name: str
    title: str
    summary: list[str]           # 人類可讀的摘要條列
    slots: dict                  # 已 normalize 的執行參數（給 audit log 用）
    risk_tier: str               # "hard-write" / "soft-write"
    created_at: str              # ISO datetime
    expires_at: str              # ISO datetime
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    created_by: Optional[str] = None  # employee_id
    tenant_id: Optional[str] = None

    def to_chat_payload(self) -> dict:
        """給前端 Chat 顯示用。executor 不傳到前端（敏感 closure）。"""
        return {
            "type": "confirm_card",
            "card": {
                "id": self.id,
                "tool_name": self.tool_name,
                "title": self.title,
                "summary": self.summary,
                "slots_preview": self.slots,
                "risk_tier": self.risk_tier,
                "created_at": self.created_at,
                "expires_at": self.expires_at,
                "ttl_seconds": self.ttl_seconds,
            },
        }


# ─── In-memory pending store ────────────────────────────────────
#
# 結構：{ card_id: {"card": ConfirmCard, "executor": Awaitable[Any]} }
#
# Note: 不存到 DB 因為 executor 是 Python closure，存不下；改用 Redis 也只能存
# 一個「重建 executor 的指令」（tool_name + args），下次再 call 一次 tool 重出卡。
# v3.1 PoC 階段先用 in-memory 證明流程。
_PENDING: dict[str, dict] = {}
_PENDING_LOCK = asyncio.Lock()


async def stash_card(
    card: ConfirmCard,
    executor: Callable[[], Awaitable[Any]],
) -> ConfirmCard:
    """暫存一張卡 + 確認時要呼叫的 executor closure。"""
    async with _PENDING_LOCK:
        _PENDING[card.id] = {
            "card": card,
            "executor": executor,
        }
    log.info("ConfirmCard stashed: %s (%s) by %s",
             card.id, card.tool_name, card.created_by)
    return card


async def peek_card(card_id: str) -> Optional[ConfirmCard]:
    """看一眼卡（不消費，不過期檢查）— 給前端 polling / 倒數計時用。"""
    async with _PENDING_LOCK:
        entry = _PENDING.get(card_id)
    return entry["card"] if entry else None


async def consume_card(card_id: str) -> Optional[dict]:
    """取出並從 pending 移除。回 None 表示卡不存在或已過期。"""
    async with _PENDING_LOCK:
        entry = _PENDING.pop(card_id, None)
    if entry is None:
        return None
    # 過期檢查
    now = datetime.now(UTC)
    expires_at = datetime.fromisoformat(entry["card"].expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if now > expires_at:
        log.warning("ConfirmCard %s expired before consume", card_id)
        return None
    return entry


async def cancel_card(card_id: str) -> bool:
    """取消（移除）卡。回 True 表示確實移除過，False 表示卡不存在。"""
    async with _PENDING_LOCK:
        removed = _PENDING.pop(card_id, None)
    return removed is not None


async def list_pending_cards(employee_id: Optional[str] = None) -> list[ConfirmCard]:
    """列出 pending cards（給「未確認的操作」清單頁用）。"""
    async with _PENDING_LOCK:
        cards = [e["card"] for e in _PENDING.values()]
    if employee_id is not None:
        cards = [c for c in cards if c.created_by == employee_id]
    return cards


async def _gc_expired(now: Optional[datetime] = None) -> int:
    """掃描並移除過期卡。回收筆數。"""
    now = now or datetime.now(UTC)
    removed = 0
    async with _PENDING_LOCK:
        for cid in list(_PENDING.keys()):
            entry = _PENDING[cid]
            expires_at = datetime.fromisoformat(entry["card"].expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if now > expires_at:
                _PENDING.pop(cid, None)
                removed += 1
    if removed:
        log.info("ConfirmCard GC removed %d expired cards", removed)
    return removed


def make_card(
    *,
    tool_name: str,
    title: str,
    summary: list[str],
    slots: dict,
    risk_tier: "RiskTier | str" = RiskTier.HARD_WRITE,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    created_by: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> ConfirmCard:
    """構造一張新 ConfirmCard。

    risk_tier 接受 RiskTier enum 或字串（向後相容；字串需是 RiskTier 合法值）。
    """
    # Normalize：enum → str；str 必須是合法值
    if isinstance(risk_tier, RiskTier):
        risk_value = risk_tier.value
    else:
        risk_value = str(risk_tier)
        # 驗證合法性 — 早抓錯而不是讓前端默默壞掉
        if risk_value not in {t.value for t in RiskTier}:
            raise ValueError(
                f"invalid risk_tier {risk_value!r}; must be one of "
                f"{[t.value for t in RiskTier]}"
            )
    now = datetime.now(UTC)
    return ConfirmCard(
        id=str(uuid.uuid4()),
        tool_name=tool_name,
        title=title,
        summary=summary,
        slots=slots,
        risk_tier=risk_value,
        created_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=ttl_seconds)).isoformat(),
        ttl_seconds=ttl_seconds,
        created_by=created_by,
        tenant_id=tenant_id,
    )


# 測試用
def _clear_all_for_test():
    """測試用：清空 pending。生產禁用。"""
    _PENDING.clear()
