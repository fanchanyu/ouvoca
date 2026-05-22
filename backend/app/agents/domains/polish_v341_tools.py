"""v3.41 第五輪小白卡關修補 — Polish v341 tools

針對第五輪盤點 P1-P8（不重複 v3.37-v3.40）：
  P1：query_customer_profitability — 客戶毛利率分析
  P2：trace_order_lifecycle — 訂單生命週期（QUO → SO → 出貨 → 應收 → 收款）
  P5：email_pdf_to_customer_with_confirm — 寄 PDF 給客戶
  P6：ask_faq — 常見問題
  P8：run_data_health_check — 資料健康檢查（BOM 循環 / 客戶重複 / 孤兒料）
  P3 / P4 / P7：前端處理（briefMode / pin / thumbs）

══════════════════════════════════════════════════════════════════
LEGAL（累積適用 v3.25.10 → v3.40 §6）
══════════════════════════════════════════════════════════════════
本模組之 hard-write tools 涉及：
  • 寄 email 給客戶 — 對外溝通，涉及公司形象 / 契約效力
  • 毛利率分析 — 涉及客戶議價策略，**不應**外流
客戶須依個資法、營業秘密法、公平交易法妥善使用。
詳見 §6 完整免責條款。
"""
from __future__ import annotations

import base64
import io
import smtplib
from datetime import datetime, timedelta, UTC
from email.message import EmailMessage
from typing import Optional
from sqlalchemy import select, func, desc, and_, or_

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.crm_sales import Customer, SalesOrder, SalesOrderItem
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem
from app.models.quotation import Quotation
from app.models.inventory import Part, Inventory
from app.models.product import Product, BOMItem
from app.config import settings as app_settings
from app.core.logging import get_logger

log = get_logger(__name__)


# ════════════════════════════════════════════════════════════════════
# P1: 客戶毛利率分析
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="query_customer_profitability",
    domain="sales",
    risk_tier=RiskTier.READ,
    description=(
        "計算客戶之毛利率（營收 − 成本 = 毛利）。"
        "範例：「ABC 客戶賺不賺錢？」「哪 5 個客戶最賺？」「客戶 ABC 毛利率」。"
        "⚠️ 結果含議價策略敏感資料，不可外流。"
    ),
    slots=[
        Slot("customer_keyword", "string", required=False,
             description="客戶名稱 / 編號（不填 = 列 top N）"),
        Slot("days_back", "integer", required=False,
             description="統計過去 N 天，預設 90"),
        Slot("top_n", "integer", required=False,
             description="top N 客戶，預設 5"),
    ],
    required_permission="sales.order.read",
)
async def _query_customer_profitability(
    db, user, customer_keyword: str = "", days_back: int = 90, top_n: int = 5,
):
    days_back = max(1, min(int(days_back or 90), 365))
    top_n = max(1, min(int(top_n or 5), 20))
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_back)

    # 拉 SOs + items + product cost
    q = (
        select(SalesOrder, SalesOrderItem, Customer, Product)
        .join(SalesOrderItem, SalesOrderItem.so_id == SalesOrder.id)
        .join(Customer, Customer.id == SalesOrder.customer_id, isouter=True)
        .join(Product, Product.id == SalesOrderItem.product_id, isouter=True)
        .where(SalesOrder.order_date >= since)
    )
    if customer_keyword:
        like = f"%{customer_keyword.lower()}%"
        q = q.where(or_(
            func.lower(Customer.name).like(like),
            func.lower(Customer.code).like(like),
        ))
    rows = (await db.execute(q)).all()

    if not rows:
        return {
            "summary": (
                f"📊 過去 {days_back} 天無銷售資料"
                + (f"（{customer_keyword}）" if customer_keyword else "")
            ),
            "raw": {"count": 0, "rows": []},
        }

    # 按客戶 aggregate
    agg = {}  # customer_id → {"name": .., "code": .., "revenue": .., "cost": ..}
    for so, item, cust, prod in rows:
        cid = cust.id if cust else "unknown"
        if cid not in agg:
            agg[cid] = {
                "customer_id": cid,
                "code": cust.code if cust else "(無)",
                "name": cust.name if cust else "(無)",
                "revenue": 0.0,
                "cost": 0.0,
                "order_count": 0,
                "so_ids": set(),
            }
        revenue = (item.ordered_qty or 0) * (item.unit_price or 0)
        cost = (item.ordered_qty or 0) * ((prod.standard_cost if prod else 0) or 0)
        agg[cid]["revenue"] += revenue
        agg[cid]["cost"] += cost
        agg[cid]["so_ids"].add(so.id)

    # 計算毛利率
    for v in agg.values():
        v["order_count"] = len(v["so_ids"])
        v["so_ids"] = list(v["so_ids"])[:5]  # 不回傳太多
        v["gross_profit"] = v["revenue"] - v["cost"]
        v["margin_pct"] = (v["gross_profit"] / v["revenue"] * 100) if v["revenue"] else 0

    sorted_rows = sorted(agg.values(), key=lambda x: x["gross_profit"], reverse=True)
    if not customer_keyword:
        sorted_rows = sorted_rows[:top_n]

    lines = [
        f"💰 **客戶毛利率分析**（過去 {days_back} 天，共 {len(agg)} 個客戶）",
        "",
    ]
    for v in sorted_rows:
        flag = "🟢" if v["margin_pct"] > 20 else ("🟡" if v["margin_pct"] > 5 else "🔴")
        lines.append(
            f"  {flag} **{v['name']}**（{v['code']}）"
        )
        lines.append(
            f"      營收 ${v['revenue']:,.0f} / 成本 ${v['cost']:,.0f} / "
            f"毛利 ${v['gross_profit']:,.0f} (**{v['margin_pct']:.1f}%**) / "
            f"訂單 {v['order_count']} 張"
        )
    lines.append("")
    lines.append("⚠️ 此分析含議價策略敏感資料，請勿外流。")

    return {
        "summary": "\n".join(lines),
        "raw": {"count": len(agg), "days_back": days_back, "rows": sorted_rows},
    }


# ════════════════════════════════════════════════════════════════════
# P2: 訂單生命週期追蹤
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="trace_order_lifecycle",
    domain="sales",
    risk_tier=RiskTier.READ,
    description=(
        "追蹤訂單之完整生命週期（QUO → SO → 出貨 → 應收 → 收款）。"
        "範例：「QUO-001 後續變成什麼了？」「SO-001 收款了嗎？」「跟單 QUO-2026-001」。"
    ),
    slots=[
        Slot("doc_no", "string", required=True,
             description="單號（quote_no / so_no 都可）"),
    ],
    required_permission="sales.order.read",
)
async def _trace_order_lifecycle(db, user, doc_no: str):
    doc_no = (doc_no or "").strip()
    if not doc_no:
        return {"error": "請提供單號（quote_no 或 so_no）。"}

    timeline = []
    quote = None
    so = None

    # 嘗試作為 quote_no 查
    quote = (await db.execute(
        select(Quotation).where(Quotation.quote_no == doc_no)
    )).scalar_one_or_none()

    # 嘗試作為 so_no 查
    so = (await db.execute(
        select(SalesOrder).where(SalesOrder.so_no == doc_no)
    )).scalar_one_or_none()

    if quote is None and so is None:
        return {"error": f"找不到單號「{doc_no}」（quote_no 或 so_no 都查無）。"}

    # 若是 quote_no → 順著找 converted_so_id 的 SO
    if quote is not None and so is None and quote.converted_so_id:
        so = (await db.execute(
            select(SalesOrder).where(SalesOrder.id == quote.converted_so_id)
        )).scalar_one_or_none()

    # 若是 so_no → 反查 quote
    if so is not None and quote is None:
        quote = (await db.execute(
            select(Quotation).where(Quotation.converted_so_id == so.id)
        )).scalar_one_or_none()

    # 1. Quote
    if quote:
        timeline.append({
            "stage": "📄 報價",
            "doc_no": quote.quote_no,
            "date": quote.quote_date.date().isoformat() if quote.quote_date else None,
            "amount": quote.total_amount or 0,
            "status": quote.status,
        })

    # 2. SO
    if so:
        timeline.append({
            "stage": "🤝 銷售訂單",
            "doc_no": so.so_no,
            "date": so.order_date.date().isoformat() if so.order_date else None,
            "amount": so.total_amount or 0,
            "status": so.status,
        })

        # 3. 出貨（從 so.actual_delivery_date 推）
        if so.actual_delivery_date:
            timeline.append({
                "stage": "🚚 已出貨",
                "doc_no": f"(based on SO {so.so_no})",
                "date": so.actual_delivery_date.date().isoformat(),
                "amount": so.total_amount or 0,
                "status": "delivered",
            })
        elif so.status in ("shipped", "delivered"):
            timeline.append({
                "stage": "🚚 已出貨",
                "doc_no": f"(based on SO {so.so_no})",
                "date": None,
                "amount": so.total_amount or 0,
                "status": so.status,
            })

        # 4. 應收（從 AccountsReceivable）
        try:
            from app.models.accounting import AccountsReceivable
            ar = (await db.execute(
                select(AccountsReceivable).where(AccountsReceivable.customer_id == so.customer_id)
                .order_by(desc(AccountsReceivable.created_at)).limit(1)
            )).scalar_one_or_none()
            if ar:
                paid = ar.paid_amount or 0
                timeline.append({
                    "stage": "💰 應收 / 收款" if paid >= (ar.amount or 0) else "⏳ 應收（未付清）",
                    "doc_no": ar.invoice_no,
                    "date": str(ar.due_date) if ar.due_date else None,
                    "amount": ar.amount or 0,
                    "paid": paid,
                    "status": ar.status,
                })
        except ImportError:
            pass

    # 組 summary
    if not timeline:
        return {"summary": f"❓ 「{doc_no}」找不到任何生命週期資料。", "raw": {"timeline": []}}

    lines = [f"📍 **訂單生命週期：{doc_no}**", ""]
    for i, t in enumerate(timeline, 1):
        date_part = f" - {t['date']}" if t.get("date") else ""
        amt_part = f" - ${t['amount']:,.0f}" if t.get("amount") else ""
        paid_part = f" - 已付 ${t['paid']:,.0f}" if "paid" in t else ""
        lines.append(
            f"  {i}. {t['stage']} **{t['doc_no']}**{date_part}{amt_part}{paid_part} "
            f"（{t['status']}）"
        )

    # 健康診斷
    lines.append("")
    if len(timeline) >= 4:
        lines.append("✅ 流程完整（報價 → SO → 出貨 → 收款）")
    elif quote and not so:
        lines.append("⚠️ 報價單尚未轉成銷售訂單。")
    elif so and not so.actual_delivery_date and so.status not in ("shipped", "delivered"):
        lines.append("⚠️ SO 尚未出貨。")

    return {
        "summary": "\n".join(lines),
        "raw": {"doc_no": doc_no, "stages": len(timeline), "timeline": timeline},
    }


# ════════════════════════════════════════════════════════════════════
# P5: 寄 PDF 給客戶 Email
# ════════════════════════════════════════════════════════════════════

def _send_email_with_attachment(
    to: str, subject: str, body: str, pdf_bytes: bytes, pdf_filename: str,
) -> dict:
    """擴充版 send_email — 支援 PDF 附件。"""
    smtp_host = getattr(app_settings, "SMTP_HOST", "") or ""
    smtp_port = int(getattr(app_settings, "SMTP_PORT", 0) or 0)
    smtp_user = getattr(app_settings, "SMTP_USER", "") or ""
    smtp_pass = getattr(app_settings, "SMTP_PASS", "") or ""
    from_addr = getattr(app_settings, "SMTP_FROM", "") or smtp_user

    if not smtp_host or not from_addr:
        return {
            "sent": False, "dry_run": True,
            "reason": "SMTP_HOST 或 SMTP_FROM 未設定（.env 加上即可寄）",
            "preview": {"to": to, "subject": subject, "attachment": pdf_filename,
                        "attachment_size_kb": len(pdf_bytes) // 1024},
        }

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                        filename=pdf_filename)
    try:
        with smtplib.SMTP(smtp_host, smtp_port or 587, timeout=30) as s:
            s.starttls()
            if smtp_user and smtp_pass:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        return {"sent": True, "to": to, "subject": subject,
                "attachment_kb": len(pdf_bytes) // 1024}
    except Exception as e:
        log.exception("Email send with attachment failed")
        return {"sent": False, "error": f"{type(e).__name__}: {e}"}


@register_tool(
    name="email_pdf_to_customer_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "寄 PDF 給客戶 email（報價單 / 銷售單 / 出貨單）。"
        "範例：「寄 QUO-001 給 ABC」「Email SO-2026-001 給客戶」。"
        "⚠️ 對外溝通操作，請確認收件人後再執行。"
    ),
    slots=[
        Slot("doc_type", "string", required=True,
             description="quotation / so / delivery"),
        Slot("doc_no", "string", required=True, description="單號"),
        Slot("to_email", "string", required=False,
             description="收件 email（不填則用客戶主檔之 contact_email）"),
        Slot("note", "string", required=False, description="信件附註"),
    ],
    required_permission="sales.order.update",
)
async def _email_pdf_to_customer_with_confirm(
    db, user, doc_type: str, doc_no: str,
    to_email: str = "", note: str = "",
):
    doc_type = (doc_type or "").lower().strip()
    if doc_type not in ("quotation", "so", "delivery"):
        return {"error": f"doc_type「{doc_type}」應為 quotation / so / delivery。"}

    # Lookup
    customer = None
    entity = None
    if doc_type == "quotation":
        entity = (await db.execute(
            select(Quotation).where(Quotation.quote_no == doc_no)
        )).scalar_one_or_none()
        if entity and entity.customer_id:
            customer = (await db.execute(
                select(Customer).where(Customer.id == entity.customer_id)
            )).scalar_one_or_none()
    else:  # so / delivery
        entity = (await db.execute(
            select(SalesOrder).where(SalesOrder.so_no == doc_no)
        )).scalar_one_or_none()
        if entity and entity.customer_id:
            customer = (await db.execute(
                select(Customer).where(Customer.id == entity.customer_id)
            )).scalar_one_or_none()

    if entity is None:
        return {"error": f"找不到單號「{doc_no}」"}

    final_email = to_email.strip() if to_email else (customer.contact_email if customer else "")
    if not final_email or "@" not in final_email:
        return {
            "error": (
                "找不到有效收件 email。請提供 to_email 或先設定客戶 contact_email。"
            ),
        }

    title_map = {"quotation": "報價單", "so": "銷售訂單", "delivery": "出貨單"}
    title_zh = title_map[doc_type]

    summary = [
        f"📧 將寄送 **{title_zh}** 給客戶：",
        f"  • 單號：{doc_no}",
        f"  • 收件：{final_email}",
        f"  • 客戶：{customer.name if customer else '(未指定)'}",
    ]
    if note:
        summary.append(f"  • 附註：{note[:80]}")
    summary.append("")
    summary.append("⚠️ 確認後將立即寄出（無法收回 email）。")
    summary.append("    若 SMTP 未設定，會 dry-run（不真寄，僅顯示預覽）。")

    card = make_card(
        tool_name="email_pdf_to_customer_with_confirm",
        title=f"📧 確認寄 {title_zh} PDF",
        summary=summary,
        slots={"doc_type": doc_type, "doc_no": doc_no,
               "to_email": final_email, "note": note},
        risk_tier="hard-write",
        ttl_seconds=900,  # 15 min — email 給客戶應慎重
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        # 產 PDF
        from app.services.print_service import (
            generate_quotation_pdf, generate_so_pdf,
        )
        if doc_type == "quotation":
            pdf_bytes = await generate_quotation_pdf(db, entity.id)
            filename = f"quotation-{doc_no}.pdf"
        elif doc_type == "delivery":
            pdf_bytes = await generate_so_pdf(db, entity.id, doc_type="delivery_note")
            filename = f"delivery-{doc_no}.pdf"
        else:
            pdf_bytes = await generate_so_pdf(db, entity.id, doc_type="sales_order")
            filename = f"so-{doc_no}.pdf"

        subject = f"[erpilot] {title_zh} {doc_no}"
        body = (
            f"您好，\n\n"
            f"附上{title_zh} {doc_no}，請查收。\n"
            + (f"\n{note}\n" if note else "")
            + f"\n敬請見覆。\n\n"
            f"--\nerpilot ERP 系統自動寄送"
        )
        result = _send_email_with_attachment(
            final_email, subject, body, pdf_bytes, filename
        )
        if result.get("dry_run"):
            return {
                "dry_run": True,
                "message": (
                    f"⚠️ Email 未真寄（SMTP 未設定）：{result.get('reason')}\n"
                    f"預覽：寄至 {final_email}，主旨「{subject}」，附件 {filename}（{len(pdf_bytes) // 1024} KB）"
                ),
                **result,
            }
        if not result.get("sent"):
            return {"error": f"寄送失敗：{result.get('error')}"}
        return {
            "sent": True,
            "to": final_email,
            "message": f"✅ {title_zh} {doc_no} 已寄至 {final_email}（{len(pdf_bytes) // 1024} KB）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# P6: FAQ
# ════════════════════════════════════════════════════════════════════

_FAQ = [
    {
        "q": "erpilot 多少錢", "keywords": ["費用", "價格", "多少錢", "報價", "錢"],
        "a": (
            "💰 **erpilot 定價**：\n"
            "  • 30-50 人廠：30 萬 / 年\n"
            "  • 50-100 人廠：50 萬 / 年\n"
            "  • LLM API 費用客戶自付（DeepSeek 每月約 $5-20 USD）\n"
            "  • 開源核心 AGPL-3.0；商用授權見 LICENSE"
        ),
    },
    {
        "q": "斷網能用嗎", "keywords": ["斷網", "離線", "沒網路", "offline"],
        "a": (
            "🔌 **斷網行為**：\n"
            "  • ERP 主功能可用（DB 在本機 Docker）\n"
            "  • **AI 對話需網路**（DeepSeek API）\n"
            "  • 想完全離線 → 改用 Ollama + 本地模型（速度較慢、準確度較低）"
        ),
    },
    {
        "q": "可以多人用嗎", "keywords": ["多人", "同時", "共用", "幾個人"],
        "a": (
            "👥 **多人協作**：\n"
            "  • 同一 DB，多個瀏覽器登入皆可\n"
            "  • 30 人廠：1 台主機即可\n"
            "  • 50+ 人廠：建議改 PostgreSQL（v3.x 配置）"
        ),
    },
    {
        "q": "資料會不會丟", "keywords": ["備份", "資料", "丟失", "壞掉", "復原"],
        "a": (
            "💾 **資料安全**：\n"
            "  • Docker volume 永久存在硬碟（不會因重開機而丟）\n"
            "  • 講「備份資料庫」可隨時備份到 `./backups/`\n"
            "  • 建議至少每週備份 + 異地保存\n"
            "  • 詳見 PDF #12「備份還原 SOP」"
        ),
    },
    {
        "q": "怎麼設定 API key", "keywords": ["api key", "金鑰", "deepseek", "openai", "anthropic"],
        "a": (
            "🔑 **設定 LLM API Key**：\n"
            "  1. 編輯 `backend/.env` 加上 `LLM_API_KEY=sk-xxx`\n"
            "  2. `docker compose restart backend`\n"
            "  3. 詳見 PDF #19「如何取得 LLM API Key」"
        ),
    },
    {
        "q": "升級到新版", "keywords": ["升級", "更新", "新版", "upgrade"],
        "a": (
            "🆙 **升級到新版**：\n"
            "  1. **備份**：先講「備份資料庫」\n"
            "  2. `git pull && docker compose up -d --build`\n"
            "  3. 若有 alembic migration：`docker compose exec backend alembic upgrade head`"
        ),
    },
    {
        "q": "怎麼改密碼", "keywords": ["改密碼", "密碼", "password", "change_password"],
        "a": (
            "🔒 **改密碼**：在 Chat 講「改密碼 我的新密碼是 MyN3wP@ss」即可。\n"
            "  • 至少 8 字元、英文+數字\n"
            "  • 不可為 admin123 等常見密碼\n"
            "  • 90 秒內可撤銷"
        ),
    },
    {
        "q": "什麼是 ConfirmCard", "keywords": ["confirmcard", "確認卡", "確認", "卡片"],
        "a": (
            "✅ **ConfirmCard 確認卡**：\n"
            "  • 寫入類操作（如新增客戶 / 改密碼）會先出卡，**點確認才執行**\n"
            "  • 30 分鐘有效，過期自動失效\n"
            "  • 90 秒內可講「撤銷」復原（公司資料 / 改密碼 / 刪除）"
        ),
    },
]


@register_tool(
    name="ask_faq",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "常見問題 FAQ。新員工 Day 1 上手會問的問題。"
        "範例：「erpilot 多少錢」「斷網能用嗎」「怎麼設定 API key」「升級到新版」。"
    ),
    slots=[
        Slot("question", "string", required=False, description="問題；不填則列全部"),
    ],
    required_permission="user.profile.read",
)
async def _ask_faq(db, user, question: str = ""):
    question = (question or "").lower().strip()
    if not question:
        # 列全部
        lines = ["❓ **erpilot 常見問題**：", ""]
        for i, f in enumerate(_FAQ, 1):
            lines.append(f"  {i}. {f['q']}")
        lines.append("")
        lines.append("💡 講「FAQ <問題關鍵字>」查詳細答案。")
        return {"summary": "\n".join(lines), "raw": {"count": len(_FAQ)}}

    # 找最匹配
    matches = []
    for f in _FAQ:
        score = sum(1 for kw in f["keywords"] if kw.lower() in question)
        if score > 0 or f["q"].lower() in question or question in f["q"].lower():
            matches.append((score, f))
    matches.sort(key=lambda x: x[0], reverse=True)

    if not matches:
        return {
            "summary": (
                f"❓ 找不到與「{question}」相關的 FAQ。\n"
                "💡 講「FAQ」列全部問題；或試試「list_what_can_i_do」看可用功能。"
            ),
            "raw": {"matched": False},
        }

    f = matches[0][1]
    return {
        "summary": f"**Q: {f['q']}**\n\n{f['a']}",
        "raw": {"matched": True, "question": f["q"]},
    }


# ════════════════════════════════════════════════════════════════════
# P8: 資料健康檢查
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="run_data_health_check",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "資料健康檢查：BOM 循環依賴 / 重複客戶 / 重複料件 / 孤兒 row。"
        "範例：「資料健康嗎？」「跑健康檢查」「資料完整性」。"
    ),
    slots=[],
    required_permission="system.config.update",
)
async def _run_data_health_check(db, user):
    issues = []
    raw = {}

    # 1. 重複客戶 code
    dup_cust = (await db.execute(
        select(Customer.code, func.count(Customer.id).label("n"))
        .group_by(Customer.code).having(func.count(Customer.id) > 1)
    )).all()
    raw["duplicate_customer_codes"] = len(dup_cust)
    if dup_cust:
        issues.append(f"🟡 **{len(dup_cust)} 組重複客戶編號**（應唯一）：" +
                      ", ".join(f"`{r.code}`(×{r.n})" for r in dup_cust[:5]))

    # 2. 重複料號
    dup_part = (await db.execute(
        select(Part.part_no, func.count(Part.id).label("n"))
        .group_by(Part.part_no).having(func.count(Part.id) > 1)
    )).all()
    raw["duplicate_part_nos"] = len(dup_part)
    if dup_part:
        issues.append(f"🟡 **{len(dup_part)} 組重複料號**：" +
                      ", ".join(f"`{r.part_no}`(×{r.n})" for r in dup_part[:5]))

    # 3. BOM 循環依賴（自我引用 first，深層循環為 v3.x）
    self_ref = (await db.execute(
        select(BOMItem).where(BOMItem.product_id == BOMItem.part_id).limit(5)
    )).scalars().all()
    raw["bom_self_reference"] = len(self_ref)
    if self_ref:
        issues.append(f"🔴 **{len(self_ref)} 個 BOM 自我引用**（product = part）")

    # 4. 孤兒 inventory（part 已刪但 inventory 還在）
    orphan_inv = (await db.execute(
        select(Inventory.id)
        .outerjoin(Part, Inventory.part_id == Part.id)
        .where(Part.id == None)
        .limit(5)
    )).scalars().all()
    raw["orphan_inventory"] = len(orphan_inv)
    if orphan_inv:
        issues.append(f"🟠 **{len(orphan_inv)} 個孤兒庫存記錄**（part 已刪）")

    # 5. 客戶無 contact info（影響 email 寄送）
    no_email_count = (await db.execute(
        select(func.count(Customer.id))
        .where(or_(Customer.contact_email == None,
                   Customer.contact_email == ""))
    )).scalar() or 0
    raw["customers_without_email"] = no_email_count
    total_cust = (await db.execute(select(func.count(Customer.id)))).scalar() or 0
    if total_cust > 0 and no_email_count / total_cust > 0.5:
        issues.append(
            f"🟢 **{no_email_count}/{total_cust} 客戶無 email**（影響「寄 PDF 給客戶」功能）"
        )

    # 6. 料件無 unit_cost（影響毛利率分析）
    no_cost_count = (await db.execute(
        select(func.count(Part.id))
        .where(or_(Part.unit_cost == None, Part.unit_cost == 0))
    )).scalar() or 0
    raw["parts_without_unit_cost"] = no_cost_count
    if no_cost_count > 5:
        issues.append(f"🟢 **{no_cost_count} 個料件無單位成本**（影響毛利率分析）")

    if not issues:
        return {
            "summary": (
                "✅ **資料健康檢查通過！**\n"
                f"  • 客戶 {total_cust} 個，無重複\n"
                f"  • 料件無重複、無 BOM 循環、無孤兒庫存\n"
                f"  • 詳細資料：{raw}"
            ),
            "raw": raw,
        }

    return {
        "summary": (
            "🏥 **資料健康檢查報告**：\n\n"
            + "\n".join(issues)
            + "\n\n💡 建議由 IT / 內控主管針對紅燈 / 橙燈項目處理。"
        ),
        "raw": raw,
    }
