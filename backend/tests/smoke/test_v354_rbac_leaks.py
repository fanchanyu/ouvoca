"""Smoke tests for v3.54 RBAC / financial data leak fixes (F-1, F-2, F-3, F-4, F-6, F-7).

These tests verify that the security fixes are present in source. They are
regex-grep based smoke checks — full integration tests should be added
separately.
"""
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND = REPO_ROOT / "backend"
FRONTEND = REPO_ROOT / "frontend-desktop"


# ============================================================
# F-3 — email_digest endpoints must require analytics.view
# ============================================================

def test_email_digest_requires_analytics_view():
    src = (BACKEND / "app" / "api" / "email_digest.py").read_text(encoding="utf-8")
    # 至少 3 個 endpoint 都改成 analytics.view（preview / preview.html / send）
    matches = re.findall(r'require_permission\("analytics\.view"\)', src)
    assert len(matches) >= 3, (
        f"email_digest.py should require analytics.view on >=3 endpoints "
        f"(preview / preview.html / send), got {len(matches)}"
    )
    # ai.agent.use 不能再出現在 require_permission 裡（已全數改掉）
    assert 'require_permission("ai.agent.use")' not in src, \
        "email_digest.py 仍含 ai.agent.use 權限 — F-3 未修完"
    # 外部 email 警告 log
    assert "external recipient" in src or "_is_external_email" in src, \
        "email_digest.py /send 缺外部 email 警告 log（F-3 未補完）"


def test_email_digest_tools_uses_analytics_view():
    src = (BACKEND / "app" / "agents" / "domains" / "email_digest_tools.py").read_text(encoding="utf-8")
    assert 'required_permission="analytics.view"' in src, \
        "email_digest_tools.py 必須改成 analytics.view"
    assert 'required_permission="ai.agent.use"' not in src, \
        "email_digest_tools.py 仍含 ai.agent.use — F-3 未修完"


# ============================================================
# F-1 — PartResponse unit_cost stripping for non-finance
# ============================================================

def test_part_response_strips_unit_cost():
    schema_src = (BACKEND / "app" / "schemas" / "inventory.py").read_text(encoding="utf-8")
    # unit_cost 必須是 Optional（可被 strip 為 None）
    assert re.search(r"unit_cost:\s*Optional\[float\]", schema_src), \
        "PartResponse.unit_cost 應改為 Optional[float] = None（F-1）"

    api_src = (BACKEND / "app" / "api" / "inventory.py").read_text(encoding="utf-8")
    assert "_strip_cost_if_no_perm" in api_src, \
        "inventory.py 缺 _strip_cost_if_no_perm helper（F-1）"
    assert "_can_see_cost" in api_src, "inventory.py 缺 _can_see_cost 判斷（F-1）"
    assert "accounting.account.read" in api_src, \
        "inventory.py 應檢查 accounting.account.read 權限（F-1）"


# ============================================================
# F-2 — CustomerResponse credit_limit stripping
# ============================================================

def test_customer_response_strips_credit_limit():
    schema_src = (BACKEND / "app" / "schemas" / "sales.py").read_text(encoding="utf-8")
    assert re.search(r"credit_limit:\s*Optional\[float\]", schema_src), \
        "CustomerResponse.credit_limit 應改為 Optional[float] = None（F-2）"

    api_src = (BACKEND / "app" / "api" / "sales.py").read_text(encoding="utf-8")
    assert "_strip_credit_if_no_perm" in api_src, \
        "sales.py 缺 _strip_credit_if_no_perm helper（F-2）"
    assert "accounting.ar.read" in api_src, \
        "sales.py 應檢查 accounting.ar.read 權限（F-2）"


# ============================================================
# F-4 — inventory-monthly.xlsx must require accounting permission
#       and drop cost columns for non-finance callers
# ============================================================

def test_inventory_monthly_xlsx_locked_down():
    api_src = (BACKEND / "app" / "api" / "reports.py").read_text(encoding="utf-8")
    # require_any_permission 必須包含 accounting.* 權限之一
    assert "require_any_permission" in api_src, \
        "reports.py inventory-monthly.xlsx 應改用 require_any_permission（F-4）"
    assert "accounting.tax_report" in api_src, \
        "reports.py inventory-monthly.xlsx 必須包含 accounting.tax_report（F-4）"
    # include_cost 透傳到 renderer
    assert "include_cost=can_see_cost" in api_src, \
        "reports.py 應把 can_see_cost 傳給 render_inventory_monthly_xlsx（F-4）"

    svc_src = (BACKEND / "app" / "services" / "reports.py").read_text(encoding="utf-8")
    assert "include_cost" in svc_src, \
        "render_inventory_monthly_xlsx 應接受 include_cost 參數（F-4）"


# ============================================================
# F-6 — demo-admin bypass only in DEBUG / ALLOW_DEMO_BYPASS
# ============================================================

def test_demo_admin_blocked_in_production():
    src = (BACKEND / "app" / "core" / "security.py").read_text(encoding="utf-8")
    # 應該 import settings 並且檢查 DEBUG / ALLOW_DEMO_BYPASS
    assert "from app.config import settings" in src, \
        "security.py 應 import settings 來檢查 DEBUG（F-6）"
    assert "settings.DEBUG" in src, "security.py 應檢查 settings.DEBUG（F-6）"
    assert "settings.ALLOW_DEMO_BYPASS" in src, \
        "security.py 應檢查 settings.ALLOW_DEMO_BYPASS（F-6）"
    assert "demo-admin bypass disabled" in src or "bypass disabled in production" in src, \
        "security.py 應在 production 拋出 demo-admin bypass disabled 錯誤（F-6）"


# ============================================================
# F-7 — Frontend Layout filters menu by permission
# ============================================================

def test_layout_filters_menu():
    layout = (FRONTEND / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    # 至少要有 requires: 欄位 + filter() 邏輯
    assert "requires:" in layout, "Layout.tsx 缺 requires 欄位（F-7）"
    assert "hasPermission" in layout, "Layout.tsx 缺 hasPermission 函數（F-7）"
    assert "visibleNav" in layout or ".filter(" in layout, \
        "Layout.tsx 缺權限過濾邏輯（F-7）"
    # 確認常見模組 menu 都帶 requires
    for code in ("inventory.part.list", "purchase.order.list", "sales.order.list"):
        assert code in layout, f"Layout.tsx 缺 {code} requires 對映（F-7）"

    # auth store 必須有 permissions 欄位 + setPermissions
    auth = (FRONTEND / "src" / "store" / "auth.ts").read_text(encoding="utf-8")
    assert "permissions" in auth, "auth.ts AuthUser 應有 permissions 欄位（F-7）"
    assert "setPermissions" in auth, "auth.ts 應有 setPermissions action（F-7）"
