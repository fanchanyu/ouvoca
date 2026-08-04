"""External-DB connection registry — service-layer single source of truth.

v3.60 (G-510)：正式路徑全面改為 DB-backed + AES-256-GCM 加密儲存。
  - async DB 函式（工具 / API 使用）：
      register_connection_db / get_connection_info_db / list_connections_db /
      list_connection_names_db / unregister_connection_db / has_connection_db
  - 連線設定（config，含 DB 帳密）只以密文存 external_connections 表，
    記憶體/API 回傳皆不含明文（decrypt 只發生在實際建立 connector 時）。
  - 既有 sync 函式保留為 in-memory fallback（db=None 時使用），
    給舊測試 / scripts 向後相容；新程式碼請用 DB 版本。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_json, encrypt_json
from app.core.logging import get_logger

log = get_logger(__name__)


# ────────────────────────────────────────────────────────────
# In-memory fallback（僅供 db=None 的舊測試/scripts；正式走 DB）
# ────────────────────────────────────────────────────────────
_CONNECTIONS: dict[str, dict] = {}


def register_connection(name: str, connector: str, config: dict) -> dict:
    """[deprecated] in-memory 註冊（db=None 路徑 / 舊測試用）。"""
    _CONNECTIONS[name] = {"connector": connector, "config": dict(config)}
    log.info("Connection %s registered in-memory with %s", name, connector)
    return _CONNECTIONS[name]


def unregister_connection(name: str) -> bool:
    """[deprecated] in-memory 移除。"""
    removed = _CONNECTIONS.pop(name, None) is not None
    if removed:
        log.info("Connection %s removed (in-memory)", name)
    return removed


def get_connection_info(name: str) -> dict | None:
    """[deprecated] in-memory 取單一連接設定。"""
    info = _CONNECTIONS.get(name)
    return None if info is None else {"connector": info["connector"], "config": dict(info["config"])}


def list_connection_names() -> list[str]:
    """[deprecated] in-memory 名稱清單。"""
    return sorted(_CONNECTIONS.keys())


def list_connections() -> list[dict]:
    """[deprecated] in-memory metadata 清單（不含 config）。"""
    return [
        {"name": name, "connector": info["connector"], "config_keys": sorted(info["config"].keys())}
        for name, info in sorted(_CONNECTIONS.items())
    ]


def has_connection(name: str) -> bool:
    """[deprecated] in-memory 存在性檢查。"""
    return name in _CONNECTIONS


def _clear_for_test() -> None:
    """測試用：清空 in-memory store。生產禁用。"""
    _CONNECTIONS.clear()


# ────────────────────────────────────────────────────────────
# DB-backed API（v3.60 / G-510）— 工具與 API 的正式路徑
# ────────────────────────────────────────────────────────────

async def register_connection_db(
    db: AsyncSession,
    name: str,
    connector: str,
    config: dict,
    *,
    description: str | None = None,
    is_active: bool = True,
    user: dict | None = None,
) -> dict:
    """upsert 一個外部 DB 連接；config 以 AES-GCM 密文儲存。"""
    from app.core.tenant_context import get_current_tenant
    from app.models.external_connection import ExternalConnection

    row = (await db.execute(
        select(ExternalConnection).where(ExternalConnection.name == name)
    )).scalar_one_or_none()
    if row is None:
        row = ExternalConnection(
            name=name,
            connector=connector,
            config_encrypted=encrypt_json(config),
            description=description,
            is_active=is_active,
            tenant_id=get_current_tenant() or "HQ",
            created_by=(user or {}).get("employee_id"),
        )
        db.add(row)
    else:
        row.connector = connector
        row.config_encrypted = encrypt_json(config)
        row.description = description
        row.is_active = is_active
    await db.commit()
    await db.refresh(row)
    log.info("External connection %s saved (encrypted) connector=%s", name, connector)
    return {"name": row.name, "connector": row.connector, "is_active": row.is_active}


async def get_connection_info_db(db: AsyncSession, name: str) -> dict | None:
    """取單一連接設定（解密後）。回 None = 不存在或已停用。"""
    from app.models.external_connection import ExternalConnection

    row = (await db.execute(
        select(ExternalConnection).where(ExternalConnection.name == name)
    )).scalar_one_or_none()
    if row is None or not row.is_active:
        return None
    try:
        config = decrypt_json(row.config_encrypted)
    except Exception as exc:
        log.error("Cannot decrypt connection %s: %s", name, exc)
        return None
    return {"connector": row.connector, "config": dict(config)}


async def list_connections_db(db: AsyncSession) -> list[dict]:
    """列出所有連接 metadata（含 connector 類型、不含 config 明文）。"""
    from app.models.external_connection import ExternalConnection

    rows = (await db.execute(
        select(ExternalConnection).order_by(ExternalConnection.name)
    )).scalars().all()
    out = []
    for row in rows:
        try:
            config_keys = sorted(decrypt_json(row.config_encrypted).keys())
        except Exception:
            config_keys = ["<undecryptable>"]
        out.append({
            "name": row.name,
            "connector": row.connector,
            "config_keys": config_keys,
            "is_active": row.is_active,
            "description": row.description,
        })
    return out


async def list_connection_names_db(db: AsyncSession) -> list[str]:
    """列出所有連接名稱（不含 config，給 LLM 看安全）。"""
    from app.models.external_connection import ExternalConnection

    rows = (await db.execute(
        select(ExternalConnection.name).order_by(ExternalConnection.name)
    )).scalars().all()
    return list(rows)


async def has_connection_db(db: AsyncSession, name: str) -> bool:
    """存在且啟用？"""
    return await get_connection_info_db(db, name) is not None


async def unregister_connection_db(db: AsyncSession, name: str) -> bool:
    """刪除（硬刪）一個連接。回 True 表示確實刪除過。"""
    from app.models.external_connection import ExternalConnection

    row = (await db.execute(
        select(ExternalConnection).where(ExternalConnection.name == name)
    )).scalar_one_or_none()
    if row is None:
        return False
    await db.delete(row)
    await db.commit()
    log.info("External connection %s deleted", name)
    return True
