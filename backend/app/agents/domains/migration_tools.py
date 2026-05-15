"""Migration tools — 從外部 DB 一次性匯入 LLM-ERP（v3.4 demo moment 3）。

Tools:
  - preview_schema_mapping (READ)  — AI 自動建議欄位對映
  - migrate_from_external_with_confirm (HARD_WRITE) — 出 ConfirmCard，確認後執行匯入

PoC 範圍：
  - 支援 customer / supplier / part 三個 domain
  - conflict_strategy: skip / overwrite
  - 同步走 connector，不額外開 thread

設計：see docs/EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md §7
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.agents.schema_mapping import (
    list_supported_domains, suggest_mapping,
)
from app.integrations.connectors import get_connector
from app.integrations.connectors.exceptions import ConnectorError


# ────────────────────────────────────────────────────────────
# Helper: 取 connection by name（從 external_db_tools 共用）
# ────────────────────────────────────────────────────────────

def _get_connection_info(name: str) -> Optional[dict]:
    from app.agents.domains.external_db_tools import _CONNECTIONS
    return _CONNECTIONS.get(name)


# ────────────────────────────────────────────────────────────
# Tool 1: preview_schema_mapping
# ────────────────────────────────────────────────────────────

@register_tool(
    name="preview_schema_mapping",
    domain="external_db",
    risk_tier=RiskTier.READ,
    description=(
        "預覽外部 DB table 對映到 LLM-ERP domain 的建議。"
        "AI 自動推薦欄位對映，每個欄位帶 confidence (0-1)。"
        "範例：「鼎新.Customer 怎麼搬到我們系統?」"
    ),
    slots=[
        Slot("connection", "string", required=True,
             description="外部 DB 連接名稱（如 legacy_dingxin）"),
        Slot("source_table", "string", required=True, description="外部 table 名稱"),
        Slot("target_domain", "string", required=True,
             description=f"目標 LLM-ERP domain：{list_supported_domains()}"),
    ],
    required_permission="external_db.mapping.preview",
)
async def _preview_schema_mapping(
    db, user,
    connection: str, source_table: str, target_domain: str,
):
    info = _get_connection_info(connection)
    if info is None:
        return {"error": f"連接不存在: {connection!r}"}

    if target_domain not in list_supported_domains():
        return {
            "error": f"未支援的 target_domain: {target_domain!r}",
            "supported": list_supported_domains(),
        }

    try:
        conn = get_connector(info["connector"], info["config"])
        source_schema = await conn.schema_of(source_table)
    except ConnectorError as e:
        return {"error": str(e)}

    if not source_schema:
        return {
            "error": f"{source_table} table 內沒資料，無法推測 schema",
            "hint": "請確認 table 有至少 1 筆資料。",
        }

    result = suggest_mapping(source_schema, target_domain)
    result["connection"] = connection
    result["source_table"] = source_table
    return result


# ────────────────────────────────────────────────────────────
# Tool 2: migrate_from_external_with_confirm
# ────────────────────────────────────────────────────────────

@register_tool(
    name="migrate_from_external_with_confirm",
    domain="external_db",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "從外部 DB 一次性匯入資料到 LLM-ERP（customer / supplier / part）。"
        "會出 ConfirmCard 列出筆數 + mapping 摘要，使用者點確認後執行。"
        "範例：「把鼎新的客戶都搬過來」「Excel 的供應商批次匯入」。"
    ),
    slots=[
        Slot("connection", "string", required=True, description="外部 DB 連接名稱"),
        Slot("source_table", "string", required=True, description="外部 table 名稱"),
        Slot("target_domain", "string", required=True,
             description="customer / supplier / part"),
        Slot("conflict_strategy", "string", required=False,
             description="衝突策略：skip（預設）/ overwrite。skip 不蓋已存在 code"),
        Slot("dry_run_limit", "integer", required=False,
             description="預覽筆數，預設 5（讓 ConfirmCard 顯示前幾筆）"),
    ],
    required_permission="external_db.migrate",
    undo_recipe="manual_review",
)
async def _migrate_with_confirm(
    db, user,
    connection: str, source_table: str, target_domain: str,
    conflict_strategy: str = "skip",
    dry_run_limit: int = 5,
):
    # 1. 先跑 preview
    preview = await _preview_schema_mapping(
        db, user,
        connection=connection, source_table=source_table, target_domain=target_domain,
    )
    if "error" in preview:
        return preview

    # 2. required 欄位至少要有對應
    if not preview["required_satisfied"]:
        missing_required = [
            m["target_field"] for m in preview["mappings"]
            if m["required"] and m["confidence"] == 0
        ]
        return {
            "error": "必填欄位找不到對應，無法 migration",
            "missing_required": missing_required,
            "hint": "請先確認外部 table 有相應欄位，或更換 target_domain。",
        }

    # 3. 取總筆數
    info = _get_connection_info(connection)
    conn = get_connector(info["connector"], info["config"])
    sample = await conn.query(source_table, limit=1000)  # PoC 上限
    total_rows = len(sample)

    if total_rows == 0:
        return {"error": f"{source_table} 沒有資料可匯入"}

    # 4. 組 ConfirmCard
    cs = preview["confidence_summary"]
    high_cm = [m for m in preview["mappings"] if m["confidence"] >= 0.9]
    medium_cm = [m for m in preview["mappings"] if 0.6 <= m["confidence"] < 0.9]
    missing_cm = [m for m in preview["mappings"] if m["confidence"] == 0 and not m["required"]]

    summary = [
        f"來源：{connection}.{source_table}",
        f"目標：{target_domain}（LLM-ERP 內 {len(preview['mappings'])} 個欄位）",
        f"總筆數：{total_rows} 筆",
        f"衝突策略：{conflict_strategy}（已存在的 code "
        + ("略過" if conflict_strategy == "skip" else "覆寫") + "）",
        "─" * 30,
        f"📋 欄位對映：高信心 {cs['high']} / 中信心 {cs['medium']} / 找不到 {cs['missing']}",
    ]

    if high_cm:
        summary.append("✅ 高信心對映（直接套用）：")
        for m in high_cm:
            summary.append(f"  • {m['target_field']:18s} ← {m['source_field']}  ({m['confidence']:.2f})")

    if medium_cm:
        summary.append("⚠️ 中信心對映（建議審視）：")
        for m in medium_cm:
            summary.append(f"  • {m['target_field']:18s} ← {m['source_field']}  ({m['confidence']:.2f})  — {m['reason']}")

    if missing_cm:
        summary.append(f"❌ 找不到對映（將留空）：{', '.join(m['target_field'] for m in missing_cm)}")

    if preview["unmapped_source_fields"]:
        unmapped_names = [s["name"] for s in preview["unmapped_source_fields"]]
        summary.append(f"📦 來源額外欄位（不會匯入）：{', '.join(unmapped_names)}")

    summary.append("─" * 30)
    summary.append(f"💡 預覽前 {min(dry_run_limit, total_rows)} 筆：")
    for i, row in enumerate(sample[:dry_run_limit], 1):
        preview_kv = [
            f"{m['target_field']}={row.get(m['source_field'], '')!r}"
            for m in preview["mappings"]
            if m["source_field"] and m["confidence"] >= 0.6
        ][:4]  # 只顯示前 4 欄
        summary.append(f"  [{i}] " + " · ".join(preview_kv))

    employee_id = (user or {}).get("employee_id")

    card = make_card(
        tool_name="migrate_from_external_with_confirm",
        title=f"確認從 {connection} 匯入 {total_rows} 筆 → {target_domain}",
        summary=summary,
        slots={
            "connection": connection,
            "source_table": source_table,
            "target_domain": target_domain,
            "conflict_strategy": conflict_strategy,
            "total_rows": total_rows,
            "mappings": preview["mappings"],
        },
        risk_tier="hard-write",
        ttl_seconds=600,  # migration 給 10 分鐘考慮時間
        created_by=employee_id,
    )

    async def execute():
        return await _do_migration(
            db, connection, source_table, target_domain,
            preview["mappings"], conflict_strategy, employee_id,
        )

    await stash_card(card, execute)
    return card.to_chat_payload()


# ────────────────────────────────────────────────────────────
# 真實 migration 執行邏輯
# ────────────────────────────────────────────────────────────

async def _do_migration(
    db, connection: str, source_table: str, target_domain: str,
    mappings: list[dict], conflict_strategy: str, employee_id: Optional[str],
) -> dict:
    """執行 migration loop。"""
    info = _get_connection_info(connection)
    if info is None:
        return {"error": "連接不存在（execute 階段）"}

    conn = get_connector(info["connector"], info["config"])
    rows = await conn.query(source_table, limit=1000)

    # mapping table: target_field → source_field (skip 0 confidence)
    mapping_dict = {
        m["target_field"]: m["source_field"]
        for m in mappings
        if m["source_field"] and m["confidence"] >= 0.6
    }

    # 動態取目標 model
    target_model_cls = _get_target_model(target_domain)
    if target_model_cls is None:
        return {"error": f"未實作的 target_domain: {target_domain}"}

    code_field = "part_no" if target_domain == "part" else "code"
    inserted = 0
    updated = 0
    skipped = 0
    failed = 0
    errors: list[str] = []

    for row in rows:
        try:
            kwargs: dict = {}
            for tgt, src in mapping_dict.items():
                v = row.get(src)
                if v is None or v == "":
                    continue
                kwargs[tgt] = _coerce_value(v, _type_of_field(target_domain, tgt))
            code_value = kwargs.get(code_field)
            if not code_value:
                failed += 1
                errors.append(f"row 缺 {code_field}: {row}")
                continue

            # 衝突檢查
            existing = (await db.execute(
                select(target_model_cls).where(getattr(target_model_cls, code_field) == code_value)
            )).scalar_one_or_none()

            if existing is not None:
                if conflict_strategy == "skip":
                    skipped += 1
                    continue
                # overwrite
                for k, v in kwargs.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
                updated += 1
            else:
                kwargs["id"] = str(uuid.uuid4())
                new = target_model_cls(**kwargs)
                db.add(new)
                inserted += 1
        except Exception as e:
            failed += 1
            errors.append(f"{type(e).__name__}: {e}")
            if len(errors) > 10:
                errors.append("...（更多錯誤已截斷）")
                break

    await db.commit()

    return {
        "status": "executed",
        "target_domain": target_domain,
        "total_processed": len(rows),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors[:10],
        "migrated_by": employee_id,
        "message": (
            f"✅ 匯入完成：新增 {inserted} 筆 / "
            f"更新 {updated} 筆 / 略過 {skipped} 筆 / 失敗 {failed} 筆"
        ),
    }


def _get_target_model(domain: str):
    """取對應 domain 的 SQLAlchemy model class。"""
    from app.models.crm_sales import Customer
    from app.models.purchase import Supplier
    from app.models.inventory import Part
    return {
        "customer": Customer,
        "supplier": Supplier,
        "part": Part,
    }.get(domain)


def _type_of_field(domain: str, field: str) -> str:
    """查 target_domain 的某個欄位預期型別。"""
    from app.agents.schema_mapping import get_target_schema
    schema = get_target_schema(domain) or []
    for tf, tp, _, _, _ in schema:
        if tf == field:
            return tp
    return "string"


def _coerce_value(v, target_type: str):
    """把 CSV/SQLite 拿到的字串轉成目標型別。"""
    if v is None or v == "":
        return None
    try:
        if target_type == "integer":
            return int(float(v))  # 允許 "1.0" → 1
        if target_type == "float":
            return float(v)
        if target_type == "boolean":
            if isinstance(v, bool):
                return v
            return str(v).lower() in ("true", "1", "yes", "y", "已核准")
    except (TypeError, ValueError):
        return None
    return str(v)


# ────────────────────────────────────────────────────────────
# 把 migration tools 加進 ExternalDbAgent
# ────────────────────────────────────────────────────────────

from app.agents.engine import AGENT_REGISTRY

if "external_db" in AGENT_REGISTRY:
    tn = AGENT_REGISTRY["external_db"]["tool_names"]
    for t in ("preview_schema_mapping", "migrate_from_external_with_confirm"):
        if t not in tn:
            tn.append(t)
