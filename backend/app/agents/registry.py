"""Tool Registry — 對話式 ERP 的核心註冊器。

詳見 docs/CONVERSATIONAL_ERP_DESIGN_ZH.md §5 原則 #1（Risk Tier 三分類）。

每個 AI tool 都用 @register_tool decorator 註冊，帶以下 metadata：
  - risk_tier:           read / soft-write / hard-write
  - slots:               需要的參數（name, type, required, description）
  - required_permission: RBAC 權限 code（hard-write 必填）
  - undo_recipe:         soft/hard-write 才有

設計原則：
  - 註冊在 import 時完成；engine.py 從 registry 取 tool 不再 hardcoded
  - Risk-tier 決定執行流：
      read       → engine 直接 call
      soft-write → engine 直接 call + 寫 ActionHistory
      hard-write → 第一次 call 回 ConfirmCard；第二次帶 confirm_token 才執行
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, Optional


class RiskTier(str, Enum):
    """Tool 風險分級 — 決定執行流的關鍵 metadata。"""
    READ = "read"             # 純查詢，直接執行
    SOFT_WRITE = "soft-write" # 寫入但低風險（draft、view filter…），直接執行 + 提供 undo
    HARD_WRITE = "hard-write" # 必須回 ConfirmCard 給使用者確認後才執行


@dataclass
class Slot:
    """Tool 一個參數的定義。"""
    name: str
    type: str           # "str" | "int" | "float" | "bool" | "list" | "dict"
    required: bool = True
    description: str = ""
    default: Any = None
    enum: Optional[list[Any]] = None  # 限定值


@dataclass
class ToolMeta:
    """Tool 完整描述 — 給 LLM 看 + 給 engine 路由用。"""
    name: str
    domain: str
    risk_tier: RiskTier
    description: str               # 給 LLM 看的自然語言敘述
    slots: list[Slot] = field(default_factory=list)
    required_permission: Optional[str] = None
    undo_recipe: Optional[str] = None  # tool name to call for undo
    func: Optional[Callable[..., Awaitable[Any]]] = None

    def to_llm_dict(self) -> dict:
        """OpenAI / DeepSeek tool-calling 格式。"""
        properties = {}
        required = []
        for s in self.slots:
            prop: dict[str, Any] = {"type": s.type, "description": s.description}
            if s.enum:
                prop["enum"] = s.enum
            properties[s.name] = prop
            if s.required:
                required.append(s.name)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


# ────────────── 全域 registry ──────────────
_REGISTRY: dict[str, ToolMeta] = {}


def register_tool(
    *,
    name: str,
    domain: str,
    risk_tier: RiskTier,
    description: str,
    slots: Optional[list[Slot]] = None,
    required_permission: Optional[str] = None,
    undo_recipe: Optional[str] = None,
):
    """裝飾器：把 async function 註冊為可被 LLM 呼叫的 tool。

    範例：
        @register_tool(
            name="query_inventory",
            domain="inventory",
            risk_tier=RiskTier.READ,
            description="查詢零件庫存",
            slots=[Slot("part_no", "str", required=False, description="料號")],
            required_permission="inventory.part.read",
        )
        async def _query_inventory(db, user, part_no=None): ...
    """
    if slots is None:
        slots = []

    # 強制檢查 hard-write 必有 required_permission
    if risk_tier == RiskTier.HARD_WRITE and not required_permission:
        raise ValueError(
            f"Tool {name!r} 是 hard-write 但沒設 required_permission — "
            "RBAC × AI 整合不可省略（見 CONVERSATIONAL_ERP_DESIGN §5 原則 #7）"
        )

    def decorator(func):
        meta = ToolMeta(
            name=name, domain=domain, risk_tier=risk_tier,
            description=description, slots=slots,
            required_permission=required_permission,
            undo_recipe=undo_recipe, func=func,
        )
        _REGISTRY[name] = meta
        # v3.8 fix #3：不再 dual-register 到 engine.TOOL_FUNCTIONS。
        # engine.TOOL_FUNCTIONS 改為對 _REGISTRY 的 read-only proxy。
        return func

    return decorator


def get_tool(name: str) -> Optional[ToolMeta]:
    """依 tool name 取單一 tool；找不到回 None。"""
    return _REGISTRY.get(name)


def list_tools(
    *,
    domain: Optional[str] = None,
    tier: Optional[RiskTier] = None,
) -> list[ToolMeta]:
    """列出（過濾）已註冊 tool。"""
    items = list(_REGISTRY.values())
    if domain is not None:
        items = [t for t in items if t.domain == domain]
    if tier is not None:
        items = [t for t in items if t.risk_tier == tier]
    return items


def all_domains() -> list[str]:
    """目前有 tool 的 domain 清單。"""
    return sorted({t.domain for t in _REGISTRY.values()})


def clear_registry() -> None:
    """測試用：清空註冊表。**勿在 production 呼叫**。"""
    _REGISTRY.clear()


def registry_size() -> int:
    return len(_REGISTRY)
