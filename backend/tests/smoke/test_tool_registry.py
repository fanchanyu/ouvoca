"""Tool Registry 規約測試 — 守護 Phase 1 框架的不變式。"""
import pytest
from app.agents.registry import (
    RiskTier, Slot, ToolMeta,
    register_tool, get_tool, list_tools, all_domains,
    clear_registry, registry_size,
)


# ─── 純函式測試（不依賴實際 tools）──────────────────────

def test_registry_can_register_and_retrieve():
    clear_registry()

    @register_tool(
        name="test_q1", domain="inventory", risk_tier=RiskTier.READ,
        description="test query 1",
        slots=[Slot("x", "str", required=False, description="x")],
    )
    async def _q1(db, user): pass

    t = get_tool("test_q1")
    assert t is not None
    assert t.name == "test_q1"
    assert t.domain == "inventory"
    assert t.risk_tier == RiskTier.READ
    assert len(t.slots) == 1


def test_hard_write_must_have_permission():
    clear_registry()
    with pytest.raises(ValueError, match="hard-write"):
        @register_tool(
            name="bad_tool", domain="inventory",
            risk_tier=RiskTier.HARD_WRITE, description="bad",
            # 故意不填 required_permission
        )
        async def _bad(db, user): pass


def test_hard_write_with_permission_ok():
    clear_registry()

    @register_tool(
        name="good_tool", domain="inventory",
        risk_tier=RiskTier.HARD_WRITE, description="good",
        required_permission="inventory.part.create",
    )
    async def _good(db, user): pass

    assert get_tool("good_tool").required_permission == "inventory.part.create"


def test_list_tools_filter_by_domain():
    clear_registry()

    @register_tool(name="a1", domain="inventory", risk_tier=RiskTier.READ, description="")
    async def a1(db, user): pass

    @register_tool(name="b1", domain="purchase", risk_tier=RiskTier.READ, description="")
    async def b1(db, user): pass

    inv = list_tools(domain="inventory")
    assert len(inv) == 1
    assert inv[0].name == "a1"


def test_list_tools_filter_by_tier():
    clear_registry()

    @register_tool(name="r1", domain="x", risk_tier=RiskTier.READ, description="")
    async def r1(db, user): pass

    @register_tool(name="w1", domain="x", risk_tier=RiskTier.HARD_WRITE,
                   required_permission="x.do", description="")
    async def w1(db, user): pass

    reads = list_tools(tier=RiskTier.READ)
    writes = list_tools(tier=RiskTier.HARD_WRITE)
    assert len(reads) == 1 and reads[0].name == "r1"
    assert len(writes) == 1 and writes[0].name == "w1"


def test_to_llm_dict_format():
    clear_registry()

    @register_tool(
        name="tool_x", domain="inv", risk_tier=RiskTier.READ,
        description="example",
        slots=[
            Slot("part_no", "str", required=True, description="料號"),
            Slot("limit", "int", required=False, description="筆數上限"),
        ],
    )
    async def _x(db, user, part_no, limit=10): pass

    d = get_tool("tool_x").to_llm_dict()
    assert d["type"] == "function"
    assert d["function"]["name"] == "tool_x"
    assert "part_no" in d["function"]["parameters"]["properties"]
    assert d["function"]["parameters"]["required"] == ["part_no"]


# ─── 整合測試：載入實際 tool modules ────────────────────

def test_real_tools_load_and_register():
    """載入 app.agents.domains 後，registry 應有真實 tools。
    必須 reload — 因為前面的 unit test 可能 clear 過 registry。
    """
    import importlib, sys
    for sub in [
        "inventory_tools", "purchase_tools", "sales_tools",
        "production_tools", "quality_tools", "warehouse_tools",
        "mps_mrp_tools", "accounting_tools", "crm_tools", "general_tools",
    ]:
        full = f"app.agents.domains.{sub}"
        try:
            if full in sys.modules:
                importlib.reload(sys.modules[full])
            else:
                importlib.import_module(full)
        except ImportError:
            pass

    # Day 1 漸進目標：先 4 個 tool 接入新 registry（之後 Day 1 推到 8）
    assert registry_size() >= 4, (
        f"目前 registry 只有 {registry_size()} 個 tool 註冊。Day 1 目標：≥ 4。"
    )


def test_no_duplicate_names():
    """工具名稱必須全域唯一（避免 LLM 路由混淆）。"""
    import importlib, sys
    for sub in [
        "inventory_tools", "purchase_tools", "sales_tools",
        "production_tools", "quality_tools", "warehouse_tools",
        "mps_mrp_tools", "accounting_tools", "crm_tools", "general_tools",
    ]:
        full = f"app.agents.domains.{sub}"
        try:
            if full in sys.modules:
                importlib.reload(sys.modules[full])
            else:
                importlib.import_module(full)
        except ImportError:
            pass
    names = [t.name for t in list_tools()]
    assert len(names) == len(set(names)), \
        f"重複的 tool name: {[n for n in names if names.count(n) > 1]}"


def test_at_least_2_domains_onboarded():
    """Day 1 漸進目標：≥ 2 個 domain 接入新 registry。"""
    import importlib, sys
    for sub in ["inventory_tools", "sales_tools"]:
        full = f"app.agents.domains.{sub}"
        if full in sys.modules:
            importlib.reload(sys.modules[full])
        else:
            importlib.import_module(full)
    domains = all_domains()
    assert len(domains) >= 2, (
        f"目前只有 {len(domains)} 個 domain 接入：{domains}。Day 1 目標：≥ 2。"
    )


def test_riskTier_enum_values():
    assert RiskTier.READ.value == "read"
    assert RiskTier.SOFT_WRITE.value == "soft-write"
    assert RiskTier.HARD_WRITE.value == "hard-write"
