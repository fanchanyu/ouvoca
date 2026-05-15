"""GlossaryAgent — 同義詞 / 別名查詢工具（v3.3 對話智能）。

當使用者用「螺絲 / 長江 / 中華」這些俗稱時，AI 走 glossary 自動對到標準 ID。
這是 ConfirmCard / hard-write 之前的關鍵預處理步驟。
"""
from __future__ import annotations

from app.agents.engine import register_agent
from app.agents.glossary import (
    GlossaryEntry, list_glossary, register_term, resolve_term,
    seed_default_glossary,
)
from app.agents.registry import register_tool, RiskTier, Slot


# 啟動時自動 seed 一些常見 demo 詞（暫時行為，等 DB 表後移除）
seed_default_glossary()


@register_tool(
    name="lookup_term",
    domain="glossary",
    risk_tier=RiskTier.READ,
    description=(
        "查詢同義詞 / 別名 / 簡稱對應到的標準實體。"
        "使用者說「螺絲」「長江」「中華」這類詞時，先呼叫此 tool 解析。"
        "若 confidence ≥ 0.7 可信任使用；< 0.7 應反問使用者確認。"
    ),
    slots=[
        Slot("term", "string", required=True, description="使用者說的詞（如「螺絲」）"),
        Slot("canonical_type", "string", required=True,
             description="實體類別：part / customer / supplier / product"),
    ],
    required_permission="ai.agent.use",
)
async def _lookup_term(db, user, term: str, canonical_type: str):
    e = resolve_term(term, canonical_type)
    if e is None:
        return {
            "found": False, "term": term, "canonical_type": canonical_type,
            "hint": (
                f"glossary 中無「{term}」對 {canonical_type} 的記錄。"
                f"請用 query_inventory / query_supplier 等 tool 直接查，"
                f"或建議使用者用標準編號。"
            ),
        }
    return {
        "found": True,
        "term": e.term,
        "canonical_type": e.canonical_type,
        "canonical_id": e.canonical_id,
        "canonical_label": e.canonical_label,
        "confidence": e.confidence,
        "language": e.language,
    }


@register_tool(
    name="list_glossary_terms",
    domain="glossary",
    risk_tier=RiskTier.READ,
    description="列出 glossary 中已登錄的同義詞，可按類別 / 關鍵字過濾。",
    slots=[
        Slot("canonical_type", "string", required=False,
             description="過濾類別：part / customer / supplier / product"),
        Slot("keyword", "string", required=False, description="關鍵字（在 term 或 canonical_label 內搜尋）"),
        Slot("limit", "integer", required=False, description="預設 50"),
    ],
    required_permission="ai.agent.use",
)
async def _list_glossary(db, user, canonical_type: str = None, keyword: str = None, limit: int = 50):
    items = list_glossary(canonical_type=canonical_type, keyword=keyword, limit=limit)
    return {
        "total": len(items),
        "terms": [
            {
                "term": e.term, "canonical_type": e.canonical_type,
                "canonical_id": e.canonical_id, "canonical_label": e.canonical_label,
                "confidence": e.confidence, "notes": e.notes,
            }
            for e in items
        ],
    }


@register_tool(
    name="register_glossary_term",
    domain="glossary",
    risk_tier=RiskTier.SOFT_WRITE,
    description=(
        "新增一個 glossary 同義詞對映。"
        "適合場景：使用者教 AI「以後我說『鋼釘』就是指 M6-BOLT-20」。"
    ),
    slots=[
        Slot("term", "string", required=True, description="使用者說的詞"),
        Slot("canonical_type", "string", required=True,
             description="part / customer / supplier / product"),
        Slot("canonical_id", "string", required=True, description="對應實體的編號或 UUID"),
        Slot("canonical_label", "string", required=False, description="顯示用名稱"),
    ],
    required_permission="ai.agent.use",
)
async def _register_term(db, user, term, canonical_type, canonical_id, canonical_label: str = ""):
    e = register_term(GlossaryEntry(
        term=term, canonical_type=canonical_type,
        canonical_id=canonical_id, canonical_label=canonical_label or canonical_id,
    ))
    return {
        "registered": True, "term": e.term, "canonical_type": e.canonical_type,
        "canonical_id": e.canonical_id, "canonical_label": e.canonical_label,
    }


register_agent(
    "glossary", "GlossaryAgent",
    system_prompt=(
        "你是 ERP 同義詞解析助手。職責：\n"
        "1. 把使用者說的俗稱 / 別名（如「螺絲」「長江」）對應到標準編號\n"
        "2. 列出已登錄詞彙\n"
        "3. 接受新增詞彙的指令（如「以後我說『鋼釘』就是 M6-BOLT-20」）\n\n"
        "重要原則：\n"
        "- confidence < 0.7 必須反問使用者確認再用\n"
        "- 找不到時直接告知，不要編造\n"
    ),
    tool_names=["lookup_term", "list_glossary_terms", "register_glossary_term"],
)
