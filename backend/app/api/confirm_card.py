"""ConfirmCard API — 給前端「確認/取消」hard-write 操作用。

設計：see docs/CONVERSATIONAL_ERP_DESIGN_ZH.md §5 + app/agents/confirm_card.py

Endpoints:
  GET  /api/agents/confirm/{card_id}  — peek 看卡
  POST /api/agents/confirm/{card_id}  — 確認 → 執行 executor → 回結果
  POST /api/agents/cancel/{card_id}   — 取消
  GET  /api/agents/pending             — 列出當下 pending（給未確認操作清單用）
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

from app.agents.confirm_card import (
    ConfirmCard, _gc_expired, cancel_card, consume_card,
    list_pending_cards, peek_card,
)
from app.core.deps import get_db
from app.core.logging import get_logger
from app.core.security import UserContext, require_permission
from sqlalchemy.ext.asyncio import AsyncSession

log = get_logger(__name__)
router = APIRouter(prefix="/api/agents", tags=["ConfirmCard"])


@router.get("/pending")
async def list_pending(
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """列出目前 pending 的 ConfirmCard。"""
    # 順手 GC
    await _gc_expired()
    cards = await list_pending_cards(employee_id=user.employee_id)
    return {
        "total": len(cards),
        "cards": [
            {
                "id": c.id, "tool_name": c.tool_name,
                "title": c.title, "summary": c.summary,
                "risk_tier": c.risk_tier,
                "created_at": c.created_at, "expires_at": c.expires_at,
            }
            for c in cards
        ],
    }


@router.get("/confirm/{card_id}")
async def get_card(
    card_id: str,
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """看卡內容（前端倒數計時 / preview 用，不消費）。"""
    card = await peek_card(card_id)
    if card is None:
        raise HTTPException(404, f"ConfirmCard {card_id} 不存在或已過期")
    # 權限檢查：只有建立者可以看
    if card.created_by and card.created_by != user.employee_id:
        raise HTTPException(403, "只有建立者可以查看此卡")
    return asdict(card)


@router.post("/confirm/{card_id}")
async def confirm_card(
    card_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """確認執行 ConfirmCard 對應的 hard-write 操作。

    流程：
      1. consume_card：取出 + 從 pending 移除（避免雙擊執行兩次）
      2. 權限檢查：只有建立者可以確認
      3. 呼叫 executor closure
      4. 回 audit log 友善訊息 + 結果

    Note: tool 自己負責的 permission（如 purchase.po.create）在 stash 階段已驗過；
    這裡只驗 ai.agent.use + 建立者身分。
    """
    entry = await consume_card(card_id)
    if entry is None:
        raise HTTPException(404, f"ConfirmCard {card_id} 不存在、已過期、或已被處理")

    card: ConfirmCard = entry["card"]
    executor = entry["executor"]

    if card.created_by and card.created_by != user.employee_id:
        raise HTTPException(403, "只有建立者可以確認此卡")

    log.info(
        "ConfirmCard executing: id=%s tool=%s by=%s",
        card.id, card.tool_name, user.employee_id,
    )

    try:
        result = await executor()
    except Exception as e:
        log.exception("ConfirmCard executor failed: %s", e)
        raise HTTPException(
            500,
            f"執行失敗: {type(e).__name__}: {e}。"
            f"操作未生效，可再次發出指令重試。",
        )

    return {
        "status": "executed",
        "card_id": card.id,
        "tool_name": card.tool_name,
        "title": card.title,
        "result": _normalize_result(result),
    }


@router.post("/cancel/{card_id}")
async def cancel_card_endpoint(
    card_id: str,
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """取消（不執行）。"""
    ok = await cancel_card(card_id)
    if not ok:
        raise HTTPException(404, f"ConfirmCard {card_id} 不存在或已過期")
    log.info("ConfirmCard cancelled: %s by %s", card_id, user.employee_id)
    return {"status": "cancelled", "card_id": card_id}


def _normalize_result(result) -> dict | str:
    """把 SQLAlchemy model / pydantic model / dict 統一成可 JSON 序列化的 dict。"""
    # pydantic v2
    if hasattr(result, "model_dump"):
        try:
            return result.model_dump(mode="json")
        except Exception:
            pass
    # SQLAlchemy ORM
    if hasattr(result, "__table__"):
        return {
            c.name: _safe_value(getattr(result, c.name))
            for c in result.__table__.columns
        }
    if isinstance(result, dict):
        return result
    return str(result)


def _safe_value(v):
    """處理 datetime / UUID / Decimal 等讓 JSON 高興。"""
    from datetime import date, datetime
    from decimal import Decimal
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return str(v)
