"""CsvFolderConnector — 內建 PoC connector，用於：

  1. 客戶把 PO 批檔放在 sftp 資料夾，每 X 分鐘同步進來
  2. Excel 匯出 → 多個 CSV，當作多個 table 處理
  3. 廠商共用資料夾（如客戶 A 每天 09:00 丟訂單 CSV）

設計：每個 CSV 檔當成一個 table，檔名（去掉 .csv）= table name。
"""
from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from typing import Optional

from app.integrations.connectors.base import Connector, ConnectorMeta
from app.integrations.connectors.exceptions import (
    ConnectionTestFailed, TableNotFound,
)
from app.integrations.connectors.registry import register_connector


@register_connector(ConnectorMeta(
    name="csv_folder",
    label="CSV 資料夾",
    kind="file",
    capabilities=["query", "list_tables", "schema_of"],
    config_schema={
        "type": "object",
        "properties": {
            "folder": {"type": "string", "description": "CSV 資料夾絕對路徑"},
            "encoding": {"type": "string", "default": "utf-8",
                         "description": "CSV 編碼，預設 utf-8（big5 / cp950 可用於台灣舊系統）"},
        },
        "required": ["folder"],
    },
    description="連接 CSV 檔案資料夾。每個 .csv 檔當成一個 table。適合：廠商共用資料夾、Excel 匯出。",
))
class CsvFolderConnector(Connector):
    """CSV 資料夾連接器。"""

    @property
    def _folder(self) -> Path:
        return Path(self.config["folder"])

    @property
    def _encoding(self) -> str:
        return self.config.get("encoding", "utf-8")

    async def test_connection(self) -> bool:
        def _do():
            p = self._folder
            if not p.exists():
                raise ConnectionTestFailed("csv_folder", f"資料夾不存在: {p}")
            if not p.is_dir():
                raise ConnectionTestFailed("csv_folder", f"不是資料夾: {p}")
            return True

        return await asyncio.to_thread(_do)

    async def list_tables(self) -> list[str]:
        def _do():
            return sorted(f.stem for f in self._folder.glob("*.csv"))

        return await asyncio.to_thread(_do)

    async def query(
        self,
        table: str,
        filters: Optional[dict] = None,
        limit: int = 100,
    ) -> list[dict]:
        available = await self.list_tables()
        if table not in available:
            raise TableNotFound(table, available)

        limit = max(1, min(int(limit), 1000))

        def _do():
            path = self._folder / f"{table}.csv"
            rows: list[dict] = []
            with open(path, encoding=self._encoding, newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if filters:
                        # CSV 全是字串，比對時轉成 str
                        if not all(
                            r.get(k) == str(v) for k, v in filters.items()
                        ):
                            continue
                    rows.append(r)
                    if len(rows) >= limit:
                        break
            return rows

        return await asyncio.to_thread(_do)
