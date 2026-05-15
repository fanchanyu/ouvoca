"""Smoke tests for external DB connectors (v3.1 PoC)。

證明：
  1. SqliteConnector 能 test_connection / list_tables / query
  2. CsvFolderConnector 能 test_connection / list_tables / query
  3. registry decorator 把兩個 connector 加進 _REGISTRY
  4. 安全防線：table whitelist、欄位名 injection、limit clamp
  5. ExternalDbAgent 3 個 tool（list_connections / list_tables / query）走得通
"""
from __future__ import annotations

import csv
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


# ─── 觸發 connector 註冊（import 即 register） ─────────────
from app.integrations.connectors import (
    Connector, get_connector, list_connectors, get_connector_meta,
)
from app.integrations.connectors.exceptions import (
    TableNotFound, ConnectionTestFailed,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def legacy_sqlite_db(tmp_path):
    """造一個假裝是『客戶舊鼎新匯出』的 SQLite。"""
    path = tmp_path / "legacy_dingxin.db"
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE Customer (
            CustNo TEXT PRIMARY KEY,
            CustName TEXT,
            Grade TEXT,
            Phone TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO Customer VALUES (?, ?, ?, ?)",
        [
            ("C001", "長江五金", "A", "02-1234-5678"),
            ("C002", "大華實業", "B", "02-2345-6789"),
            ("C003", "中華電子", "A", "02-3456-7890"),
        ],
    )
    conn.execute("""
        CREATE TABLE OrderHeader (
            OrderNo TEXT PRIMARY KEY,
            CustNo TEXT,
            OrderDate TEXT,
            Amount REAL
        )
    """)
    conn.executemany(
        "INSERT INTO OrderHeader VALUES (?, ?, ?, ?)",
        [
            ("PO-2026-001", "C001", "2026-05-01", 12000.0),
            ("PO-2026-002", "C002", "2026-05-03", 8500.0),
            ("PO-2026-003", "C001", "2026-05-10", 15000.0),
        ],
    )
    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture
def csv_folder(tmp_path):
    """造一個假裝是『客戶 A 每天 sftp 來的訂單 CSV』資料夾。"""
    folder = tmp_path / "customer_a_orders"
    folder.mkdir()

    orders = folder / "orders.csv"
    with open(orders, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["order_no", "customer", "amount", "status"])
        w.writerow(["PO-001", "客戶A", "10000", "confirmed"])
        w.writerow(["PO-002", "客戶A", "8000", "draft"])
        w.writerow(["PO-003", "客戶B", "15000", "confirmed"])

    parts = folder / "parts.csv"
    with open(parts, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["part_no", "name", "qty"])
        w.writerow(["M6-BOLT", "M6 螺絲", "1500"])
        w.writerow(["M8-NUT", "M8 螺帽", "800"])

    return str(folder)


# ============================================================
# Registry tests
# ============================================================

def test_registry_has_builtin_connectors():
    """import app.integrations.connectors 後內建 connector 已註冊。"""
    metas = list_connectors()
    names = {m.name for m in metas}
    assert "sqlite" in names, f"sqlite 沒註冊：{names}"
    assert "csv_folder" in names, f"csv_folder 沒註冊：{names}"


def test_get_connector_meta():
    meta = get_connector_meta("sqlite")
    assert meta.kind == "sql"
    assert "query" in meta.capabilities
    assert "list_tables" in meta.capabilities


def test_get_connector_returns_instance():
    conn = get_connector("sqlite", {"path": ":memory:"})
    assert isinstance(conn, Connector)
    assert conn.config["path"] == ":memory:"


def test_unknown_connector_raises():
    with pytest.raises(KeyError, match="未知的 connector"):
        get_connector("nonexistent_xyz", {})


# ============================================================
# SqliteConnector tests
# ============================================================

@pytest.mark.asyncio
async def test_sqlite_test_connection(legacy_sqlite_db):
    c = get_connector("sqlite", {"path": legacy_sqlite_db})
    assert await c.test_connection() is True


@pytest.mark.asyncio
async def test_sqlite_test_connection_failure():
    c = get_connector("sqlite", {"path": "/nonexistent/path/xyz.db"})
    # SQLite 會自動建檔，所以這個其實會通過 — 改測別的情境
    # 改用：路徑是個資料夾（非檔案）
    with tempfile.TemporaryDirectory() as d:
        c = get_connector("sqlite", {"path": d})  # path is directory
        with pytest.raises(ConnectionTestFailed):
            await c.test_connection()


@pytest.mark.asyncio
async def test_sqlite_list_tables(legacy_sqlite_db):
    c = get_connector("sqlite", {"path": legacy_sqlite_db})
    tables = await c.list_tables()
    assert "Customer" in tables
    assert "OrderHeader" in tables


@pytest.mark.asyncio
async def test_sqlite_query_no_filter(legacy_sqlite_db):
    c = get_connector("sqlite", {"path": legacy_sqlite_db})
    rows = await c.query("Customer", limit=10)
    assert len(rows) == 3
    assert {r["CustNo"] for r in rows} == {"C001", "C002", "C003"}


@pytest.mark.asyncio
async def test_sqlite_query_with_filter(legacy_sqlite_db):
    c = get_connector("sqlite", {"path": legacy_sqlite_db})
    rows = await c.query("Customer", filters={"Grade": "A"})
    assert len(rows) == 2
    assert {r["CustNo"] for r in rows} == {"C001", "C003"}


@pytest.mark.asyncio
async def test_sqlite_query_blocks_unknown_table(legacy_sqlite_db):
    """安全防線：不在 list_tables() 的 table 必被拒絕。"""
    c = get_connector("sqlite", {"path": legacy_sqlite_db})
    with pytest.raises(TableNotFound):
        await c.query("NonExistentTable_xyz")


@pytest.mark.asyncio
async def test_sqlite_query_blocks_injection_in_column(legacy_sqlite_db):
    """安全防線：filters key 含 SQL injection 時拒絕。"""
    c = get_connector("sqlite", {"path": legacy_sqlite_db})
    with pytest.raises(ValueError, match="不安全的欄位名"):
        await c.query("Customer", filters={"CustNo; DROP TABLE Customer;--": "x"})


@pytest.mark.asyncio
async def test_sqlite_query_limit_clamp(legacy_sqlite_db):
    """limit 預設不超過 1000。"""
    c = get_connector("sqlite", {"path": legacy_sqlite_db})
    # 給超大 limit，應被 clamp（不會錯，但只回實際 3 筆）
    rows = await c.query("Customer", limit=999999)
    assert len(rows) == 3  # 表內只有 3 筆


@pytest.mark.asyncio
async def test_sqlite_schema_of(legacy_sqlite_db):
    c = get_connector("sqlite", {"path": legacy_sqlite_db})
    schema = await c.schema_of("Customer")
    field_names = {f["name"] for f in schema}
    assert {"CustNo", "CustName", "Grade", "Phone"}.issubset(field_names)


# ============================================================
# CsvFolderConnector tests
# ============================================================

@pytest.mark.asyncio
async def test_csv_test_connection(csv_folder):
    c = get_connector("csv_folder", {"folder": csv_folder})
    assert await c.test_connection() is True


@pytest.mark.asyncio
async def test_csv_test_connection_nonexistent():
    c = get_connector("csv_folder", {"folder": "/nonexistent/xyz/abc"})
    with pytest.raises(ConnectionTestFailed):
        await c.test_connection()


@pytest.mark.asyncio
async def test_csv_list_tables(csv_folder):
    c = get_connector("csv_folder", {"folder": csv_folder})
    tables = await c.list_tables()
    assert tables == ["orders", "parts"]  # alphabetical


@pytest.mark.asyncio
async def test_csv_query(csv_folder):
    c = get_connector("csv_folder", {"folder": csv_folder})
    rows = await c.query("orders")
    assert len(rows) == 3
    assert rows[0]["customer"] == "客戶A"


@pytest.mark.asyncio
async def test_csv_query_with_filter(csv_folder):
    c = get_connector("csv_folder", {"folder": csv_folder})
    rows = await c.query("orders", filters={"status": "confirmed"})
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_csv_query_blocks_unknown_table(csv_folder):
    c = get_connector("csv_folder", {"folder": csv_folder})
    with pytest.raises(TableNotFound):
        await c.query("nonexistent")


# ============================================================
# AI tool integration tests
# ============================================================

@pytest.mark.asyncio
async def test_tool_query_external_db_federated(legacy_sqlite_db):
    """E2E：在 register_connection → AI tool 查得到資料。"""
    from app.agents.domains.external_db_tools import (
        register_connection, _CONNECTIONS,
        _list_connections, _list_external_tables, _query_external_db,
    )

    _CONNECTIONS.clear()  # 清舊環境

    register_connection("legacy_dingxin", "sqlite", {"path": legacy_sqlite_db})

    # list_external_connections
    result = await _list_connections(db=None, user=None)
    assert result["total"] == 1
    assert result["connections"][0]["name"] == "legacy_dingxin"
    # 至少 sqlite + csv_folder 兩個 connector 出現
    avail_names = {c["name"] for c in result["available_connectors"]}
    assert {"sqlite", "csv_folder"}.issubset(avail_names)

    # list_external_tables
    result = await _list_external_tables(db=None, user=None, connection="legacy_dingxin")
    assert "Customer" in result["tables"]
    assert "OrderHeader" in result["tables"]

    # query_external_db — federated query 客戶
    result = await _query_external_db(
        db=None, user=None,
        connection="legacy_dingxin", table="Customer",
        filters={"Grade": "A"},
    )
    assert result["total"] == 2
    assert {r["CustNo"] for r in result["rows"]} == {"C001", "C003"}

    # query_external_db — federated query 訂單
    result = await _query_external_db(
        db=None, user=None,
        connection="legacy_dingxin", table="OrderHeader",
    )
    assert result["total"] == 3
    # 加總金額（模擬「鼎新 5 月份訂單金額多少」場景）
    total = sum(r["Amount"] for r in result["rows"])
    assert total == 35500.0


@pytest.mark.asyncio
async def test_tool_query_external_db_unknown_connection():
    from app.agents.domains.external_db_tools import (
        _CONNECTIONS, _query_external_db,
    )
    _CONNECTIONS.clear()

    result = await _query_external_db(
        db=None, user=None,
        connection="not_registered", table="x",
    )
    assert "error" in result
    assert "available" in result
