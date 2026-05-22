"""Multi-Agent Engine — intent classification, agent + tool registry, LLM dispatcher."""
import json
from typing import Any, Callable
import httpx

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


# --------------------------------------------------------------------------
# Intent classifier — weighted keyword match
# --------------------------------------------------------------------------

INTENT_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "inventory": [
        ("庫存", 5), ("庫存查詢", 8), ("還有多少", 5), ("剩多少", 6),
        ("零件", 3), ("庫存量", 6), ("料號", 4), ("庫存不足", 5),
        ("inventory", 5), ("stock", 5), ("物料", 4),
    ],
    "purchase": [
        ("採購", 6), ("採購單", 8), ("供應商", 5), ("請購", 6),
        ("報價", 5), ("交期", 4), ("下單", 5), ("PO", 5),
        ("purchase", 5), ("supplier", 4),
    ],
    "production": [
        ("生產", 6), ("工單", 7), ("派工", 6), ("工序", 6),
        ("機台", 4), ("完工", 5), ("產量", 5),
        ("production", 5), ("work order", 5),
    ],
    "mps_mrp": [
        ("MPS", 7), ("MRP", 7), ("需求規劃", 6), ("物料需求", 6),
        ("供需", 5), ("forecast", 5), ("主排程", 6), ("計畫訂單", 6),
    ],
    "quality": [
        ("檢驗", 6), ("品質", 5), ("不良", 5), ("矯正", 5),
        ("CAPA", 6), ("抽樣", 5), ("合格率", 5),
        ("quality", 5), ("inspection", 5),
    ],
    "sales": [
        ("銷售", 6), ("出貨", 5), ("報價單", 5), ("銷售訂單", 7),
        ("sales", 5), ("ship", 4),
    ],
    "accounting": [
        ("財務", 5), ("傳票", 6), ("會計", 5), ("應收", 5),
        ("月結", 6), ("借貸", 5), ("科目", 4),
        ("accounting", 5), ("journal", 5),
    ],
    "warehouse": [
        ("倉庫", 6), ("儲位", 5), ("盤點", 6), ("揀貨", 5),
        ("調撥", 5), ("入庫", 4), ("出庫", 4),
        ("warehouse", 5), ("bin", 4),
    ],
    "crm": [
        ("CRM", 6), ("潛在客戶", 5), ("拜訪", 4), ("商機", 5),
        ("合約", 4), ("lead", 5), ("opportunity", 5), ("客戶", 3),
    ],
    "hr": [
        ("員工", 5), ("人事", 6), ("部門", 5), ("簽核", 6), ("approval", 5),
    ],
}


def classify_intent(message: str) -> str:
    scores: dict[str, int] = {}
    lower = message.lower()
    for domain, kws in INTENT_KEYWORDS.items():
        s = 0
        for kw, w in kws:
            if kw.lower() in lower:
                s += w
        if s:
            scores[domain] = s
    if not scores:
        return "general"
    return max(scores, key=scores.get)


# --------------------------------------------------------------------------
# Tool & Agent registries
# --------------------------------------------------------------------------
# v3.8 fix #3：殺掉舊 register_tool / TOOL_FUNCTIONS dual-registration。
# 唯一真相來源 = app.agents.registry._REGISTRY（每個 tool 含 risk_tier / slots / 權限）。
# TOOL_FUNCTIONS 名稱保留為 read-only proxy，不再接受註冊。

AGENT_REGISTRY: dict[str, dict] = {}


class _ToolFunctionsProxy:
    """Read-only dict-like view 對映新 registry，給既有 caller / tests 用。

    新代碼請直接用 `app.agents.registry._REGISTRY` 或 `get_tool(name)`。
    """

    def _data(self) -> dict[str, dict]:
        from app.agents.registry import _REGISTRY
        return {
            name: {
                "name": meta.name,
                "description": meta.description,
                "parameters": meta.to_llm_dict()["function"]["parameters"],
                "func": meta.func,
            }
            for name, meta in _REGISTRY.items()
        }

    def __contains__(self, name: str) -> bool:
        from app.agents.registry import _REGISTRY
        return name in _REGISTRY

    def __getitem__(self, name: str) -> dict:
        return self._data()[name]

    def get(self, name: str, default=None):
        from app.agents.registry import get_tool
        meta = get_tool(name)
        if meta is None:
            return default
        return {
            "name": meta.name,
            "description": meta.description,
            "parameters": meta.to_llm_dict()["function"]["parameters"],
            "func": meta.func,
        }

    def keys(self):
        from app.agents.registry import _REGISTRY
        return _REGISTRY.keys()

    def values(self):
        return self._data().values()

    def items(self):
        return self._data().items()

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        from app.agents.registry import _REGISTRY
        return len(_REGISTRY)


TOOL_FUNCTIONS = _ToolFunctionsProxy()


def get_tool_definitions(tool_names: list[str]) -> list[dict]:
    """v3.8: 改從新 registry 直接讀（含 RiskTier / required_permission metadata）。"""
    from app.agents.registry import get_tool
    out: list[dict] = []
    for name in tool_names:
        meta = get_tool(name)
        if meta is None:
            continue
        out.append(meta.to_llm_dict())
    return out


async def execute_tool(name: str, args: dict, db=None, user=None) -> str:
    """v3.8: 直接從 registry 取 tool meta + func。"""
    from app.agents.registry import get_tool, RiskTier
    meta = get_tool(name)
    if meta is None or meta.func is None:
        return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)

    # v3.40 M5：hard-write 凍結檢查（讓「解凍」工具本身可以執行）
    if (meta.risk_tier == RiskTier.HARD_WRITE
            and name != "toggle_hard_write_freeze_with_confirm"
            and name != "undo_last_admin_change"  # v3.43 P1-4：撤銷工具凍結時仍可用
            and db is not None):
        from sqlalchemy import select as _select
        from app.models.permission import Tenant
        from datetime import datetime as _dt, UTC as _UTC
        try:
            t = (await db.execute(
                _select(Tenant).where(Tenant.code == "HQ")
            )).scalar_one_or_none()
            if t and t.settings:
                frozen_until = (t.settings or {}).get("hard_write_frozen_until")
                if frozen_until:
                    until_dt = _dt.fromisoformat(frozen_until)
                    if until_dt.tzinfo is None:
                        until_dt = until_dt.replace(tzinfo=_UTC)
                    if _dt.now(_UTC) < until_dt:
                        # v3.43 P1-4：log + 回更豐富的結構（含 http_equivalent: 423 給前端 mapping）
                        reason = (t.settings or {}).get("hard_write_freeze_reason") or "(無)"
                        log.warning(
                            "Hard-write frozen blocked: tool=%s user=%s until=%s reason=%s",
                            name, (user or {}).get("user_id", "anon"), frozen_until, reason,
                        )
                        return json.dumps({
                            "error": (
                                f"🔒 系統 hard-write 已凍結至 {until_dt.date().isoformat()}。"
                                f"原因：{reason}。"
                                f"如需解凍：在 Chat 講「解凍」（需 system.config.update 權限）。"
                            ),
                            "frozen": True,
                            "frozen_until": frozen_until,
                            "frozen_reason": reason,
                            "http_equivalent": 423,  # Locked — 前端可據此 render 鎖頭 icon
                            "tool_blocked": name,
                        }, ensure_ascii=False)
        except Exception:
            # 凍結檢查若 fail（DB / 表不存在）不要 block tool
            pass

    # Slot-filling reverse-ask：缺 required slot 時回 structured needs_input
    missing = _missing_required_slots(name, args)
    if missing:
        # v3.39 K4：retry counter — 連問同個 tool 第 N 次仍缺 → fallback
        retry_count = _bump_slot_retry(user, name)
        if retry_count >= 3:
            _reset_slot_retry(user, name)
            return json.dumps({
                "needs_input": False,
                "retry_exceeded": True,
                "error": (
                    f"已連續 3 次無法湊齊「{name}」所需欄位。"
                    "建議改用前端表單頁面填寫，或重新組織描述後再試。"
                ),
                "hint": "您可以講「我要用表單建客戶」直接打開表單頁。",
            }, ensure_ascii=False)
        return json.dumps({
            "needs_input": True,
            "retry_count": retry_count,
            "missing": [
                {"name": s.name, "type": s.type, "description": s.description}
                for s in missing
            ],
            "ask": _build_reverse_ask(name, missing),
            "guidance": (
                "缺少必要欄位。請直接問使用者這些欄位，不要編造預設值。"
                "如果使用者用同義詞或關鍵字（如「螺絲」、「長江」），"
                "考慮先呼叫 lookup_term / query_supplier 解析。"
                + (f" （已重試 {retry_count}/3 次）" if retry_count > 1 else "")
            ),
        }, ensure_ascii=False)

    # 成功取到所有欄位 → 重置該 tool 的 retry counter
    _reset_slot_retry(user, name)

    try:
        result = await meta.func(db=db, user=user, **args)
        if hasattr(result, "__dict__") and not isinstance(result, (dict, list)):
            result = {"success": True, "data": str(result)}
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as exc:
        log.exception("Tool %s execution failed", name)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


_NO_REGISTRY_META: set[str] = set()


# v3.39 K4：per-user-per-tool slot-filling retry counter
# 結構：{ user_key: {tool_name: count} }
_SLOT_RETRY: dict[str, dict[str, int]] = {}


def _slot_retry_key(user) -> str:
    return (user or {}).get("user_id") or (user or {}).get("employee_id") or "anonymous"


def _bump_slot_retry(user, tool_name: str) -> int:
    """記錄該使用者該 tool 之 slot-filling 失敗次數；回新值（從 1 起）。"""
    key = _slot_retry_key(user)
    entry = _SLOT_RETRY.setdefault(key, {})
    entry[tool_name] = entry.get(tool_name, 0) + 1
    return entry[tool_name]


def _reset_slot_retry(user, tool_name: str) -> None:
    key = _slot_retry_key(user)
    entry = _SLOT_RETRY.get(key)
    if entry:
        entry.pop(tool_name, None)


def _missing_required_slots(name: str, args: dict) -> list:
    """檢查 args 是否缺少 required slot（從新 registry 取 slots metadata）。

    回值：缺少的 Slot 物件 list；若 tool 未在新 registry 註冊則回空 list（向後相容）。

    Note: 不能在模組頂層 import registry — registry 反過來 import engine.register_tool
    形成 cycle。但快取 None lookup 結果到 _NO_REGISTRY_META 集，避免 hot path 重複 dict miss。
    """
    if name in _NO_REGISTRY_META:
        return []
    from app.agents.registry import get_tool
    meta = get_tool(name)
    if meta is None:
        _NO_REGISTRY_META.add(name)
        return []
    return [
        s for s in meta.slots
        if s.required and (s.name not in args or args.get(s.name) in (None, "", []))
    ]


def _build_reverse_ask(tool_name: str, missing: list) -> str:
    """組一段 LLM 友善的反問提示字串。"""
    if len(missing) == 1:
        s = missing[0]
        return (
            f"執行 {tool_name} 需要先知道「{s.description or s.name}」。"
            f"請反問使用者。"
        )
    items = "、".join(f"「{s.description or s.name}」" for s in missing)
    return (
        f"執行 {tool_name} 需要先知道 {len(missing)} 個欄位：{items}。"
        f"請反問使用者，**一次問完所有缺漏項**。"
    )


def register_agent(domain: str, name: str, system_prompt: str, tool_names: list[str]) -> None:
    AGENT_REGISTRY[domain] = {
        "name": name,
        "domain": domain,
        "system_prompt": system_prompt,
        "tool_names": tool_names,
    }


def get_agent(domain: str) -> dict | None:
    return AGENT_REGISTRY.get(domain) or AGENT_REGISTRY.get("general")


# --------------------------------------------------------------------------
# LLM provider dispatch
# --------------------------------------------------------------------------

async def chat_completion(messages: list[dict], tools: list[dict] | None = None) -> dict:
    provider = settings.LLM_PROVIDER
    if provider == "deepseek":
        return await _deepseek_chat(messages, tools)
    if provider == "openai":
        return await _openai_chat(messages, tools)
    if provider == "anthropic":
        return await _anthropic_chat(messages, tools)
    if provider == "ollama":
        return await _ollama_chat(messages, tools)
    return {"content": f"Unsupported LLM provider: {provider}", "tool_calls": []}


def _httpx_client_kwargs() -> dict:
    """共用的 httpx client 設定（含 SSL verify 控制）。"""
    return {
        "timeout": settings.LLM_TIMEOUT_SECONDS,
        "verify": settings.LLM_VERIFY_SSL,
    }


async def _deepseek_chat(messages, tools):
    async with httpx.AsyncClient(**_httpx_client_kwargs()) as client:
        payload = {"model": settings.LLM_MODEL or "deepseek-chat", "messages": messages,
                   "temperature": 0.3, "max_tokens": 4096}
        if tools:
            payload["tools"] = tools
        resp = await client.post(
            settings.LLM_BASE_URL + "/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}",
                     "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        choice = resp.json()["choices"][0]["message"]
        return {"content": choice.get("content", ""), "tool_calls": choice.get("tool_calls", [])}


async def _openai_chat(messages, tools):
    async with httpx.AsyncClient(**_httpx_client_kwargs()) as client:
        payload = {"model": settings.LLM_MODEL or "gpt-4o", "messages": messages,
                   "temperature": 0.3, "max_tokens": 4096}
        if tools:
            payload["tools"] = tools
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}",
                     "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        choice = resp.json()["choices"][0]["message"]
        return {"content": choice.get("content", ""), "tool_calls": choice.get("tool_calls", [])}


async def _anthropic_chat(messages, tools):
    system_msg = ""
    msgs = []
    for m in messages:
        if m["role"] == "system":
            system_msg += (m.get("content") or "") + "\n"
        else:
            msgs.append({"role": m["role"], "content": m.get("content") or ""})
    async with httpx.AsyncClient(**_httpx_client_kwargs()) as client:
        payload = {
            "model": settings.LLM_MODEL or "claude-sonnet-4-20250514",
            "system": system_msg.strip(),
            "messages": msgs, "max_tokens": 4096,
        }
        if tools:
            payload["tools"] = tools
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.LLM_API_KEY,
                     "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        tool_calls = []
        content = ""
        for block in data.get("content", []):
            if block["type"] == "text":
                content += block.get("text", "")
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "function": {"name": block.get("name", ""),
                                 "arguments": json.dumps(block.get("input", {}))},
                })
        return {"content": content, "tool_calls": tool_calls}


async def _ollama_chat(messages, tools):
    async with httpx.AsyncClient(timeout=120, verify=settings.LLM_VERIFY_SSL) as client:
        payload = {"model": settings.LLM_MODEL or "qwen2.5:7b", "messages": messages, "stream": False}
        resp = await client.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return {"content": resp.json().get("message", {}).get("content", ""), "tool_calls": []}
