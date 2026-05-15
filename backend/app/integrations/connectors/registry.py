"""Connector registry — 用 @register_connector decorator 註冊各種外部 DB 適配器。

範例：
    @register_connector(ConnectorMeta(
        name="sqlite",
        label="SQLite 檔案 DB",
        kind="sql",
        capabilities=["query", "list_tables", "stream"],
        config_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    ))
    class SqliteConnector(Connector):
        ...

之後：
    conn = get_connector("sqlite", {"path": "/data/legacy.db"})
    rows = await conn.query("customer", limit=10)
"""
from __future__ import annotations

from typing import Type

from app.integrations.connectors.base import Connector, ConnectorMeta


# 內部註冊表
_REGISTRY: dict[str, Type[Connector]] = {}


def register_connector(meta: ConnectorMeta):
    """Decorator：把 Connector 子類加入 registry。"""

    def deco(cls: Type[Connector]):
        # Basic validation
        if not issubclass(cls, Connector):
            raise TypeError(f"{cls.__name__} 必須繼承 Connector")
        if meta.name in _REGISTRY:
            existing = _REGISTRY[meta.name]
            if existing is not cls:  # 允許重複註冊同一類（hot-reload 友善）
                raise ValueError(
                    f"Connector {meta.name!r} 已被 {existing.__name__} 註冊，無法覆寫成 {cls.__name__}"
                )
        cls.meta = meta
        _REGISTRY[meta.name] = cls
        return cls

    return deco


def get_connector(name: str, config: dict) -> Connector:
    """取得 connector 實例。

    raises:
        KeyError — 未註冊的 connector name
    """
    if name not in _REGISTRY:
        raise KeyError(
            f"未知的 connector: {name!r}。已註冊：{sorted(_REGISTRY)}"
        )
    return _REGISTRY[name](config)


def list_connectors() -> list[ConnectorMeta]:
    """列出已註冊的 connector（給前端「Add Connection」UI 用）。"""
    return [cls.meta for cls in _REGISTRY.values()]


def get_connector_meta(name: str) -> ConnectorMeta:
    """取單一 connector 的後設資料。"""
    if name not in _REGISTRY:
        raise KeyError(f"未知的 connector: {name!r}")
    return _REGISTRY[name].meta


def _clear_registry_for_test():
    """測試用：清空 registry。生產環境不該呼叫。"""
    _REGISTRY.clear()
