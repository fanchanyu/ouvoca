"""Email digest service — 組裝每日摘要內容（v3.5 MVP #4 收尾）。

設計：see docs/CONVERSATIONAL_ERP_DESIGN_ZH.md §5 + ROADMAP Phase 3 G-302。

包含 3 個層次：
  1. KPI 數字（DSO / 庫存周轉 / 毛利率 / OEE / 採購集中度）
  2. 警示（低於安全庫存的零件、逾期應收、未完工逾期工單）
  3. 今日事件摘要（最近 24h 內的事件）

輸出格式：
  - dict（結構化資料）給前端 preview 用
  - html 字串給 SMTP 寄送用
  - markdown 字串給 Chat / Slack 用

實際 SMTP 寄送：用 stdlib smtplib + SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS
（從 .env 讀；空字串時降級成「lazy mode：只組內容不寄」）。
"""
from __future__ import annotations

import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from email.message import EmailMessage
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.events.engine import EventBus
from app.models.accounting import AccountsReceivable
from app.models.crm_sales import SalesOrder
from app.models.inventory import Inventory, Part
from app.models.production import ProductionOrder
from app.models.purchase import PurchaseOrder

log = get_logger(__name__)


@dataclass
class DigestSection:
    """摘要的一個段落（KPI / Alert / Event）。"""
    title: str
    icon: str
    items: list[dict]   # 結構化資料給前端
    text_lines: list[str]  # 文字版


@dataclass
class Digest:
    """完整摘要 — 含 metadata + 3 個段落 + 多種輸出。"""
    generated_at: str
    period_label: str  # "昨日" / "今日 (截至 18:00)"
    recipient: Optional[str]
    sections: list[DigestSection]
    summary_line: str  # 一句話結論（給 push 通知 / Email subject）

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "period_label": self.period_label,
            "recipient": self.recipient,
            "summary_line": self.summary_line,
            "sections": [
                {
                    "title": s.title, "icon": s.icon,
                    "items": s.items, "text_lines": s.text_lines,
                }
                for s in self.sections
            ],
        }

    def to_markdown(self) -> str:
        out: list[str] = [
            f"# 老闆儀表板 — {self.period_label}",
            f"",
            f"_生成時間：{self.generated_at}_",
            f"",
            f"> {self.summary_line}",
            f"",
        ]
        for s in self.sections:
            out.append(f"## {s.icon} {s.title}")
            out.append("")
            for line in s.text_lines:
                out.append(f"- {line}")
            out.append("")
        out.append("---")
        out.append("_本郵件由 LLM-ERP 自動生成（v3.5）_")
        return "\n".join(out)

    def to_html(self) -> str:
        rows: list[str] = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'/>",
            "<style>",
            "body{font-family:'Microsoft JhengHei',sans-serif;color:#1f2937;max-width:680px;margin:0 auto;padding:24px}",
            "h1{color:#1e40af;border-bottom:2px solid #1e40af;padding-bottom:8px}",
            "h2{color:#374151;margin-top:24px}",
            ".summary{background:#eff6ff;border-left:4px solid #1e40af;padding:12px 16px;margin:16px 0;border-radius:4px}",
            ".section{background:#f9fafb;border-radius:8px;padding:16px;margin:12px 0}",
            "ul{padding-left:20px} li{margin:4px 0}",
            ".footer{color:#9ca3af;font-size:12px;text-align:center;margin-top:32px;border-top:1px solid #e5e7eb;padding-top:12px}",
            "</style></head><body>",
            f"<h1>老闆儀表板 — {self.period_label}</h1>",
            f"<p style='color:#6b7280;font-size:13px'>生成時間：{self.generated_at}</p>",
            f"<div class='summary'>📌 {self.summary_line}</div>",
        ]
        for s in self.sections:
            rows.append(f"<div class='section'><h2>{s.icon} {s.title}</h2><ul>")
            for line in s.text_lines:
                rows.append(f"<li>{line}</li>")
            rows.append("</ul></div>")
        rows.append("<div class='footer'>本郵件由 LLM-ERP 自動生成（v3.5）</div></body></html>")
        return "".join(rows)


# ────────────────────────────────────────────────────────────
# 主要組裝函式
# ────────────────────────────────────────────────────────────

async def build_digest(
    db: AsyncSession,
    recipient: Optional[str] = None,
    period_hours: int = 24,
) -> Digest:
    """產生 digest。period_hours 控制「最近多久」的統計。"""
    now = datetime.now(UTC).replace(tzinfo=None)
    period_start = now - timedelta(hours=period_hours)

    sections: list[DigestSection] = []

    # ─── Section 1: 警示 ─────────────────────────────────
    alerts = await _build_alerts(db, period_start)
    sections.append(alerts)

    # ─── Section 2: 今日事件摘要 ──────────────────────────
    events = await _build_event_summary(db, period_start)
    sections.append(events)

    # ─── Section 3: KPI ──────────────────────────────────
    kpi = await _build_kpi_snapshot(db)
    sections.append(kpi)

    # 一句話結論
    summary = _build_summary_line(alerts, events)

    return Digest(
        generated_at=now.isoformat(),
        period_label=f"最近 {period_hours} 小時",
        recipient=recipient,
        sections=sections,
        summary_line=summary,
    )


async def _build_alerts(db: AsyncSession, period_start: datetime) -> DigestSection:
    """警示：低於安全庫存 / 逾期應收 / 未完工逾期工單。"""
    items: list[dict] = []
    lines: list[str] = []

    # (a) 低於安全庫存
    low_stock_rows = (await db.execute(
        select(Inventory, Part)
        .join(Part, Inventory.part_id == Part.id)
        .where(Inventory.qty_available < Part.safety_stock)
        .where(Part.safety_stock > 0)
        .limit(5)
    )).all()
    for inv, p in low_stock_rows:
        items.append({
            "type": "low_stock", "severity": "warn",
            "part_no": p.part_no, "name": p.name,
            "qty_available": inv.qty_available, "safety_stock": p.safety_stock,
            "shortage": p.safety_stock - inv.qty_available,
        })
        lines.append(
            f"🔴 **{p.part_no}** ({p.name})：剩 {inv.qty_available:g} / 安全 {p.safety_stock:g}"
            f"（短缺 {p.safety_stock - inv.qty_available:g}）"
        )

    # (b) 逾期應收
    overdue_ar = (await db.execute(
        select(AccountsReceivable)
        .where(AccountsReceivable.due_date < datetime.now(UTC).replace(tzinfo=None))
        .where(AccountsReceivable.status != "paid")
        .limit(5)
    )).scalars().all()
    for ar in overdue_ar:
        items.append({
            "type": "overdue_ar", "severity": "danger",
            "invoice_no": ar.invoice_no,
            "amount": ar.amount, "paid_amount": ar.paid_amount,
            "due_date": str(ar.due_date), "aging_days": ar.aging_days,
        })
        lines.append(
            f"💰 應收 **{ar.invoice_no}** 逾期 {ar.aging_days} 天，"
            f"未收 ${ar.amount - ar.paid_amount:,.0f}"
        )

    # (c) 已釋放但逾期的工單
    overdue_wo = (await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.status.in_(["released", "in_progress"]))
        .where(ProductionOrder.scheduled_end < datetime.now(UTC).replace(tzinfo=None))
        .limit(5)
    )).scalars().all()
    for wo in overdue_wo:
        delay_days = (datetime.now(UTC).replace(tzinfo=None) - wo.scheduled_end).days if wo.scheduled_end else 0
        items.append({
            "type": "overdue_wo", "severity": "warn",
            "wo_no": wo.wo_no, "status": wo.status,
            "scheduled_end": str(wo.scheduled_end),
            "delay_days": delay_days,
        })
        lines.append(f"🏭 工單 **{wo.wo_no}** 逾期 {delay_days} 天（狀態 {wo.status}）")

    if not lines:
        lines.append("✅ 沒有警示")

    return DigestSection(
        title="關鍵警示", icon="⚠️", items=items, text_lines=lines,
    )


async def _build_event_summary(db: AsyncSession, period_start: datetime) -> DigestSection:
    """今日事件摘要：從 EventBus in-memory history 統計。"""
    items: list[dict] = []
    lines: list[str] = []

    # EventBus 是 in-memory（無 DB 表）— 從 history 拉
    all_events = EventBus.get_history(limit=500)
    period_events = [e for e in all_events if e.created_at >= period_start]

    # 依 domain 統計
    domain_counts: dict[str, int] = {}
    for e in period_events:
        domain_counts[e.domain] = domain_counts.get(e.domain, 0) + 1

    for domain, count in sorted(domain_counts.items()):
        items.append({"domain": domain, "count": count})
        lines.append(f"`{domain}`：{count} 個事件")

    total = len(period_events)
    if total == 0:
        lines = ["(沒有新事件)"]

    # 重要事件 — 最近 5 個
    important_names = {
        "so.created", "so.shipped", "po.received",
        "wo.completed", "stock.below_safety",
    }
    important = [e for e in period_events if e.name in important_names][-5:]
    if important:
        lines.append("**重要事件**：")
        for e in reversed(important):
            ts = e.created_at.strftime("%H:%M") if e.created_at else "?"
            eid = (e.entity_id or "")[:8]
            lines.append(f"  {ts} · `{e.name}` · {e.entity_type} {eid}…")

    return DigestSection(
        title=f"今日事件（共 {total} 個）", icon="📅",
        items=items, text_lines=lines,
    )


async def _build_kpi_snapshot(db: AsyncSession) -> DigestSection:
    """KPI 快照。"""
    items: list[dict] = []
    lines: list[str] = []

    # 出貨件數（30 天）
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
    so_shipped_count = (await db.execute(
        select(func.count(SalesOrder.id))
        .where(SalesOrder.status == "shipped")
        .where(SalesOrder.actual_delivery_date >= cutoff)
    )).scalar() or 0
    so_shipped_amount = (await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0))
        .where(SalesOrder.status == "shipped")
        .where(SalesOrder.actual_delivery_date >= cutoff)
    )).scalar() or 0

    items.append({"label": "30 日出貨筆數", "value": so_shipped_count})
    items.append({"label": "30 日出貨金額", "value": float(so_shipped_amount)})
    lines.append(f"📦 30 日出貨：{so_shipped_count} 筆，金額 ${so_shipped_amount:,.0f}")

    # 進行中 PO 數
    po_in_progress = (await db.execute(
        select(func.count(PurchaseOrder.id))
        .where(PurchaseOrder.status.in_(["approved", "sent", "partial_received"]))
    )).scalar() or 0
    items.append({"label": "進行中採購單", "value": po_in_progress})
    lines.append(f"🛒 進行中採購單：{po_in_progress} 張")

    # 進行中 WO 數
    wo_in_progress = (await db.execute(
        select(func.count(ProductionOrder.id))
        .where(ProductionOrder.status.in_(["released", "in_progress"]))
    )).scalar() or 0
    items.append({"label": "進行中工單", "value": wo_in_progress})
    lines.append(f"🏭 進行中工單：{wo_in_progress} 張")

    return DigestSection(
        title="KPI 快照", icon="📊", items=items, text_lines=lines,
    )


def _build_summary_line(alerts: DigestSection, events: DigestSection) -> str:
    n_alerts = sum(1 for i in alerts.items if i.get("severity") in ("warn", "danger"))
    n_events = sum(i.get("count", 0) for i in events.items)
    if n_alerts == 0 and n_events == 0:
        return "今日無重大狀況，工廠運作正常。"
    if n_alerts == 0:
        return f"今日 {n_events} 個事件，無警示。"
    return f"⚠️ 今日 {n_alerts} 項警示需注意，另有 {n_events} 個事件。"


# ────────────────────────────────────────────────────────────
# SMTP 寄送
# ────────────────────────────────────────────────────────────

def send_email(
    to: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
) -> dict:
    """寄送 email。若 SMTP_* 環境變數沒設，回 dry_run 模式（不真寄）。"""
    smtp_host = getattr(settings, "SMTP_HOST", "") or ""
    smtp_port = int(getattr(settings, "SMTP_PORT", 0) or 0)
    smtp_user = getattr(settings, "SMTP_USER", "") or ""
    smtp_pass = getattr(settings, "SMTP_PASS", "") or ""
    from_addr = getattr(settings, "SMTP_FROM", "") or smtp_user

    if not smtp_host or not from_addr:
        log.info("SMTP not configured — dry_run for to=%s subject=%s", to, subject)
        return {
            "sent": False,
            "dry_run": True,
            "reason": "SMTP_HOST 或 SMTP_FROM 未設定（.env 加上即可生效）",
            "preview": {"to": to, "subject": subject},
        }

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    if text:
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
    else:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(smtp_host, smtp_port or 587, timeout=15) as s:
            s.starttls()
            if smtp_user and smtp_pass:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        log.info("Email sent to %s", to)
        return {"sent": True, "to": to, "subject": subject}
    except Exception as e:
        log.exception("Email send failed")
        return {"sent": False, "dry_run": False, "error": f"{type(e).__name__}: {e}"}
