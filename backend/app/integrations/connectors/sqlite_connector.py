"""SqliteConnector — 內建 PoC connector，主要用途：

  1. 測試外部 DB 整合框架（不需架設真實 SQL Server）
  2. 給「客戶用 Access / 自家 .db 檔」這種情境用
  3. 測試 smoke / integration test 的 fixture

注意：sqlite3 是同步 driver，但我們用 asyncio.to_thread 包成 async 介面。
正式 SqlServerConnector 用 pyodbc + aioodbc 走真 async。
"""
from __future__ import annotations

import asyncio
import sqlite3
from typing import Optional

from app.integrations.connectors.base import Connector, ConnectorMeta
from app.integrations.connectors.exceptions import (
    ConnectionTestFailed, TableNotFound,
)
from app.integrations.connectors.registry import register_connector


@register_connector(ConnectorMeta(
    name="sqlite",
    label="SQLite 檔案 DB",
    kind="sql",
    capabilities=["query", "list_tables", "schema_of", "stream"],
    config_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "SQLite 檔案絕對路徑"},
        },
        "required": ["path"],
    },
    description="連接 SQLite 檔案 DB。適合：客戶舊系統 export 出的 .db 檔、自家 Access 轉檔。",
))
class SqliteConnector(Connector):
    """SQLite 連接器。"""

    def _conn(self) -> sqlite3.Connection:
        """每次操作新開連線（thread-safe）。"""
        path = self.config["path"]
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    async def test_connection(self) -> bool:
        def _do():
            try:
                conn = self._conn()
                conn.execute("SELECT 1").fetchone()
                conn.close()
                return True
            except Exception as e:
                raise ConnectionTestFailed("sqlite", str(e))

        return await asyncio.to_thread(_do)

    async def list_tables(self) -> list[str]:
        def _do():
            conn = self._conn()
            cur = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
            tables = [r[0] for r in cur.fetchall()]
            conn.close()
            return tables

        return await asyncio.to_thread(_do)

    async def query(
        self,
        table: str,
        filters: Optional[dict] = None,
        limit: int = 100,
    ) -> list[dict]:
        # 安全防線：table 必在 whitelist
        available = await self.list_tables()
        if table not in available:
            raise TableNotFound(table, available)

        # limit clamp（防大查詢）
        limit = max(1, min(int(limit), 1000))

        def _do():
            conn = self._conn()
            sql = f'SELECT * FROM "{table}"'  # 雙引號保護識別碼
            params: list = []
            if filters:
                conditions = []
                for k, v in filters.items():
                    # 欄位名只允許 alphanumeric + underscore（防注入）
                    if not _is_safe_identifier(k):
                        raise ValueError(f"不安全的欄位名: {k!r}")
                    conditions.append(f'"{k}" = ?')
                    params.append(v)
                sql += " WHERE " + " AND ".join(conditions)
            sql += f" LIMIT {limit}"
            cur = conn.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows

        return await asyncio.to_thread(_do)


def _is_safe_identifier(s: str) -> bool:
    """欄位/表名只允許 [A-Za-z_][A-Za-z0-9_]* 防 injection。"""
    if not s:
        return False
    if not (s[0].isalpha() or s[0] == "_"):
        return False
    return all(c.isalnum() or c == "_" for c in s)
