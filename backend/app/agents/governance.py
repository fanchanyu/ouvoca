"""
AI Governance — 治理底線：① 成本記錄 ② Prompt 安全偵測 ③ 高風險動作門控

目的：賣 AI-Native ERP 不能沒有安全帶。

設計原則：
- 不可侵入：在 agent 主流程「外圍」掛載（不改原本 logic）
- 可審計：每次 LLM call 必須留 cost / risk / confirm 紀錄到 DecisionLog
- 可關閉：所有檢查可透過 env flag 停用（測試 / 除錯時）
"""
from __future__ import annotations
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from app.core.logging import get_logger

log = get_logger(__name__)


# ─── 1. Cost tracking ──────────────────────────────────────

# 各 LLM provider 每 1M token 的單價（USD），取 2025-Q1 公開價格
MODEL_PRICING = {
    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-v3": {"input": 0.14, "output": 0.28},
    # Ollama 本地
    "ollama": {"input": 0, "output": 0},  # 本地零成本
}


@dataclass
class LLMCallMetrics:
    """單次 LLM call 的成本明細。"""
    agent_name: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    risk_flagged: bool = False
    risk_reason: Optional[str] = None
    human_confirmed: Optional[bool] = None  # None = N/A, True = approved, False = rejected
    tool_calls: list = field(default_factory=list)

    @property
    def cost_usd(self) -> float:
        """換算 USD。Unknown model → 0（避免高估）。"""
        pricing = MODEL_PRICING.get(self.model)
        if not pricing:
            return 0.0
        return (
            (self.input_tokens / 1_000_000) * pricing["input"]
            + (self.output_tokens / 1_000_000) * pricing["output"]
        )

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": self.latency_ms,
            "risk_flagged": self.risk_flagged,
            "human_confirmed": self.human_confirmed,
        }


# ─── 2. Prompt-injection 偵測 ──────────────────────────────

# 常見的 prompt injection / jailbreak 樣式
_INJECTION_PATTERNS = [
    # 中文常見手法
    r"(?i)忽略.*(指令|提示|prompt|instruction)",
    r"(?i)(忘掉|忘記).*(之前|前面|以上)",
    r"(?i)現在你是.*(管理員|admin|superuser|root)",
    r"(?i)(扮演|你現在扮演).*(駭客|hacker|惡意)",
    # 英文常見手法
    r"(?i)ignore\s+(previous|above|prior|all)\s+(instruction|prompt|rule)",
    r"(?i)disregard\s+(previous|above)",
    r"(?i)forget\s+(everything|all|previous)",
    r"(?i)you\s+are\s+now\s+(admin|root|superuser|dan|developer\s+mode)",
    r"(?i)pretend\s+to\s+be\s+(admin|root|hacker|jailbroken)",
    r"(?i)(reveal|show|leak|dump)\s+(system\s+)?prompt",
    # 資料抽取嘗試
    r"(?i)dump\s+(all\s+)?(customer|user|password|secret|api\s*key)",
    r"(?i)SELECT\s+\*\s+FROM\s+(users|customers|passwords)",
    r"(?i)show\s+me\s+(all|every).*?(password|api\s*key|token|secret)",
    # tool-call hijack
    r"(?i)call\s+(delete|drop|truncate)_.*tool",
    r"(?i)execute\s+arbitrary\s+(code|sql|shell)",
]


def detect_prompt_injection(user_message: str) -> tuple[bool, Optional[str]]:
    """回 (is_risky, matched_pattern_or_None)。

    這只是「第一道防線」（regex），生產建議再加：
    - LLM-based intent classifier 雙檢
    - 結構化輸出（讓 LLM 只能填 JSON 模板）
    - rate limit per user
    """
    if os.getenv("PROMPT_SAFETY_ENABLED", "true").lower() != "true":
        return (False, None)

    for pat in _INJECTION_PATTERNS:
        m = re.search(pat, user_message)
        if m:
            return (True, m.group(0))

    return (False, None)


# ─── 3. 高風險動作門控（Human-in-the-Loop）────────────────

# 哪些 tool 是「高風險」必須人工確認
HIGH_RISK_TOOLS = {
    # 寫入金額 / 核准
    "approve_purchase_order",       # 核准 PO
    "approve_sales_order",
    "post_journal_entry",            # 過帳會計分錄
    "close_month",                   # 月結
    # 刪除類
    "delete_customer",
    "delete_supplier",
    "delete_part",
    # 大量批次
    "bulk_inventory_adjust",
    "bulk_price_update",
    # 對外通訊
    "send_email_blast",
    "send_line_broadcast",
}

# 金額門檻（USD），超過要人工確認（即使 tool 不在 HIGH_RISK 也算）
HIGH_RISK_AMOUNT_USD = float(os.getenv("HIGH_RISK_AMOUNT_USD", "10000"))


def requires_human_confirmation(
    tool_name: str,
    args: dict | None = None,
) -> tuple[bool, str]:
    """回 (needs_confirm, reason)。"""
    if tool_name in HIGH_RISK_TOOLS:
        return (True, f"工具 {tool_name} 屬於高風險清單")

    if args:
        for key in ("amount", "total", "qty", "value"):
            v = args.get(key)
            if isinstance(v, (int, float)) and abs(float(v)) >= HIGH_RISK_AMOUNT_USD:
                return (True, f"金額/數量 {v} 超過門檻 {HIGH_RISK_AMOUNT_USD}")

    return (False, "")


# ─── 4. DecisionLog 寫入助手 ────────────────────────────────

async def log_ai_decision(
    db,  # AsyncSession (lazy import to avoid circular)
    *,
    session_id: str,
    user_id: Optional[str],
    domain: str,
    query: str,
    decision: str,
    metrics: LLMCallMetrics,
    reasoning: Optional[str] = None,
    alternatives: Optional[list] = None,
    score: Optional[float] = None,
):
    """把一次 AI 互動完整記下 — 供 audit / 成本分析。

    幂等：失敗不擋使用者請求（只 log warning）。
    """
    try:
        import uuid as _uuid
        from app.models.ai_governance import DecisionLog

        row = DecisionLog(
            id=str(_uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            domain=domain,
            query=query[:2000],         # 截斷防 DB 爆
            decision=decision[:5000],
            alternatives=alternatives,
            reasoning=reasoning,
            score=score,
            agent_name=metrics.agent_name,
            model=metrics.model,
            input_tokens=metrics.input_tokens,
            output_tokens=metrics.output_tokens,
            cost_usd=metrics.cost_usd,
            latency_ms=metrics.latency_ms,
            risk_flagged=metrics.risk_flagged,
            human_confirmed=metrics.human_confirmed,
        )
        db.add(row)
        await db.commit()
    except Exception as e:
        log.warning("log_ai_decision failed (non-blocking): %s", e)


# ─── 5. Convenience: 計時器 ────────────────────────────────

class CallTimer:
    """`with CallTimer() as t: ...; t.elapsed_ms`"""
    def __enter__(self):
        self._t0 = time.time()
        self.elapsed_ms = 0
        return self

    def __exit__(self, *args):
        self.elapsed_ms = int((time.time() - self._t0) * 1000)
