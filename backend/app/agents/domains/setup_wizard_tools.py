"""安裝精靈 LLM tools (v3.37) — Day 0/1 全面補完電腦小白卡關點

修以下硬傷：
  D0-4：set_company_info_with_confirm — PDF 不再印「Ouvoca 範例公司」
  D0-2：change_my_password_with_confirm — 強制改預設 admin/admin123
  D2-2：list_available_roles — 角色中文化（不再天書）
  D2-4：show_import_excel_guide — 一步一步引導匯入 Excel
  D2-5：proactive_alerts — 主動偵測「應收逾期 / 低庫存 / 待簽核」

══════════════════════════════════════════════════════════════════
LEGAL（累積適用 v3.25.10 → v3.36 §6）
══════════════════════════════════════════════════════════════════
本模組之 hard-write tools 影響 Tenant 主檔 / User 密碼 / 角色配置。
這些是高敏感操作，Ouvoca 已強制 ConfirmCard + audit log。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, func, and_

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.permission import Tenant, RoleDef, UserRoleAssignment
from app.models.organization import User, Employee


# ════════════════════════════════════════════════════════════════════
# D0-4: 設定我的公司
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="set_company_info_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "設定本公司基本資料（名稱 / 統編 / 地址 / 電話）— 之後所有 PDF "
        "（報價單 / 採購單 / 銷售單 / 出貨單）會自動印這份資料而非預設值。"
        "範例：「公司叫長江精密」「統編 12345678」「地址改台北市信義區...」。"
    ),
    slots=[
        Slot("name", "string", required=True, description="公司全名（如：長江精密股份有限公司）"),
        Slot("tax_id", "string", required=False, description="統一編號（8 碼數字）"),
        Slot("address", "string", required=False, description="登記地址"),
        Slot("phone", "string", required=False, description="公司主電話"),
    ],
    required_permission="system.config.update",
)
async def _set_company_info_with_confirm(
    db, user, name: str, tax_id: str = "", address: str = "", phone: str = "",
):
    # 找 HQ Tenant — 若不存在則建一個（小白第一次設定時可能還沒 HQ）
    tenant = (await db.execute(
        select(Tenant).where(Tenant.code == "HQ")
    )).scalar_one_or_none()

    # 簡單驗證統編（台灣 8 碼）
    if tax_id and not re.fullmatch(r"\d{8}", tax_id):
        return {"error": f"統編「{tax_id}」格式錯誤（應為 8 碼數字）。"}

    old_name = (tenant.settings or {}).get("name") if tenant else None
    old_name = old_name or (tenant.name if tenant else "(無)")

    summary = [
        f"📝 **公司名稱**：{old_name} → **{name}**",
    ]
    if tax_id:
        summary.append(f"🧾 **統一編號**：{tax_id}")
    if address:
        summary.append(f"📮 **地址**：{address[:60]}")
    if phone:
        summary.append(f"📞 **電話**：{phone}")
    summary.append("")
    summary.append("✅ 確認後此公司資料將印在所有後續 PDF 上。")

    card = make_card(
        tool_name="set_company_info_with_confirm",
        title="🏢 確認設定公司資料",
        summary=summary,
        slots={"name": name, "tax_id": tax_id, "address": address, "phone": phone},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        import uuid
        nonlocal tenant
        # v3.38 N2：執行前先快照 before-state 推入 undo stack
        from app.agents.domains.polish_tools import push_undo
        before_snapshot = None
        if tenant is not None:
            before_snapshot = {
                "name": tenant.name,
                "settings": dict(tenant.settings or {}),
            }

        if tenant is None:
            tenant = Tenant(
                id=str(uuid.uuid4()), code="HQ",
                name=name, tenant_type="hq", is_active=True,
                settings={"name": name, "tax_id": tax_id,
                          "address": address, "phone": phone},
            )
            db.add(tenant)
        else:
            tenant.name = name
            settings = dict(tenant.settings or {})
            settings.update({"name": name, "tax_id": tax_id,
                              "address": address, "phone": phone})
            tenant.settings = settings
        await db.commit()

        # 推入 undo（only if had a previous tenant — 新建的不撤銷）
        if before_snapshot is not None:
            user_id = (user or {}).get("user_id") or (user or {}).get("employee_id") or "anonymous"
            push_undo(user_id, {
                "kind": "set_company_info",
                "before": before_snapshot,
            })

        return {
            "tenant_id": tenant.id,
            "message": f"✅ 公司資料已更新為「{name}」（90 秒內可撤銷）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# D0-2: 改自己的密碼
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="change_my_password_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "修改自己的登入密碼。**安裝後首要動作** — 預設 admin/admin123 必須換掉。"
        "範例：「改密碼」「我要改密碼成 MyN3wP@ss」「密碼換掉」。"
    ),
    slots=[
        Slot("new_password", "string", required=True,
             description="新密碼（≥8 字元、需有英文 + 數字）"),
    ],
    required_permission="user.profile.read",
)
async def _change_my_password_with_confirm(db, user, new_password: str):
    if not user or not user.get("user_id"):
        return {"error": "尚未登入，無法改密碼。"}

    # 基本密碼強度檢查
    if len(new_password) < 8:
        return {"error": "密碼太短，至少 8 字元。"}
    if not re.search(r"[A-Za-z]", new_password):
        return {"error": "密碼需包含至少 1 個英文字母。"}
    if not re.search(r"\d", new_password):
        return {"error": "密碼需包含至少 1 個數字。"}
    if new_password.lower() in {"admin123", "password", "12345678"}:
        return {"error": f"「{new_password}」太常見，請換更安全的。"}

    u = (await db.execute(
        select(User).where(User.id == user["user_id"])
    )).scalar_one_or_none()
    if u is None:
        return {"error": "找不到您的帳號。"}

    summary = [
        f"👤 帳號：{u.username}",
        f"🔒 將更新為新密碼（長度 {len(new_password)} 字元）",
        "",
        "⚠️ 確認後此密碼立即生效；舊密碼無法登入。",
        "📝 請記在安全的地方（不要寫在便利貼上！）。",
    ]

    card = make_card(
        tool_name="change_my_password_with_confirm",
        title="🔑 確認修改密碼",
        summary=summary,
        # ⚠️ 不把 new_password 放進 slots（會被 audit log 記到）
        slots={"user_id": u.id, "username": u.username,
               "password_length": len(new_password)},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    # closure 抓 new_password；不會被 stash 到 DB
    async def execute():
        from app.services.auth import hash_password
        from app.agents.domains.polish_tools import push_undo
        # v3.38 N2：先存舊密碼 hash，供 90 秒內撤銷
        old_hash = u.hashed_password
        u.hashed_password = hash_password(new_password)
        await db.commit()
        # 推 undo（舊 hash 已記，撤銷時直接還原）
        user_id = (user or {}).get("user_id") or (user or {}).get("employee_id") or "anonymous"
        push_undo(user_id, {
            "kind": "change_password",
            "before": {"user_id": u.id, "hashed_password": old_hash},
        })
        return {
            "username": u.username,
            "message": "✅ 密碼已更新，下次登入請用新密碼（90 秒內可撤銷）。",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# D2-2: 列出角色 — 中文化（不再天書）
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="list_available_roles",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "列出系統內所有可指派的角色（含中文名 + 權限數）。"
        "範例：「我可以給哪些角色？」「列出全部角色」。"
    ),
    slots=[],
    required_permission="permission.role.read",
)
async def _list_available_roles(db, user):
    roles = (await db.execute(
        select(RoleDef).order_by(RoleDef.code)
    )).scalars().all()
    if not roles:
        return {"summary": "（系統尚未建立任何角色）", "raw": {"roles": []}}

    lines = [f"🎭 **可指派角色清單**（{len(roles)} 個）：", ""]
    raw = []
    for r in roles:
        zh = r.name_zh or "(無中文名)"
        desc = r.description or "(無說明)"
        lines.append(f"- **{zh}** (`{r.code}`)")
        lines.append(f"  {desc[:80]}")
        raw.append({"code": r.code, "name_zh": r.name_zh,
                    "description": r.description})
    lines.append("")
    lines.append("💡 想授權：「給阿玲 採購經理 角色」or 「拿掉阿明的會計權限」。")

    return {"summary": "\n".join(lines), "raw": {"roles": raw}}


# ════════════════════════════════════════════════════════════════════
# D2-4: 匯入 Excel 步驟引導
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="show_import_excel_guide",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "顯示「我要匯入 Excel」一步一步引導。"
        "範例：「我要匯入客戶清單」「匯入既有的料件 Excel」「鼎新資料怎麼搬過來」。"
    ),
    slots=[
        Slot("entity", "string", required=False,
             description="哪一種資料：customers / parts / suppliers（不填則列總覽）"),
    ],
    required_permission="user.profile.read",
)
async def _show_import_excel_guide(db, user, entity: str = ""):
    entity = (entity or "").lower().strip()

    common = [
        "📥 **匯入 Excel — 3 步流程**：",
        "",
        "1️⃣ **準備 Excel 檔**",
        "   - 第一列：欄位名（可中文或英文）",
        "   - 後續每列：一筆資料",
        "   - 存成 `.xlsx` 或 `.csv`",
        "",
        "2️⃣ **連到外部資料**",
        "   - 用 LLM 工具：「列出外部資料連線」→ 若無，先建（鼎新 / 正航 / Excel 上傳）",
        "   - 或直接「上傳 Excel 客戶清單」（Settings → 外部資料）",
        "",
        "3️⃣ **執行匯入（含 ConfirmCard 確認）**",
        "   - 工具：「把外部 customers 表的資料搬進來」",
        "   - AI 會自動對映欄位 → 顯示「我準備寫入 35 筆，要繼續嗎？」",
        "   - 點確認 → 完成（已存在的自動 skip）",
        "",
    ]
    by_entity = {
        "customers": [
            "🎯 **客戶清單匯入**：必要欄位：name；建議：code / contact_person / contact_phone / credit_limit。"
        ],
        "parts": [
            "🎯 **料件清單匯入**：必要欄位：part_no、name；建議：unit / safety_stock / unit_cost。"
        ],
        "suppliers": [
            "🎯 **供應商清單匯入**：必要欄位：name；建議：code / contact_person / lead_time_days。"
        ],
    }
    if entity in by_entity:
        common.extend(["", *by_entity[entity]])
    else:
        common.extend([
            "💡 **支援的資料型態**：",
            "  - customers（客戶清單）",
            "  - parts（料件清單）",
            "  - suppliers（供應商清單）",
        ])
    common.extend([
        "",
        "⚠️ **法律提醒**：",
        "  - 鼎新 / 正航等商用 ERP 之資料庫 schema 為其智慧財產，串接前請確認您之授權允許",
        "  - 詳見 PDF #22「第三方 ERP 授權合規通知」",
    ])

    return {
        "summary": "\n".join(common),
        "raw": {"entity": entity or "all"},
    }


# ════════════════════════════════════════════════════════════════════
# D2-5: 主動推播（應收逾期 / 低庫存 / 待簽核）
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="proactive_alerts",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "主動偵測**老闆今天應該關心的 3 件事**：應收逾期 / 低於安全庫存 / 待簽核。"
        "範例：「今天有什麼要注意的？」「主動提醒」「老闆儀表板的紅燈」。"
    ),
    slots=[],
    required_permission="user.profile.read",
)
async def _proactive_alerts(db, user):
    from app.models.crm_sales import SalesOrder
    from app.models.inventory import Part, Inventory
    from app.models.approval_workflow import ApprovalRequestV2 as ApprovalRequest

    alerts = []
    raw = {}

    # 1. 應收逾期（SO status=delivered/confirmed 但 payment_status=unpaid，且超過 30 天）
    cutoff = datetime.now(UTC) - timedelta(days=30)
    overdue_q = await db.execute(
        select(func.count(SalesOrder.id)).where(
            and_(
                SalesOrder.payment_status == "unpaid",
                SalesOrder.order_date < cutoff,
                SalesOrder.status.in_(("delivered", "confirmed", "shipped")),
            )
        )
    )
    n_overdue = overdue_q.scalar() or 0
    raw["overdue_receivables"] = n_overdue
    if n_overdue > 0:
        alerts.append(f"🔴 **{n_overdue} 筆應收已逾期 30 天以上** — 該打電話追款了。")

    # 2. 低於安全庫存
    low_stock_q = await db.execute(
        select(func.count(Part.id))
        .join(Inventory, Inventory.part_id == Part.id)
        .where(
            and_(
                Part.is_active == True,
                Part.safety_stock > 0,
                Inventory.qty_on_hand < Part.safety_stock,
            )
        )
    )
    n_low = low_stock_q.scalar() or 0
    raw["low_stock"] = n_low
    if n_low > 0:
        alerts.append(f"🟡 **{n_low} 個料件低於安全庫存** — 該補貨了。")

    # 3. 待簽核
    try:
        pending_q = await db.execute(
            select(func.count(ApprovalRequest.id))
            .where(ApprovalRequest.status == "pending")
        )
        n_pending = pending_q.scalar() or 0
        raw["pending_approvals"] = n_pending
        if n_pending > 0:
            alerts.append(f"🟠 **{n_pending} 件待簽核** — 卡在審批流程。")
    except Exception:
        # ApprovalRequest 表可能不存在或欄位有別 — 不要 fail
        raw["pending_approvals"] = None

    if not alerts:
        return {
            "summary": (
                "✅ **目前一切都好！**\n"
                "- 沒有逾期應收\n"
                "- 庫存安全水位 OK\n"
                "- 沒有卡住的審批\n\n"
                "💡 想看更詳細？試試「老闆儀表板」「Daily Briefing」。"
            ),
            "raw": raw,
        }

    return {
        "summary": (
            "🔔 **老闆今天該關心的事**：\n\n"
            + "\n".join(alerts)
            + "\n\n💡 想處理哪一項？告訴我「列出逾期客戶」或「列出低庫存料件」。"
        ),
        "raw": raw,
    }
