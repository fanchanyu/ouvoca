"""System settings API (M1-3)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import UserContext, require_permission
from app.services.system_settings import get_setting, list_settings, set_setting

router = APIRouter(prefix="/api/system", tags=["SystemSettings"])


class SettingUpsert(BaseModel):
    value: Any
    group: str | None = Field(default=None, max_length=40)
    description: str | None = Field(default=None, max_length=200)


@router.get("/settings")
async def get_all_settings(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.config.read")),
):
    return {"total": len(await list_settings(db)), "settings": await list_settings(db)}


@router.get("/settings/{key}")
async def get_one_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.config.read")),
):
    value = await get_setting(db, key)
    return {"key": key, "value": value}


@router.put("/settings/{key}")
async def put_setting(
    key: str,
    data: SettingUpsert,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("system.config.update")),
):
    row = await set_setting(
        db, key, data.value,
        group=data.group, description=data.description,
        updated_by=user.employee_id,
    )
    return {"key": row.key, "value": row.value, "group": row.group}
