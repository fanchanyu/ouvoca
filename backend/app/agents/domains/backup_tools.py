"""備份 AI tools（審計 P1-7）— 對話式備份/列出/還原。"""
from __future__ import annotations

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot


@register_tool(
    name="list_backups",
    domain="system",
    risk_tier=RiskTier.READ,
    description="列出所有備份（時間/大小/是否可還原）。範例：「有哪些備份」「上次備份什麼時候」",
    slots=[],
    required_permission="system.backup.read",
)
async def _list_backups(db, user):
    from app.services.backup import list_backups
    rows = list_backups()
    return {"total": len(rows), "backups": rows}


@register_tool(
    name="create_backup_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description="立即建立一份資料庫備份。範例：「現在備份」「備份一下資料庫」",
    slots=[],
    required_permission="system.backup.create",
)
async def _create_backup_with_confirm(db, user):
    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="create_backup_with_confirm",
        title="建立資料庫備份",
        summary=["將目前資料庫複製為一份快照備份", "備份檔儲存在 backend/backups/"],
        slots={},
        risk_tier="hard-write",
        created_by=employee_id,
    )

    async def execute():
        from app.services.backup import create_backup
        return await create_backup(db, reason=f"chat:{employee_id or 'anon'}")

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="restore_backup_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "從備份還原資料庫（**破壞性**：覆蓋現行資料，不可逆）。"
        "範例：「還原到昨天 3 點的備份」"
    ),
    slots=[
        Slot("backup_name", "string", required=True, description="備份檔名（先 list_backups 查）"),
    ],
    required_permission="system.backup.restore",
)
async def _restore_backup_with_confirm(db, user, backup_name: str):
    from app.services.backup import _is_valid_sqlite, BACKUP_DIR
    from pathlib import Path

    target = BACKUP_DIR / backup_name
    if not target.exists() or not _is_valid_sqlite(target):
        return {"error": f"備份不存在或不是有效 SQLite：{backup_name}",
                "hint": "請先 list_backups 確認名稱"}

    employee_id = (user or {}).get("employee_id")
    card = make_card(
        tool_name="restore_backup_with_confirm",
        title=f"還原備份 {backup_name}",
        summary=[
            f"備份：{backup_name}",
            "⚠️ 還原會**覆蓋現行資料庫**且不可逆。",
            "系統會先保留一份 pre-restore 救援檔在 backend/backups/。",
            "還原後建議重新啟動服務。",
        ],
        slots={"backup_name": backup_name},
        risk_tier="hard-write",
        ttl_seconds=300,
        created_by=employee_id,
    )

    async def execute():
        from app.services.backup import restore_backup
        return restore_backup(backup_name)

    await stash_card(card, execute)
    return card.to_chat_payload()
