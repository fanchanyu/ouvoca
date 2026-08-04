"""External DB connections management API (v3.60 / G-510).

讓「外部資料庫整合」不必只能靠程式註冊：
  GET    /api/external-connections            — 列表（metadata，無明文 config）
  POST   /api/external-connections            — 新增/更新（config 加密儲存）
  DELETE /api/external-connections/{name}     — 刪除

權限：external_db.connection.list / external_db.connection.write
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import UserContext, require_permission
from app.services.connections import (
    get_connection_info_db,
    list_connections_db,
    register_connection_db,
    unregister_connection_db,
)

router = APIRouter(prefix="/api/external-connections", tags=["ExternalConnections"])


class ExternalConnectionUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    connector: str = Field(min_length=1, max_length=50)
    config: dict = Field(description="連線設定（敏感值會加密儲存）")
    description: str | None = None
    is_active: bool = True


@router.get("")
async def list_external_connections(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("external_db.connection.list")),
):
    conns = await list_connections_db(db)
    return {"total": len(conns), "connections": conns}


@router.post("")
async def upsert_external_connection(
    data: ExternalConnectionUpsert,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("external_db.connection.write")),
):
    saved = await register_connection_db(
        db,
        data.name,
        data.connector,
        data.config,
        description=data.description,
        is_active=data.is_active,
        user={"employee_id": user.employee_id},
    )
    return saved


@router.delete("/{name}")
async def delete_external_connection(
    name: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("external_db.connection.write")),
):
    info = await get_connection_info_db(db, name)
    if info is None:
        raise HTTPException(404, f"連接不存在或已停用: {name}")
    ok = await unregister_connection_db(db, name)
    return {"deleted": ok, "name": name}
