"""v3.60 P0-2 tests — 細表（child tables）tenant 隔離。

審計問題：SalesOrderItem / BOMItem / JournalLine / Operation / DispatchLog /
InspectionResult / StockCountItem / PurchaseOrderItem / QuotationItem /
RoutingStep / ApprovalStepV2 / ContractPricing / MpsEntry / MrpItem /
ReorderRule / ReplenishSuggestion 缺 TenantMixin → 自動 tenant filter
對這些表不生效，多租戶部署有跨廠洩漏路徑。
"""
from __future__ import annotations

from pathlib import Path

EXPECTED_TENANT_MIXIN_TABLES = [
    "BOMItem", "JournalLine", "SalesOrderItem", "ContractPricing",
    "ApprovalStepV2", "QuotationItem", "StockCountItem", "InspectionResult",
    "Operation", "DispatchLog", "RoutingStep", "PurchaseOrderItem",
    "MpsEntry", "MrpItem", "ReorderRule", "ReplenishSuggestion",
]


def test_child_tables_have_tenant_mixin():
    """16 張細表的 class 定義必須是 (Base, TenantMixin)。"""
    models_dir = Path(__file__).resolve().parents[2] / "app" / "models"
    missing = []
    for model_name in EXPECTED_TENANT_MIXIN_TABLES:
        found = False
        for py in models_dir.glob("*.py"):
            text = py.read_text(encoding="utf-8")
            if f"class {model_name}(Base, TenantMixin):" in text:
                found = True
                break
        if not found:
            missing.append(model_name)
    assert not missing, f"以下細表仍缺 TenantMixin：{missing}"


def test_tenant_mixin_column_present():
    from app.models._mixins import TenantMixin
    assert hasattr(TenantMixin, "tenant_id")


def test_migration_v006_covers_all_tables():
    """migration v006 應包含全部 16 張表的 backfill。"""
    mig = (Path(__file__).resolve().parents[2] / "alembic" / "versions" /
           "v007_tenant_id_child_tables.py").read_text(encoding="utf-8")
    expected_tablenames = [
        "bom_items", "journal_lines", "sales_order_items", "contract_pricing",
        "approval_workflow_steps", "quotation_items", "stock_count_items",
        "inspection_results", "operations", "dispatch_logs", "routing_steps",
        "purchase_order_items", "mps_entries", "mrp_items",
        "reorder_rules", "replenish_suggestions",
    ]
    for table in expected_tablenames:
        assert table in mig, f"migration v006 缺 {table}"
    assert "UPDATE" in mig and "SET tenant_id = 'HQ'" in mig, "migration v006 缺 backfill"
