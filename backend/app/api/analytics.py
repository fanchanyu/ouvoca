"""
Analytics API — 給客戶決策用的 KPI endpoint 群。

設計原則：
1. 所有指標都是「即時計算」（不依賴 BI 工具或 DWH）
2. 回傳結構統一：metric / value / unit / breakdown / period / generated_at
3. 全部走 RBAC，需要 `analytics.view` 權限
4. 對效能敏感的查詢用 SQL aggregate（不要 ORM N+1）

KPI 清單：
- /dso              Days Sales Outstanding 應收帳款週轉天數
- /inventory-turn   庫存週轉率
- /gross-margin     毛利率（依產品/客戶/期間）
- /oee              Overall Equipment Effectiveness
- /purchase-concentration 採購集中度（top suppliers 佔比）
- /ai-cost          LLM 月度成本（依 agent / 依 model）
- /summary          老闆儀表板（一頁所有重點）
"""
from __future__ import annotations
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import require_permission, UserContext

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def _period_dates(period_days: int) -> tuple[datetime, datetime]:
    """回 (period_start, period_end_inclusive)。"""
    end = datetime.now(UTC).replace(tzinfo=None)
    start = end - timedelta(days=period_days)
    return start, end


# ─── DSO ────────────────────────────────────────────────────
@router.get("/dso")
async def dso(
    period_days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """應收帳款週轉天數 (Days Sales Outstanding)
    DSO = (期末 AR / 期間銷售) × 期間天數
    """
    from app.models.accounting import AccountsReceivable
    from app.models.crm_sales import SalesOrder

    start, end = _period_dates(period_days)

    # 期末未結 AR 總額
    ar_q = select(func.coalesce(func.sum(AccountsReceivable.amount), 0)).where(
        AccountsReceivable.status.in_(("open", "outstanding"))
    )
    ar_total = float((await db.execute(ar_q)).scalar() or 0)

    # 期間銷售（已出貨的 SO 金額）
    sales_q = select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
        and_(
            SalesOrder.actual_delivery_date.between(start, end),
            SalesOrder.status.in_(("shipped", "delivered", "closed")),
        )
    )
    sales_total = float((await db.execute(sales_q)).scalar() or 0)

    dso_value = (ar_total / sales_total * period_days) if sales_total > 0 else 0.0

    return {
        "metric": "dso",
        "value": round(dso_value, 1),
        "unit": "days",
        "breakdown": {
            "ar_outstanding": ar_total,
            "sales_in_period": sales_total,
            "period_days": period_days,
        },
        "interpretation": (
            "正常 30-45 天；> 60 天表示客戶付款拖延需追"
            if dso_value > 0
            else "期間內無銷售或 AR — 不適用"
        ),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
    }


# ─── Inventory Turn ─────────────────────────────────────────
@router.get("/inventory-turn")
async def inventory_turn(
    period_days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """庫存週轉率 = COGS / 平均庫存。
    簡化版：用「出庫總量」近似 COGS、用當下 qty_on_hand 近似平均庫存。
    """
    from app.models.inventory import InventoryTransaction, Inventory, Part

    start, end = _period_dates(period_days)

    # 期間出庫量（以金額計）
    out_q = select(
        func.coalesce(func.sum(InventoryTransaction.qty * Part.unit_cost), 0)
    ).select_from(InventoryTransaction).join(
        Part, Part.id == InventoryTransaction.part_id
    ).where(
        and_(
            InventoryTransaction.created_at.between(start, end),
            InventoryTransaction.transaction_type.in_((
                "outbound", "issue", "consumption"
            )),
        )
    )
    cogs_value = float((await db.execute(out_q)).scalar() or 0)

    # 當下庫存金額
    inv_q = select(
        func.coalesce(func.sum(Inventory.qty_on_hand * Part.unit_cost), 0)
    ).select_from(Inventory).join(Part, Part.id == Inventory.part_id)
    inv_value = float((await db.execute(inv_q)).scalar() or 0)

    # 年化週轉率
    annualization = 365 / period_days
    turn = (cogs_value / inv_value * annualization) if inv_value > 0 else 0.0

    return {
        "metric": "inventory_turn",
        "value": round(turn, 2),
        "unit": "times/year",
        "breakdown": {
            "cogs_value_in_period": round(cogs_value, 2),
            "current_inventory_value": round(inv_value, 2),
            "period_days": period_days,
        },
        "interpretation": (
            "電子業健康 6-12；金屬加工 3-6；食品 12+；< 2 表庫存過剩"
        ),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
    }


# ─── Gross Margin ───────────────────────────────────────────
@router.get("/gross-margin")
async def gross_margin(
    period_days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """毛利率 = (銷售收入 - COGS) / 銷售收入。
    簡化：用已出貨 SO 收入 vs 對應 SO items 的成本（part.unit_cost）。
    """
    from app.models.crm_sales import SalesOrder, SalesOrderItem
    from app.models.product import Product
    from app.models.inventory import Part

    start, end = _period_dates(period_days)

    # 收入
    rev_q = select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
        and_(
            SalesOrder.actual_delivery_date.between(start, end),
            SalesOrder.status.in_(("shipped", "delivered", "closed")),
        )
    )
    revenue = float((await db.execute(rev_q)).scalar() or 0)

    # 成本：SO item 的 (ordered_qty × 對應 part.unit_cost)
    cost_q = select(
        func.coalesce(func.sum(SalesOrderItem.ordered_qty * Part.unit_cost), 0)
    ).select_from(SalesOrderItem).join(
        SalesOrder, SalesOrder.id == SalesOrderItem.so_id
    ).join(
        Product, Product.id == SalesOrderItem.product_id
    ).join(
        Part, Part.part_no == Product.product_no
    ).where(
        and_(
            SalesOrder.actual_delivery_date.between(start, end),
            SalesOrder.status.in_(("shipped", "delivered", "closed")),
        )
    )
    cogs = float((await db.execute(cost_q)).scalar() or 0)

    gross_profit = revenue - cogs
    margin = (gross_profit / revenue * 100) if revenue > 0 else 0.0

    return {
        "metric": "gross_margin",
        "value": round(margin, 2),
        "unit": "percent",
        "breakdown": {
            "revenue": round(revenue, 2),
            "cogs": round(cogs, 2),
            "gross_profit": round(gross_profit, 2),
        },
        "interpretation": (
            "製造業 20-40% 健康；< 15% 警訊；> 50% 待驗證售價是否合理"
        ),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
    }


# ─── OEE ────────────────────────────────────────────────────
@router.get("/oee")
async def oee(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """Overall Equipment Effectiveness = 可用率 × 效能 × 品質。
    當前簡化版：用 WO 完成率近似品質指標（之後接入工時統計可補完）。
    """
    from app.models.production import ProductionOrder

    start, end = _period_dates(period_days)

    base_q = select(ProductionOrder).where(
        ProductionOrder.created_at.between(start, end),
    )
    wos = list((await db.execute(base_q)).scalars().all())

    if not wos:
        return {
            "metric": "oee",
            "value": 0,
            "unit": "percent",
            "interpretation": "期間內無工單，無法計算",
            "breakdown": {"work_orders": 0},
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
        }

    total_ordered = sum(w.ordered_qty for w in wos)
    total_completed = sum(w.completed_qty or 0 for w in wos)
    quality = (total_completed / total_ordered * 100) if total_ordered > 0 else 0

    # 可用率：completed / created 比例（沒卡單）
    completed_count = sum(1 for w in wos if w.status == "completed")
    availability = (completed_count / len(wos) * 100) if wos else 0

    # 簡化效能：假設 80%（之後接 actual_duration / planned_duration）
    performance = 80.0

    oee_value = (availability * performance * quality) / 10000

    return {
        "metric": "oee",
        "value": round(oee_value, 1),
        "unit": "percent",
        "breakdown": {
            "availability_pct": round(availability, 1),
            "performance_pct": round(performance, 1),
            "quality_pct": round(quality, 1),
            "wo_count": len(wos),
            "completed_count": completed_count,
        },
        "interpretation": (
            "世界級 85%；製造業健康 60-75%；< 50% 需深度檢討"
        ),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
    }


# ─── Purchase Concentration ─────────────────────────────────
@router.get("/purchase-concentration")
async def purchase_concentration(
    period_days: int = Query(180, ge=7, le=730),
    top_n: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """採購集中度：top N 供應商佔總採購金額的比例。
    > 60% = 高度集中（供應商議價力大、斷貨風險）
    < 30% = 過度分散（可能採購量議價力弱）
    """
    from app.models.purchase import PurchaseOrder, Supplier

    start, end = _period_dates(period_days)

    # 每家供應商在期間內的採購總額
    q = select(
        Supplier.code, Supplier.name,
        func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label("total"),
    ).select_from(Supplier).outerjoin(
        PurchaseOrder, and_(
            PurchaseOrder.supplier_id == Supplier.id,
            PurchaseOrder.order_date.between(start, end),
            PurchaseOrder.status.in_(("approved", "received", "partial_received")),
        ),
    ).group_by(Supplier.id, Supplier.code, Supplier.name)

    rows = list((await db.execute(q)).all())
    rows.sort(key=lambda r: r.total, reverse=True)

    grand_total = sum(r.total for r in rows)
    top_rows = rows[:top_n]
    top_total = sum(r.total for r in top_rows)

    concentration = (top_total / grand_total * 100) if grand_total > 0 else 0.0

    return {
        "metric": "purchase_concentration",
        "value": round(concentration, 1),
        "unit": "percent",
        "breakdown": {
            "top_n": top_n,
            "top_suppliers": [
                {"code": r.code, "name": r.name, "amount": float(r.total)}
                for r in top_rows
            ],
            "grand_total": float(grand_total),
            "supplier_count": len(rows),
        },
        "interpretation": (
            "> 60% 高度集中（議價弱、風險集中）；30-60% 健康；< 30% 過度分散"
        ),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
    }


# ─── AI Cost ────────────────────────────────────────────────
@router.get("/ai-cost")
async def ai_cost(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """LLM 月度成本明細（從 DecisionLog 統計 token cost）。
    若 DecisionLog 沒記 cost — 顯示 0 + 提示要打開 cost tracking。
    """
    start, end = _period_dates(period_days)

    # 試著從 DecisionLog 抓 token / cost
    try:
        from app.models.ai_governance import DecisionLog

        q = select(
            DecisionLog.agent_name,
            func.count(DecisionLog.id).label("call_count"),
            func.coalesce(func.sum(DecisionLog.input_tokens), 0).label("in_tokens"),
            func.coalesce(func.sum(DecisionLog.output_tokens), 0).label("out_tokens"),
            func.coalesce(func.sum(DecisionLog.cost_usd), 0).label("cost_usd"),
        ).where(
            DecisionLog.created_at.between(start, end)
        ).group_by(DecisionLog.agent_name)

        rows = list((await db.execute(q)).all())
        by_agent = [
            {
                "agent": r.agent_name,
                "calls": int(r.call_count),
                "in_tokens": int(r.in_tokens),
                "out_tokens": int(r.out_tokens),
                "cost_usd": round(float(r.cost_usd), 4),
            }
            for r in rows
        ]
        total_cost = sum(a["cost_usd"] for a in by_agent)
        total_calls = sum(a["calls"] for a in by_agent)

    except Exception as e:
        return {
            "metric": "ai_cost",
            "value": 0,
            "unit": "USD",
            "breakdown": {
                "error": str(e),
                "by_agent": [],
                "total_calls": 0,
            },
            "interpretation": (
                "需在 DecisionLog 加 input_tokens/output_tokens/cost_usd 欄位"
                "並由 LLM provider adapter 寫入"
            ),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
        }

    return {
        "metric": "ai_cost",
        "value": round(total_cost, 2),
        "unit": "USD",
        "breakdown": {
            "by_agent": by_agent,
            "total_calls": total_calls,
            "avg_cost_per_call": (
                round(total_cost / total_calls, 4) if total_calls else 0
            ),
        },
        "interpretation": (
            "50 人廠典型 NT$ 800-3000/月。"
            "超量請檢查：(1) 是否被攻擊 (2) cache 是否生效 (3) prompt 是否冗長"
        ),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
    }


# ─── Boss Dashboard Summary ─────────────────────────────────
@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission("analytics.view")),
):
    """老闆儀表板：一頁所有 KPI（給 LINE Bot / Mobile Dashboard 用）。"""
    # 平行（為了示意，這裡先序列拿）
    results: Dict[str, Any] = {}
    for name, fn in [
        ("dso", dso), ("inventory_turn", inventory_turn),
        ("gross_margin", gross_margin), ("oee", oee),
        ("purchase_concentration", purchase_concentration),
        ("ai_cost", ai_cost),
    ]:
        try:
            # 直接呼叫底層（不走 FastAPI 注入）
            if name == "dso":
                results[name] = await dso(90, db, user)
            elif name == "inventory_turn":
                results[name] = await inventory_turn(90, db, user)
            elif name == "gross_margin":
                results[name] = await gross_margin(90, db, user)
            elif name == "oee":
                results[name] = await oee(30, db, user)
            elif name == "purchase_concentration":
                results[name] = await purchase_concentration(180, 5, db, user)
            elif name == "ai_cost":
                results[name] = await ai_cost(30, db, user)
        except Exception as e:
            results[name] = {"error": str(e)}

    return {
        "metric": "boss_summary",
        "kpis": {k: v.get("value") if isinstance(v, dict) else None for k, v in results.items()},
        "full": results,
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
    }
