"""Auto CrmEvent logger（Sprint J v3.16）— erpilot 原創設計。

對標傳統 CRM（Salesforce / HubSpot）「業務手動記 activity」的痛點：
  - 業務忙起來就忘了記
  - 記了也常常 1-2 句敷衍
  - 結果 Customer 360 timeline 空白 = 主管 / 後手交接時資訊斷層

erpilot 原創解：**業務動作自動產生 CrmEvent**，不需手動：
  - SO 成立 / 確認 / 出貨 / 取消 → 自動 log
  - PO 成立 → 自動 log（給對應的「主要客戶」如果有）
  - Lead 轉客戶 → 自動 log「轉換時間 / 來源」
  - Opportunity 階段變化 → 自動 log

這支模組訂閱 EventBus，任何 service emit domain event 就自動串到 CRM timeline。
跟手動 CrmEvent 共存（業務想加 note 還是可以）。
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.events.engine import EventBus, DomainEvent
from app.models.crm_sales import CrmEvent

log = get_logger(__name__)


# ── 對映：domain event → CRM event 樣板 ────────────────────
EVENT_TEMPLATES: dict[str, dict] = {
    "so.created": {
        "event_type": "order",
        "subject_fn": lambda d: f"📋 銷售單 {d.get('so_no')} 成立",
        "desc_fn": lambda d: f"訂單金額 NT$ {float(d.get('total', 0)):,.0f}",
    },
    "so.confirmed": {
        "event_type": "order",
        "subject_fn": lambda d: f"✅ 銷售單 {d.get('so_no')} 已確認",
        "desc_fn": lambda d: f"NT$ {float(d.get('total', 0)):,.0f}，進入備貨",
    },
    "so.shipped": {
        "event_type": "order",
        "subject_fn": lambda d: f"🚚 銷售單 {d.get('so_no')} 已出貨",
        "desc_fn": lambda d: None,
    },
    "so.cancelled": {
        "event_type": "order",
        "subject_fn": lambda d: f"🚫 銷售單 {d.get('so_no')} 取消",
        "desc_fn": lambda d: f"原因：{d.get('reason', '未填')}",
    },
    "lead.converted": {
        "event_type": "milestone",
        "subject_fn": lambda d: "🎯 從 Lead 轉為正式客戶",
        "desc_fn": lambda d: f"客戶 {d.get('customer_name', '?')} 已正式建檔",
    },
    "opportunity.stage_changed": {
        "event_type": "milestone",
        "subject_fn": lambda d: f"💼 商機階段：{d.get('stage')}",
        "desc_fn": lambda d: f"NT$ {float(d.get('amount', 0)):,.0f}",
    },
}


async def _resolve_customer_id(db: AsyncSession, event: DomainEvent) -> Optional[str]:
    """從 domain event payload 找對應的 customer_id。

    處理：
      - so.* events：payload 直接帶 customer_id
      - lead.converted：payload 帶 customer_id
      - opportunity.stage_changed：payload 帶 opp_id，要查 Opp 拿 customer_id
    """
    d = event.data or {}
    cid = d.get("customer_id")
    if cid:
        return cid
    # opportunity 要查
    if event.entity_type == "Opportunity":
        from app.models.crm_sales import Opportunity
        opp = (await db.execute(
            select(Opportunity).where(Opportunity.id == event.entity_id)
        )).scalar_one_or_none()
        return opp.customer_id if opp else None
    return None


async def auto_log_to_crm(event: DomainEvent) -> None:
    """訂閱 EventBus，把符合樣板的 domain event 自動寫 CrmEvent。"""
    tpl = EVENT_TEMPLATES.get(event.name)
    if tpl is None:
        return

    # 取得 DB session（事件總線 callback 在 EventBus.emit 後跑）
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            cid = await _resolve_customer_id(db, event)
            if not cid:
                # 沒對應的客戶就跳過（不是錯，例如 SO 沒設客戶）
                return

            subject = tpl["subject_fn"](event.data or {})
            desc = tpl["desc_fn"](event.data or {})

            ce = CrmEvent(
                id=str(uuid.uuid4()),
                customer_id=cid,
                event_type=tpl["event_type"],
                subject=subject,
                description=desc,
                reference_type=event.entity_type,
                reference_id=event.entity_id,
                created_at=datetime.now(UTC).replace(tzinfo=None),
                created_by=None,  # 系統自動產的；FK 是 employees 不能填 "system"
            )
            db.add(ce)
            await db.commit()
            log.debug("auto_log_to_crm: %s → customer=%s subject=%s",
                      event.name, cid, subject)
        except Exception as exc:  # pylint: disable=broad-except
            # 自動 log 失敗不應該擋住主流程
            log.warning("auto_log_to_crm failed for %s: %s", event.name, exc)


def install_auto_crm_logging() -> None:
    """app startup 時呼叫一次，把 listener 註冊上去。"""
    for event_name in EVENT_TEMPLATES.keys():
        EventBus.subscribe(event_name, auto_log_to_crm)
    log.info("Auto-CRM logging installed for %d event types", len(EVENT_TEMPLATES))
