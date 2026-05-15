"""Email digest API — preview / send / today（v3.5 MVP #4 收尾）。

Endpoints:
  GET  /api/email-digest/preview        — 看當下摘要內容（JSON）
  GET  /api/email-digest/preview.html   — 看 HTML 版本（給 admin 預覽長相）
  POST /api/email-digest/send           — 真寄（若 SMTP 沒設則 dry_run）
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import UserContext, require_permission
from app.services.email_digest import build_digest, send_email

router = APIRouter(prefix="/api/email-digest", tags=["EmailDigest"])


@router.get("/preview")
async def preview_digest(
    period_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """看當下摘要（JSON）— 給前端 preview 用。"""
    d = await build_digest(db, recipient=user.employee_id, period_hours=period_hours)
    return d.to_dict()


@router.get("/preview.html", response_class=HTMLResponse)
async def preview_digest_html(
    period_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """看 HTML 版本（給 admin 預覽長相）。"""
    d = await build_digest(db, recipient=user.employee_id, period_hours=period_hours)
    return HTMLResponse(d.to_html())


@router.post("/send")
async def send_digest(
    to: str,
    period_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """真寄摘要 email。SMTP 沒設則 dry_run。"""
    if "@" not in to:
        raise HTTPException(400, f"無效的 email 地址: {to!r}")
    d = await build_digest(db, recipient=to, period_hours=period_hours)
    subject = f"[LLM-ERP] {d.period_label}摘要：{d.summary_line[:30]}"
    result = send_email(
        to=to, subject=subject,
        html=d.to_html(), text=d.to_markdown(),
    )
    return {**result, "period_hours": period_hours, "digest_summary": d.summary_line}
