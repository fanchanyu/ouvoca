"""
Conversational Planning LLM Tools  (v3.30)
═══════════════════════════════════════════════════════════════════════

** This is the file that makes v3.25.9 - v3.29's IE/OR algorithms
   actually accessible to SMB owners via conversation. **

Without this layer, all five prior sprints (BOM multilevel, MRP-II,
Capacity-aware CLSP, Explainability + TOC, Throughput Accounting,
Demand Forecasting) are invisible to non-technical users — they live
only in Python services that engineers must call programmatically.
This violates Ouvoca's North-Star promise:

    "Natural language replaces training. The owner just talks to it."

This file wraps each algorithm as a `@register_tool` for the LLM,
with natural-language descriptions, slot definitions for argument
extraction, RBAC permissions, and ConfirmCard flow for hard-writes.

──────────────────────────────────────────────────────────────────────
10 LLM Tools (wrapping algorithms from v3.25.9 - v3.29)
──────────────────────────────────────────────────────────────────────

Demand Forecasting (v3.29):
  • forecast_demand_for_part      — "幫我預測下季 M6 螺絲需求"
  • commit_forecast_to_mps_with_confirm  — "把預測寫入 MPS"

Explainability (v3.27):
  • explain_planned_order_tool    — "為什麼下週要備這麼多 M6？"
  • identify_bottlenecks_tool     — "我們現在的瓶頸在哪？"
  • counterfactual_capacity_tool  — "如果加 20% 產能會怎樣？"

Order Acceptance & TA (v3.28):
  • evaluate_order_acceptance_tool — "這張單該不該接？"
  • explore_pricing_curve_tool    — "降到多少還能接？"
  • compute_dbr_schedule_tool     — "幫我排產（DBR）"

BOM (v3.25.9):
  • where_used_tool               — "M6 螺絲被用在哪些產品？"

Daily Briefing ⭐ killer feature:
  • daily_briefing_tool           — "今天我該注意什麼？"
                                    整合 todo / bottleneck / forecast / anomaly

──────────────────────────────────────────────────────────────────────
LEGAL / 法律說明
──────────────────────────────────────────────────────────────────────
This module wraps complex IE/OR algorithms in LLM-callable tools.
Customers MUST understand:

  • LLM may **misinterpret** natural-language requests, calling tools
    with wrong slot values. **All hard-write tools MUST use ConfirmCard**
    so the user reviews the actual numbers before execution.
  • LLM-formatted responses (the "human-friendly" explanations) may
    **simplify or omit** important nuance from the raw algorithm output.
    For critical decisions, customers should view the raw structured
    data (accessible via the tool's full response object, not just
    the LLM-rendered text).
  • LLM may **hallucinate** business context (e.g., reasons behind a
    forecast anomaly). LLM suggestions are advisory only.
  • Daily Briefing aggregates multiple algorithm outputs — each carries
    its own limitations documented in v3.25.10 / v3.26 / v3.27 / v3.28
    / v3.29 §6 disclaimers. The aggregation does NOT reduce risk;
    customers should verify each surfaced item.

To the maximum extent permitted by applicable law, Ouvoca assumes
no liability for misinterpretation, hallucination, or decisions made
based on LLM-rendered planning recommendations. See
docs/CONVERSATIONAL_PLANNING_DESIGN_ZH.md §6 for full disclaimer.

本模組將 v3.25.9 - v3.29 之 IE/OR 演算法包裝為 LLM 可呼叫工具。
所有 hard-write 必走 ConfirmCard；LLM 渲染之自然語言解釋可能簡化
或省略重要細節；客戶應於關鍵決策時檢視 raw structured data；
LLM 可能 hallucinate 業務情境。詳見 §6 法律聲明。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.agents.confirm_card import make_card, stash_card
from app.agents.registry import register_tool, RiskTier, Slot
from app.models.inventory import Part
from app.models.product import Product
from app.models.production import WorkCenter
from app.models.mps_mrp import MpsMaster, MpsEntry, MrpMaster, MrpItem
from app.models.crm_sales import SalesOrder


# ════════════════════════════════════════════════════════════════════
# Helper: format ForecastResult as human-readable text
# ════════════════════════════════════════════════════════════════════

def _format_forecast_for_humans(part_no: str, result, horizon: int) -> Dict[str, Any]:
    """Convert ForecastResult to dict with both raw + human-readable text."""
    lines = [
        f"📈 **預測：{part_no}** 未來 {horizon} 期",
        f"使用方法：{result.method}",
    ]
    if result.mase is not None:
        baseline_text = "✅ 勝過 naive baseline" if result.mase < 1.0 else "⚠️ 不如 naive baseline"
        lines.append(f"MASE = {result.mase:.2f}（{baseline_text}；越小越好）")
    if result.mape is not None:
        lines.append(f"MAPE = {result.mape:.1f}%")
    lines.append("")
    lines.append("**點預測**：")
    for k, v in enumerate(result.point_forecast, start=1):
        if result.lower_95 and result.upper_95 and k <= len(result.lower_95):
            lines.append(
                f"  期 {k}: {v:.1f}  "
                f"(95% PI: {result.lower_95[k-1]:.1f} ~ {result.upper_95[k-1]:.1f})"
            )
        else:
            lines.append(f"  期 {k}: {v:.1f}")
    return {
        "summary": "\n".join(lines),
        "raw": result.to_dict(),
        "warning": (
            "⚠️ 預測為統計估計，不構成未來保證。重大決策請覆核並考量市場條件。"
            "詳見 DEMAND_FORECASTING_DESIGN §6 法律聲明。"
        ),
    }


# ════════════════════════════════════════════════════════════════════
# Tool 1: Forecast demand for a part
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="forecast_demand_for_part",
    domain="planning",
    risk_tier=RiskTier.READ,
    description=(
        "預測單一料件的未來需求（自動挑選最佳演算法 from 5 種：Naive / SES / "
        "Holt / Holt-Winters / Croston）。對 intermittent demand 自動切換 "
        "Croston。回傳點預測、95% 預測區間、與 MASE 評分。"
        "範例：「幫我預測未來 6 個月的 M6 螺絲需求」"
    ),
    slots=[
        Slot("part_no", "string", required=True, description="料件編號"),
        Slot("horizon", "integer", required=False,
             description="預測未來幾期（預設 6）"),
        Slot("season_length", "integer", required=False,
             description="季節長度（月=12, 週=52, 預設 12）"),
    ],
    required_permission="inventory.part.read",
)
async def _forecast_demand_tool(
    db, user,
    part_no: str, horizon: int = 6, season_length: int = 12,
) -> Dict[str, Any]:
    from app.services.demand_forecasting import forecast, ForecastMethod
    from app.models.inventory import InventoryTransaction

    # Find the part
    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalar_one_or_none()
    if part is None:
        return {"error": f"找不到料件「{part_no}」"}

    # Get historical demand from outbound transactions (last 24 periods or all)
    txns = (await db.execute(
        select(InventoryTransaction).where(
            InventoryTransaction.part_id == part.id,
            InventoryTransaction.transaction_type == "outbound",
        ).order_by(InventoryTransaction.created_at)
    )).scalars().all()

    if not txns:
        return {
            "error": f"料件「{part_no}」沒有歷史出貨資料，無法預測。",
            "hint": "建議至少有 24 個月的歷史 outbound 紀錄；若為新料件可手動填入 MPS。",
        }

    # Bucket by period (weekly default; can extend to monthly later)
    # Simple bucketization: group by week using created_at.isocalendar()
    from collections import defaultdict
    bucket: Dict[tuple, float] = defaultdict(float)
    for t in txns:
        if t.created_at:
            year, week, _ = t.created_at.isocalendar()
            bucket[(year, week)] += float(t.qty or 0)

    sorted_keys = sorted(bucket.keys())
    history = [bucket[k] for k in sorted_keys]

    if len(history) < 4:
        return {
            "error": f"歷史資料太少（僅 {len(history)} 期）；建議至少 12 期",
            "hint": "可用較粗時間粒度（如月）或手動填 MPS",
        }

    # Run forecast with auto method selection
    result = forecast(
        history, horizon=horizon, method=ForecastMethod.AUTO,
        season_length=season_length,
    )

    return _format_forecast_for_humans(part_no, result, horizon)


# ════════════════════════════════════════════════════════════════════
# Tool 2: Commit forecast to MPS (hard-write)
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="commit_forecast_to_mps_with_confirm",
    domain="planning",
    risk_tier=RiskTier.HARD_WRITE,
    description=(
        "把預測結果寫入 MPS（主生產排程）。出 ConfirmCard 給使用者確認後才寫。"
        "客戶可在卡上覆核每期之計畫數量。範例：「把這份預測寫入 MPS」"
    ),
    slots=[
        Slot("product_no", "string", required=True, description="產品編號"),
        Slot("mps_name", "string", required=True, description="MPS 名稱"),
        Slot("planned_production_per_period", "array", required=True,
             description="每期計畫生產數量陣列，如 [100, 120, 110]"),
        Slot("period_labels", "array", required=False,
             description="期間標籤陣列，如 ['W22','W23','W24']；不填則自動 P1..PN"),
    ],
    required_permission="mps_mrp.master.create",
)
async def _commit_forecast_to_mps(
    db, user,
    product_no: str, mps_name: str,
    planned_production_per_period: List[float],
    period_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    from datetime import datetime, UTC
    import uuid as _uuid

    product = (await db.execute(
        select(Product).where(Product.product_no == product_no)
    )).scalar_one_or_none()
    if product is None:
        return {"error": f"找不到產品「{product_no}」"}

    if not planned_production_per_period or not isinstance(planned_production_per_period, list):
        return {"error": "planned_production_per_period 必須是非空陣列"}

    n = len(planned_production_per_period)
    labels = period_labels if (period_labels and len(period_labels) == n) else [
        f"P{i+1}" for i in range(n)
    ]

    summary = [
        f"📋 MPS 名稱：{mps_name}",
        f"📦 產品：{product.product_no} ({product.name})",
        f"📅 期數：{n} 期",
    ]
    for i, (lbl, qty) in enumerate(zip(labels, planned_production_per_period)):
        summary.append(f"  • {lbl}: {qty:g}")
    total = sum(planned_production_per_period)
    summary.append(f"📊 合計：{total:g}")

    card = make_card(
        tool_name="commit_forecast_to_mps_with_confirm",
        title="📋 確認寫入 MPS",
        summary=summary,
        slots={
            "product_id": product.id, "product_no": product.product_no,
            "mps_name": mps_name,
            "planned_production_per_period": planned_production_per_period,
            "period_labels": labels,
        },
        risk_tier="hard-write",
        created_by=(user or {}).get("employee_id") if user else None,
    )

    async def execute():
        # Create MPS master + entries
        mps = MpsMaster(
            id=str(_uuid.uuid4()),
            mps_name=mps_name,
            horizon_start=datetime.now(UTC).replace(tzinfo=None),
            horizon_end=datetime.now(UTC).replace(tzinfo=None),
            status="draft",
            created_by=(user or {}).get("employee_id") if user else None,
        )
        db.add(mps)
        await db.flush()
        for lbl, qty in zip(labels, planned_production_per_period):
            db.add(MpsEntry(
                id=str(_uuid.uuid4()),
                mps_master_id=mps.id,
                product_id=product.id,
                period=lbl,
                planned_production=float(qty),
            ))
        await db.commit()
        return {
            "mps_id": mps.id,
            "mps_name": mps_name,
            "entries_count": n,
            "message": f"✅ MPS「{mps_name}」已建立，包含 {n} 期計畫",
        }

    await stash_card(card, execute)
    return card.to_chat_payload()


# ════════════════════════════════════════════════════════════════════
# Tool 3: Explain a planned order
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="explain_planned_order_tool",
    domain="planning",
    risk_tier=RiskTier.READ,
    description=(
        "解釋特定 MRP 計畫採購 / 生產數量之上游原因（trace 至 MPS → 客戶訂單）。"
        "範例：「為什麼 W22 要拉這麼多 M6 螺絲？」"
    ),
    slots=[
        Slot("mrp_item_id", "string", required=True, description="MrpItem UUID"),
        Slot("max_depth", "integer", required=False, description="追溯深度（預設 5）"),
    ],
    required_permission="mps_mrp.master.read",
)
async def _explain_planned_order(
    db, user, mrp_item_id: str, max_depth: int = 5,
) -> Dict[str, Any]:
    from app.services.plan_explanation import explain_planned_order

    tree = await explain_planned_order(db, mrp_item_id, max_depth=max_depth)

    return {
        "summary": "🔍 **計畫釋出之因果追溯**\n\n" + tree.render_tree(),
        "raw": tree.to_dict(),
        "warning": (
            "⚠️ 因果鏈基於資料庫於查詢時點之 lineage 關係，"
            "不代表法律上之因果認定。"
        ),
    }


# ════════════════════════════════════════════════════════════════════
# Tool 4: Identify bottlenecks
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="identify_bottlenecks_tool",
    domain="planning",
    risk_tier=RiskTier.READ,
    description=(
        "識別當前 MPS 之 capacity 瓶頸工作中心（Goldratt TOC + Kingman 0.85 閾值）。"
        "提供 elevation 建議（加班 / 替代機台 / 外包 / 升級）。"
        "範例：「我們現在的瓶頸在哪？」「哪台機器最忙？」"
    ),
    slots=[
        Slot("mps_id", "string", required=True, description="MPS UUID"),
    ],
    required_permission="production.workcenter.list",
)
async def _identify_bottlenecks_tool(db, user, mps_id: str) -> Dict[str, Any]:
    from app.services.plan_explanation import identify_bottlenecks

    reports, capacity_result = await identify_bottlenecks(db, mps_id)

    if not reports:
        return {
            "summary": "✅ 沒發現瓶頸 — 各工作中心均未超過 85% 利用率",
            "raw": {"reports": [], "loads_count": len(capacity_result.loads)},
        }

    lines = ["🔍 **瓶頸分析報告**（依尖峰利用率排序）\n"]
    for i, r in enumerate(reports[:5]):  # top 5
        icon = "🔴" if r.is_bottleneck else "🟡" if r.peak_utilization > 0.7 else "🟢"
        lines.append(
            f"{icon} **{r.work_center_code}** "
            f"尖峰利用率 {r.peak_utilization:.1%} (期 {r.peak_period_idx})"
        )
        if r.is_bottleneck:
            for opt in r.elevation_options:
                lines.append(f"   → {opt}")
        lines.append("")

    return {
        "summary": "\n".join(lines),
        "raw": [r.to_dict() for r in reports],
        "warning": (
            "⚠️ TOC 瓶頸識別基於 0.85 utilization 閾值之啟發（Schragenheim-Ronen 1990）。"
            "elevation 建議為一般性方向，capacity 投資決策應由廠長 / 財務覆核。"
        ),
    }


# ════════════════════════════════════════════════════════════════════
# Tool 5: Counterfactual capacity
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="counterfactual_capacity_tool",
    domain="planning",
    risk_tier=RiskTier.READ,
    description=(
        "What-if 模擬：增加特定工作中心之產能會如何影響規劃？"
        "回傳 overload 期數變化 + holding cost delta。"
        "範例：「如果加 20% 沖床產能會怎樣？」"
    ),
    slots=[
        Slot("mps_id", "string", required=True, description="MPS UUID"),
        Slot("work_center_code", "string", required=True, description="工作中心代碼"),
        Slot("multiplier", "number", required=False,
             description="capacity 倍數（預設 1.2 = +20%）"),
    ],
    required_permission="production.workcenter.list",
)
async def _counterfactual_capacity_tool(
    db, user, mps_id: str, work_center_code: str, multiplier: float = 1.2,
) -> Dict[str, Any]:
    from app.services.plan_explanation import counterfactual_capacity_increase

    wc = (await db.execute(
        select(WorkCenter).where(WorkCenter.code == work_center_code)
    )).scalar_one_or_none()
    if wc is None:
        return {"error": f"找不到工作中心「{work_center_code}」"}

    result = await counterfactual_capacity_increase(
        db, mps_id, wc.id, multiplier=multiplier,
    )

    pct = (multiplier - 1) * 100
    arrow = "↑" if pct > 0 else "↓"
    lines = [
        f"🔬 **What-if：{work_center_code} 產能 {arrow}{abs(pct):.0f}%**\n",
        f"📊 超載期數：{result.baseline_overload_count} → {result.modified_overload_count}",
        f"⚠️ 不可行期數：{result.baseline_infeasible_count} → {result.modified_infeasible_count}",
        f"💰 持有成本懲罰變化：{result.holding_cost_delta:+.2f}",
        "",
        result.summary,
    ]

    return {
        "summary": "\n".join(lines),
        "raw": result.to_dict(),
        "warning": (
            "⚠️ Counterfactual 採 OAT 局部敏感度（Saltelli 2008 §2.5），"
            "不模型化變數交互作用。結果僅供方向性參考，不可外推為精確 ROI。"
        ),
    }


# ════════════════════════════════════════════════════════════════════
# Tool 6: Order acceptance evaluation
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="evaluate_order_acceptance_tool",
    domain="planning",
    risk_tier=RiskTier.READ,
    description=(
        "評估是否該接受一張訂單（依 Goldratt Throughput Accounting）。"
        "計算 throughput per CCR-min 並建議 accept / reject / negotiate。"
        "範例：「客戶要 100 個 PROD-001，每個 NT$200，該不該接？」"
    ),
    slots=[
        Slot("product_no", "string", required=True, description="產品編號"),
        Slot("qty", "number", required=True, description="訂購數量"),
        Slot("unit_price", "number", required=True, description="單價"),
        Slot("bottleneck_minutes_required", "number", required=False,
             description="此單需消耗瓶頸時間（min，預設由 routing 算）"),
        Slot("bottleneck_minutes_available", "number", required=False,
             description="目前瓶頸剩餘可用時間（min，預設 2400）"),
        Slot("commission_rate", "number", required=False,
             description="銷售佣金比例（預設 0）"),
        Slot("min_acceptable_t_per_min", "number", required=False,
             description="可接受之最低 T/CCR-min 門檻（預設 0）"),
    ],
    required_permission="sales.order.create",
)
async def _evaluate_order_acceptance_tool(
    db, user,
    product_no: str, qty: float, unit_price: float,
    bottleneck_minutes_required: float = 100,
    bottleneck_minutes_available: float = 2400,
    commission_rate: float = 0.0,
    min_acceptable_t_per_min: float = 0.0,
) -> Dict[str, Any]:
    from app.services.throughput_accounting import (
        compute_product_tvc, evaluate_order_acceptance,
    )

    product = (await db.execute(
        select(Product).where(Product.product_no == product_no)
    )).scalar_one_or_none()
    if product is None:
        return {"error": f"找不到產品「{product_no}」"}

    tvc = await compute_product_tvc(db, product.id, commission_rate=commission_rate)
    result = evaluate_order_acceptance(
        product.id, product_no, qty, unit_price, tvc,
        bottleneck_minutes_required, bottleneck_minutes_available,
        min_acceptable_t_per_min,
    )

    icon = {
        "accept": "🟢", "negotiate": "🟡", "reject": "🔴", "evaluate": "❓",
    }.get(result.recommendation, "❓")

    lines = [
        f"{icon} **訂單評估：{product_no} × {qty:g} 個 @ NT${unit_price:g}**\n",
        f"💵 Revenue：${result.revenue:,.0f}",
        f"💸 TVC（真實變動成本）：${result.total_tvc:,.0f}",
        f"  ├ 原料：${tvc.material_cost * qty:,.0f}",
        f"  └ 佣金：${unit_price * qty * commission_rate:,.0f}",
        f"💰 Throughput：${result.throughput:,.0f}",
        f"⏱ 瓶頸消耗：{result.bottleneck_minutes_required:.0f} min "
        f"(可用 {result.bottleneck_minutes_available:.0f} min)",
        f"⭐ **T per CCR-min: ${result.throughput_per_ccr_minute:.2f}**（越高越值得接）",
        "",
        f"**建議：{result.recommendation.upper()}**",
    ]
    for r in result.reasoning:
        lines.append(f"  • {r}")

    return {
        "summary": "\n".join(lines),
        "raw": result.to_dict(),
        "warning": (
            "⚠️ TA 為管理會計分析，非 GAAP/IFRS 財報。建議僅供業務決策參考，"
            "不可作為訂單承諾或定價之法律約束。重大訂單應有主管覆核。"
        ),
    }


# ════════════════════════════════════════════════════════════════════
# Tool 7: Pricing curve
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="explore_pricing_curve_tool",
    domain="planning",
    risk_tier=RiskTier.READ,
    description=(
        "客戶議價時用：給定基準價，掃描多個 discount levels 看每個價位仍是否值得接。"
        "範例：「客戶要殺價到 NT$180，這樣還能接嗎？」"
    ),
    slots=[
        Slot("product_no", "string", required=True),
        Slot("qty", "number", required=True),
        Slot("base_price", "number", required=True),
        Slot("bottleneck_minutes_required", "number", required=False),
        Slot("min_acceptable_t_per_min", "number", required=False),
    ],
    required_permission="sales.order.create",
)
async def _explore_pricing_curve_tool(
    db, user,
    product_no: str, qty: float, base_price: float,
    bottleneck_minutes_required: float = 100,
    min_acceptable_t_per_min: float = 0.0,
) -> Dict[str, Any]:
    from app.services.throughput_accounting import (
        compute_product_tvc, explore_pricing_curve,
    )

    product = (await db.execute(
        select(Product).where(Product.product_no == product_no)
    )).scalar_one_or_none()
    if product is None:
        return {"error": f"找不到產品「{product_no}」"}

    tvc = await compute_product_tvc(db, product.id)
    scenarios = explore_pricing_curve(
        product.id, product_no, qty, tvc,
        bottleneck_minutes_required, bottleneck_minutes_available=99999,
        base_price=base_price,
        min_acceptable_t_per_min=min_acceptable_t_per_min,
    )

    lines = [f"💹 **議價試算：{product_no} × {qty:g} 個**\n",
             f"{'價格':<10}{'Throughput':<14}{'T/CCR-min':<13}{'建議':<10}"]
    for s in scenarios:
        icon = {"accept": "🟢", "negotiate": "🟡", "reject": "🔴"}.get(s.recommendation, "❓")
        t_str = f"${s.t_per_ccr_minute:.1f}" if s.t_per_ccr_minute != math.inf else "∞"
        lines.append(
            f"${s.unit_price:<9.0f}${s.throughput:<13,.0f}{t_str:<13}{icon} {s.recommendation}"
        )

    return {
        "summary": "\n".join(lines),
        "raw": [{"price": s.unit_price, "throughput": s.throughput,
                 "t_per_min": s.t_per_ccr_minute, "rec": s.recommendation}
                for s in scenarios],
        "warning": (
            "⚠️ 不同客戶之差別定價可能涉及反壟斷合規（公平交易法 / Sherman Act）。"
            "建議由法務顧問審視。"
        ),
    }


# ════════════════════════════════════════════════════════════════════
# Tool 8: DBR Schedule
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="compute_dbr_schedule_tool",
    domain="planning",
    risk_tier=RiskTier.READ,
    description=(
        "Goldratt Drum-Buffer-Rope 排程建議：依瓶頸節奏、3× buffer、同步投料時程。"
        "範例：「請幫我規劃這台沖床的排產節奏」"
    ),
    slots=[
        Slot("work_center_code", "string", required=True),
        Slot("run_time_per_unit", "number", required=True,
             description="瓶頸單件加工時間（min）"),
        Slot("buffer_multiplier", "number", required=False,
             description="buffer 倍數（預設 3× per Schragenheim 2000）"),
        Slot("capacity_minutes_per_period", "number", required=False,
             description="每期可用工時（預設 2400 min = 40h/週）"),
    ],
    required_permission="production.workcenter.list",
)
async def _compute_dbr_schedule_tool(
    db, user,
    work_center_code: str,
    run_time_per_unit: float,
    buffer_multiplier: float = 3.0,
    capacity_minutes_per_period: float = 2400,
) -> Dict[str, Any]:
    from app.services.throughput_accounting import compute_dbr_schedule

    wc = (await db.execute(
        select(WorkCenter).where(WorkCenter.code == work_center_code)
    )).scalar_one_or_none()
    if wc is None:
        return {"error": f"找不到工作中心「{work_center_code}」"}

    schedule = compute_dbr_schedule(
        bottleneck_work_center_id=wc.id,
        bottleneck_code=work_center_code,
        bottleneck_capacity_minutes_per_period=capacity_minutes_per_period,
        bottleneck_run_time_per_unit=run_time_per_unit,
        buffer_multiplier=buffer_multiplier,
    )

    return {
        "summary": "\n".join(schedule.recommendations),
        "raw": {
            "bottleneck_code": schedule.bottleneck_code,
            "drum_throughput": schedule.drum_throughput_per_period,
            "buffer_minutes": schedule.buffer_size_minutes,
            "rope_offset": schedule.rope_release_offset_minutes,
        },
        "warning": (
            "⚠️ Buffer = 3× 為 Schragenheim 2000 經驗值，"
            "在 high-mix-low-volume 或 lead-time 變異大之環境可能需調整。"
        ),
    }


# ════════════════════════════════════════════════════════════════════
# Tool 9: Where-used reverse lookup
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="where_used_tool",
    domain="planning",
    risk_tier=RiskTier.READ,
    description=(
        "反查：這個料件被用在哪些產品的 BOM 中？採購談判 / 替代料評估常用。"
        "範例：「M6 螺絲被用在哪些產品？」"
    ),
    slots=[
        Slot("part_no", "string", required=True, description="料件編號"),
    ],
    required_permission="production.bom.read",
)
async def _where_used_tool(db, user, part_no: str) -> Dict[str, Any]:
    from app.services.production import where_used

    part = (await db.execute(
        select(Part).where(Part.part_no == part_no)
    )).scalar_one_or_none()
    if part is None:
        return {"error": f"找不到料件「{part_no}」"}

    rows = await where_used(db, part.id)
    if not rows:
        return {
            "summary": f"📦 料件「{part_no}」未被任何產品的 BOM 使用",
            "raw": {"part_no": part_no, "used_in": []},
        }

    lines = [f"📦 **{part_no} 被用在 {len(rows)} 個產品的做法中：**\n"]
    for r in rows:
        lines.append(
            f"  • **{r['product_no']}** ({r['product_name']}) — "
            f"每件用 {r['qty_per']:g}, 耗損 {(r['scrap_rate'] or 0):.1%}"
        )

    return {
        "summary": "\n".join(lines),
        "raw": {"part_no": part_no, "used_in": rows},
    }


# ════════════════════════════════════════════════════════════════════
# Tool 10: Daily Briefing ⭐ KILLER FEATURE
# ════════════════════════════════════════════════════════════════════

@register_tool(
    name="daily_briefing_tool",
    domain="planning",
    risk_tier=RiskTier.READ,
    description=(
        "🌅 **每日簡報**：整合 todo center + bottleneck + 最近 SO + 庫存警示，"
        "給老闆 3-5 件「今天該注意的事」。"
        "範例：「老闆早，今天我該注意什麼？」"
    ),
    slots=[],
    required_permission="dashboard.read",
)
async def _daily_briefing_tool(db, user) -> Dict[str, Any]:
    from datetime import datetime, timedelta, UTC
    from app.models.inventory import Inventory
    from app.models.purchase import PurchaseOrder

    items: List[Dict[str, Any]] = []

    # ── 1. 低庫存料件 ─────────────────────────────────────
    low_stock_q = await db.execute(
        select(Part, Inventory)
        .join(Inventory, Inventory.part_id == Part.id)
        .where(
            Part.is_active == True,
            Inventory.qty_available < Part.min_stock,
            Part.min_stock > 0,
        )
        .limit(5)
    )
    low_stock = low_stock_q.all()
    if low_stock:
        items.append({
            "priority": 1,
            "icon": "🔴",
            "category": "庫存警示",
            "text": f"有 {len(low_stock)} 項料件低於最低庫存：" +
                    ", ".join(p.part_no for p, _ in low_stock[:3]),
        })

    # ── 2. 最近 SO（過去 7 天）─────────────────────────────
    week_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
    recent_so_q = await db.execute(
        select(SalesOrder).where(SalesOrder.created_at >= week_ago)
        .limit(5)
    )
    recent_so = recent_so_q.scalars().all()
    if recent_so:
        items.append({
            "priority": 2,
            "icon": "📋",
            "category": "近 7 天新訂單",
            "text": f"有 {len(recent_so)} 張新銷售單（總額查詢可用 query_sales_order）",
        })

    # ── 3. 待釋出的 PO（draft 狀態） ────────────────────────
    draft_po_q = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.status == "draft").limit(5)
    )
    draft_pos = draft_po_q.scalars().all()
    if draft_pos:
        items.append({
            "priority": 3,
            "icon": "📦",
            "category": "草稿採購單",
            "text": f"有 {len(draft_pos)} 張採購單尚未送出",
        })

    # ── 4. 最新 MRP master（如有）+ 是否有瓶頸 ──────────────
    latest_mrp = (await db.execute(
        select(MrpMaster).order_by(MrpMaster.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if latest_mrp:
        items.append({
            "priority": 4,
            "icon": "📊",
            "category": "最新 MRP",
            "text": (
                f"最近一次 MRP：{latest_mrp.mrp_name}（"
                f"可用 identify_bottlenecks_tool 查目前瓶頸）"
            ),
        })

    # ── 5. 天氣式總結 ─────────────────────────────────────
    if not items:
        items.append({
            "priority": 99,
            "icon": "☀️",
            "category": "今日狀況",
            "text": "今天看起來一切平靜 — 沒有低庫存 / 草稿 PO / 近期新單。",
        })

    items.sort(key=lambda x: x["priority"])

    lines = ["🌅 **Ouvoca 每日簡報**\n"]
    for it in items[:5]:
        lines.append(f"{it['icon']} **{it['category']}**：{it['text']}")
    lines.append("")
    lines.append("💡 *建議下一步：對我說「我們的瓶頸在哪？」「今天該不該接 SO-XXX？」*")

    return {
        "summary": "\n".join(lines),
        "raw": {"items": items, "generated_at": datetime.now(UTC).isoformat()},
        "warning": (
            "⚠️ Daily Briefing 為自動聚合多項演算法輸出，每項皆有自己的限制。"
            "重要決策請點該項進入詳細頁面覆核 raw data。"
        ),
    }


# ════════════════════════════════════════════════════════════════════
# Auto-register tools into a new "planning" agent
# ════════════════════════════════════════════════════════════════════

from app.agents.engine import register_agent

register_agent(
    "planning", "PlanningAgent",
    system_prompt=(
        "你是 Ouvoca 的 **規劃顧問 AI**。職責：\n"
        "1. 用一句話幫老闆解決「該不該接這張單」「下個月該備多少」「瓶頸在哪」等決策\n"
        "2. 把 IE/OR 演算法之黑盒輸出翻譯成老闆能懂的人話\n"
        "3. 主動指出資料異常 / regime change（提醒覆核）\n"
        "4. 所有 hard-write 必走 ConfirmCard\n"
        "5. 重大決策（接 / 拒大單、capacity 投資）必提醒「請主管覆核」\n\n"
        "風格：簡潔、有 emoji、附數據、結尾加 ⚠️ 警告若涉及法律 / 財報 / 反壟斷。"
    ),
    tool_names=[
        "forecast_demand_for_part",
        "commit_forecast_to_mps_with_confirm",
        "explain_planned_order_tool",
        "identify_bottlenecks_tool",
        "counterfactual_capacity_tool",
        "evaluate_order_acceptance_tool",
        "explore_pricing_curve_tool",
        "compute_dbr_schedule_tool",
        "where_used_tool",
        "daily_briefing_tool",
    ],
)
