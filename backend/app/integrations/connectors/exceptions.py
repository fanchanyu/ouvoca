"""Connector 例外類別。

對應 docs/EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md §4.3 安全防線。
"""


class ConnectorError(Exception):
    """所有 connector 相關錯誤的 base。"""


class ConnectionTestFailed(ConnectorError):
    """test_connection() 失敗。"""

    def __init__(self, connector: str, reason: str):
        self.connector = connector
        self.reason = reason
        super().__init__(f"連線失敗 ({connector}): {reason}")


class TableNotFound(ConnectorError):
    """query/schema_of 指定的 table 不在 list_tables 結果中（防 SQL injection）。"""

    def __init__(self, table: str, available: list[str]):
        self.table = table
        self.available = available
        super().__init__(
            f"找不到 table: {table!r}。可用 tables: {available[:10]}"
            + ("..." if len(available) > 10 else "")
        )


class SchemaIncompatible(ConnectorError):
    """Schema mapping 無法自動推薦（confidence 太低）。"""

    def __init__(self, source_table: str, target_domain: str, reason: str):
        self.source_table = source_table
        self.target_domain = target_domain
        super().__init__(
            f"無法自動 mapping {source_table!r} → {target_domain!r}: {reason}"
        )
