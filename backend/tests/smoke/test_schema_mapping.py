"""Smoke tests for v3.4 Schema Mapping AI + Migration（demo moment 3）。

驗證：
  1. suggest_mapping 演算法（exact / alias / partial / unmapped）
  2. preview_schema_mapping tool 走通
  3. migrate_from_external_with_confirm 出 ConfirmCard + 真實匯入
  4. 衝突策略 skip / overwrite 都對
"""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

from app.agents.confirm_card import _clear_all_for_test, consume_card
from app.agents.schema_mapping import (
    get_target_schema, list_supported_domains, suggest_mapping,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def _clean_cards():
    _clear_all_for_test()
    yield
    _clear_all_for_test()


@pytest_asyncio.fixture
async def db(client):
    """每測試一個新 session + 測試後清掉 DX-* 客戶（避免 test pollution）。"""
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer
    from sqlalchemy import delete

    async with AsyncSessionLocal() as session:
        yield session

    # cleanup：刪掉測試插入的 DX-* 客戶
    async with AsyncSessionLocal() as cleanup:
        await cleanup.execute(delete(Customer).where(Customer.code.like("DX-%")))
        await cleanup.commit()


@pytest.fixture
def demo_user():
    return {"employee_id": "emp-mig-001", "username": "tester", "roles": ["admin"]}


@pytest.fixture
def legacy_customer_sqlite(tmp_path):
    """假裝鼎新匯出的 customer table。"""
    path = tmp_path / "dingxin.db"
    c = sqlite3.connect(str(path))
    c.execute("""
        CREATE TABLE Customer (
            CustNo TEXT PRIMARY KEY,
            CustName TEXT,
            Grade TEXT,
            Phone TEXT,
            Address TEXT,
            CreditLimit REAL,
            UnknownField TEXT
        )
    """)
    c.executemany(
        "INSERT INTO Customer VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("DX-001", "鼎新客戶 A", "A", "02-1234-5678", "台北市", 500000, "ignore_me"),
            ("DX-002", "鼎新客戶 B", "B", "02-2345-6789", "新北市", 300000, "ignore_me"),
            ("DX-003", "鼎新客戶 C", "A", "02-3456-7890", "桃園市", 800000, "ignore_me"),
        ],
    )
    c.commit()
    c.close()
    return str(path)


# ============================================================
# 演算法層
# ============================================================

class TestSuggestMapping:
    def test_exact_match_high_confidence(self):
        source = [
            {"name": "code", "type": "str"},
            {"name": "name", "type": "str"},
        ]
        r = suggest_mapping(source, "customer")
        # code 對 code、name 對 name 都是 1.0
        by_target = {m["target_field"]: m for m in r["mappings"]}
        assert by_target["code"]["confidence"] == 1.0
        assert by_target["name"]["confidence"] == 1.0
        assert r["required_satisfied"] is True

    def test_alias_match_high_confidence(self):
        """CustNo / CustName 是 customer.code / name 的別名。"""
        source = [
            {"name": "CustNo", "type": "str"},
            {"name": "CustName", "type": "str"},
            {"name": "Grade", "type": "str"},
        ]
        r = suggest_mapping(source, "customer")
        by_target = {m["target_field"]: m for m in r["mappings"]}
        assert by_target["code"]["source_field"] == "CustNo"
        assert by_target["code"]["confidence"] >= 0.9
        assert by_target["name"]["source_field"] == "CustName"
        assert by_target["grade"]["source_field"] == "Grade"

    def test_unknown_target_domain(self):
        r = suggest_mapping([], "nonexistent")
        assert "error" in r
        assert "supported" in r

    def test_missing_required_flag(self):
        """source 完全沒對應 code/name → required_satisfied=False。"""
        source = [{"name": "weird_col", "type": "str"}]
        r = suggest_mapping(source, "customer")
        assert r["required_satisfied"] is False

    def test_unmapped_source_listed(self):
        source = [
            {"name": "CustNo", "type": "str"},
            {"name": "CustName", "type": "str"},
            {"name": "TotallyWeird", "type": "str"},
        ]
        r = suggest_mapping(source, "customer")
        unmapped_names = {f["name"] for f in r["unmapped_source_fields"]}
        assert "TotallyWeird" in unmapped_names
        assert "CustNo" not in unmapped_names  # 已用

    def test_supplier_schema(self):
        source = [
            {"name": "SupplierNo", "type": "str"},
            {"name": "SupplierName", "type": "str"},
        ]
        r = suggest_mapping(source, "supplier")
        by_target = {m["target_field"]: m for m in r["mappings"]}
        assert by_target["code"]["source_field"] == "SupplierNo"
        assert by_target["name"]["source_field"] == "SupplierName"

    def test_part_schema(self):
        source = [
            {"name": "PartNo", "type": "str"},
            {"name": "PartName", "type": "str"},
            {"name": "Unit", "type": "str"},
        ]
        r = suggest_mapping(source, "part")
        by_target = {m["target_field"]: m for m in r["mappings"]}
        assert by_target["part_no"]["source_field"] == "PartNo"
        assert by_target["name"]["source_field"] == "PartName"
        assert by_target["unit"]["source_field"] == "Unit"

    def test_list_supported_domains(self):
        domains = list_supported_domains()
        assert {"customer", "supplier", "part"}.issubset(set(domains))

    def test_get_target_schema(self):
        s = get_target_schema("customer")
        assert s is not None
        assert any(t[0] == "code" for t in s)


# ============================================================
# Tool 層
# ============================================================

class TestPreviewTool:
    @pytest.mark.asyncio
    async def test_preview_unknown_connection(self, db, demo_user):
        from app.agents.domains.migration_tools import _preview_schema_mapping
        result = await _preview_schema_mapping(
            db=db, user=demo_user,
            connection="not_registered", source_table="x", target_domain="customer",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_preview_unknown_domain(self, db, demo_user, legacy_customer_sqlite):
        from app.agents.domains.external_db_tools import (
            _CONNECTIONS, register_connection,
        )
        from app.agents.domains.migration_tools import _preview_schema_mapping

        _CONNECTIONS.clear()
        register_connection("dx", "sqlite", {"path": legacy_customer_sqlite})

        result = await _preview_schema_mapping(
            db=db, user=demo_user,
            connection="dx", source_table="Customer", target_domain="invoice",
        )
        assert "error" in result
        assert "supported" in result

    @pytest.mark.asyncio
    async def test_preview_dingxin_customer(self, db, demo_user, legacy_customer_sqlite):
        from app.agents.domains.external_db_tools import (
            _CONNECTIONS, register_connection,
        )
        from app.agents.domains.migration_tools import _preview_schema_mapping

        _CONNECTIONS.clear()
        register_connection("dx", "sqlite", {"path": legacy_customer_sqlite})

        result = await _preview_schema_mapping(
            db=db, user=demo_user,
            connection="dx", source_table="Customer", target_domain="customer",
        )
        assert "error" not in result
        assert result["required_satisfied"] is True

        by_target = {m["target_field"]: m for m in result["mappings"]}
        assert by_target["code"]["source_field"] == "CustNo"
        assert by_target["name"]["source_field"] == "CustName"
        assert by_target["grade"]["source_field"] == "Grade"
        # UnknownField 應該 unmapped
        unmapped_names = {f["name"] for f in result["unmapped_source_fields"]}
        assert "UnknownField" in unmapped_names


# ============================================================
# Migration with ConfirmCard
# ============================================================

class TestMigration:
    @pytest.mark.asyncio
    async def test_migrate_emits_confirm_card(self, db, demo_user, legacy_customer_sqlite):
        from app.agents.domains.external_db_tools import (
            _CONNECTIONS, register_connection,
        )
        from app.agents.domains.migration_tools import _migrate_with_confirm

        _CONNECTIONS.clear()
        register_connection("dx", "sqlite", {"path": legacy_customer_sqlite})

        result = await _migrate_with_confirm(
            db=db, user=demo_user,
            connection="dx", source_table="Customer", target_domain="customer",
        )
        assert result.get("type") == "confirm_card"
        # ConfirmCard 應該還沒寫入
        from app.models.crm_sales import Customer
        from sqlalchemy import select
        rows = (await db.execute(select(Customer))).scalars().all()
        # 不應有來自 DX-XXX 的客戶
        codes = {c.code for c in rows}
        assert "DX-001" not in codes
        # 但 ConfirmCard 應在 pending
        card_id = result["card"]["id"]
        from app.agents.confirm_card import peek_card
        assert await peek_card(card_id) is not None

    @pytest.mark.asyncio
    async def test_migrate_confirm_actually_inserts(
        self, db, demo_user, legacy_customer_sqlite
    ):
        from app.agents.domains.external_db_tools import (
            _CONNECTIONS, register_connection,
        )
        from app.agents.domains.migration_tools import _migrate_with_confirm
        from app.models.crm_sales import Customer
        from sqlalchemy import select

        _CONNECTIONS.clear()
        register_connection("dx", "sqlite", {"path": legacy_customer_sqlite})

        # Step 1: 出卡
        result = await _migrate_with_confirm(
            db=db, user=demo_user,
            connection="dx", source_table="Customer", target_domain="customer",
        )
        card_id = result["card"]["id"]

        # Step 2: consume 並執行
        entry = await consume_card(card_id)
        assert entry is not None
        exec_result = await entry["executor"]()
        assert exec_result["status"] == "executed"
        assert exec_result["inserted"] == 3
        assert exec_result["failed"] == 0

        # Step 3: 驗 DB 真的有了
        rows = (await db.execute(
            select(Customer).where(Customer.code.in_(["DX-001", "DX-002", "DX-003"]))
        )).scalars().all()
        assert len(rows) == 3
        # 名稱對到了
        by_code = {c.code: c for c in rows}
        assert by_code["DX-001"].name == "鼎新客戶 A"
        assert by_code["DX-001"].grade == "A"
        assert by_code["DX-001"].contact_phone == "02-1234-5678"
        assert by_code["DX-001"].credit_limit == 500000.0

    @pytest.mark.asyncio
    async def test_migrate_skip_conflicts(self, db, demo_user, legacy_customer_sqlite):
        """已存在 code 用 skip 策略 → 略過。"""
        from app.agents.domains.external_db_tools import (
            _CONNECTIONS, register_connection,
        )
        from app.agents.domains.migration_tools import _migrate_with_confirm
        from app.models.crm_sales import Customer
        from sqlalchemy import select

        _CONNECTIONS.clear()
        register_connection("dx", "sqlite", {"path": legacy_customer_sqlite})

        # 預先插一筆 DX-001
        existing = Customer(
            id=str(uuid.uuid4()), code="DX-001", name="OLD NAME", grade="C",
        )
        db.add(existing)
        await db.commit()

        result = await _migrate_with_confirm(
            db=db, user=demo_user,
            connection="dx", source_table="Customer", target_domain="customer",
            conflict_strategy="skip",
        )
        entry = await consume_card(result["card"]["id"])
        exec_result = await entry["executor"]()
        assert exec_result["inserted"] == 2  # DX-002, DX-003
        assert exec_result["skipped"] == 1   # DX-001 已存在

        # 確認 DX-001 名稱仍是 OLD NAME
        old = (await db.execute(
            select(Customer).where(Customer.code == "DX-001")
        )).scalar_one()
        assert old.name == "OLD NAME"

    @pytest.mark.asyncio
    async def test_migrate_overwrite_conflicts(
        self, db, demo_user, legacy_customer_sqlite
    ):
        """overwrite 策略 → 蓋掉已存在。"""
        from app.agents.domains.external_db_tools import (
            _CONNECTIONS, register_connection,
        )
        from app.agents.domains.migration_tools import _migrate_with_confirm
        from app.models.crm_sales import Customer
        from sqlalchemy import select

        _CONNECTIONS.clear()
        register_connection("dx", "sqlite", {"path": legacy_customer_sqlite})

        existing = Customer(
            id=str(uuid.uuid4()), code="DX-002", name="OLD B", grade="D",
        )
        db.add(existing)
        await db.commit()

        result = await _migrate_with_confirm(
            db=db, user=demo_user,
            connection="dx", source_table="Customer", target_domain="customer",
            conflict_strategy="overwrite",
        )
        entry = await consume_card(result["card"]["id"])
        exec_result = await entry["executor"]()
        assert exec_result["updated"] == 1   # DX-002 被覆寫
        assert exec_result["inserted"] == 2  # DX-001, DX-003

        # 確認 DX-002 名稱已變
        new = (await db.execute(
            select(Customer).where(Customer.code == "DX-002")
        )).scalar_one()
        assert new.name == "鼎新客戶 B"


# ============================================================
# Registry sanity
# ============================================================

def test_v34_tools_registered():
    from app.agents import TOOL_FUNCTIONS, AGENT_REGISTRY
    assert "preview_schema_mapping" in TOOL_FUNCTIONS
    assert "migrate_from_external_with_confirm" in TOOL_FUNCTIONS
    # 接到 external_db agent
    external_tools = AGENT_REGISTRY["external_db"]["tool_names"]
    assert "preview_schema_mapping" in external_tools
    assert "migrate_from_external_with_confirm" in external_tools


def test_migrate_is_hard_write():
    """migrate 必須是 hard-write（出 ConfirmCard）。"""
    from app.agents.registry import get_tool, RiskTier
    meta = get_tool("migrate_from_external_with_confirm")
    assert meta is not None
    assert meta.risk_tier == RiskTier.HARD_WRITE
    assert meta.required_permission is not None
