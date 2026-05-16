"""External-DB connection registry — service-layer single source of truth (v3.8).

設計（v3.8 fix #4）：
  之前 `agents/domains/external_db_tools._CONNECTIONS` 是模組私有 dict，
  其它模組（migration_tools）伸手進去讀，破壞封裝。

  現在 connection 設定移到 service layer。
  agent / tool 只透過此處公開 API 操作，不該直接讀 dict。

長期方向（per user 2026-05-15 audit decision）：
  全面 stateless — 此 store 之後會換成 DB-backed `external_connection` 表
  ＋ AES-256 加密 config 欄位。介面（list / get / register / unregister）保持，
  只換實作即可，下游 caller 零改動。
"""
from __future__ import annotations

from typing import Optional

from app.core.logging import get_logger

log = get_logger(__name__)


# ────────────────────────────────────────────────────────────
# In-memory store（之後會被 DB-backed 取代，但 API 不變）
# ────────────────────────────────────────────────────────────
#
# 結構：{
#   "legacy_dingxin": {"connector": "sqlite", "config": {"path": "/data/dingxin.db"}},
#   "customer_a_csv": {"connector": "csv_folder", "config": {"folder": "D:/orders"}},
# }
_CONNECTIONS: dict[str, dict] = {}


def register_connection(name: str, connector: str, config: dict) -> dict:
    """註冊（或覆寫）一個外部 DB 連接。"""
    _CONNECTIONS[name] = {"connector": connector, "config": dict(config)}
    log.info("Connection %s registered with %s", name, connector)
    return _CONNECTIONS[name]


def unregister_connection(name: str) -> bool:
    """移除連接。回 True 表示確實有移除過。"""
    removed = _CONNECTIONS.pop(name, None) is not None
    if removed:
        log.info("Connection %s removed", name)
    return removed


def get_connection_info(name: str) -> Optional[dict]:
    """取單一連接設定 — 給 migration_tools 等需要還原 connector 用。

    回 dict 的 copy 以避免 caller 不小心 mutate。
    """
    info = _CONNECTIONS.get(name)
    return None if info is None else {"connector": info["connector"], "config": dict(info["config"])}


def list_connection_names() -> list[str]:
    """列出所有已設定連接的名字（不含 config，給 LLM 看安全）。"""
    return sorted(_CONNECTIONS.keys())


def list_connections() -> list[dict]:
    """列出所有連接 metadata（含 connector 類型、不含 config 內容）。"""
    return [
        {
            "name": name,
            "connector": info["connector"],
            "config_keys": sorted(info["config"].keys()),
        }
        for name, info in sorted(_CONNECTIONS.items())
    ]


def has_connection(name: str) -> bool:
    return name in _CONNECTIONS


def _clear_for_test() -> None:
    """測試用：清空 store。生產禁用。"""
    _CONNECTIONS.clear()
