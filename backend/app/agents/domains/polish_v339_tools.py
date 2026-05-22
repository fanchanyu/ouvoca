"""v3.39 第三輪小白卡關修補 — Polish v339 tools

針對第三輪盤點 K1-K8（不重複 v3.37/v3.38 已修）：
  K1：upload_company_logo_with_confirm — PDF 上印 LOGO
  K2：delete_customer/part/supplier_with_confirm — 高頻刪除工具
  K3：分頁 offset / next_page
  K6：trigger_daily_digest_now — 手動觸發 + 文件說明 cron
  K7：print_multiple_orders_with_confirm — 批次列印 PDF zip
  K8：Docker 開機自啟引導（OS 不同方法，由 backend 提供說明）

══════════════════════════════════════════════════════════════════
LEGAL（累積適用 v3.25.10 → v3.38 §6）
══════════════════════════════════════════════════════════════════
本模組之 hard-write tools 涉及：
  • LOGO 圖檔上傳並嵌入 PDF — 客戶須擁有 LOGO 著作權
  • 客戶 / 料件 / 供應商刪除 — 不可逆操作
  • 批次列印產生多份 PDF — 含完整商業機密
客戶須依個資法、營業秘密法、商業會計法妥善使用。
"""
from __future__ import annotations

import base64
import io
import zipfile
from datetime import datetime, UTC
from sqlalchemy import select, func

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.permission import Tenant
from app.models.crm_sales import Customer
from app.models.purchase import Supplier
from app.models.inventory import Part


# ════════════════════════════════════════════════════════════════════
# K1: 公司 LOGO 上傳（base64 → Tenant.settings.logo_b64）
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="upload_company_logo_with_confirm",
    domain="system",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "上傳公司 LOGO 圖檔（PNG / JPG，建議 200x80 px）— 之後所有 PDF "
        "頂部會印上此 LOGO，對外文件不再像「白板影印紙」。"
        "範例：「上傳公司 logo」「我要設 logo」。"
        "⚠️ 需先用「上傳檔案」API 取得 file_id，再呼叫此工具。"
    ),
    slots=[
        Slot("file_id", "string", required=True,
             description="已上傳之 Attachment ID（用 /api/files/upload）"),
    ],
    required_permission="system.config.update",
)
async def _upload_company_logo_with_confirm(db, user, file_id: str):
    from app.models.attachment import Attachment
    from pathlib import Path

    att = (await db.execute(
        select(Attachment).where(Attachment.id == file_id)
    )).scalar_one_or_none()
    if att is None:
        return {"error": f"找不到檔案 {file_id}（請先用 /api/files/upload 上傳）"}

    # 限制：只接受圖片 + ≤ 500 KB
    if not (att.content_type or "").startswith("image/"):
        return {"error": f"檔案類型 {att.content_type} 不是圖片，請上傳 PNG / JPG。"}
    if att.size_bytes > 500_000:
        return {"error": f"檔案 {att.size_bytes // 1024} KB 太大（上限 500 KB），請壓縮後再上傳。"}

    summary = [
        f"🖼️ 將設定公司 LOGO：",
        f"  • 檔名：{att.filename}",
        f"  • 大小：{att.size_bytes // 1024} KB",
        f"  • 類型：{att.content_type}",
        "",
        "✅ 確認後所有後續 PDF（報價 / 採購 / 銷售 / 出貨）頂部都會印此 LOGO。",
    ]

    card = make_card(
        tool_name="upload_company_logo_with_confirm",
        title="🖼️ 確認設定公司 LOGO",
        summary=summary,
        slots={"file_id": file_id, "filename": att.filename},
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        # 把檔案讀進來 → base64 → 存到 Tenant.settings.logo_b64
        from app.api.files import UPLOADS_DIR
        disk_path = UPLOADS_DIR / att.file_path
        if not disk_path.exists():
            return {"error": f"檔案實體不存在於 disk：{disk_path}"}
        with open(disk_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("ascii")

        t = (await db.execute(
            select(Tenant).where(Tenant.code == "HQ")
        )).scalar_one_or_none()
        if t is None:
            return {"error": "找不到 HQ Tenant，請先設定公司資料。"}

        settings = dict(t.settings or {})
        settings["logo_b64"] = logo_b64
        settings["logo_filename"] = att.filename
        settings["logo_mime"] = att.content_type
        t.settings = settings
        await db.commit()
        return {
            "tenant_id": t.id,
            "size_kb": att.size_bytes // 1024,
            "message": f"✅ LOGO 已設定（{att.filename}）— 下次印 PDF 會出現。",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# K2: Delete 三件套 — Customer / Supplier / Part
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="delete_customer_with_confirm",
    domain="sales",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "刪除指定客戶（**僅在無任何銷售訂單時可刪**；否則改用「停用」）。"
        "範例：「刪掉客戶 CUS-0005」「刪客戶 ABC 公司」「移除客戶 XXX」。"
    ),
    slots=[Slot("customer_keyword", "string", required=True,
                description="客戶編號或名稱")],
    required_permission="sales.customer.delete",
)
async def _delete_customer_with_confirm(db, user, customer_keyword: str):
    keyword = customer_keyword.strip()
    c = (await db.execute(
        select(Customer).where(
            (Customer.code == keyword) | (Customer.name == keyword)
        )
    )).scalar_one_or_none()
    if c is None:
        # fuzzy
        like = f"%{keyword.lower()}%"
        c = (await db.execute(
            select(Customer).where(
                (func.lower(Customer.code).like(like)) | (func.lower(Customer.name).like(like))
            ).limit(2)
        )).scalars().first()
        if c is None:
            return {"error": f"找不到客戶「{keyword}」"}

    # 預檢查（service 層真執行時也會檢，這裡先告訴使用者）
    from app.models.crm_sales import SalesOrder
    has_so = (await db.execute(
        select(SalesOrder).where(SalesOrder.customer_id == c.id).limit(1)
    )).scalar_one_or_none()
    if has_so is not None:
        return {
            "error": (
                f"⚠️ 客戶「{c.code} - {c.name}」已有銷售訂單，**不可刪除**。\n"
                "建議改用「停用客戶 {c.code}」"
                "（將 is_active 設 false，資料保留但不可下單）。"
            ),
        }

    summary = [
        f"⚠️ **將永久刪除客戶**：",
        f"  • 編號：{c.code}",
        f"  • 名稱：{c.name}",
        f"  • 等級：{c.grade or '(無)'}",
        f"  • 信用額度：${c.credit_limit:,.0f}",
        "",
        "❗ **此操作不可逆**（90 秒撤銷視窗無效於刪除）。",
        "如有疑慮，建議改用「停用」（is_active=false）。",
    ]

    card = make_card(
        tool_name="delete_customer_with_confirm",
        title="🗑️ 確認刪除客戶",
        summary=summary,
        slots={"customer_id": c.id, "code": c.code, "name": c.name},
        risk_tier="hard-write",
        ttl_seconds=600,  # 10 分鐘 — 刪除類給更長思考時間
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        # v3.40 M4：先 snapshot 推入 undo stack
        from app.agents.domains.polish_tools import push_undo
        snapshot = {col.name: getattr(c, col.name)
                    for col in Customer.__table__.columns}
        from app.services.sales import delete_customer
        try:
            r = await delete_customer(db, c.id, user)
            uid = (user or {}).get("user_id") or "anonymous"
            push_undo(uid, {"kind": "delete_customer", "before": {"snapshot": snapshot}})
            return {"message": f"✅ 客戶 {r['code']} 已刪除（90 秒內可撤銷）。", **r}
        except Exception as e:
            return {"error": f"刪除失敗：{str(e)[:200]}"}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="delete_supplier_with_confirm",
    domain="purchase",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "刪除指定供應商（**僅在無任何採購單時可刪**）。"
        "範例：「刪掉供應商 S-001」「移除長江五金」。"
    ),
    slots=[Slot("supplier_keyword", "string", required=True,
                description="供應商編號或名稱")],
    required_permission="purchase.supplier.delete",
)
async def _delete_supplier_with_confirm(db, user, supplier_keyword: str):
    keyword = supplier_keyword.strip()
    s = (await db.execute(
        select(Supplier).where(
            (Supplier.code == keyword) | (Supplier.name == keyword)
        )
    )).scalar_one_or_none()
    if s is None:
        s = (await db.execute(
            select(Supplier).where(
                (Supplier.code.like(f"%{keyword}%")) | (Supplier.name.like(f"%{keyword}%"))
            ).limit(2)
        )).scalars().first()
        if s is None:
            return {"error": f"找不到供應商「{keyword}」"}

    from app.models.purchase import PurchaseOrder
    has_po = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.supplier_id == s.id).limit(1)
    )).scalar_one_or_none()
    if has_po is not None:
        return {
            "error": (
                f"⚠️ 供應商「{s.code} - {s.name}」已有採購單，不可刪除。"
                "建議改用「停用供應商」（is_active=false）。"
            ),
        }

    summary = [
        f"⚠️ **將永久刪除供應商**：",
        f"  • 編號：{s.code}",
        f"  • 名稱：{s.name}",
        f"  • 層級：{s.tier or '(無)'}",
        "",
        "❗ **此操作不可逆**。如有疑慮請改用停用。",
    ]
    card = make_card(
        tool_name="delete_supplier_with_confirm",
        title="🗑️ 確認刪除供應商",
        summary=summary,
        slots={"supplier_id": s.id, "code": s.code, "name": s.name},
        risk_tier="hard-write",
        ttl_seconds=600,
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        # v3.40 M4：先 snapshot 推入 undo stack
        from app.agents.domains.polish_tools import push_undo
        snapshot = {col.name: getattr(s, col.name)
                    for col in Supplier.__table__.columns}
        await db.delete(s)
        await db.commit()
        uid = (user or {}).get("user_id") or "anonymous"
        push_undo(uid, {"kind": "delete_supplier", "before": {"snapshot": snapshot}})
        return {"message": f"✅ 供應商 {s.code} 已刪除（90 秒內可撤銷）。",
                "supplier_id": s.id, "code": s.code}

    await stash_card(card, execute)
    return card.to_chat_payload()


@register_tool(
    name="delete_part_with_confirm",
    domain="inventory",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "刪除指定料件（**僅在無任何 BOM / 庫存交易 / PO line 引用時可刪**）。"
        "範例：「刪料件 M6-BOLT」「移除料號 ABC-001」。"
    ),
    slots=[Slot("part_keyword", "string", required=True,
                description="料號或品名")],
    required_permission="inventory.part.delete",
)
async def _delete_part_with_confirm(db, user, part_keyword: str):
    keyword = part_keyword.strip()
    p = (await db.execute(
        select(Part).where(
            (Part.part_no == keyword) | (Part.name == keyword)
        )
    )).scalar_one_or_none()
    if p is None:
        p = (await db.execute(
            select(Part).where(
                (Part.part_no.like(f"%{keyword}%")) | (Part.name.like(f"%{keyword}%"))
            ).limit(2)
        )).scalars().first()
        if p is None:
            return {"error": f"找不到料件「{keyword}」"}

    # 預檢查 BOM / PO line / Inventory transaction
    from app.models.product import BOMItem
    from app.models.purchase import PurchaseOrderItem
    from app.models.inventory import InventoryTransaction
    in_bom = (await db.execute(
        select(BOMItem).where(BOMItem.part_id == p.id).limit(1)
    )).scalar_one_or_none()
    if in_bom:
        return {"error": f"⚠️ 料件「{p.part_no}」已用於 BOM，不可刪除（先從 BOM 移除）。"}
    in_po = (await db.execute(
        select(PurchaseOrderItem).where(PurchaseOrderItem.part_id == p.id).limit(1)
    )).scalar_one_or_none()
    if in_po:
        return {"error": f"⚠️ 料件「{p.part_no}」有採購紀錄，不可刪除（改用停用 is_active=false）。"}
    in_tx = (await db.execute(
        select(InventoryTransaction).where(InventoryTransaction.part_id == p.id).limit(1)
    )).scalar_one_or_none()
    if in_tx:
        return {"error": f"⚠️ 料件「{p.part_no}」有庫存交易紀錄，不可刪除。"}

    summary = [
        f"⚠️ **將永久刪除料件**：",
        f"  • 料號：{p.part_no}",
        f"  • 品名：{p.name}",
        f"  • 類別：{p.category or '(無)'}",
        "",
        "❗ **此操作不可逆**。",
    ]
    card = make_card(
        tool_name="delete_part_with_confirm",
        title="🗑️ 確認刪除料件",
        summary=summary,
        slots={"part_id": p.id, "part_no": p.part_no, "name": p.name},
        risk_tier="hard-write",
        ttl_seconds=600,
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        # v3.40 M4：先 snapshot
        from app.agents.domains.polish_tools import push_undo
        snapshot = {col.name: getattr(p, col.name)
                    for col in Part.__table__.columns}
        # 也清掉 Inventory 行（FK CASCADE 沒設）
        from app.models.inventory import Inventory
        inv = (await db.execute(
            select(Inventory).where(Inventory.part_id == p.id)
        )).scalar_one_or_none()
        if inv:
            await db.delete(inv)
        await db.delete(p)
        await db.commit()
        uid = (user or {}).get("user_id") or "anonymous"
        push_undo(uid, {"kind": "delete_part", "before": {"snapshot": snapshot}})
        return {"message": f"✅ 料件 {p.part_no} 已刪除（90 秒內可撤銷）。",
                "part_id": p.id, "part_no": p.part_no}

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# K7: 批次列印（將多張 PDF 打包成 zip）
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="print_multiple_orders_with_confirm",
    domain="print",
    risk_tier=RiskTier.HARD_WRITE,  # 雖然是讀，但會大量耗運算，加 confirm 保護
    description=(
        "批次列印多張單據 PDF 並打包成 ZIP。"
        "範例：「印 SO-001 SO-002 SO-003」「批次印這個月的 PO」。"
    ),
    slots=[
        Slot("doc_type", "string", required=True,
             description="種類：so（銷售單） / po（採購單） / quotation（報價單）"),
        Slot("doc_nos", "string", required=True,
             description="單號清單，用逗號分隔（如：SO-001,SO-002,SO-003）"),
    ],
    required_permission="sales.order.read",
)
async def _print_multiple_orders_with_confirm(
    db, user, doc_type: str, doc_nos: str,
):
    doc_type = (doc_type or "").lower().strip()
    nos = [n.strip() for n in (doc_nos or "").split(",") if n.strip()]
    if not nos:
        return {"error": "請提供至少一個單號（用逗號分隔）。"}
    if len(nos) > 50:
        return {"error": f"一次最多 50 張，您給了 {len(nos)} 張。"}
    if doc_type not in ("so", "po", "quotation"):
        return {"error": f"不支援的 doc_type「{doc_type}」（應為 so/po/quotation）。"}

    summary = [
        f"📦 將批次列印 **{len(nos)} 張 {doc_type.upper()}** 並打包 ZIP：",
        "",
    ]
    for no in nos[:10]:
        summary.append(f"  • {no}")
    if len(nos) > 10:
        summary.append(f"  ...（及其它 {len(nos) - 10} 張）")
    summary.append("")
    summary.append("✅ 確認後產生 ZIP，瀏覽器自動下載。")

    card = make_card(
        tool_name="print_multiple_orders_with_confirm",
        title=f"📦 確認批次列印 {len(nos)} 張",
        summary=summary,
        slots={"doc_type": doc_type, "doc_nos": nos, "count": len(nos)},
        risk_tier="hard-write",
        ttl_seconds=600,
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        from app.services.print_service import (
            generate_so_pdf, generate_po_pdf, generate_quotation_pdf,
        )
        from app.models.crm_sales import SalesOrder
        from app.models.purchase import PurchaseOrder
        from app.models.quotation import Quotation

        buf = io.BytesIO()
        success = []
        failed = []
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for no in nos:
                try:
                    if doc_type == "so":
                        entity = (await db.execute(
                            select(SalesOrder).where(SalesOrder.so_no == no)
                        )).scalar_one_or_none()
                        if not entity:
                            failed.append(no); continue
                        pdf = await generate_so_pdf(db, entity.id, doc_type="sales_order")
                        zf.writestr(f"{no}.pdf", pdf)
                    elif doc_type == "po":
                        entity = (await db.execute(
                            select(PurchaseOrder).where(PurchaseOrder.po_no == no)
                        )).scalar_one_or_none()
                        if not entity:
                            failed.append(no); continue
                        pdf = await generate_po_pdf(db, entity.id)
                        zf.writestr(f"{no}.pdf", pdf)
                    elif doc_type == "quotation":
                        entity = (await db.execute(
                            select(Quotation).where(Quotation.quote_no == no)
                        )).scalar_one_or_none()
                        if not entity:
                            failed.append(no); continue
                        pdf = await generate_quotation_pdf(db, entity.id)
                        zf.writestr(f"{no}.pdf", pdf)
                    success.append(no)
                except Exception as e:
                    failed.append(f"{no}({str(e)[:30]})")

        zip_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        return {
            "message": f"✅ 批次列印完成：{len(success)} 成功，{len(failed)} 失敗。",
            "success_count": len(success),
            "failed_count": len(failed),
            "failed_list": failed,
            "filename": f"{doc_type}-batch-{ts}.zip",
            "base64": zip_b64,
            "size_kb": len(buf.getvalue()) // 1024,
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# K6: 手動觸發 daily digest（cron 由 OS / docker compose 接管）
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="trigger_daily_digest_now",
    domain="system",
    risk_tier=RiskTier.READ,
    description=(
        "立刻產生並寄出今日 daily digest（給老闆看的「今日重點」）。"
        "範例：「現在發 daily digest」「立刻寄今日摘要給我」「我要看 daily」。"
        "💡 想定時自動寄？請見 docs/pdf/33_第二輪卡關修補法律聲明_中文.pdf §6 教您設 cron / Task Scheduler。"
    ),
    slots=[
        Slot("to", "string", required=False,
             description="收件信箱（不填則只 preview 不寄）"),
        Slot("period_hours", "integer", required=False,
             description="回顧時長（小時），預設 24"),
    ],
    required_permission="user.profile.read",
)
async def _trigger_daily_digest_now(db, user, to: str = "", period_hours: int = 24):
    from app.services.email_digest import build_digest
    digest = await build_digest(db, period_hours=period_hours)

    summary_lines = [
        f"📰 **今日 Daily Digest（過去 {period_hours} 小時）**",
        "",
        digest.get("summary", "(無資料)") if isinstance(digest, dict) else str(digest)[:500],
    ]

    if to:
        summary_lines.append("")
        summary_lines.append(f"📤 已準備寄至：{to}（請另外用 send_digest tool 確認）")

    return {
        "summary": "\n".join(summary_lines),
        "raw": {
            "digest": digest if isinstance(digest, dict) else {"text": str(digest)[:1000]},
            "to": to,
            "period_hours": period_hours,
        },
    }


# ════════════════════════════════════════════════════════════════════
# K3: 分頁查詢 — 給「下一頁」清單查
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="list_customers_paginated",
    domain="sales",
    risk_tier=RiskTier.READ,
    description=(
        "分頁列出客戶（含「下一頁」）— 1000 筆也不爆 LLM。"
        "範例：「列客戶第 2 頁」「給我所有客戶分頁」「客戶總共幾個？」"
    ),
    slots=[
        Slot("page", "integer", required=False, description="頁數，預設 1"),
        Slot("page_size", "integer", required=False, description="每頁筆數，預設 20，最大 50"),
        Slot("keyword", "string", required=False, description="名稱或編號關鍵字"),
    ],
    required_permission="crm.customer.read",
)
async def _list_customers_paginated(db, user, page: int = 1,
                                     page_size: int = 20, keyword: str = ""):
    from sqlalchemy import func
    page = max(1, int(page or 1))
    page_size = min(50, max(1, int(page_size or 20)))
    offset = (page - 1) * page_size

    q = select(Customer)
    if keyword:
        like = f"%{keyword.lower()}%"
        q = q.where((func.lower(Customer.code).like(like)) | (func.lower(Customer.name).like(like)))

    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar() or 0
    rows = (await db.execute(
        q.order_by(Customer.code).offset(offset).limit(page_size)
    )).scalars().all()

    total_pages = (total + page_size - 1) // page_size
    lines = [
        f"👥 **客戶清單 — 第 {page}/{total_pages} 頁**（共 {total} 筆）",
        "",
    ]
    for c in rows:
        lines.append(f"  • **{c.code}** - {c.name}"
                     + (f" ({c.grade})" if c.grade else ""))
    if not rows:
        lines.append("（本頁無資料）")
    elif page < total_pages:
        lines.append("")
        lines.append(f"💡 看下一頁：「列客戶第 {page + 1} 頁」")

    return {
        "summary": "\n".join(lines),
        "raw": {
            "page": page, "page_size": page_size, "total": total,
            "total_pages": total_pages,
            "items": [{"id": c.id, "code": c.code, "name": c.name,
                       "grade": c.grade} for c in rows],
        },
    }
