"""Connector 介面契約 + ConnectorMeta dataclass。

設計原則（v3.1）：
  1. read-only by default — 子類預設只實作讀取
  2. table whitelist — query 必先過 list_tables 驗證
  3. filters 參數化 — 子類用 prepared statement，禁止字串拼接
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


@dataclass
class ConnectorMeta:
    """Connector 後設資料（用 @register_connector 註冊）。"""

    name: str                       # 內部名稱（lowercase, snake_case）：sqlite / csv_folder / sql_server
    label: str                      # 顯示名稱：SQLite 檔案 DB / SQL Server (鼎新/正航)
    kind: str                       # "sql" | "rest" | "file"
    capabilities: list[str] = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)  # JSON schema for connection config UI
    description: str = ""


class Connector(ABC):
    """所有外部 DB connector 的 base class。

    子類負責：
      - 連線管理（test_connection）
      - 結構探索（list_tables / schema_of）
      - 安全查詢（query）

    子類不應實作的寫入操作 — 那走 service 層 + ConfirmCard。
    """

    meta: ConnectorMeta = None  # 由 @register_connector 在類別上 set

    def __init__(self, config: dict):
        """config: 連線設定（host/port/user/password/path/...），由 register_connection 傳入。"""
        self.config = config

    @abstractmethod
    async def test_connection(self) -> bool:
        """測試連線可達。失敗應 raise ConnectionTestFailed（含原因）。"""
        ...

    @abstractmethod
    async def list_tables(self) -> list[str]:
        """列出可查詢的 table（將作為 query 的 whitelist）。"""
        ...

    @abstractmethod
    async def query(
        self,
        table: str,
        filters: Optional[dict] = None,
        limit: int = 100,
    ) -> list[dict]:
        """查詢某 table。

        強制契約：
          - table 必在 list_tables() 結果中（否則 raise TableNotFound）
          - filters 為 dict {col: value}，子類用 prepared statement
          - limit ≤ 1000（避免大查詢拖死）
          - 回傳 list[dict]，欄位名照外部 DB 原樣（mapping 在 tool 層做）
        """
        ...

    async def schema_of(self, table: str) -> list[dict]:
        """回傳某 table 的欄位 schema（給 AI mapping 推薦用）。

        預設實作：query 1 筆推測欄位 + 類型；子類可 override 走 metadata 表更精確。
        """
        rows = await self.query(table, limit=1)
        if not rows:
            return []
        sample = rows[0]
        return [
            {
                "name": k,
                "type": type(v).__name__ if v is not None else "unknown",
                "nullable": True,
            }
            for k, v in sample.items()
        ]

    async def stream(
        self,
        table: str,
        batch_size: int = 1000,
    ) -> AsyncIterator[list[dict]]:
        """串流查詢（給 migration / sync 用）。

        預設實作：循環呼叫 query() 分頁。子類可 override 走 cursor 更高效。
        """
        # PoC 階段先用 limit + offset 簡化；正式版要走 cursor / keyset
        offset = 0
        while True:
            # NOTE: 預設 query 不支援 offset，子類要支援才能用 stream
            batch = await self.query(table, limit=batch_size)
            if not batch:
                break
            yield batch
            if len(batch) < batch_size:
                break
            offset += batch_size
