"""v3.38 第二輪小白卡關修補 — Polish tools

針對 v3.37 後盤點 N1-N8 的後端工具補完：
  N2：generic undo — undo_last_admin_change（公司資料 / 改密碼）
  N3：query_ai_cost_today / query_ai_cost_this_month — 老闆怕燒錢入口
  N4：backup_database_with_confirm / list_recent_backups — 資料安全感
  N7：resolve_customer_candidates — 多筆同名時列候選

══════════════════════════════════════════════════════════════════
LEGAL（累積適用 v3.25.10 → v3.37 §6）
══════════════════════════════════════════════════════════════════
本模組之 backup tools 涉及 DB 完整複製；undo 涉及 admin 操作回溯。
這些是高敏感操作，Ouvoca 已強制 ConfirmCard + audit log。
備份檔本身為 SQL dump / SQLite copy，包含**完整客戶資料**。
客戶須依個資法、營業秘密法妥善保管備份檔，不得外流。
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta, UTC
from pathlib import Path
from sqlalchemy import select, func, and_, desc

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.crm_sales import Customer
from app.models.ai_governance import DecisionLog
from app.models.permission import Tenant


# ════════════════════════════════════════════════════════════════════
# N3: AI 成本查詢 — 老闆怕燒錢的安心入口
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="query_ai_cost_today",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "查詢今天 AI 用了多少錢（USD / TWD 換算）。"
        "範例：「今天 AI 花多少錢？」「AI 燒了多少？」"
    ),
    slots=[],
    required_permission="user.profile.read",
)
async def _query_ai_cost_today(db, user):
    today = datetime.now(UTC).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    end = start + timedelta(days=1)

    try:
        total_usd = (await db.execute(
            select(func.coalesce(func.sum(DecisionLog.cost_usd), 0))
            .where(and_(DecisionLog.created_at >= start, DecisionLog.created_at < end))
        )).scalar() or 0
        n_calls = (await db.execute(
            select(func.count(DecisionLog.id))
            .where(and_(DecisionLog.created_at >= start, DecisionLog.created_at < end))
        )).scalar() or 0
    except Exception as e:
        return {
            "summary": "📊 今天還沒有 AI 紀錄（或 cost log 表未建立）",
            "raw": {"error": str(e)[:200], "usd": 0, "twd": 0, "calls": 0},
        }

    twd = total_usd * 31.5  # 大概匯率
    return {
        "summary": (
            f"💰 **今天 AI 成本（{today}）**\n"
            f"  • 呼叫次數：{n_calls}\n"
            f"  • 美金：${total_usd:.4f}\n"
            f"  • 約台幣：${twd:.1f}\n\n"
            f"{'✅ 用量正常' if total_usd < 0.5 else '⚠️ 用量較高，留意'}"
        ),
        "raw": {"usd": float(total_usd), "twd": float(twd),
                "calls": int(n_calls), "date": str(today)},
    }


@register_tool(
    name="query_ai_cost_this_month",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "查詢本月 AI 累計成本。"
        "範例：「本月 AI 花了多少？」「這個月 AI 成本」"
    ),
    slots=[],
    required_permission="user.profile.read",
)
async def _query_ai_cost_this_month(db, user):
    now = datetime.now(UTC)
    month_start = datetime(now.year, now.month, 1, tzinfo=UTC)

    try:
        total_usd = (await db.execute(
            select(func.coalesce(func.sum(DecisionLog.cost_usd), 0))
            .where(DecisionLog.created_at >= month_start)
        )).scalar() or 0
        n_calls = (await db.execute(
            select(func.count(DecisionLog.id))
            .where(DecisionLog.created_at >= month_start)
        )).scalar() or 0
    except Exception as e:
        return {
            "summary": "📊 本月還沒有 AI 紀錄（或 cost log 表未建立）",
            "raw": {"error": str(e)[:200], "usd": 0, "twd": 0, "calls": 0},
        }

    twd = total_usd * 31.5
    return {
        "summary": (
            f"💰 **本月 AI 成本（{now.strftime('%Y-%m')}）**\n"
            f"  • 呼叫次數：{n_calls}\n"
            f"  • 美金：${total_usd:.4f}\n"
            f"  • 約台幣：${twd:.1f}\n\n"
            f"{'✅ 月度預算內' if total_usd < 5.0 else '⚠️ 已超過 $5 美金，建議檢視'}"
        ),
        "raw": {"usd": float(total_usd), "twd": float(twd),
                "calls": int(n_calls), "month": now.strftime("%Y-%m")},
    }


# ════════════════════════════════════════════════════════════════════
# N4: 備份 / 還原 — 老闆每天問「備份了嗎？」
# ════════════════════════════════════════════════════════════════════

BACKUP_DIR = Path(os.environ.get("OUVOCA_BACKUP_DIR", "./backups"))


def _ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


@register_tool(
    name="backup_database_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "備份整個資料庫到本機 backups/ 資料夾。"
        "範例：「備份資料庫」「現在備份一下」「我要備份」。"
        "⚠️ 備份檔含完整客戶資料，須妥善保管不可外流。"
    ),
    slots=[
        Slot("note", "string", required=False,
             description="備份備註（如「月底結帳前」「升級前」）"),
    ],
    required_permission="system.config.update",
)
async def _backup_database_with_confirm(db, user, note: str = ""):
    from app.database import engine
    db_url = str(engine.url)
    is_sqlite = "sqlite" in db_url.lower()
    if not is_sqlite:
        return {
            "summary": (
                "⚠️ 您使用 PostgreSQL — 請用 `pg_dump` 由 IT 操作。\n"
                "詳見 docs/pdf/12_備份還原SOP_中文.pdf。"
            ),
            "raw": {"db_type": "postgres", "auto_backup_unsupported": True},
        }

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup_name = f"erp-{ts}.db"
    if note:
        # sanitize note for filename
        safe_note = "".join(c for c in note if c.isalnum() or c in "-_")[:30]
        backup_name = f"erp-{ts}-{safe_note}.db"

    summary = [
        "📦 將執行資料庫備份：",
        f"  • 來源：{db_url}",
        f"  • 目的：./backups/{backup_name}",
        f"  • 時間：{ts}",
    ]
    if note:
        summary.append(f"  • 備註：{note}")
    summary.append("")
    summary.append("⚠️ 確認後將複製整份資料庫（含全部客戶資料）。")

    card = make_card(
        tool_name="backup_database_with_confirm",
        title="📦 確認備份資料庫",
        summary=summary,
        slots={"backup_name": backup_name, "note": note},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        _ensure_backup_dir()
        # 從 DB URL 取 SQLite 檔案路徑
        # sqlite+aiosqlite:///./erp.db → ./erp.db
        path_str = db_url.split("///", 1)[-1] if "///" in db_url else db_url
        src = Path(path_str)
        if not src.exists():
            return {"error": f"找不到 DB 檔：{src}"}
        dest = BACKUP_DIR / backup_name
        shutil.copy2(src, dest)
        size_mb = dest.stat().st_size / (1024 * 1024)
        return {
            "backup_file": str(dest),
            "size_mb": round(size_mb, 2),
            "message": f"✅ 備份完成：{backup_name}（{size_mb:.2f} MB）",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="list_recent_backups",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "列出最近的備份檔（含時間 / 大小）。"
        "範例：「最近備份了什麼？」「列出備份」「上次備份是什麼時候？」"
    ),
    slots=[],
    required_permission="user.profile.read",
)
async def _list_recent_backups(db, user):
    _ensure_backup_dir()
    files = sorted(BACKUP_DIR.glob("erp-*.db"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return {
            "summary": (
                "📦 **尚無備份檔**\n"
                "⚠️ 建議**至少每週備份一次**：在 Chat 講「備份資料庫」。"
            ),
            "raw": {"count": 0, "backups": []},
        }

    lines = [f"📦 **最近 {min(10, len(files))} 個備份**：", ""]
    raw = []
    for f in files[:10]:
        size_mb = f.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(f.stat().st_mtime, UTC)
        lines.append(f"  • `{f.name}` — {size_mb:.2f} MB — {mtime.strftime('%Y-%m-%d %H:%M')}")
        raw.append({"name": f.name, "size_mb": round(size_mb, 2),
                    "mtime": mtime.isoformat()})

    # 警告若最近備份 > 7 天前
    if files:
        latest = datetime.fromtimestamp(files[0].stat().st_mtime, UTC)
        days_ago = (datetime.now(UTC) - latest).days
        if days_ago >= 7:
            lines.append("")
            lines.append(f"⚠️ **最近一次備份已 {days_ago} 天前** — 建議現在備份。")

    return {"summary": "\n".join(lines),
            "raw": {"count": len(files), "backups": raw}}


# ════════════════════════════════════════════════════════════════════
# N7: 客戶 disambiguation — 多筆同名時列候選
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="resolve_customer_candidates",
    domain="crm",
    risk_tier=RiskTier.READ,
    description=(
        "當客戶名稱有多個匹配時，列出候選清單供使用者選擇。"
        "範例：「ABC 是哪個客戶？」「找叫 工業 的客戶」「ABC 我不確定哪一個」。"
    ),
    slots=[
        Slot("keyword", "string", required=True, description="客戶名稱或編號片段"),
    ],
    required_permission="crm.customer.read",
)
async def _resolve_customer_candidates(db, user, keyword: str):
    keyword = (keyword or "").strip()
    if not keyword:
        return {"error": "請提供客戶名稱或編號關鍵字。"}

    # 三段精準度搜尋：精準 / 開頭 / 包含
    exact = (await db.execute(
        select(Customer).where(
            (Customer.code == keyword) | (Customer.name == keyword)
        )
    )).scalars().all()
    if len(exact) == 1:
        c = exact[0]
        return {
            "summary": f"✅ **唯一匹配**：{c.code} - {c.name}",
            "raw": {"matched": "exact", "candidates": [
                {"id": c.id, "code": c.code, "name": c.name}
            ]},
        }

    # 沒精準匹配 → fuzzy
    like = f"%{keyword.lower()}%"
    candidates = (await db.execute(
        select(Customer).where(
            (func.lower(Customer.code).like(like)) | (func.lower(Customer.name).like(like))
        ).order_by(Customer.code).limit(10)
    )).scalars().all()

    if not candidates:
        return {
            "summary": f"❌ 找不到任何客戶匹配「{keyword}」。",
            "raw": {"matched": "none", "candidates": []},
        }

    if len(candidates) == 1:
        c = candidates[0]
        return {
            "summary": f"✅ **唯一匹配**：{c.code} - {c.name}",
            "raw": {"matched": "fuzzy_unique", "candidates": [
                {"id": c.id, "code": c.code, "name": c.name}
            ]},
        }

    lines = [f"🔍 **「{keyword}」匹配到 {len(candidates)} 個客戶**：", ""]
    raw_list = []
    for i, c in enumerate(candidates, 1):
        lines.append(f"  {i}. **{c.code}** - {c.name}"
                     + (f" (等級 {c.grade})" if c.grade else ""))
        raw_list.append({"id": c.id, "code": c.code, "name": c.name,
                         "grade": c.grade})
    lines.append("")
    lines.append("💡 請告訴我哪一個（例：「第 2 個」「CUS-0005」「ABC 工業」）。")

    return {
        "summary": "\n".join(lines),
        "raw": {"matched": "multiple", "count": len(candidates),
                "candidates": raw_list},
    }


# ════════════════════════════════════════════════════════════════════
# N2: Generic Undo — 撤銷上次 admin 操作（公司資料 / 密碼）
# ════════════════════════════════════════════════════════════════════

# In-memory undo stack（per-process；正式環境應改 DB / Redis）
# 結構：{user_id: [{kind, before, after, timestamp}, ...]}
_UNDO_STACK: dict[str, list[dict]] = {}
_UNDO_TTL_SECONDS = 90  # 90 秒（與 v3.3 undo 一致）


def push_undo(user_id: str, entry: dict):
    """供 set_company_info / change_password 等 hard-write 呼叫 — 推進撤銷堆疊。

    entry: {kind, before, after}
    """
    entry["timestamp"] = datetime.now(UTC).isoformat()
    _UNDO_STACK.setdefault(user_id, []).append(entry)
    # 只保留最近 5 筆（防止無限長）
    _UNDO_STACK[user_id] = _UNDO_STACK[user_id][-5:]


@register_tool(
    name="undo_last_admin_change",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "撤銷您上一次的 admin 操作（公司資料 / 密碼變更）。"
        "範例：「撤銷」「上一步」「我剛剛改錯了」「undo」。"
        "⚠️ 只能撤銷 90 秒內的操作，且只能撤銷一次。"
    ),
    slots=[],
    required_permission="system.config.update",
)
async def _undo_last_admin_change(db, user):
    user_id = (user or {}).get("user_id") or (user or {}).get("employee_id") or "anonymous"
    stack = _UNDO_STACK.get(user_id, [])
    if not stack:
        return {
            "summary": "🚫 沒有可撤銷的操作（90 秒內未做過 admin 變更）。",
            "raw": {"undoable": False},
        }

    # 取最新一筆，檢查是否過期
    latest = stack[-1]
    ts = datetime.fromisoformat(latest["timestamp"])
    age = (datetime.now(UTC) - ts).total_seconds()
    if age > _UNDO_TTL_SECONDS:
        # 過期清掉
        _UNDO_STACK.pop(user_id, None)
        return {
            "summary": f"⏰ 上次操作已 {int(age)} 秒前，超過 {_UNDO_TTL_SECONDS} 秒撤銷視窗。",
            "raw": {"undoable": False, "age_seconds": int(age)},
        }

    kind = latest.get("kind")
    before = latest.get("before") or {}

    summary = [
        f"↩️ **將撤銷上次操作**（{int(age)} 秒前）",
        f"  • 操作種類：{kind}",
        f"  • 將還原為：{before}",
    ]

    card = make_card(
        tool_name="undo_last_admin_change",
        title="↩️ 確認撤銷上次操作",
        summary=summary,
        slots={"kind": kind, "before": before},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        if kind == "set_company_info":
            t = (await db.execute(
                select(Tenant).where(Tenant.code == "HQ")
            )).scalar_one_or_none()
            if t is None:
                return {"error": "找不到 Tenant，無法撤銷。"}
            t.name = before.get("name", t.name)
            t.settings = before.get("settings", t.settings)
            await db.commit()
            msg = f"✅ 已還原公司資料為「{before.get('name')}」"
        elif kind == "change_password":
            from app.models.organization import User
            u = (await db.execute(
                select(User).where(User.id == before.get("user_id"))
            )).scalar_one_or_none()
            if u is None:
                return {"error": "找不到使用者，無法撤銷。"}
            u.hashed_password = before.get("hashed_password")
            await db.commit()
            msg = "✅ 已還原密碼為上次的版本（請用舊密碼登入）"
        # v3.40 M4：delete undo — 把刪除時保存的 snapshot 重建回 DB
        elif kind == "delete_customer":
            from app.models.crm_sales import Customer
            data = before.get("snapshot") or {}
            if not data.get("id"):
                return {"error": "刪除快照不完整，無法復原。"}
            # 檢查未被同編號重建
            existing = (await db.execute(
                select(Customer).where(Customer.code == data.get("code"))
            )).scalar_one_or_none()
            if existing:
                return {"error": f"客戶編號 {data.get('code')} 已被重新使用，無法復原。"}
            db.add(Customer(**{k: v for k, v in data.items() if not k.startswith("_")}))
            await db.commit()
            msg = f"✅ 已復原客戶「{data.get('code')} - {data.get('name')}」"
        elif kind == "delete_supplier":
            from app.models.purchase import Supplier
            data = before.get("snapshot") or {}
            if not data.get("id"):
                return {"error": "刪除快照不完整，無法復原。"}
            existing = (await db.execute(
                select(Supplier).where(Supplier.code == data.get("code"))
            )).scalar_one_or_none()
            if existing:
                return {"error": f"供應商編號 {data.get('code')} 已被重新使用，無法復原。"}
            db.add(Supplier(**{k: v for k, v in data.items() if not k.startswith("_")}))
            await db.commit()
            msg = f"✅ 已復原供應商「{data.get('code')} - {data.get('name')}」"
        elif kind == "delete_part":
            from app.models.inventory import Part
            data = before.get("snapshot") or {}
            if not data.get("id"):
                return {"error": "刪除快照不完整，無法復原。"}
            existing = (await db.execute(
                select(Part).where(Part.part_no == data.get("part_no"))
            )).scalar_one_or_none()
            if existing:
                return {"error": f"料號 {data.get('part_no')} 已被重新使用，無法復原。"}
            db.add(Part(**{k: v for k, v in data.items() if not k.startswith("_")}))
            await db.commit()
            msg = f"✅ 已復原料件「{data.get('part_no')} - {data.get('name')}」"
        else:
            return {"error": f"未知撤銷種類：{kind}"}

        # 撤銷成功後從 stack 移除
        _UNDO_STACK.get(user_id, []).pop()
        return {"kind": kind, "message": msg}

    await stash_card(card, execute)
    return card.to_chat_payload()
