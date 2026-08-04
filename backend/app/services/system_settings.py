"""System settings service (M1-3) — 系統組態 key-value。

優先序：env（環境變數 OUVOCA_SETTING_<KEY>）> DB（system_settings 表）> 預設值。
用途：幣別、稅率、時區、備份排程等 14 項開機即用預設。
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_setting import SystemSetting

# 開機即用預設（Turnkey Phase 0 / P0-6 系統組態）
DEFAULT_SETTINGS: dict[str, dict[str, Any]] = {
    "company.name": {"value": "我的公司", "group": "company", "description": "公司名稱（PDF 抬頭）"},
    "company.tax_id": {"value": "", "group": "company", "description": "統一編號"},
    "company.address": {"value": "", "group": "company", "description": "公司地址"},
    "company.phone": {"value": "", "group": "company", "description": "公司電話"},
    "currency.default": {"value": "TWD", "group": "finance", "description": "預設幣別"},
    "tax.vat_rate": {"value": 0.05, "group": "finance", "description": "台灣營業稅率 5%"},
    "finance.credit_limit_check": {"value": True, "group": "finance", "description": "SO 建立時強制檢查客戶信用額度"},
    "timezone.default": {"value": "Asia/Taipei", "group": "general", "description": "預設時區"},
    "locale.default": {"value": "zh-TW", "group": "general", "description": "預設語系"},
    "backup.enabled": {"value": True, "group": "backup", "description": "自動備份開關"},
    "backup.schedule": {"value": "03:00", "group": "backup", "description": "每日備份時間"},
    "backup.retention_days": {"value": 30, "group": "backup", "description": "備份保留天數"},
    "security.login_lockout_threshold": {"value": 5, "group": "security", "description": "登入失敗鎖定次數"},
    "ai.daily_limit_per_user": {"value": 200, "group": "ai", "description": "每人每日 LLM 呼叫上限"},
}


def _env_override(key: str) -> Any | None:
    env_key = f"OUVOCA_SETTING_{key.upper().replace('.', '_').replace('-', '_')}"
    raw = os.environ.get(env_key)
    if raw is None:
        return None
    # 嘗試轉型：bool / int / float，失敗保留字串
    low = raw.lower()
    if low in ("true", "1"):
        return True
    if low in ("false", "0"):
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _default_for(key: str) -> Any:
    spec = DEFAULT_SETTINGS.get(key)
    return None if spec is None else spec["value"]


async def get_setting(db: AsyncSession, key: str, default: Any = None) -> Any:
    """讀單一設定：env > DB > 預設。"""
    env_val = _env_override(key)
    if env_val is not None:
        return env_val
    row = (await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )).scalar_one_or_none()
    if row is not None:
        return row.value
    return default if default is not None else _default_for(key)


async def set_setting(
    db: AsyncSession,
    key: str,
    value: Any,
    *,
    group: str | None = None,
    description: str | None = None,
    updated_by: str | None = None,
    is_system: bool = False,
) -> SystemSetting:
    """寫入（upsert）一筆設定。"""
    row = (await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )).scalar_one_or_none()
    if row is None:
        spec = DEFAULT_SETTINGS.get(key, {})
        row = SystemSetting(
            key=key,
            value=value,
            group=group or spec.get("group", "general"),
            description=description or spec.get("description"),
            is_system=is_system,
            updated_by=updated_by,
            updated_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(row)
    else:
        row.value = value
        if group is not None:
            row.group = group
        if description is not None:
            row.description = description
        row.updated_by = updated_by
        row.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(row)
    return row


async def list_settings(db: AsyncSession) -> list[dict]:
    """列出全部設定（含預設值；環境變數覆蓋會標記）。"""
    rows = (await db.execute(
        select(SystemSetting).order_by(SystemSetting.key)
    )).scalars().all()
    db_map = {r.key: r for r in rows}
    out = []
    seen = set()
    for key, spec in DEFAULT_SETTINGS.items():
        seen.add(key)
        env_val = _env_override(key)
        row = db_map.get(key)
        out.append({
            "key": key,
            "value": env_val if env_val is not None else (row.value if row else spec["value"]),
            "group": (row.group if row else spec.get("group", "general")),
            "description": (row.description if row else spec.get("description")),
            "source": "env" if env_val is not None else ("db" if row else "default"),
            "is_system": bool(row.is_system) if row else spec.get("is_system", False),
        })
    # 自訂設定（不在 DEFAULT_SETTINGS）
    for row in rows:
        if row.key not in seen:
            out.append({
                "key": row.key, "value": row.value, "group": row.group,
                "description": row.description, "source": "db",
                "is_system": bool(row.is_system),
            })
    return out
