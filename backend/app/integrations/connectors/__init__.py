"""外部資料庫串接（External DB Connectors）— v3.1 戰略補強。

設計：see docs/EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md

匯入此 package 自動註冊內建 connector：
  - SqliteConnector
  - CsvFolderConnector
"""
from app.integrations.connectors.base import Connector, ConnectorMeta
from app.integrations.connectors.registry import (
    register_connector, get_connector,
    list_connectors, get_connector_meta,
)
from app.integrations.connectors.exceptions import (
    ConnectorError, ConnectionTestFailed, TableNotFound,
    SchemaIncompatible,
)

# 內建 connector：import 即註冊
from app.integrations.connectors import sqlite_connector  # noqa: F401
from app.integrations.connectors import csv_connector  # noqa: F401

__all__ = [
    "Connector", "ConnectorMeta",
    "register_connector", "get_connector",
    "list_connectors", "get_connector_meta",
    "ConnectorError", "ConnectionTestFailed",
    "TableNotFound", "SchemaIncompatible",
]
