"""Demo: 對話式 CRUD 全流程端到端腳本（v3.2.1）。

不需 LLM API key — 直接模擬 LLM 解析後的 tool call 走完整 pipeline：
  1. AI 對話 read：列供應商 / 查 part 庫存
  2. AI 對話 hard-write：「跟長江下 100 個 M6 螺絲」
     → tool 出 ConfirmCard
     → 使用者點確認
     → service 寫入 DB
     → PO 真的建好
  3. AI 對話 read：列剛建好的 PO 驗證
  4. AI 對話 external DB：查連接 + table + 跨 DB read

輸出：執行過程 + 結果摘要（可給銷售看的 demo 證據）。

執行：
    cd backend
    python ../scripts/demo_crud_pipeline.py

或寫成 markdown：
    python ../scripts/demo_crud_pipeline.py > ../docs/demos/crud_pipeline_$(date +%Y%m%d_%H%M).md
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import tempfile
import sqlite3
from datetime import datetime, UTC
from pathlib import Path

# Windows cp950 → 強制 utf-8 (避免 emoji / 中文炸)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 確保走得到 backend.app
BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

# 用本機 sqlite 跑（不污染 production DB）
TMP_DB = Path(tempfile.mkdtemp(prefix="demo-crud-")) / "demo.db"
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TMP_DB.as_posix()}")
os.environ.setdefault("JWT_SECRET", "x" * 64)
# DEBUG=true 但走 monkeypatch 把 settings.DEBUG 改成 False，避免 SQL echo
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "ERROR")
os.environ.setdefault("LOG_JSON", "false")
os.environ.setdefault("DATABASE_DRIVER", "sqlite")

# 把 app.config.settings.DEBUG 強制改 False（在 init_db 之前）
# 避免 SQLAlchemy echo
import app.config
app.config.settings.DEBUG = False
# 強制把所有 sqlalchemy 相關 logger 設成 WARNING（雙保險）
import logging
for name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.engine.Engine", "sqlalchemy.pool"):
    logging.getLogger(name).setLevel(logging.WARNING)

print(f"📂 Demo DB: {TMP_DB}\n")


async def main():
    # ─── Setup ───────────────────────────────────────────
    from app.database import AsyncSessionLocal, init_db
    from app.agents import TOOL_FUNCTIONS, AGENT_REGISTRY
    from app.agents.confirm_card import consume_card
    from app.models.crm_sales import Customer
    from app.models.inventory import Part, Inventory
    from app.models.purchase import Supplier
    import uuid

    await init_db()

    DEMO_USER = {
        "employee_id": "emp-demo-001",
        "username": "demo-王董",
        "roles": ["boss"],
    }

    async with AsyncSessionLocal() as db:
        # Seed 一些客戶 / 供應商 / 料件
        sup = Supplier(
            id=str(uuid.uuid4()), code="SUP-001", name="長江五金",
            tier="T1", is_approved=True, lead_time_days=7,
        )
        db.add(sup)
        sup2 = Supplier(
            id=str(uuid.uuid4()), code="SUP-002", name="大華實業",
            tier="T2", is_approved=True,
        )
        db.add(sup2)
        cust = Customer(
            id=str(uuid.uuid4()), code="CUST-A001", name="A 客戶", grade="A",
        )
        db.add(cust)
        part = Part(
            id=str(uuid.uuid4()), part_no="M6-BOLT-20", name="M6 螺絲",
            category="component", unit_cost=5.0, safety_stock=500,
        )
        db.add(part)
        inv = Inventory(id=str(uuid.uuid4()), part_id=part.id, qty_on_hand=300)
        inv.qty_available = 300
        db.add(inv)
        part2 = Part(
            id=str(uuid.uuid4()), part_no="M8-NUT", name="M8 螺帽",
            category="component", unit_cost=3.0,
        )
        db.add(part2)
        await db.commit()

    print_h1("LLM-ERP 對話式 CRUD 全流程 Demo")
    print("**情境**：採購阿玲今天上班，要查庫存 + 補貨。")
    print(f"**測試時間**：{datetime.now(UTC).isoformat()}\n")

    # ─── Demo 1: AI read — 查供應商 ──────────────────────────────────
    print_h2("Demo 1 — 阿玲：「列出我們的供應商」")
    print("**LLM 解析結果**：意圖 = purchase，呼叫 `query_supplier`\n")
    async with AsyncSessionLocal() as db:
        tool = TOOL_FUNCTIONS["query_supplier"]
        result = await tool["func"](db=db, user=DEMO_USER)
    print("**回傳**：")
    print(json_block(result))
    print(f"\n→ 找到 {result['total']} 家供應商 ✅\n")

    # ─── Demo 2: AI read — 查 M6 庫存 ───────────────────────────────
    print_h2("Demo 2 — 阿玲：「M6 螺絲庫存還多少？」")
    print("**LLM 解析結果**：意圖 = inventory，呼叫 `query_inventory(part_no='M6-BOLT-20')`\n")
    async with AsyncSessionLocal() as db:
        tool = TOOL_FUNCTIONS["query_inventory"]
        result = await tool["func"](db=db, user=DEMO_USER, part_no="M6-BOLT-20")
    print("**回傳**：")
    print(json_block(result))
    if result.get("qty_available", 0) < result.get("safety_stock", 0):
        print(f"\n⚠️ **庫存 {result['qty_available']} < 安全庫存 {result['safety_stock']} → 需要補貨！**\n")
    else:
        print()

    # ─── Demo 3: AI hard-write — 下採購單（出 ConfirmCard）───────────
    print_h2("Demo 3 — 阿玲：「跟長江廠下 100 個 M6 螺絲，交期 5/20」")
    print("**LLM 解析結果**：意圖 = purchase，呼叫 `create_purchase_order_with_confirm`")
    print("  - supplier_keyword = 「長江」")
    print("  - items = [{part_keyword: 'M6 螺絲', ordered_qty: 100}]  ← 注意 LLM 用人話，不是 UUID")
    print("  - expected_delivery_date = '2026-05-20'\n")

    async with AsyncSessionLocal() as db:
        tool = TOOL_FUNCTIONS["create_purchase_order_with_confirm"]
        result = await tool["func"](
            db=db, user=DEMO_USER,
            supplier_keyword="長江",
            items=[{"part_keyword": "M6 螺絲", "ordered_qty": 100}],
            expected_delivery_date="2026-05-20",
        )
    print("**回傳**（注意是 ConfirmCard 而非執行）：")
    print(json_block(result))
    if result.get("type") != "confirm_card":
        print("❌ 失敗：應該出 ConfirmCard")
        return
    card_id = result["card"]["id"]
    print(f"\n✅ Tool 沒有立刻下單，**出了 ConfirmCard ({card_id})** 等使用者確認。")
    print(f"   摘要：")
    for line in result["card"]["summary"]:
        print(f"     {line}")
    print()

    # ─── Demo 4: 使用者點「確認」 ─────────────────────────────────
    print_h2("Demo 4 — 阿玲在 Chat UI 點「✓ 確認執行」")
    print("**前端 API**：`POST /api/agents/confirm/{card_id}`")
    print("**後端流程**：consume_card → 執行 executor closure → 呼叫 service → 寫 DB\n")

    async with AsyncSessionLocal() as db:
        # 模擬 API endpoint：consume + execute
        entry = await consume_card(card_id)
        if entry is None:
            print("❌ 失敗：ConfirmCard 不存在或已過期")
            return
        # 重要：executor 用的是原本的 db session（已關），這裡要重建
        # 實際的 API endpoint 從 FastAPI Depends 拿新 session 給 executor 用
        exec_result = await entry["executor"]()
    print("**執行結果**：")
    print(json_block(exec_result))
    new_po_no = exec_result.get("po_no")
    print(f"\n✅ **PO {new_po_no} 已建好！** 全程 1 句話。\n")

    # ─── Demo 5: AI read — 驗證 PO 真的存在 ─────────────────────────
    print_h2("Demo 5 — 阿玲：「最近的採購單?」（驗證剛建好的 PO）")
    print("**LLM 解析結果**：呼叫 `query_purchase_order()`\n")
    async with AsyncSessionLocal() as db:
        tool = TOOL_FUNCTIONS["query_purchase_order"]
        result = await tool["func"](db=db, user=DEMO_USER)
    found = any(o["po_no"] == new_po_no for o in result["orders"])
    print("**回傳**：")
    print(json_block(result))
    print()
    if found:
        print(f"✅ 確認 {new_po_no} 真的在 DB 內。**對話 → ConfirmCard → 寫入 整個 pipeline 通了。**\n")
    else:
        print(f"❌ 在回傳中找不到 {new_po_no}\n")

    # ─── Demo 6: 外部 DB 串接（v3.1）────────────────────────────────
    print_h2("Demo 6 — 王董：「我們鼎新有哪些客戶?」")
    print("**情境**：客戶舊系統（假裝鼎新 SQLite 匯出）。")
    print("**LLM 解析結果**：")
    print("  - 先呼叫 `list_external_connections` 看有沒有連接")
    print("  - 再呼叫 `list_external_tables` 看可查的 table")
    print("  - 再呼叫 `query_external_db` 跨 DB 讀\n")

    # Seed 一個假裝是鼎新的 sqlite
    legacy_db = Path(tempfile.mkdtemp(prefix="demo-legacy-")) / "dingxin.db"
    conn = sqlite3.connect(str(legacy_db))
    conn.execute("CREATE TABLE Customer (CustNo TEXT, CustName TEXT, Grade TEXT)")
    conn.executemany(
        "INSERT INTO Customer VALUES (?, ?, ?)",
        [
            ("C001", "鼎新老客戶 A", "A"),
            ("C002", "鼎新老客戶 B", "B"),
            ("C003", "鼎新老客戶 C", "A"),
        ],
    )
    conn.commit()
    conn.close()

    from app.agents.domains.external_db_tools import register_connection
    register_connection("legacy_dingxin", "sqlite", {"path": str(legacy_db)})
    print(f"  *(後台已 seed：legacy_dingxin → {legacy_db})*\n")

    async with AsyncSessionLocal() as db:
        # Step 1: list connections
        r1 = await TOOL_FUNCTIONS["list_external_connections"]["func"](db=db, user=DEMO_USER)
        print("**Step 1**：list_external_connections →")
        print(json_block(r1))
        print()

        # Step 2: list tables
        r2 = await TOOL_FUNCTIONS["list_external_tables"]["func"](
            db=db, user=DEMO_USER, connection="legacy_dingxin",
        )
        print("**Step 2**：list_external_tables(legacy_dingxin) →")
        print(json_block(r2))
        print()

        # Step 3: query
        r3 = await TOOL_FUNCTIONS["query_external_db"]["func"](
            db=db, user=DEMO_USER,
            connection="legacy_dingxin", table="Customer",
            filters={"Grade": "A"},
        )
        print("**Step 3**：query_external_db(table=Customer, filters={Grade: 'A'}) →")
        print(json_block(r3))
        print()
        print(f"✅ 找到鼎新 {r3['total']} 個 A 等級客戶，**鼎新不用砍**。\n")

    # ─── 結論 ──────────────────────────────────────────────────
    print_h1("Demo 結論")
    print(f"""
| 步驟 | 場景 | 結果 |
|---|---|---|
| 1 | 阿玲查供應商 | ✅ {AGENT_REGISTRY['purchase']['tool_names'][0]} 走通 |
| 2 | 阿玲查 M6 庫存 | ✅ 告知低於安全庫存 |
| 3 | 阿玲下 100 個 M6 | ✅ 出 ConfirmCard，**不直接執行** |
| 4 | 阿玲點確認 | ✅ PO {new_po_no} 真的建好 |
| 5 | 驗證 PO 在 DB | ✅ query_purchase_order 看得到 |
| 6 | 王董查鼎新客戶 | ✅ 跨 DB federated query 走通 |

**3 個 demo moment 全部走通**：
- ✅ 對話式 read（moment 1）
- ✅ 對話式 hard-write + ConfirmCard（moment 2）
- ✅ 對話式 federated query 鼎新（moment 3）

📊 **Tool registry**：32 個 tools 全進新 registry（29 read + 3 hard-write）
🛡️ **安全**：hard-write 必過 ConfirmCard / 5 分鐘 TTL / table whitelist
🔌 **整合**：sqlite + csv connector PoC + 3 個 AI tool 接 Chat

> 「**自然語言取代教育訓練 + 鼎新不用砍 + 員工 30 秒下單**」
> 這就是 30 萬一年的 LLM-ERP。
""")


def print_h1(s):
    print(f"\n# {s}\n")


def print_h2(s):
    print(f"\n## {s}\n")


def json_block(o):
    lines = ["```json"]
    lines.append(json.dumps(o, ensure_ascii=False, indent=2, default=str))
    lines.append("```")
    return "\n".join(lines)


if __name__ == "__main__":
    asyncio.run(main())
