"""Files / Attachment API（Sprint E v3.13）— 通用檔案上傳。

Endpoints:
  POST   /api/files/upload          multipart 上傳，回 Attachment
  GET    /api/files                 列出（可選 ?category=quote）
  GET    /api/files/{id}            檔案 metadata
  GET    /api/files/{id}/download   下載
  DELETE /api/files/{id}            刪除（含 disk 上的 file）

設計：
  - 檔案存 backend/uploads/{tenant_id}/{yyyy-mm}/{uuid}_{filename}
  - 不存進 DB（避免 BLOB 膨脹）
  - 容量上限：每檔 25 MB（可由 settings.MAX_UPLOAD_MB 調）
  - 副檔名白名單：pdf, xlsx, xls, csv, jpg, png, docx
  - permission：上傳 ai.agent.use；刪除 system.config.update（避免使用者亂刪別人的）
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.logging import get_logger
from app.core.security import UserContext, require_permission
from app.models.attachment import ATTACHMENT_CATEGORIES, Attachment

log = get_logger(__name__)
router = APIRouter(prefix="/api/files", tags=["Files"])


# ── 設定 ─────────────────────────────────────────────────────
MAX_BYTES = 25 * 1024 * 1024   # 25 MB
ALLOWED_EXTS = frozenset({".pdf", ".xlsx", ".xls", ".csv", ".jpg", ".jpeg", ".png", ".docx", ".txt"})
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


def _safe_filename(name: str) -> str:
    """去掉路徑分隔符 / null byte / 控制字元，限 200 字元。"""
    cleaned = "".join(c for c in name if c.isprintable() and c not in '/\\\x00')
    return cleaned.replace("..", "_").strip()[:200] or "unnamed"


def _validate_ext(filename: str) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            400,
            f"檔案類型不支援：{ext or '無副檔名'}。"
            f"允許：{', '.join(sorted(ALLOWED_EXTS))}",
        )


# ── Schemas ─────────────────────────────────────────────────
class AttachmentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    category: str
    description: Optional[str]
    uploaded_by: Optional[str]
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ── Endpoints ──────────────────────────────────────────────
@router.post("/upload", response_model=AttachmentResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """上傳檔案（multipart/form-data）。

    Body fields:
      - file (binary, required)
      - category (str, default 'general'; quote / invoice / po / spec / contract / general)
      - description (str, optional)
    """
    if category not in ATTACHMENT_CATEGORIES:
        raise HTTPException(400, f"category 不合法。允許：{sorted(ATTACHMENT_CATEGORIES)}")

    raw_name = file.filename or "unnamed"
    safe_name = _safe_filename(raw_name)
    _validate_ext(safe_name)

    # 讀檔（同時防超大檔）
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(413, f"檔案太大：{len(content) // 1024 // 1024} MB（上限 25 MB）")
    if len(content) == 0:
        raise HTTPException(400, "檔案為空")

    # 算目錄：uploads/{tenant_id}/{yyyy-mm}/
    tenant_id = (user.tenant_id or "HQ") if hasattr(user, "tenant_id") else "HQ"
    yyyy_mm = datetime.now(UTC).strftime("%Y-%m")
    sub_dir = UPLOADS_DIR / tenant_id / yyyy_mm
    sub_dir.mkdir(parents=True, exist_ok=True)

    att_id = str(uuid.uuid4())
    disk_filename = f"{att_id}_{safe_name}"
    disk_path = sub_dir / disk_filename
    rel_path = f"{tenant_id}/{yyyy_mm}/{disk_filename}"

    # 寫磁碟
    disk_path.write_bytes(content)

    # 寫 DB
    att = Attachment(
        id=att_id,
        filename=safe_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        file_path=rel_path,
        category=category,
        description=description,
        uploaded_by=getattr(user, "user_id", None) or getattr(user, "employee_id", None),
        uploaded_at=datetime.now(UTC).replace(tzinfo=None),
        parsed_status="pending",
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)

    log.info("File uploaded: %s (%d bytes, %s) by %s",
             safe_name, len(content), category, getattr(user, "username", "?"))

    return att


@router.get("", response_model=list[AttachmentResponse])
async def list_files(
    category: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    """列出附件。可選 ?category=quote 過濾。"""
    q = select(Attachment).order_by(Attachment.uploaded_at.desc()).limit(min(limit, 500))
    if category:
        if category not in ATTACHMENT_CATEGORIES:
            raise HTTPException(400, f"category 不合法：{category}")
        q = q.where(Attachment.category == category)
    rows = (await db.execute(q)).scalars().all()
    return rows


@router.get("/{file_id}", response_model=AttachmentResponse)
async def get_file_meta(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    att = (await db.execute(select(Attachment).where(Attachment.id == file_id))).scalar_one_or_none()
    if not att:
        raise HTTPException(404, "檔案不存在")
    return att


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("ai.agent.use")),
):
    att = (await db.execute(select(Attachment).where(Attachment.id == file_id))).scalar_one_or_none()
    if not att:
        raise HTTPException(404, "檔案不存在")
    disk_path = UPLOADS_DIR / att.file_path
    if not disk_path.exists():
        log.error("Attachment %s 在 DB 但 disk 不見：%s", file_id, disk_path)
        raise HTTPException(410, "檔案實體已遺失（DB 記錄存在但磁碟檔不見）")
    return FileResponse(
        path=str(disk_path),
        filename=att.filename,
        media_type=att.content_type,
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.config.update")),
):
    """刪除（同時清掉 disk 上的檔）。"""
    att = (await db.execute(select(Attachment).where(Attachment.id == file_id))).scalar_one_or_none()
    if not att:
        raise HTTPException(404, "檔案不存在")
    disk_path = UPLOADS_DIR / att.file_path
    try:
        if disk_path.exists():
            disk_path.unlink()
    except OSError as exc:
        log.warning("刪除 disk 檔失敗 %s: %s（DB 記錄仍會清掉）", disk_path, exc)
    await db.execute(delete(Attachment).where(Attachment.id == file_id))
    await db.commit()
    log.info("File deleted: %s by %s", att.filename, getattr(user, "username", "?"))
    return {"deleted": True, "id": file_id}
