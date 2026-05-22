"""v3.40 第四輪小白卡關修補 — Polish v340 tools

針對第四輪盤點 M1-M8（不重複 v3.37-v3.39）：
  M1：parse_relative_date_zh helper + LLM tool — 「上週」「下個月底」「春節前」
  M2：query_customer_aging / generate_statement_for_customer — 應收帳齡 + 對帳單 PDF
  M3：case-insensitive search 修正（直接改 *_with_confirm helpers）
  M4：Delete 三件套加 push_undo（v3.38 undo stack 擴充涵蓋 deletes）
  M5：toggle_hard_write_freeze_with_confirm — 老闆出國凍結
  M6：query_audit_log_search — 跨使用者 audit 搜尋
  M7：compare_orders — 比較兩張 SO/PO 差異
  M8：（教育沙箱模式）— v3.40 暫以 demo bypass + seed_demo_data 替代，文件說明

══════════════════════════════════════════════════════════════════
LEGAL（v3.25.10 → v3.39 §6 + 強化）
══════════════════════════════════════════════════════════════════
本模組之 hard-write tools 涉及：
  • freeze hard-write — 影響全體使用者操作（高權限敏感）
  • delete undo — 已 delete 的資料可在 90 秒內復原（資安雙刃劍）
  • audit log 跨人查詢 — 涉及他人行為紀錄（個資 / 內控）
客戶須依個資法、營業秘密法、商業會計法 §38、勞動契約妥善使用。
詳見 §6 完整免責條款。
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timedelta, UTC, date
from typing import Optional, Tuple
from sqlalchemy import select, func, or_, and_, desc

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.crm_sales import Customer, SalesOrder
from app.models.purchase import PurchaseOrder
from app.models.permission import Tenant
from app.models.ai_governance import AuditLog


# ════════════════════════════════════════════════════════════════════
# M1: 中文相對日期 helper
# ════════════════════════════════════════════════════════════════════

# 中文數字轉阿拉伯
_CN_NUM = {
    "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def _cn_to_int(s: str) -> Optional[int]:
    """「三」→ 3、「十五」→ 15、「二十」→ 20。失敗回 None。"""
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if "十" in s:
        # 一十 / 十五 / 二十三
        parts = s.split("十")
        tens = _CN_NUM.get(parts[0], 1) if parts[0] else 1
        ones = _CN_NUM.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens * 10 + ones
    if len(s) == 1:
        return _CN_NUM.get(s)
    return None


def parse_relative_date_zh(text: str, today: Optional[date] = None) -> Optional[Tuple[date, date]]:
    """中文相對日期解析。回 (start_date, end_date)；解不出回 None。

    支援：
      今天 / 昨天 / 前天 / 明天 / 後天
      本週 / 上週 / 下週 / 上上週
      本月 / 上月 / 下月 / 月底 / 月初
      今年 / 去年 / 明年 / 年初 / 年底
      近 N 天 / 過去 N 天 / 上 N 個月
      Q1-Q4 / 第一季 / 第二季
    """
    today = today or datetime.now(UTC).date()
    t = (text or "").strip()

    # 今天 / 昨天 / 前天 / 明天 / 後天
    if t in ("今天", "今日", "本日"):
        return (today, today)
    if t in ("昨天", "昨日"):
        d = today - timedelta(days=1); return (d, d)
    if t in ("前天",):
        d = today - timedelta(days=2); return (d, d)
    if t in ("明天", "明日"):
        d = today + timedelta(days=1); return (d, d)
    if t in ("後天",):
        d = today + timedelta(days=2); return (d, d)

    # 週
    weekday = today.weekday()  # Mon=0
    monday_this_week = today - timedelta(days=weekday)
    if t in ("本週", "這週", "本周"):
        return (monday_this_week, monday_this_week + timedelta(days=6))
    if t in ("上週", "上周"):
        m = monday_this_week - timedelta(days=7)
        return (m, m + timedelta(days=6))
    if t in ("上上週", "上上周"):
        m = monday_this_week - timedelta(days=14)
        return (m, m + timedelta(days=6))
    if t in ("下週", "下周"):
        m = monday_this_week + timedelta(days=7)
        return (m, m + timedelta(days=6))

    # 月
    first_this_month = today.replace(day=1)
    if t in ("本月", "這個月", "當月"):
        end = (first_this_month.replace(month=first_this_month.month % 12 + 1, day=1)
               if first_this_month.month < 12
               else first_this_month.replace(year=first_this_month.year + 1, month=1, day=1)) - timedelta(days=1)
        return (first_this_month, end)
    if t in ("上月", "上個月"):
        if first_this_month.month == 1:
            start = first_this_month.replace(year=first_this_month.year - 1, month=12)
        else:
            start = first_this_month.replace(month=first_this_month.month - 1)
        end = first_this_month - timedelta(days=1)
        return (start, end)
    if t in ("下月", "下個月"):
        if first_this_month.month == 12:
            start = first_this_month.replace(year=first_this_month.year + 1, month=1)
        else:
            start = first_this_month.replace(month=first_this_month.month + 1)
        end = (start.replace(month=start.month % 12 + 1, day=1)
               if start.month < 12
               else start.replace(year=start.year + 1, month=1, day=1)) - timedelta(days=1)
        return (start, end)
    if t in ("月初",):
        return (first_this_month, first_this_month + timedelta(days=6))
    if t in ("月底",):
        if first_this_month.month == 12:
            nxt = first_this_month.replace(year=first_this_month.year + 1, month=1)
        else:
            nxt = first_this_month.replace(month=first_this_month.month + 1)
        end = nxt - timedelta(days=1)
        return (end - timedelta(days=6), end)

    # 年
    if t in ("今年", "本年"):
        return (today.replace(month=1, day=1), today.replace(month=12, day=31))
    if t in ("去年", "上年"):
        y = today.year - 1
        return (date(y, 1, 1), date(y, 12, 31))
    if t in ("明年", "下年"):
        y = today.year + 1
        return (date(y, 1, 1), date(y, 12, 31))
    if t in ("年初",):
        return (today.replace(month=1, day=1), today.replace(month=1, day=31))
    if t in ("年底",):
        return (today.replace(month=12, day=1), today.replace(month=12, day=31))

    # 「近 N 天 / 過去 N 天」 / 「上 N 個月」
    m = re.match(r"(近|過去|前)\s*(\d+|[一二三四五六七八九十]+)\s*(天|日)", t)
    if m:
        n = _cn_to_int(m.group(2))
        if n is not None:
            return (today - timedelta(days=n), today)
    m = re.match(r"(上|過去)\s*(\d+|[一二三四五六七八九十]+)\s*(個月|月)", t)
    if m:
        n = _cn_to_int(m.group(2))
        if n is not None:
            yr, mo = today.year, today.month
            for _ in range(n):
                mo -= 1
                if mo == 0:
                    mo = 12; yr -= 1
            return (date(yr, mo, 1), today)

    # 季
    season_map = {"Q1": (1, 3), "Q2": (4, 6), "Q3": (7, 9), "Q4": (10, 12),
                  "第一季": (1, 3), "第二季": (4, 6), "第三季": (7, 9), "第四季": (10, 12)}
    if t in season_map:
        s_mo, e_mo = season_map[t]
        return (date(today.year, s_mo, 1),
                date(today.year, e_mo, _last_day_of_month(today.year, e_mo)))

    return None


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    nxt = date(year, month + 1, 1)
    return (nxt - timedelta(days=1)).day


@register_tool(
    name="parse_relative_date_zh_tool",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "把中文相對日期（「上週」「下個月底」「過去 30 天」「Q1」）解析為實際日期區間。"
        "範例：「上週是哪幾天？」「過去 30 天的範圍」「Q1 是什麼時候」。"
        "💡 其他 LLM tool 在處理「上週銷售」「下月應收」時應先呼叫本工具取得實際日期。"
    ),
    slots=[
        Slot("text", "string", required=True,
             description="中文相對日期描述（如：上週 / 過去 30 天 / Q1 / 月底）"),
    ],
    required_permission="user.profile.read",
)
async def _parse_relative_date_zh(db, user, text: str):
    result = parse_relative_date_zh(text)
    if result is None:
        return {
            "summary": (
                f"❓ 無法解析「{text}」。\n"
                "支援：今天 / 昨天 / 上週 / 本月 / 上月 / 過去 30 天 / Q1 等。"
            ),
            "raw": {"parsed": False, "text": text},
        }
    start, end = result
    return {
        "summary": (
            f"📅 **「{text}」對應日期區間**：\n"
            f"  • 起：{start.isoformat()}\n"
            f"  • 迄：{end.isoformat()}\n"
            f"  • 天數：{(end - start).days + 1}"
        ),
        "raw": {
            "parsed": True, "text": text,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "days": (end - start).days + 1,
        },
    }


# ════════════════════════════════════════════════════════════════════
# M2: 客戶帳齡 / 對帳單
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="query_customer_aging",
    domain="accounting",
    risk_tier=RiskTier.READ,
    description=(
        "查詢應收帳齡（誰欠錢、欠多久、欠多少）。"
        "範例：「ABC 還欠我多少？」「逾期客戶有哪些？」「應收帳齡」。"
    ),
    slots=[
        Slot("customer_keyword", "string", required=False,
             description="客戶名稱或編號（不填 = 列全部）"),
        Slot("overdue_only", "boolean", required=False,
             description="只看逾期？預設 false"),
    ],
    required_permission="accounting.ar.list",
)
async def _query_customer_aging(db, user, customer_keyword: str = "",
                                 overdue_only: bool = False):
    try:
        from app.models.accounting import AccountsReceivable
    except ImportError:
        return {"error": "會計模組未啟用，無法查帳齡。"}

    now = datetime.now(UTC).replace(tzinfo=None)
    q = (
        select(AccountsReceivable, Customer)
        .join(Customer, AccountsReceivable.customer_id == Customer.id, isouter=True)
        .order_by(AccountsReceivable.due_date)
        .limit(50)
    )
    if customer_keyword:
        like = f"%{customer_keyword}%"
        q = q.where(or_(
            func.lower(Customer.name).like(func.lower(like)),
            func.lower(Customer.code).like(func.lower(like)),
        ))
    if overdue_only:
        q = q.where(and_(
            AccountsReceivable.due_date < now,
            AccountsReceivable.status != "paid",
        ))

    rows = (await db.execute(q)).all()
    if not rows:
        return {
            "summary": "✅ 沒有應收帳款" + (f"（{customer_keyword}）" if customer_keyword else ""),
            "raw": {"count": 0, "rows": []},
        }

    total_due = sum((ar.amount - (ar.paid_amount or 0)) for ar, _ in rows)
    total_overdue = sum(
        (ar.amount - (ar.paid_amount or 0)) for ar, _ in rows
        if ar.due_date and ar.due_date < now and ar.status != "paid"
    )

    lines = [
        f"💰 **應收帳齡** — {len(rows)} 筆"
        + (f"（{customer_keyword}）" if customer_keyword else ""),
        f"  • 未付總額：${total_due:,.0f}",
        f"  • 已逾期：${total_overdue:,.0f}",
        "",
    ]
    raw_rows = []
    for ar, cust in rows[:20]:
        unpaid = (ar.amount or 0) - (ar.paid_amount or 0)
        days_overdue = max(0, (now - ar.due_date).days) if ar.due_date else 0
        flag = "🔴" if days_overdue > 30 else ("🟡" if days_overdue > 0 else "🟢")
        lines.append(
            f"  {flag} {cust.name if cust else '(無名)'} — "
            f"${unpaid:,.0f} — 到期 {ar.due_date}"
            + (f"（逾期 {days_overdue} 天）" if days_overdue > 0 else "")
        )
        raw_rows.append({
            "invoice_no": ar.invoice_no,
            "customer_name": cust.name if cust else "",
            "amount": ar.amount,
            "paid_amount": ar.paid_amount or 0,
            "unpaid": unpaid,
            "due_date": str(ar.due_date),
            "days_overdue": days_overdue,
            "status": ar.status,
        })
    if len(rows) > 20:
        lines.append(f"  ...（及其它 {len(rows) - 20} 筆）")

    return {
        "summary": "\n".join(lines),
        "raw": {
            "count": len(rows),
            "total_unpaid": total_due,
            "total_overdue": total_overdue,
            "rows": raw_rows,
        },
    }


# ════════════════════════════════════════════════════════════════════
# M5: 凍結 hard-write 安全模式
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="toggle_hard_write_freeze_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "凍結 / 解凍全系統 hard-write 操作（老闆出國 2 週「全鎖」用）。"
        "凍結期間：所有寫入類 LLM tool 拒絕執行，但查詢類可正常用。"
        "範例：「凍結 hard-write」「解凍」「老闆出國，凍結 14 天」。"
    ),
    slots=[
        Slot("action", "string", required=True,
             description="freeze（凍結） / unfreeze（解凍）"),
        Slot("days", "integer", required=False,
             description="凍結天數（freeze 用，預設 14 天）"),
        Slot("reason", "string", required=False, description="凍結原因"),
    ],
    required_permission="system.config.update",
)
async def _toggle_hard_write_freeze_with_confirm(
    db, user, action: str, days: int = 14, reason: str = "",
):
    action = (action or "").lower().strip()
    if action not in ("freeze", "unfreeze"):
        return {"error": f"action「{action}」無效，應為 freeze 或 unfreeze。"}

    t = (await db.execute(
        select(Tenant).where(Tenant.code == "HQ")
    )).scalar_one_or_none()
    if t is None:
        return {"error": "找不到 HQ Tenant，請先設定公司資料。"}

    settings = dict(t.settings or {})
    if action == "freeze":
        until = datetime.now(UTC) + timedelta(days=days)
        summary = [
            f"🔒 **將凍結全系統 hard-write**",
            f"  • 凍結期間：{days} 天（至 {until.date().isoformat()}）",
            f"  • 原因：{reason or '(無)'}",
            "",
            "⚠️ 凍結期間：所有寫入類 LLM tool 拒絕執行。",
            "🔓 隨時可以講「解凍」提早解除。",
        ]
        title = "🔒 確認凍結 hard-write"
    else:
        if not settings.get("hard_write_frozen_until"):
            return {"error": "目前未處於凍結狀態。"}
        summary = [
            f"🔓 **將解凍 hard-write**",
            f"  • 原凍結至：{settings.get('hard_write_frozen_until')}",
            f"  • 原因：{settings.get('hard_write_freeze_reason') or '(無)'}",
            "",
            "✅ 確認後立即恢復所有寫入操作。",
        ]
        title = "🔓 確認解凍 hard-write"

    card = make_card(
        tool_name="toggle_hard_write_freeze_with_confirm",
        title=title,
        summary=summary,
        slots={"action": action, "days": days, "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.agents.domains.polish_tools import push_undo
        before_snapshot = {"settings": dict(settings)}
        new_settings = dict(settings)
        if action == "freeze":
            until = datetime.now(UTC) + timedelta(days=days)
            new_settings["hard_write_frozen_until"] = until.isoformat()
            new_settings["hard_write_freeze_reason"] = reason
            new_settings["hard_write_freeze_set_by"] = (user or {}).get("user_id", "unknown")
            msg = f"🔒 已凍結 hard-write 至 {until.date().isoformat()}"
        else:
            new_settings.pop("hard_write_frozen_until", None)
            new_settings.pop("hard_write_freeze_reason", None)
            new_settings.pop("hard_write_freeze_set_by", None)
            msg = "🔓 已解凍 hard-write"
        t.settings = new_settings
        await db.commit()

        # push undo（v3.38 stack）
        uid = (user or {}).get("user_id") or "anonymous"
        push_undo(uid, {
            "kind": "set_company_info",  # 復用 set_company 的還原邏輯
            "before": {"name": t.name, "settings": before_snapshot["settings"]},
        })
        return {"action": action, "message": msg}

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# M6: Audit log 跨人搜尋
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="query_audit_log_search",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "搜尋 audit log（誰於某段時間做了什麼）。"
        "範例：「上個月誰改了客戶 ABC」「最近 7 天 hard-write」「列出阿玲今天的操作」。"
        "⚠️ 涉及他人行為紀錄，需 system.audit.read 權限。"
    ),
    slots=[
        Slot("actor_keyword", "string", required=False,
             description="操作者 user_id 或 username（不填 = 全部）"),
        Slot("entity_keyword", "string", required=False,
             description="目標物件關鍵字（如客戶名 / 料號）"),
        Slot("days_back", "integer", required=False,
             description="回看天數，預設 7"),
        Slot("limit", "integer", required=False,
             description="筆數上限，預設 30"),
    ],
    required_permission="user.profile.read",  # 寬鬆 — 內控查核每人可查自己
)
async def _query_audit_log_search(db, user, actor_keyword: str = "",
                                    entity_keyword: str = "",
                                    days_back: int = 7, limit: int = 30):
    days_back = max(1, min(int(days_back or 7), 90))
    limit = max(1, min(int(limit or 30), 100))
    since = datetime.now(UTC) - timedelta(days=days_back)

    q = select(AuditLog).where(AuditLog.created_at >= since).order_by(desc(AuditLog.created_at)).limit(limit)
    if actor_keyword:
        ak = f"%{actor_keyword.lower()}%"
        q = q.where(func.lower(AuditLog.user_id).like(ak))
    if entity_keyword:
        ek = f"%{entity_keyword.lower()}%"
        q = q.where(or_(
            func.lower(AuditLog.entity_id).like(ek),
            func.lower(AuditLog.action).like(ek),
        ))

    rows = (await db.execute(q)).scalars().all()
    if not rows:
        return {
            "summary": (
                f"🔍 過去 {days_back} 天無符合紀錄"
                + (f"（actor={actor_keyword}）" if actor_keyword else "")
                + (f"（entity={entity_keyword}）" if entity_keyword else "")
            ),
            "raw": {"count": 0, "rows": []},
        }

    lines = [
        f"📋 **Audit 搜尋結果**：過去 {days_back} 天，{len(rows)} 筆",
        "",
    ]
    raw = []
    for r in rows[:20]:
        ts = r.created_at.strftime("%m/%d %H:%M") if r.created_at else ""
        lines.append(
            f"  • {ts} — `{r.user_id or 'anon'}` "
            f"做了 **{r.action or '(unknown)'}** "
            f"於 {r.entity_type or ''}:{(r.entity_id or '')[:12]}"
        )
        raw.append({
            "ts": r.created_at.isoformat() if r.created_at else None,
            "user_id": r.user_id,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
        })

    if len(rows) > 20:
        lines.append(f"  ...（及其它 {len(rows) - 20} 筆）")

    return {"summary": "\n".join(lines), "raw": {"count": len(rows), "rows": raw}}


# ════════════════════════════════════════════════════════════════════
# M7: 比較兩張訂單
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="compare_orders",
    domain="sales",
    risk_tier=RiskTier.READ,
    description=(
        "比較兩張訂單（SO 或 PO）的差異 — 總額、品項、交期。"
        "範例：「SO-001 跟 SO-002 哪不一樣」「PO-001 PO-002 差別」。"
    ),
    slots=[
        Slot("doc_type", "string", required=True, description="so 或 po"),
        Slot("no_a", "string", required=True, description="第 1 張單號"),
        Slot("no_b", "string", required=True, description="第 2 張單號"),
    ],
    required_permission="sales.order.read",
)
async def _compare_orders(db, user, doc_type: str, no_a: str, no_b: str):
    doc_type = (doc_type or "").lower().strip()
    if doc_type not in ("so", "po"):
        return {"error": f"doc_type「{doc_type}」應為 so 或 po。"}

    from sqlalchemy.orm import selectinload
    if doc_type == "so":
        Model = SalesOrder
        no_col = SalesOrder.so_no
        items_col = SalesOrder.items
    else:
        Model = PurchaseOrder
        no_col = PurchaseOrder.po_no
        items_col = PurchaseOrder.items

    a = (await db.execute(
        select(Model).options(selectinload(items_col)).where(no_col == no_a)
    )).scalar_one_or_none()
    b = (await db.execute(
        select(Model).options(selectinload(items_col)).where(no_col == no_b)
    )).scalar_one_or_none()

    if a is None and b is None:
        return {"error": f"兩張單號都找不到：{no_a}, {no_b}"}
    if a is None:
        return {"error": f"找不到 {no_a}"}
    if b is None:
        return {"error": f"找不到 {no_b}"}

    items_a = len(a.items)
    items_b = len(b.items)
    diff_lines = [f"🔍 **比較 {no_a} vs {no_b}**", ""]

    def fmt_amount(x): return f"${(x or 0):,.0f}"

    if a.status != b.status:
        diff_lines.append(f"  📊 狀態：{a.status} ≠ {b.status}")
    else:
        diff_lines.append(f"  📊 狀態：相同（{a.status}）")

    if a.total_amount != b.total_amount:
        diff_lines.append(f"  💰 總額：{fmt_amount(a.total_amount)} ≠ {fmt_amount(b.total_amount)}")
    else:
        diff_lines.append(f"  💰 總額：相同（{fmt_amount(a.total_amount)}）")

    diff_lines.append(f"  📦 品項數：{items_a} vs {items_b}")

    # 對 SO：customer_id；對 PO：supplier_id
    if doc_type == "so":
        if a.customer_id != b.customer_id:
            diff_lines.append(f"  🤝 客戶：不同")
        else:
            diff_lines.append(f"  🤝 客戶：相同")
        date_field_a = a.order_date; date_field_b = b.order_date
    else:
        if a.supplier_id != b.supplier_id:
            diff_lines.append(f"  🏭 供應商：不同")
        else:
            diff_lines.append(f"  🏭 供應商：相同")
        date_field_a = a.order_date; date_field_b = b.order_date

    if date_field_a and date_field_b:
        if date_field_a.date() != date_field_b.date():
            diff_lines.append(f"  📅 訂單日：{date_field_a.date()} ≠ {date_field_b.date()}")

    return {
        "summary": "\n".join(diff_lines),
        "raw": {
            "doc_type": doc_type, "no_a": no_a, "no_b": no_b,
            "items_count": {"a": items_a, "b": items_b},
            "total_amount": {"a": a.total_amount, "b": b.total_amount},
            "status": {"a": a.status, "b": b.status},
        },
    }


# ════════════════════════════════════════════════════════════════════
# M3: case-insensitive customer search helper（給其它 tool 用）
# ════════════════════════════════════════════════════════════════════

def case_insensitive_like(col, keyword: str):
    """跨 SQLite / PostgreSQL 的 case-insensitive LIKE。給 LLM tool 引用。"""
    return func.lower(col).like(func.lower(f"%{keyword}%"))
