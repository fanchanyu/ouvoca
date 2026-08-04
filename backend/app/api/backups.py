"""備份管理 API（審計 P1-7）— 建立 / 列出 / 刪除 / 還原。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_db
from app.core.security import UserContext, require_permission
from app.services import backup as backup_svc
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/system/backups", tags=["Backups"])


@router.get("")
async def list_backups(
    user: UserContext = Depends(require_permission("system.backup.read")),
):
    return {"total": len(backup_svc.list_backups()), "backups": backup_svc.list_backups()}


@router.post("")
async def create_backup(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.backup.create")),
):
    result = await backup_svc.create_backup(db, reason=f"api:{user.employee_id}")
    if not result["created"]:
        raise HTTPException(400, result["reason"])
    return result


@router.delete("/{name}")
async def delete_backup(
    name: str,
    user: UserContext = Depends(require_permission("system.backup.create")),
):
    ok = backup_svc.delete_backup(name)
    if not ok:
        raise HTTPException(404, f"備份不存在：{name}")
    return {"deleted": True, "name": name}


@router.post("/{name}/restore")
async def restore_backup(
    name: str,
    confirm: bool = False,
    user: UserContext = Depends(require_permission("system.backup.restore")),
):
    """還原備份（**破壞性**：覆蓋現行 DB，需 confirm=true）。"""
    if not confirm:
        raise HTTPException(
            400,
            "還原會覆蓋現行資料庫且不可逆。請確認後以 ?confirm=true 再次呼叫。",
        )
    result = backup_svc.restore_backup(name)
    if not result["restored"]:
        raise HTTPException(400, result["reason"])
    return result
