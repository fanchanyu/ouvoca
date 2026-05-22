"""v3.42 第六輪小白卡關修補 — Polish v342 tools

針對第六輪盤點 R1-R8（R4 是 middleware / R8 是 frontend，分檔處理）：
  R1：create_user_with_confirm + deactivate_user_with_confirm — 使用者帳號管理
  R2：global_search — 跨表搜尋（客戶+料件+供應商+員工）
  R3：attach_file_to_entity_with_confirm — 附件 LLM 入口
  R5：add_business_days_tw — 工作天計算（含台灣 2026 國定假日）
  R6：export_chat_session — 對話 transcript 匯出
  R7：set_timezone_with_confirm + get_tenant_timezone helper

══════════════════════════════════════════════════════════════════
LEGAL（累積適用 v3.25.10 → v3.41 §6）
══════════════════════════════════════════════════════════════════
本模組之 hard-write tools 涉及：
  • 使用者帳號管理 — 影響全系統存取控制（高敏感）
  • 附件 — 涉及個資 / 商業機密 / 著作權
  • 對話 transcript — 含使用者輸入歷史（個資 / 商業機密）
客戶須依個資法、營業秘密法、勞動契約、著作權法妥善使用。
詳見 §6 完整免責條款。
"""
from __future__ import annotations

import io
import re
import uuid
from datetime import datetime, timedelta, UTC, date
from typing import Optional, Tuple
from sqlalchemy import select, func, desc, or_, and_

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.crm_sales import Customer
from app.models.purchase import Supplier
from app.models.inventory import Part
from app.models.organization import Employee, User
from app.models.permission import Tenant
from app.models.attachment import Attachment
from app.models.ai_governance import ConversationLog


# ════════════════════════════════════════════════════════════════════
# R7: 時區處理
# ════════════════════════════════════════════════════════════════════

# 常見時區白名單（防 user 輸入亂值）
ALLOWED_TIMEZONES = {
    "Asia/Taipei", "Asia/Hong_Kong", "Asia/Shanghai", "Asia/Tokyo",
    "Asia/Seoul", "Asia/Singapore", "Asia/Kuala_Lumpur", "Asia/Bangkok",
    "America/Los_Angeles", "America/New_York", "Europe/London", "UTC",
}


async def get_tenant_timezone(db) -> str:
    """從 HQ Tenant.settings 取時區；找不到回 Asia/Taipei。"""
    t = (await db.execute(
        select(Tenant).where(Tenant.code == "HQ")
    )).scalar_one_or_none()
    if t is None or not t.settings:
        return "Asia/Taipei"
    return (t.settings or {}).get("timezone") or "Asia/Taipei"


def format_dt_local(dt: datetime, tz: str = "Asia/Taipei") -> str:
    """把 datetime 轉為使用者時區之顯示字串。"""
    if dt is None:
        return ""
    try:
        # Python 3.9+ zoneinfo
        from zoneinfo import ZoneInfo
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M") + " UTC"


@register_tool(
    name="set_timezone_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "設定本公司時區（影響所有 LLM 回答之日期 / 時間顯示）。"
        "範例：「公司時區設台北」「換成 Asia/Taipei」「我們在日本」。"
        "預設 Asia/Taipei。"
    ),
    slots=[
        Slot("timezone", "string", required=True,
             description="IANA 時區字串（如 Asia/Taipei / Asia/Tokyo / America/Los_Angeles）"),
    ],
    required_permission="system.config.update",
)
async def _set_timezone_with_confirm(db, user, timezone: str):
    timezone = (timezone or "").strip()
    if timezone not in ALLOWED_TIMEZONES:
        return {
            "error": (
                f"時區「{timezone}」不在白名單。"
                f"支援：{', '.join(sorted(ALLOWED_TIMEZONES))}"
            ),
        }
    old_tz = await get_tenant_timezone(db)

    summary = [
        f"🌏 **將公司時區設為**：{timezone}",
        f"  • 原時區：{old_tz}",
        "",
        f"✅ 確認後所有 LLM 回答之日期 / 時間顯示會用「{timezone}」",
        "⚠️ DB 儲存仍為 UTC（不影響資料），僅影響顯示",
    ]
    card = make_card(
        tool_name="set_timezone_with_confirm",
        title="🌏 確認設定時區",
        summary=summary,
        slots={"timezone": timezone},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        t = (await db.execute(
            select(Tenant).where(Tenant.code == "HQ")
        )).scalar_one_or_none()
        if t is None:
            return {"error": "找不到 HQ Tenant，請先設定公司資料。"}
        settings = dict(t.settings or {})
        settings["timezone"] = timezone
        t.settings = settings
        await db.commit()
        return {"timezone": timezone, "message": f"✅ 時區已設為 {timezone}"}

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# R1: 使用者帳號管理
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="create_user_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "建立新使用者帳號（給新員工開帳號）。"
        "範例：「給阿明開帳號」「新員工小華建帳號 username=hua」。"
        "⚠️ 此操作影響系統存取，僅限授權人員。"
    ),
    slots=[
        Slot("username", "string", required=True,
             description="登入帳號（英數字 / 底線；3-32 字元）"),
        Slot("password", "string", required=True,
             description="初始密碼（≥8 字元；員工首次登入應立即改）"),
        Slot("employee_keyword", "string", required=False,
             description="連結至既有員工（姓名 / 員工編號）"),
        Slot("is_superuser", "boolean", required=False,
             description="是否超級管理員（預設 false）"),
    ],
    required_permission="system.config.update",
)
async def _create_user_with_confirm(
    db, user, username: str, password: str,
    employee_keyword: str = "", is_superuser: bool = False,
):
    if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", username):
        return {"error": f"username「{username}」格式不符（應為英數/底線，3-32 字元）"}

    # 密碼基本強度
    if len(password) < 8:
        return {"error": "密碼至少 8 字元。"}
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return {"error": "密碼需含英文字母 + 數字。"}

    # 檢查 username 唯一
    existing = (await db.execute(
        select(User).where(User.username == username)
    )).scalar_one_or_none()
    if existing is not None:
        return {"error": f"帳號 {username!r} 已存在。"}

    # 連 employee（可選）
    emp = None
    if employee_keyword:
        like = f"%{employee_keyword.lower()}%"
        emp = (await db.execute(
            select(Employee).where(
                or_(
                    func.lower(Employee.name).like(like),
                    func.lower(Employee.employee_no).like(like),
                )
            ).limit(1)
        )).scalar_one_or_none()
        if emp is None:
            return {"error": f"找不到員工「{employee_keyword}」（不連結請留空）"}

    summary = [
        f"👤 **將建立新帳號**：",
        f"  • 帳號：{username}",
        f"  • 密碼長度：{len(password)} 字元",
        f"  • 員工連結：{emp.name + '（' + (emp.employee_no or '') + '）' if emp else '(無)'}",
        f"  • 超級管理員：{'是 ⭐' if is_superuser else '否'}",
        "",
        "⚠️ 確認後立即生效；新員工首次登入應立即改密碼。",
    ]
    if is_superuser:
        summary.insert(
            -2,
            "🔴 **超級管理員不受任何權限限制** — 僅限公司負責人 / 1 名備援",
        )

    card = make_card(
        tool_name="create_user_with_confirm",
        title="👤 確認建立使用者",
        summary=summary,
        # ⚠️ 不把 password 放進 slots
        slots={
            "username": username,
            "password_length": len(password),
            "employee_id": emp.id if emp else None,
            "is_superuser": is_superuser,
        },
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.auth import hash_password
        new_user = User(
            id=str(uuid.uuid4()),
            username=username,
            hashed_password=hash_password(password),
            employee_id=emp.id if emp else None,
            is_active=True,
            is_superuser=is_superuser,
        )
        db.add(new_user)
        await db.commit()
        return {
            "user_id": new_user.id,
            "username": username,
            "message": f"✅ 帳號 {username} 已建立"
            + ("（⭐ 超級管理員）" if is_superuser else "")
            + "；請通知該員工首次登入立即改密碼。",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="deactivate_user_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "停用（不刪除）使用者帳號（給離職員工封存）。"
        "範例：「停用阿明的帳號」「離職員工 hua 帳號封存」。"
    ),
    slots=[
        Slot("username_keyword", "string", required=True,
             description="帳號名稱或員工姓名"),
        Slot("reason", "string", required=False, description="停用原因（留底用）"),
    ],
    required_permission="system.config.update",
)
async def _deactivate_user_with_confirm(
    db, user, username_keyword: str, reason: str = "",
):
    keyword = (username_keyword or "").strip()
    if not keyword:
        return {"error": "請提供帳號或員工姓名。"}

    like = f"%{keyword.lower()}%"
    u = (await db.execute(
        select(User).where(func.lower(User.username).like(like)).limit(1)
    )).scalar_one_or_none()

    if u is None:
        # 試員工姓名 → 找對應 user
        emp = (await db.execute(
            select(Employee).where(func.lower(Employee.name).like(like)).limit(1)
        )).scalar_one_or_none()
        if emp:
            u = (await db.execute(
                select(User).where(User.employee_id == emp.id).limit(1)
            )).scalar_one_or_none()

    if u is None:
        return {"error": f"找不到「{keyword}」之帳號。"}

    if not u.is_active:
        return {"error": f"帳號 {u.username} 已是停用狀態。"}

    summary = [
        f"🚫 **將停用帳號**：",
        f"  • 帳號：{u.username}",
        f"  • 員工 ID：{u.employee_id or '(未連)'}",
        f"  • 超級管理員：{'是' if u.is_superuser else '否'}",
        f"  • 原因：{reason or '(無)'}",
        "",
        "✅ 確認後該帳號**立即無法登入**（不會刪除資料）。",
        "💡 之後仍可重新啟用（is_active=true）",
    ]

    card = make_card(
        tool_name="deactivate_user_with_confirm",
        title="🚫 確認停用帳號",
        summary=summary,
        slots={"user_id": u.id, "username": u.username, "reason": reason},
        risk_tier="hard-write",
        ttl_seconds=900,  # 15 min — 停用較慎重
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        u.is_active = False
        await db.commit()
        return {
            "user_id": u.id,
            "username": u.username,
            "message": f"✅ 帳號 {u.username} 已停用。",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# R2: 全域跨表搜尋
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="global_search",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "跨表搜尋關鍵字（客戶 + 料件 + 供應商 + 員工）— "
        "「ABC 是客戶還是料件？」一次找出所有 ABC 相關。"
        "範例：「找 ABC」「搜尋 M6」「ABC 在哪」。"
    ),
    slots=[
        Slot("keyword", "string", required=True, description="搜尋關鍵字"),
        Slot("limit_per_table", "integer", required=False,
             description="每表最多回幾筆（預設 5）"),
    ],
    required_permission="user.profile.read",
)
async def _global_search(db, user, keyword: str, limit_per_table: int = 5):
    keyword = (keyword or "").strip()
    if not keyword or len(keyword) < 2:
        return {"error": "請提供至少 2 字元的關鍵字。"}
    limit = max(1, min(int(limit_per_table or 5), 20))
    like = f"%{keyword.lower()}%"

    # 並行查 4 表
    cust = (await db.execute(
        select(Customer).where(
            or_(func.lower(Customer.code).like(like),
                func.lower(Customer.name).like(like))
        ).limit(limit)
    )).scalars().all()
    parts = (await db.execute(
        select(Part).where(
            or_(func.lower(Part.part_no).like(like),
                func.lower(Part.name).like(like))
        ).limit(limit)
    )).scalars().all()
    sups = (await db.execute(
        select(Supplier).where(
            or_(func.lower(Supplier.code).like(like),
                func.lower(Supplier.name).like(like))
        ).limit(limit)
    )).scalars().all()
    emps = (await db.execute(
        select(Employee).where(
            or_(func.lower(Employee.name).like(like),
                func.lower(Employee.employee_no).like(like))
        ).limit(limit)
    )).scalars().all()

    total = len(cust) + len(parts) + len(sups) + len(emps)
    if total == 0:
        return {
            "summary": f"🔍 找不到「{keyword}」之相關資料（已搜尋客戶 / 料件 / 供應商 / 員工）",
            "raw": {"count": 0, "matches": {}},
        }

    lines = [f"🔍 **「{keyword}」搜尋結果**（共 {total} 筆）", ""]
    if cust:
        lines.append(f"🤝 **客戶**（{len(cust)}）：")
        for c in cust:
            lines.append(f"  • `{c.code}` - {c.name}")
    if parts:
        lines.append(f"\n📦 **料件**（{len(parts)}）：")
        for p in parts:
            lines.append(f"  • `{p.part_no}` - {p.name}")
    if sups:
        lines.append(f"\n🏭 **供應商**（{len(sups)}）：")
        for s in sups:
            lines.append(f"  • `{s.code}` - {s.name}")
    if emps:
        lines.append(f"\n👤 **員工**（{len(emps)}）：")
        for e in emps:
            lines.append(f"  • {e.name}"
                         + (f"（{e.employee_no}）" if e.employee_no else ""))

    return {
        "summary": "\n".join(lines),
        "raw": {
            "count": total,
            "matches": {
                "customers": [{"id": c.id, "code": c.code, "name": c.name} for c in cust],
                "parts":     [{"id": p.id, "part_no": p.part_no, "name": p.name} for p in parts],
                "suppliers": [{"id": s.id, "code": s.code, "name": s.name} for s in sups],
                "employees": [{"id": e.id, "name": e.name, "employee_no": e.employee_no} for e in emps],
            },
        },
    }


# ════════════════════════════════════════════════════════════════════
# R3: 附件 LLM 入口
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="attach_file_to_entity_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "把已上傳的檔案連結到指定業務單據（SO / PO / Quote）。"
        "範例：「把 file-id-xxx 附到 SO-001」「客戶寄的規格書連到 PO-001」。"
        "⚠️ 須先用 /api/files/upload 上傳取得 file_id。"
    ),
    slots=[
        Slot("file_id", "string", required=True, description="Attachment ID"),
        Slot("entity_type", "string", required=True,
             description="sales_order / purchase_order / quotation"),
        Slot("entity_no", "string", required=True, description="單號"),
    ],
    required_permission="ai.agent.use",
)
async def _attach_file_to_entity_with_confirm(
    db, user, file_id: str, entity_type: str, entity_no: str,
):
    entity_type = (entity_type or "").lower().strip()
    if entity_type not in ("sales_order", "purchase_order", "quotation"):
        return {"error": f"entity_type「{entity_type}」應為 sales_order / purchase_order / quotation。"}

    att = (await db.execute(
        select(Attachment).where(Attachment.id == file_id)
    )).scalar_one_or_none()
    if att is None:
        return {"error": f"找不到檔案 {file_id}（請先用 /api/files/upload 上傳）"}

    # 找 entity 確認存在
    entity_id = None
    entity_label = ""
    if entity_type == "sales_order":
        from app.models.crm_sales import SalesOrder
        e = (await db.execute(
            select(SalesOrder).where(SalesOrder.so_no == entity_no)
        )).scalar_one_or_none()
        if e:
            entity_id = e.id
            entity_label = f"SO {e.so_no}"
    elif entity_type == "purchase_order":
        from app.models.purchase import PurchaseOrder
        e = (await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.po_no == entity_no)
        )).scalar_one_or_none()
        if e:
            entity_id = e.id
            entity_label = f"PO {e.po_no}"
    elif entity_type == "quotation":
        from app.models.quotation import Quotation
        e = (await db.execute(
            select(Quotation).where(Quotation.quote_no == entity_no)
        )).scalar_one_or_none()
        if e:
            entity_id = e.id
            entity_label = f"Quote {e.quote_no}"

    if entity_id is None:
        return {"error": f"找不到 {entity_type}「{entity_no}」"}

    summary = [
        f"📎 **將連結附件**：",
        f"  • 檔案：{att.filename}（{att.size_bytes // 1024} KB）",
        f"  • 連結至：{entity_label}",
        f"  • 類型：{att.content_type}",
    ]

    card = make_card(
        tool_name="attach_file_to_entity_with_confirm",
        title="📎 確認連結附件",
        summary=summary,
        slots={"file_id": file_id, "entity_type": entity_type, "entity_id": entity_id},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        att.parsed_target_type = entity_type
        att.parsed_target_id = entity_id
        att.parsed_status = "parsed"
        att.parsed_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()
        return {
            "file_id": file_id,
            "entity_label": entity_label,
            "message": f"✅ {att.filename} 已連結至 {entity_label}",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# R5: 工作天計算（含台灣 2026 國定假日）
# ════════════════════════════════════════════════════════════════════

# 台灣 2026 國定假日（含補假；資料來源：行政院人事行政總處）
TW_HOLIDAYS_2026 = {
    date(2026, 1, 1),    # 元旦
    date(2026, 2, 15),   # 農曆除夕（補假；2026 春節 2/16-2/20）
    date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
    date(2026, 2, 19), date(2026, 2, 20),
    date(2026, 2, 27),  # 二二八紀念日（連假，假設補休 2/27 週五）
    date(2026, 2, 28),
    date(2026, 4, 3), date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6),  # 清明連假
    date(2026, 5, 1),    # 勞動節
    date(2026, 6, 19), date(2026, 6, 20),  # 端午
    date(2026, 9, 25),   # 中秋（含補假）
    date(2026, 10, 9), date(2026, 10, 10), date(2026, 10, 11),  # 國慶
}


def add_business_days_tw(start_date: date, n_days: int) -> date:
    """加 N 個工作天（跳過週末 + 台灣 2026 國定假日）。"""
    if n_days == 0:
        return start_date
    direction = 1 if n_days > 0 else -1
    remaining = abs(n_days)
    cur = start_date
    while remaining > 0:
        cur = cur + timedelta(days=direction)
        if cur.weekday() < 5 and cur not in TW_HOLIDAYS_2026:
            remaining -= 1
    return cur


def is_business_day_tw(d: date) -> bool:
    return d.weekday() < 5 and d not in TW_HOLIDAYS_2026


@register_tool(
    name="add_business_days_tw",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "計算「N 個工作天後」之日期（自動跳過週末 + 台灣國定假日）。"
        "範例：「今天起 3 個工作天是哪天？」「PO-001 5 個工作天後交期」「下週五是工作天嗎？」"
    ),
    slots=[
        Slot("n_days", "integer", required=True, description="工作天數（可負；如 -3 = 倒推 3 個工作天）"),
        Slot("start_date", "string", required=False, description="起始日期 YYYY-MM-DD（不填 = 今天）"),
    ],
    required_permission="user.profile.read",
)
async def _add_business_days_tw(db, user, n_days: int, start_date: str = ""):
    if start_date:
        try:
            start = date.fromisoformat(start_date)
        except ValueError:
            return {"error": f"start_date「{start_date}」格式錯誤（應為 YYYY-MM-DD）"}
    else:
        # 用 tenant tz 算「今天」
        tz = await get_tenant_timezone(db)
        try:
            from zoneinfo import ZoneInfo
            start = datetime.now(UTC).astimezone(ZoneInfo(tz)).date()
        except Exception:
            start = datetime.now(UTC).date()

    end = add_business_days_tw(start, int(n_days))
    weekday_zh = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]

    return {
        "summary": (
            f"📅 **{abs(n_days)} 個工作天{'後' if n_days >= 0 else '前'}**：\n"
            f"  • 起：{start.isoformat()}（{weekday_zh[start.weekday()]}）\n"
            f"  • 訖：{end.isoformat()}（{weekday_zh[end.weekday()]}）\n"
            f"  • 已跳過：週末 + 台灣國定假日"
        ),
        "raw": {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "n_days": int(n_days),
            "start_weekday": weekday_zh[start.weekday()],
            "end_weekday": weekday_zh[end.weekday()],
        },
    }


# ════════════════════════════════════════════════════════════════════
# R6: 對話 transcript 匯出
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="export_chat_session",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "把對話歷史匯出為 markdown（教育訓練 / 留底）。"
        "範例：「匯出今天的對話」「把 session 對話存下來」。"
        "⚠️ 對話含使用者輸入歷史（可能含個資 / 商業機密），請妥善保管。"
    ),
    slots=[
        Slot("session_id", "string", required=False,
             description="session id（不填 = 本人最近 N 條）"),
        Slot("days_back", "integer", required=False, description="回看天數，預設 1"),
        Slot("limit", "integer", required=False, description="最多訊息數，預設 100"),
    ],
    required_permission="user.profile.read",
)
async def _export_chat_session(
    db, user, session_id: str = "", days_back: int = 1, limit: int = 100,
):
    days_back = max(1, min(int(days_back or 1), 30))
    limit = max(1, min(int(limit or 100), 500))
    since = datetime.now(UTC) - timedelta(days=days_back)

    q = (
        select(ConversationLog)
        .where(ConversationLog.created_at >= since)
        .order_by(ConversationLog.created_at)
        .limit(limit)
    )
    if session_id:
        q = q.where(ConversationLog.session_id == session_id)
    elif user and user.get("user_id"):
        q = q.where(ConversationLog.user_id == user["user_id"])

    rows = (await db.execute(q)).scalars().all()
    if not rows:
        return {
            "summary": f"📝 過去 {days_back} 天無對話紀錄。",
            "raw": {"count": 0, "markdown_base64": ""},
        }

    tz = await get_tenant_timezone(db)

    md_lines = [
        f"# Chat Session Export",
        f"",
        f"- **匯出時間**：{format_dt_local(datetime.now(UTC), tz)}",
        f"- **時區**：{tz}",
        f"- **回看**：過去 {days_back} 天",
        f"- **訊息數**：{len(rows)}",
        f"",
        f"---",
        f"",
    ]
    for r in rows:
        role_icon = "👤" if r.role == "user" else "🤖"
        ts = format_dt_local(r.created_at, tz)
        md_lines.append(f"### {role_icon} {r.role.capitalize()} · {ts}"
                        + (f" · `{r.agent}`" if r.agent else ""))
        md_lines.append("")
        md_lines.append(r.message or "(empty)")
        md_lines.append("")

    md_content = "\n".join(md_lines)
    import base64
    md_b64 = base64.b64encode(md_content.encode("utf-8")).decode("ascii")

    return {
        "summary": (
            f"📝 **對話 transcript 已匯出**：\n"
            f"  • {len(rows)} 則訊息\n"
            f"  • 過去 {days_back} 天\n"
            f"  • 大小：{len(md_content) // 1024 + 1} KB\n"
            f"⚠️ 含使用者輸入歷史，請妥善保管。"
        ),
        "raw": {
            "count": len(rows),
            "session_id": session_id or "(my recent)",
            "markdown_base64": md_b64,
            "filename": f"chat-export-{datetime.now(UTC).strftime('%Y%m%d-%H%M')}.md",
            "fmt": "md",
            "entity": "chat-transcript",
        },
    }
