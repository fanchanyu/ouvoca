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

TOOL_FUNCTIONS: dict[str, dict] = {}
AGENT_REGISTRY: dict[str, dict] = {}


def register_tool(name: str, description: str, parameters: dict, func: Callable) -> None:
    TOOL_FUNCTIONS[name] = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "func": func,
    }


def get_tool_definitions(tool_names: list[str]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in TOOL_FUNCTIONS.values() if t["name"] in tool_names
    ]


async def execute_tool(name: str, args: dict, db=None, user=None) -> str:
    tool = TOOL_FUNCTIONS.get(name)
    if not tool:
        return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)

    # v3.3 Slot-filling reverse-ask：
    # 若 tool 有在新 registry 註冊 slots metadata，先驗 required slots。
    # 缺欄位時不執行 tool，回 structured `needs_input` 讓 LLM 自動反問使用者。
    missing = _missing_required_slots(name, args)
    if missing:
        return json.dumps({
            "needs_input": True,
            "missing": [
                {"name": s.name, "type": s.type, "description": s.description}
                for s in missing
            ],
            "ask": _build_reverse_ask(name, missing),
            "guidance": (
                "缺少必要欄位。請直接問使用者這些欄位，不要編造預設值。"
                "如果使用者用同義詞或關鍵字（如「螺絲」、「長江」），"
                "考慮先呼叫 lookup_term / query_supplier 解析。"
            ),
        }, ensure_ascii=False)

    try:
        result = await tool["func"](db=db, user=user, **args)
        if hasattr(result, "__dict__") and not isinstance(result, (dict, list)):
            result = {"success": True, "data": str(result)}
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as exc:
        log.exception("Tool %s execution failed", name)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


_NO_REGISTRY_META: set[str] = set()


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
