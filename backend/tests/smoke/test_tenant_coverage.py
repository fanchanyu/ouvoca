"""Tenant isolation coverage audit (v3.8 fix #2).

這支 test 不是「跑通」就好，而是**鎖住已知 gap**：
  - 已採用 TenantMixin 的 model 必須在 EXPECTED_TENANT_MIXIN
  - 已知 NOT 用 TenantMixin 的 model 必須在 KNOWN_GAPS
  - 任何「新加 model 沒進兩個 list 之一」會被 test 抓到 → 強迫做決策

對應 audit finding:
  - permission.py 的 tenant_id 是手動 Column（不走 TenantMixin）—— 這是有意的，
    因為 super_admin 角色需跨租戶可見，自動 filter 反而擋掉
  - warehouse / supplier_plus / ai_governance / organization 完全沒 tenant_id —— TODO
"""
from __future__ import annotations

import inspect
import pytest

from app.models import _mixins as mixins_module


# ─── 預期已加 TenantMixin 的 model 模組 ─────────────────────────
EXPECTED_TENANT_MIXIN = {
    "accounting",
    "approval_workflow",  # v3.22 新增（多階審批，ApprovalRule + RequestV2 + Step）
    "policy_rule",        # v3.25 新增（家規 House Rules：PolicyRule + AuditLog）
    "quotation",          # v3.32 新增（報價單 + 行）
    "stock_count",        # v3.32 新增（盤點單 + 行）
    "tax_tw",             # v3.54 新增（EInvoiceRecord 持久化，統一發票合規）
    "attachment",   # v3.13 新增（檔案上傳，按租戶隔離存 uploads/{tenant_id}/）
    "crm_sales",
    "inventory",
    "mps_mrp",
    "product",
    "production",
    "purchase",
    "quality",
    "warehouse",   # v3.x P0 跨租戶洩漏修復：WarehouseZone/BinLocation/PickTask/CycleCount 全上 TenantMixin
}

# ─── 已知 gap：暫時沒上 TenantMixin（但有理由） ─────────────────
KNOWN_GAPS = {
    "permission": "手動 tenant_id Column；super_admin 跨租戶刻意設計",
    "supplier_plus": "v3.9 補（同上）",
    "ai_governance": "v3.9 補（DecisionLog/ConversationLog 跨租戶分析有需求）",
    "organization": "保留討論：員工/部門可能屬公司而非租戶層級",
    "glossary": "v3.46 Phase 2 G-201：同義詞表全公司共用，不需 tenant 隔離（單廠部署）；多租戶擴充時再加 created_by tenant 過濾",
}


def _model_modules() -> list[str]:
    """掃出 app.models.* 的模組名（不含 _mixins / __init__）。"""
    import app.models as pkg
    out: list[str] = []
    for name in dir(pkg):
        attr = getattr(pkg, name)
        if inspect.ismodule(attr) and attr.__package__ == "app.models":
            short = attr.__name__.rsplit(".", 1)[-1]
            if short.startswith("_") or short == "__init__":
                continue
            out.append(short)
    # fallback：直接掃檔案
    if not out:
        from pathlib import Path
        models_dir = Path(pkg.__file__).parent
        for p in models_dir.glob("*.py"):
            if p.stem.startswith("_") or p.stem == "__init__":
                continue
            out.append(p.stem)
    return sorted(set(out))


def test_tenant_mixin_coverage_is_documented():
    """每個 app.models.* 都必須在 EXPECTED_TENANT_MIXIN 或 KNOWN_GAPS 內。

    新加 model 沒被分類 → test 失敗 → 強迫做決策（要不要 tenant-scope）。
    """
    all_modules = set(_model_modules())
    classified = EXPECTED_TENANT_MIXIN | set(KNOWN_GAPS.keys())
    unclassified = all_modules - classified
    assert not unclassified, (
        f"新增 model {sorted(unclassified)} 沒被分類！\n"
        f"請決定是要走 TenantMixin（加進 EXPECTED_TENANT_MIXIN）還是\n"
        f"暫時不需要（加進 KNOWN_GAPS 並寫理由）。\n"
        f"見 backend/tests/smoke/test_tenant_coverage.py"
    )


def test_expected_modules_actually_use_tenant_mixin():
    """已宣告會用 TenantMixin 的模組，實際必有 import + 至少 1 個 model 用。"""
    import importlib
    failed = []
    for short in EXPECTED_TENANT_MIXIN:
        mod = importlib.import_module(f"app.models.{short}")
        src = inspect.getsource(mod)
        if "TenantMixin" not in src:
            failed.append(short)
    assert not failed, f"宣告用 TenantMixin 但實際沒 import: {failed}"


def test_known_gaps_have_reason():
    """已知 gap 必須有理由（避免「TODO 但忘了寫為什麼」）。"""
    for name, reason in KNOWN_GAPS.items():
        assert reason and len(reason) >= 5, f"{name} 的 KNOWN_GAPS 理由太短"


def test_permission_tenant_id_is_intentional():
    """permission.py 手動 tenant_id（不走 TenantMixin）— 鎖住設計決策。

    若有人嘗試把 permission.py 改成 TenantMixin，這 test 應該失敗 + 提醒
    auto-filter 會擋掉 super_admin 跨租戶查詢。
    """
    from app.models import permission as perm_mod
    src = inspect.getsource(perm_mod)
    assert "TenantMixin" not in src, (
        "permission.py 不該繼承 TenantMixin — auto-filter 會擋 super_admin "
        "跨租戶查詢系統角色。如果需要改，請先在 docs/PERMISSION_MODEL.md "
        "解釋為何 super_admin 場景下 auto-filter 不會打架。"
    )
    # 但 tenant_id 欄位本身要在
    assert "tenant_id" in src, "permission.py 應有 tenant_id 欄位（手動定義）"
