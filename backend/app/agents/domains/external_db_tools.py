"""ExternalDbAgent — 跨資料庫對話 tool（v3.1 戰略補強）。

讓 AI 對話直接查外部 DB（Federated Query）：
  - 王董：「鼎新 5 月份訂單?」→ 走 query_external_db
  - 阿玲：「鼎新有哪些 table?」→ 走 list_external_tables
  - 任何：「我設了哪些連接?」→ 走 list_external_connections

設計：see docs/EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md §5
"""
from __future__ import annotations

from app.agents.engine import register_agent
from app.agents.registry import register_tool, RiskTier, Slot
from app.integrations.connectors import (
    get_connector, list_connectors,
)
from app.integrations.connectors.exceptions import ConnectorError
# v3.8 fix #4：connection store 移到 service layer
from app.services.connections import (
    get_connection_info, list_connections as _svc_list_connections,
    register_connection, unregister_connection,
)


# v3.8 後向相容：保留 _CONNECTIONS 名稱給既有測試 import，
# 但實際讀寫透過 service layer。下次 sprint 移除這個 alias。
class _ConnectionsAlias:
    """Read-only mapping proxy 指向 services.connections._CONNECTIONS。

    保留是為了既有測試（test_connectors.py / test_schema_mapping.py /
    demo_crud_pipeline.py / demo_deepseek_e2e.py）的 `_CONNECTIONS.clear()`
    呼叫不破。長期應改成呼叫 `services.connections._clear_for_test()`。
    """
    def clear(self):
        from app.services.connections import _clear_for_test
        _clear_for_test()

    def __contains__(self, name):
        from app.services.connections import has_connection
        return has_connection(name)

    def keys(self):
        from app.services.connections import list_connection_names
        return list_connection_names()

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        from app.services.connections import list_connection_names
        return len(list_connection_names())


_CONNECTIONS = _ConnectionsAlias()


def _connections_snapshot() -> dict[str, dict]:
    """測試用：取得目前所有連接的 snapshot。"""
    from app.services.connections import _CONNECTIONS as _svc
    return dict(_svc)


# ============================================================
# Tool 1: list_external_connections
# ============================================================

@register_tool(
    name="list_external_connections",
    domain="external_db",
    risk_tier=RiskTier.READ,
    description="列出目前已設定的所有外部 DB 連接。",
    slots=[],
    required_permission="external_db.connection.list",
)
async def _list_connections(db, user):
    conns = _svc_list_connections()
    return {
        "total": len(conns),
        "connections": conns,
        "available_connectors": [
            {"name": m.name, "label": m.label, "kind": m.kind}
            for m in list_connectors()
        ],
    }


# ============================================================
# Tool 2: list_external_tables
# ============================================================

@register_tool(
    name="list_external_tables",
    domain="external_db",
    risk_tier=RiskTier.READ,
    description="列出某外部 DB 連接的所有 table / sheet / file（供 AI mapping 推薦用）。",
    slots=[
        Slot("connection", "string", required=True,
             description="連接名稱（如 legacy_dingxin / customer_a_csv）"),
    ],
    required_permission="external_db.table.list",
)
async def _list_external_tables(db, user, connection: str):
    info = get_connection_info(connection)
    if info is None:
        from app.services.connections import list_connection_names
        return {
            "error": f"連接不存在: {connection!r}",
            "available": list_connection_names(),
        }
    try:
        conn = get_connector(info["connector"], info["config"])
        tables = await conn.list_tables()
        return {
            "connection": connection,
            "connector": info["connector"],
            "total": len(tables),
            "tables": tables,
        }
    except ConnectorError as e:
        return {"error": str(e), "connection": connection}


# ============================================================
# Tool 3: query_external_db
# ============================================================

@register_tool(
    name="query_external_db",
    domain="external_db",
    risk_tier=RiskTier.READ,
    description=(
        "跨資料庫查詢：對外部 DB 的某 table 做 filter + limit 查詢。"
        "支援場景：『鼎新 5 月份訂單金額多少』、『客戶 A 的 CSV 裡有幾筆 PO』。"
    ),
    slots=[
        Slot("connection", "string", required=True,
             description="連接名稱（如 legacy_dingxin）"),
        Slot("table", "string", required=True,
             description="外部 table 名稱（先用 list_external_tables 查可用值）"),
        Slot("filters", "object", required=False,
             description='WHERE 條件 dict，如 {"customer_no": "C001", "status": "active"}'),
        Slot("limit", "integer", required=False,
             description="回傳筆數上限（預設 100、最大 1000）"),
    ],
    required_permission="external_db.query",
)
async def _query_external_db(
    db, user,
    connection: str, table: str,
    filters: dict | None = None, limit: int = 100,
):
    info = get_connection_info(connection)
    if info is None:
        from app.services.connections import list_connection_names
        return {
            "error": f"連接不存在: {connection!r}",
            "available": list_connection_names(),
        }
    try:
        conn = get_connector(info["connector"], info["config"])
        rows = await conn.query(table, filters=filters, limit=limit)
        return {
            "connection": connection,
            "connector": info["connector"],
            "table": table,
            "filters": filters,
            "limit": limit,
            "total": len(rows),
            "rows": rows,
        }
    except ConnectorError as e:
        return {
            "error": str(e),
            "connection": connection, "table": table,
        }


# ============================================================
# Agent 註冊
# ============================================================

register_agent(
    "external_db", "ExternalDbAgent",
    system_prompt=(
        "你是 ERP 外部資料庫整合助手。職責：\n"
        "1. 幫使用者查詢已連接的外部 DB（鼎新 / 正航 / 自家 SQL / Excel CSV）\n"
        "2. 列出可用連接、可用 table\n"
        "3. 跨 DB 比對數字（如「鼎新訂單 vs LLM-ERP 訂單」）\n\n"
        "重要原則：\n"
        "- 查詢前先用 list_external_connections 確認連接存在\n"
        "- 不知道 table 名稱時先用 list_external_tables 列出\n"
        "- 結果筆數多時用 filters 縮小範圍，不要硬拉 1000 筆\n"
        "- 使用繁體中文回覆"
    ),
    tool_names=[
        "list_external_connections",
        "list_external_tables",
        "query_external_db",
    ],
)
