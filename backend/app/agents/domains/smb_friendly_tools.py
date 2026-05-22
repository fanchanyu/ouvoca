"""電腦小白友善 LLM tools 補完 (v3.35)

回答客戶第一天上手就會問的問題：
  「我是誰？」「Ouvoca 好嗎？」「我能對 AI 講什麼？」
  「我做過什麼？」「上週問過什麼？」「客戶 X 全部資料」
  「給阿玲採購權限」「拿掉阿明的會計權限」

══════════════════════════════════════════════════════════════════
LEGAL（累積適用 v3.25.10 → v3.34.1 §6）
══════════════════════════════════════════════════════════════════
本模組之 hard-write（grant/revoke role）影響系統存取控制。
  • 給某員工角色 = 給他該角色所有 permission（含寫入 / 刪除）
  • 拿掉角色 = 該員工立即失去存取
  • 重大角色變更應額外有書面審批 + 對應 HR/法務記錄

於適用法律所允許之最大範圍內，Ouvoca 對誤授權所衍生之資料外洩 /
契約爭議 / 違規操作不承擔責任。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, func

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.organization import Employee, User
from app.models.permission import RoleDef, UserRoleAssignment
from app.models.ai_governance import ConversationLog, AuditLog
from app.models.crm_sales import Customer, SalesOrder


# ════════════════════════════════════════════════════════════════════
# 1. whoami — 「我是誰？」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="whoami",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "查詢我目前登入的身分（姓名、員工編號、部門、角色）。"
        "範例：「我是誰？」「我登入是誰？」「我有什麼權限？」"
    ),
    slots=[],
    required_permission="user.profile.read",
)
async def _whoami(db, user):
    if not user or not user.get("employee_id"):
        return {"summary": "❓ 尚未登入或無 employee_id", "raw": {"logged_in": False}}

    emp = (await db.execute(
        select(Employee).where(Employee.id == user["employee_id"])
    )).scalar_one_or_none()
    if emp is None:
        return {"summary": f"⚠️ 員工資料缺失（employee_id={user['employee_id']}）",
                "raw": {"logged_in": True}}

    # Get user roles
    u = (await db.execute(
        select(User).where(User.employee_id == emp.id)
    )).scalar_one_or_none()

    roles_info = []
    if u:
        assignments = (await db.execute(
            select(UserRoleAssignment, RoleDef)
            .join(RoleDef, RoleDef.id == UserRoleAssignment.role_id)
            .where(
                UserRoleAssignment.user_id == u.id,
                UserRoleAssignment.is_active == True,
            )
        )).all()
        roles_info = [r.name_zh or r.code for _a, r in assignments]

    lines = [
        f"👤 **{emp.name}**（員工編號 {emp.employee_no}）",
        f"📞 {emp.email or '(未填 email)'}",
        f"💼 職稱：{emp.title or '(未設)'}",
    ]
    if u:
        lines.append(f"🔑 登入帳號：{u.username}")
        if u.is_superuser:
            lines.append("⭐ **超級管理員**（不受權限限制）")
    if roles_info:
        lines.append(f"🎭 角色：{', '.join(roles_info)}")
    else:
        lines.append("🎭 角色：(尚無)")

    return {
        "summary": "\n".join(lines),
        "raw": {
            "employee_no": emp.employee_no,
            "name": emp.name,
            "username": u.username if u else None,
            "is_superuser": u.is_superuser if u else False,
            "roles": roles_info,
            "logged_in": True,
        },
    }


# ════════════════════════════════════════════════════════════════════
# 2. system_health — 「Ouvoca 怎麼樣了？」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="system_health",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "查詢 Ouvoca 系統健康狀態（DB / LLM / 服務）。"
        "範例：「Ouvoca 好嗎？」「系統正常嗎？」"
    ),
    slots=[],
    required_permission="system.health.read",
)
async def _system_health(db, user):
    from app.config import settings

    # DB ping
    try:
        await db.execute(select(func.count()).select_from(Employee))
        db_ok = True
        db_msg = "✅ DB 正常"
    except Exception as e:
        db_ok = False
        db_msg = f"❌ DB 異常：{str(e)[:80]}"

    # LLM status (依 settings)
    llm_provider = settings.LLM_PROVIDER
    llm_has_key = bool(settings.LLM_API_KEY) and "change" not in settings.LLM_API_KEY.lower()
    llm_msg = f"✅ LLM 設定（{llm_provider}）" if llm_has_key else f"⚠️ LLM API key 未設定（provider: {llm_provider}）"

    # Count entities
    counts = {}
    try:
        counts["employees"] = (await db.execute(
            select(func.count()).select_from(Employee).where(Employee.id != None)
        )).scalar() or 0
        counts["customers"] = (await db.execute(
            select(func.count()).select_from(Customer)
        )).scalar() or 0
        counts["sales_orders"] = (await db.execute(
            select(func.count()).select_from(SalesOrder)
        )).scalar() or 0
    except Exception:
        pass

    lines = [
        "🩺 **Ouvoca 系統健康檢查**",
        "",
        db_msg,
        llm_msg,
        f"📊 系統版本：{settings.APP_VERSION}",
        "",
        "**資料量**：",
        f"  • 員工：{counts.get('employees', '?')}",
        f"  • 客戶：{counts.get('customers', '?')}",
        f"  • 銷售單：{counts.get('sales_orders', '?')}",
    ]
    return {
        "summary": "\n".join(lines),
        "raw": {"db_ok": db_ok, "llm_has_key": llm_has_key,
                "version": settings.APP_VERSION, "counts": counts},
    }


# ════════════════════════════════════════════════════════════════════
# 3. list_what_can_i_do — 「我能對 AI 講什麼？」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="list_what_can_i_do",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "📚 列出我能對 Ouvoca 講的話 / 能做的事（top 20）。"
        "範例：「我能做什麼？」「Ouvoca 會做什麼？」「教我用法」"
    ),
    slots=[
        Slot("category", "string", required=False,
             description="purchase/sales/inventory/production/quality/accounting/tax；不填則全部"),
    ],
    required_permission=None,  # 任何登入者都能查
)
async def _list_what_can_i_do(db, user, category: str = None):
    # 提示性清單 — 從 ICP 老闆角度，列最常用 LLM tools
    examples_by_cat = {
        "業務": [
            "「幫長江廠報 100 個 M6 螺絲 @ 5 元」 → 建立報價單",
            "「客戶接受了，QUO-001 轉訂單」 → 自動建 SO",
            "「為 SO-001 開發票」 → 開立電子發票",
            "「客戶 X 還欠多少？」 → 查 AR",
        ],
        "採購": [
            "「跟長江廠下 100 個 M6 螺絲」 → 建立採購單",
            "「該補哪些料？」 → 智慧採購建議",
            "「PO-001 改成 200 個」 → 修改 PO 行",
            "「PO-001 交期改 6/5」 → 改交期",
            "「收貨入庫 PO-001」 → PO 收貨",
        ],
        "庫存": [
            "「庫存有多少 M6 螺絲？」 → 查庫存",
            "「我要月底盤點」 → 建立盤點單",
            "「批次 keyin: M6=95, M8=200」 → 批次登錄實盤",
        ],
        "生產": [
            "「釋放工單 WO-001」 → WO 釋放",
            "「完工 WO-001 100 個」 → 報工",
            "「PROD-001 的 BOM 是什麼？」 → 查做法",
        ],
        "品保": [
            "「QC 合格 100 個」 → 完成檢驗",
            "「為 INS-001 開不合格單」 → 建立 NCR",
            "「為 NCR-001 開矯正措施」 → 建立 CAPA",
        ],
        "規劃": [
            "「我們的瓶頸在哪？」 → TOC 瓶頸分析",
            "「該不該接這張單？」 → Throughput 評估",
            "「下個月該備多少 M6？」 → 需求預測",
            "「今天該注意什麼？」 → 每日簡報",
            "「為什麼下週這麼忙？」 → 計畫解釋",
        ],
        "稅務": [
            "「這個月營業稅多少？」 → 月度稅務概況",
            "「查 12345678 統編對不對」 → 驗證統編",
        ],
        "管理": [
            "「給阿玲採購權限」 → 角色授權",
            "「我有什麼要審？」 → 待審清單",
            "「批准 REQ-001」 → 批准",
            "「我是誰？」 → 身份查詢",
        ],
    }

    if category:
        cat_map = {
            "purchase": "採購", "sales": "業務", "inventory": "庫存",
            "production": "生產", "quality": "品保", "accounting": "管理",
            "tax": "稅務", "planning": "規劃",
        }
        cat_zh = cat_map.get(category.lower(), category)
        examples = {cat_zh: examples_by_cat.get(cat_zh, [])}
    else:
        examples = examples_by_cat

    lines = ["💡 **Ouvoca 能做的事**（你可以對 AI 講以下話）：\n"]
    for cat, items in examples.items():
        if not items:
            continue
        lines.append(f"### {cat}")
        for it in items:
            lines.append(f"  • {it}")
        lines.append("")
    lines.append("💬 不知道從哪開始？試試「今天該注意什麼？」")

    return {"summary": "\n".join(lines), "raw": {"categories": list(examples.keys())}}


# ════════════════════════════════════════════════════════════════════
# 4. query_my_recent_actions — 「我做過什麼？」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="query_my_recent_actions",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "📜 查詢我最近做過的操作（建單 / 改單 / 審批）。"
        "範例：「我做過什麼？」「我今天操作什麼？」"
    ),
    slots=[
        Slot("days", "integer", required=False, description="查幾天內（預設 7）"),
        Slot("limit", "integer", required=False, description="筆數上限（預設 20）"),
    ],
    required_permission="audit.log.read",
)
async def _query_my_recent_actions(db, user, days: int = 7, limit: int = 20):
    uid = (user or {}).get("user_id") or (user or {}).get("employee_id")
    if not uid:
        return {"error": "尚未登入或缺 user_id"}

    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    rows = (await db.execute(
        select(AuditLog)
        .where(
            AuditLog.user_id == uid,
            AuditLog.created_at >= since,
        )
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )).scalars().all()

    if not rows:
        return {
            "summary": f"✅ 過去 {days} 天我沒有操作紀錄",
            "raw": {"items": [], "days": days},
        }

    lines = [f"📜 **最近 {days} 天我的操作（{len(rows)} 筆）**：\n"]
    for r in rows[:limit]:
        time_str = r.created_at.strftime("%m/%d %H:%M") if r.created_at else "?"
        lines.append(
            f"  • {time_str} | {r.action[:40]} | {r.entity_type or 'system'} "
            f"({r.result if hasattr(r, 'result') else ''})"
        )
    return {
        "summary": "\n".join(lines),
        "raw": {"count": len(rows), "days": days},
    }


# ════════════════════════════════════════════════════════════════════
# 5. search_chat_history — 「我上週問過什麼？」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="search_chat_history",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "🔍 搜尋我過去對 AI 講過的話。範例：「上週我問過利潤？」「找 BOM 的對話」"
    ),
    slots=[
        Slot("keyword", "string", required=True, description="關鍵字"),
        Slot("days", "integer", required=False, description="查幾天內（預設 30）"),
    ],
    required_permission="chat.history.read",
)
async def _search_chat_history(db, user, keyword: str, days: int = 30):
    uid = (user or {}).get("user_id")
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    q = select(ConversationLog).where(
        ConversationLog.created_at >= since,
    )
    if uid:
        q = q.where(ConversationLog.user_id == uid)
    # search in user_input field
    if hasattr(ConversationLog, "user_input"):
        q = q.where(ConversationLog.user_input.contains(keyword))
    q = q.order_by(ConversationLog.created_at.desc()).limit(20)
    rows = (await db.execute(q)).scalars().all()

    if not rows:
        return {
            "summary": f"❓ 過去 {days} 天找不到含「{keyword}」的對話",
            "raw": {"keyword": keyword, "items": []},
        }

    lines = [f"🔍 **找到 {len(rows)} 筆含「{keyword}」的對話**：\n"]
    for r in rows[:10]:
        t = r.created_at.strftime("%m/%d %H:%M") if r.created_at else "?"
        prompt = (getattr(r, "user_input", "") or "")[:80]
        lines.append(f"  • {t}: {prompt}...")
    return {"summary": "\n".join(lines), "raw": {"count": len(rows)}}


# ════════════════════════════════════════════════════════════════════
# 6. query_customer_360 — 「客戶 X 全部資料」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="query_customer_360",
    domain="crm",
    risk_tier=RiskTier.READ,
    description=(
        "👤 客戶 360 度全貌：基本資料 + 所有 SO + 信用額度 + 最近活動。"
        "範例：「客戶 X 全部資料」「長江廠最近狀況」"
    ),
    slots=[
        Slot("customer_keyword", "string", required=True),
    ],
    required_permission="crm.customer.read",
)
async def _query_customer_360(db, user, customer_keyword: str):
    cu = (await db.execute(
        select(Customer).where(
            (Customer.code == customer_keyword) |
            (Customer.name.contains(customer_keyword))
        )
    )).scalars().first()
    if cu is None:
        return {"error": f"找不到客戶「{customer_keyword}」"}

    # SO 統計
    so_rows = (await db.execute(
        select(SalesOrder).where(SalesOrder.customer_id == cu.id)
        .order_by(SalesOrder.created_at.desc())
        .limit(10)
    )).scalars().all()
    so_total = sum((s.total_amount or 0) for s in so_rows)
    so_recent = so_rows[:5]

    lines = [
        f"👤 **{cu.code} - {cu.name}**",
        "",
        f"📞 聯絡人：{cu.contact_person or '(未填)'} / {cu.contact_email or '?'} / {cu.contact_phone or '?'}",
        f"🏠 地址：{cu.address or '(未填)'}",
        f"💳 付款條件：{cu.payment_terms or '(未設)'}",
        f"💰 信用額度：${cu.credit_limit or 0:,.0f}",
        f"⭐ 等級：{cu.grade}",
        f"📊 狀態：{'active' if cu.is_active else 'inactive'}",
        "",
        f"📋 **最近 10 張 SO**（合計 ${so_total:,.0f}）：",
    ]
    if not so_rows:
        lines.append("  （無 SO 紀錄）")
    else:
        for s in so_recent:
            lines.append(
                f"  • {s.so_no} | {s.status} | ${s.total_amount or 0:,.0f}"
            )

    return {
        "summary": "\n".join(lines),
        "raw": {
            "customer_no": cu.code, "name": cu.name,
            "credit_limit": cu.credit_limit,
            "so_count": len(so_rows), "so_total": so_total,
            "is_active": cu.is_active,
        },
    }


# ════════════════════════════════════════════════════════════════════
# 7. grant_role_with_confirm — 「給阿玲採購權限」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="grant_role_with_confirm",
    domain="permission",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "🔑 給某員工角色（賦予他該角色之全部權限）。"
        "範例：「給阿玲採購權限」「阿明加會計角色」"
    ),
    slots=[
        Slot("employee_keyword", "string", required=True, description="員工姓名或編號"),
        Slot("role_code", "string", required=True,
             description="角色 code（如 procurement_clerk / accountant / warehouse_keeper）"),
        Slot("reason", "string", required=False, description="授權原因（建議填）"),
    ],
    required_permission="permission.role.assign",
)
async def _grant_role_with_confirm(
    db, user, employee_keyword: str, role_code: str, reason: str = "",
):
    emp = (await db.execute(
        select(Employee).where(
            (Employee.employee_no == employee_keyword) |
            (Employee.name.contains(employee_keyword))
        )
    )).scalars().first()
    if emp is None:
        return {"error": f"找不到員工「{employee_keyword}」"}

    u = (await db.execute(
        select(User).where(User.employee_id == emp.id)
    )).scalar_one_or_none()
    if u is None:
        return {"error": f"員工 {emp.name} 尚未建立登入帳號"}

    role = (await db.execute(
        select(RoleDef).where(RoleDef.code == role_code)
    )).scalar_one_or_none()
    if role is None:
        return {
            "error": f"找不到角色 code「{role_code}」",
            "hint": "可用 list_roles 查所有可選角色",
        }

    summary = [
        f"🔑 **授予角色**",
        f"員工：{emp.name} (員工編號 {emp.employee_no})",
        f"角色：{role.name_zh or role.code} (code: {role.code})",
        f"原因：{reason or '(未填，建議填以供日後追溯)'}",
        "",
        "⚠️ 授權後該員工**立即**擁有此角色之全部權限",
        "⚠️ 重大角色（如 super_admin / finance_manager）建議書面審批",
    ]
    card = make_card(
        tool_name="grant_role_with_confirm",
        title="🔑 確認授予角色",
        summary=summary,
        slots={"user_id": u.id, "role_id": role.id,
               "employee_name": emp.name, "role_code": role.code,
               "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.permission import assign_role
        actor_id = (user or {}).get("employee_id") or "system"
        # tenant_id from user context; fallback to HQ
        tenant_id = (user or {}).get("tenant_id") or "HQ"
        try:
            assigned = await assign_role(
                db, user_id=u.id, role_id=role.id,
                tenant_id=tenant_id, actor_id=actor_id, reason=reason,
            )
            return {
                "employee": emp.name, "role": role.code,
                "message": f"✅ 已授予 {emp.name} 「{role.name_zh or role.code}」角色",
            }
        except Exception as e:
            return {"error": f"授權失敗：{str(e)[:100]}"}

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# 8. revoke_role_with_confirm — 「拿掉阿明的會計權限」
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="revoke_role_with_confirm",
    domain="permission",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "❌ 拿掉某員工的角色（撤銷該角色之全部權限）。"
        "範例：「拿掉阿明會計權限」「阿玲不做採購了」"
    ),
    slots=[
        Slot("employee_keyword", "string", required=True),
        Slot("role_code", "string", required=True),
        Slot("reason", "string", required=False, description="撤銷原因（建議填）"),
    ],
    required_permission="permission.role.assign",
)
async def _revoke_role_with_confirm(
    db, user, employee_keyword: str, role_code: str, reason: str = "",
):
    emp = (await db.execute(
        select(Employee).where(
            (Employee.employee_no == employee_keyword) |
            (Employee.name.contains(employee_keyword))
        )
    )).scalars().first()
    if emp is None:
        return {"error": f"找不到員工「{employee_keyword}」"}

    u = (await db.execute(
        select(User).where(User.employee_id == emp.id)
    )).scalar_one_or_none()
    if u is None:
        return {"error": f"員工 {emp.name} 無登入帳號"}

    role = (await db.execute(
        select(RoleDef).where(RoleDef.code == role_code)
    )).scalar_one_or_none()
    if role is None:
        return {"error": f"找不到角色「{role_code}」"}

    assignment = (await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == u.id,
            UserRoleAssignment.role_id == role.id,
            UserRoleAssignment.is_active == True,
        )
    )).scalar_one_or_none()
    if assignment is None:
        return {"error": f"員工 {emp.name} 目前未持有「{role.name_zh or role.code}」角色"}

    summary = [
        f"❌ **撤銷角色**",
        f"員工：{emp.name} (員工編號 {emp.employee_no})",
        f"角色：{role.name_zh or role.code}",
        f"原因：{reason or '(未填，建議填)'}",
        "",
        "⚠️ 撤銷後該員工**立即**失去此角色之全部權限",
        "⚠️ 該員工進行中之工作可能中斷（如批准流程、未完成單據）",
    ]
    card = make_card(
        tool_name="revoke_role_with_confirm",
        title="❌ 確認撤銷角色",
        summary=summary,
        slots={"assignment_id": assignment.id, "employee_name": emp.name,
               "role_code": role.code, "reason": reason},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        assignment.is_active = False
        await db.commit()
        return {
            "employee": emp.name, "role": role.code,
            "message": f"✅ 已撤銷 {emp.name} 的「{role.name_zh or role.code}」角色",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# Register agents
# ════════════════════════════════════════════════════════════════════

from app.agents.engine import AGENT_REGISTRY as _AGENT_REGISTRY, register_agent

if "system" not in _AGENT_REGISTRY:
    register_agent(
        "system", "SystemAgent",
        system_prompt=(
            "你是 Ouvoca 之**系統助手**。職責：whoami / 健康檢查 / 「我能做什麼」/ "
            "個人操作歷史 / 對話歷史搜尋。回答簡潔有 emoji，主動引導使用者用其他 tool。"
        ),
        tool_names=[
            "whoami", "system_health", "list_what_can_i_do",
            "query_my_recent_actions", "search_chat_history",
        ],
    )

# permission agent
if "permission" not in _AGENT_REGISTRY:
    register_agent(
        "permission", "PermissionAgent",
        system_prompt=(
            "你是 Ouvoca 之**權限管理助手**。職責：授予 / 撤銷角色。"
            "**重大角色變更必走 ConfirmCard**。建議使用者填撤銷 / 授權原因以供日後追溯。"
        ),
        tool_names=["grant_role_with_confirm", "revoke_role_with_confirm"],
    )

# Attach customer 360 to crm agent
if "crm" in _AGENT_REGISTRY:
    _tn = _AGENT_REGISTRY["crm"]["tool_names"]
    if "query_customer_360" not in _tn:
        _tn.append("query_customer_360")
