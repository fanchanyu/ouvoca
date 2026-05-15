"""Email digest AI tools — 讓 AI 透過對話查 / 寄摘要（v3.5 MVP #4）。

王董：「今天的摘要?」→ preview_email_digest
王董：「寄一份摘要給 wang@example.com」→ send_email_digest_with_confirm
"""
from __future__ import annotations

from app.agents.confirm_card import make_card, stash_card
from app.agents.engine import AGENT_REGISTRY
from app.agents.registry import register_tool, RiskTier, Slot
from app.services.email_digest import build_digest, send_email


@register_tool(
    name="preview_email_digest",
    domain="analytics",
    risk_tier=RiskTier.READ,
    description=(
        "預覽老闆儀表板摘要：警示 / 今日事件 / KPI 快照。"
        "範例：「今天工廠狀況」「最近 24 小時摘要」"
    ),
    slots=[
        Slot("period_hours", "integer", required=False,
             description="統計區間（小時），預設 24"),
    ],
    required_permission="ai.agent.use",
)
async def _preview_digest(db, user, period_hours: int = 24):
    if period_hours < 1:
        period_hours = 24
    if period_hours > 168:
        period_hours = 168
    d = await build_digest(
        db,
        recipient=(user or {}).get("employee_id"),
        period_hours=period_hours,
    )
    return {
        "summary_line": d.summary_line,
        "period_label": d.period_label,
        "generated_at": d.generated_at,
        "sections": [
            {
                "icon": s.icon, "title": s.title,
                "lines": s.text_lines[:8],  # 限長度避免 token 爆
                "items_count": len(s.items),
            }
            for s in d.sections
        ],
    }


@register_tool(
    name="send_email_digest_with_confirm",
    domain="analytics",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "寄送每日摘要 Email 給指定收件人。"
        "AI 會出 ConfirmCard 給使用者確認收件人 + 內容預覽，確認後才寄。"
        "範例：「寄今天摘要給 wang@example.com」"
    ),
    slots=[
        Slot("to", "string", required=True, description="收件人 email"),
        Slot("period_hours", "integer", required=False, description="統計區間，預設 24"),
    ],
    required_permission="ai.agent.use",
)
async def _send_digest_with_confirm(db, user, to: str, period_hours: int = 24):
    if "@" not in to:
        return {"error": f"無效的 email 地址: {to!r}"}

    d = await build_digest(
        db,
        recipient=to,
        period_hours=period_hours or 24,
    )

    summary = [
        f"收件人：{to}",
        f"區間：{d.period_label}",
        f"主旨：[LLM-ERP] {d.period_label}摘要",
        f"結論：{d.summary_line}",
        f"段落數：{len(d.sections)}",
    ]
    for s in d.sections:
        summary.append(f"  • {s.icon} {s.title}（{len(s.items)} 項）")

    card = make_card(
        tool_name="send_email_digest_with_confirm",
        title=f"確認寄送摘要 Email 給 {to}",
        summary=summary,
        slots={"to": to, "period_hours": period_hours or 24},
        risk_tier="hard-write",
        ttl_seconds=120,
        created_by=(user or {}).get("employee_id"),
    )

    async def execute():
        subject = f"[LLM-ERP] {d.period_label}摘要：{d.summary_line[:30]}"
        result = send_email(
            to=to, subject=subject,
            html=d.to_html(), text=d.to_markdown(),
        )
        return {
            "to": to,
            "sent": result.get("sent", False),
            "dry_run": result.get("dry_run", False),
            "reason": result.get("reason"),
            "error": result.get("error"),
            "message": (
                f"✅ Email 已寄出給 {to}" if result.get("sent")
                else f"⚠️ Dry-run（SMTP 未設）— 內容已組好但未寄送。"
                if result.get("dry_run")
                else f"❌ 寄送失敗：{result.get('error', 'unknown')}"
            ),
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# 接到 GeneralAgent + 增強 BossDashboard 場景
for agent_name in ("general", "purchase", "sales", "production"):
    if agent_name in AGENT_REGISTRY:
        tn = AGENT_REGISTRY[agent_name]["tool_names"]
        for t in ("preview_email_digest", "send_email_digest_with_confirm"):
            if t not in tn:
                tn.append(t)
