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
from app.core.logging import get_logger
from app.core.security import UserContext, require_permission
from app.services.email_digest import build_digest, send_email

log = get_logger(__name__)

router = APIRouter(prefix="/api/email-digest", tags=["EmailDigest"])


# 預設允許寄出的 email domain（之後可改成從 tenant 設定載入）
_ALLOWED_EMAIL_DOMAINS = {"example.com", "ouvoca.com", "llm-erp.local"}


def _is_external_email(addr: str) -> bool:
    """簡易判斷：domain 不在白名單即視為外部。"""
    if "@" not in addr:
        return True
    domain = addr.rsplit("@", 1)[1].strip().lower()
    return domain not in _ALLOWED_EMAIL_DOMAINS


@router.get("/preview")
async def preview_digest(
    period_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """看當下摘要（JSON）— 給前端 preview 用。"""
    d = await build_digest(db, recipient=user.employee_id, period_hours=period_hours)
    return d.to_dict()


@router.get("/preview.html", response_class=HTMLResponse)
async def preview_digest_html(
    period_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """看 HTML 版本（給 admin 預覽長相）。"""
    d = await build_digest(db, recipient=user.employee_id, period_hours=period_hours)
    return HTMLResponse(d.to_html())


@router.post("/send")
async def send_digest(
    to: str,
    period_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """真寄摘要 email。SMTP 沒設則 dry_run。"""
    if "@" not in to:
        raise HTTPException(400, f"無效的 email 地址: {to!r}")
    # 外部 email 警告（F-3 防資料外洩 audit log）
    if _is_external_email(to):
        log.warning(
            "email_digest external recipient: user_id=%s employee_id=%s to=%s",
            user.user_id, user.employee_id, to,
        )
    d = await build_digest(db, recipient=to, period_hours=period_hours)
    subject = f"[LLM-ERP] {d.period_label}摘要：{d.summary_line[:30]}"
    result = send_email(
        to=to, subject=subject,
        html=d.to_html(), text=d.to_markdown(),
    )
    return {**result, "period_hours": period_hours, "digest_summary": d.summary_line}
