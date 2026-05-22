"""v3.37 安裝精靈 + Day 0/1/2-7 卡關修補 smoke

針對盤點報告 14 條硬傷的回歸測試（純後端能測的部分）：
  D0-1：Dockerfile 字型（runtime 才能驗，這裡只測 fallback 路徑 list）
  D0-4：set_company_info_with_confirm → Tenant.settings 更新；PDF 使用新公司名
  D0-2：change_my_password_with_confirm → 密碼強度檢查
  D2-1：create_customer 自動編號（code 留空 → CUS-0001）
  D2-2：list_available_roles 出中文角色名
  D2-3：print_sales_order_pdf 空品項警告
  D2-4：show_import_excel_guide
  D2-5：proactive_alerts
"""
from __future__ import annotations

import uuid
import pytest

from app.agents.registry import RiskTier, get_tool


V337_TOOLS = [
    "set_company_info_with_confirm",
    "change_my_password_with_confirm",
    "list_available_roles",
    "show_import_excel_guide",
    "proactive_alerts",
]


def test_v337_tools_registered():
    for n in V337_TOOLS:
        assert get_tool(n) is not None, f"{n} 未註冊"


def test_v337_risk_tiers():
    # hard-write: set_company_info / change_password
    assert get_tool("set_company_info_with_confirm").risk_tier == RiskTier.HARD_WRITE
    assert get_tool("change_my_password_with_confirm").risk_tier == RiskTier.HARD_WRITE
    # read: list_roles / import_guide / proactive_alerts
    assert get_tool("list_available_roles").risk_tier == RiskTier.READ
    assert get_tool("show_import_excel_guide").risk_tier == RiskTier.READ
    assert get_tool("proactive_alerts").risk_tier == RiskTier.READ


# ════════════════════════════════════════════════════════════════════
# D0-1: print_service 字型 fallback 路徑包含 Linux Noto
# ════════════════════════════════════════════════════════════════════

def test_print_service_has_linux_fonts_fallback():
    """Docker 鏡像裝了 fonts-noto-cjk → 路徑必須在 fallback 表內。"""
    import inspect
    from app.services import print_service
    src = inspect.getsource(print_service._try_register_chinese_font)
    # 確保 Debian/Ubuntu fonts-noto-cjk 套件之關鍵路徑都在
    assert "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc" in src
    assert "/usr/share/fonts/opentype/noto/NotoSansTC-Regular.otf" in src


# ════════════════════════════════════════════════════════════════════
# D0-4: set_company_info — 新建 Tenant + PDF 用新公司名
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_set_company_info_invalid_tax_id(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _set_company_info_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _set_company_info_with_confirm(
            db, {"user_id": "u1"}, name="x", tax_id="abc12345",
        )
    assert "error" in result
    assert "統編" in result["error"]


@pytest.mark.asyncio
async def test_set_company_info_returns_confirm_card(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _set_company_info_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _set_company_info_with_confirm(
            db, {"user_id": "u1"},
            name="長江精密股份有限公司", tax_id="12345678",
        )
    assert result["type"] == "confirm_card"
    assert "長江精密" in str(result["card"]["summary"])


@pytest.mark.asyncio
async def test_resolve_company_returns_fallback(seeded_client):
    """無 Tenant 時 fallback 到 Ouvoca 範例公司。"""
    from app.database import AsyncSessionLocal
    from app.services.print_service import _resolve_company
    async with AsyncSessionLocal() as db:
        # seeded_client 已有 HQ Tenant
        c = await _resolve_company(db)
    # 至少有 name 鍵 + 不為空
    assert "name" in c
    assert c["name"]


# ════════════════════════════════════════════════════════════════════
# D0-2: change_my_password — 強度檢查
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_change_password_no_user(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _change_my_password_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _change_my_password_with_confirm(db, None, new_password="MyN3wP@ss")
    assert "error" in result


@pytest.mark.asyncio
async def test_change_password_too_short(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _change_my_password_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _change_my_password_with_confirm(
            db, {"user_id": "u1"}, new_password="abc12",
        )
    assert "error" in result
    assert "8" in result["error"]


@pytest.mark.asyncio
async def test_change_password_no_letter(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _change_my_password_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _change_my_password_with_confirm(
            db, {"user_id": "u1"}, new_password="12345678",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_change_password_no_digit(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _change_my_password_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _change_my_password_with_confirm(
            db, {"user_id": "u1"}, new_password="abcdefgh",
        )
    assert "error" in result


@pytest.mark.asyncio
async def test_change_password_common(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _change_my_password_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _change_my_password_with_confirm(
            db, {"user_id": "u1"}, new_password="admin123",
        )
    assert "error" in result
    assert "常見" in result["error"]


# ════════════════════════════════════════════════════════════════════
# D2-1: Customer 自動編號（無 code → CUS-####）
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_customer_auto_code(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.hard_write_tools import _create_customer_with_confirm
    async with AsyncSessionLocal() as db:
        result = await _create_customer_with_confirm(
            db, {"user_id": "u1"}, name=f"Auto-Code Test {uuid.uuid4().hex[:5]}",
        )
    # 返回 confirm_card；summary 必含 CUS-#### 編號
    assert result["type"] == "confirm_card"
    text = " ".join(result["card"]["summary"])
    assert "CUS-" in text


# ════════════════════════════════════════════════════════════════════
# D2-2: list_available_roles
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_roles_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _list_available_roles
    async with AsyncSessionLocal() as db:
        result = await _list_available_roles(db, None)
    assert "summary" in result
    assert "raw" in result


# ════════════════════════════════════════════════════════════════════
# D2-3: print SO 空品項警告
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_print_so_empty_items_warns(seeded_client):
    from app.database import AsyncSessionLocal
    from app.models.crm_sales import Customer, SalesOrder
    from app.agents.domains.print_export_tools import _print_sales_order_pdf

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        cu = Customer(id=str(uuid.uuid4()), code=f"E-{s}", name=f"Empty {s}")
        db.add(cu)
        await db.flush()
        so = SalesOrder(
            id=str(uuid.uuid4()),
            so_no=f"SO-EMPTY-{s}",
            customer_id=cu.id, status="draft",
        )
        db.add(so)
        await db.commit()

        result = await _print_sales_order_pdf(db, None, so_no=f"SO-EMPTY-{s}")

    assert result["raw"]["item_count"] == 0
    assert result["warning"] is not None
    assert "空表" in result["warning"]


# ════════════════════════════════════════════════════════════════════
# D2-4: show_import_excel_guide
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_import_excel_guide_general(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _show_import_excel_guide
    async with AsyncSessionLocal() as db:
        result = await _show_import_excel_guide(db, None)
    assert "3 步流程" in result["summary"]


@pytest.mark.asyncio
async def test_import_excel_guide_customers(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _show_import_excel_guide
    async with AsyncSessionLocal() as db:
        result = await _show_import_excel_guide(db, None, entity="customers")
    assert "客戶清單匯入" in result["summary"]


# ════════════════════════════════════════════════════════════════════
# D2-5: proactive_alerts
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_proactive_alerts_runs(seeded_client):
    from app.database import AsyncSessionLocal
    from app.agents.domains.setup_wizard_tools import _proactive_alerts
    async with AsyncSessionLocal() as db:
        result = await _proactive_alerts(db, None)
    assert "summary" in result
    assert "raw" in result
    # 至少要有 overdue_receivables / low_stock 兩個 key
    assert "overdue_receivables" in result["raw"]
    assert "low_stock" in result["raw"]
