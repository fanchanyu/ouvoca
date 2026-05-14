"""LLM Benchmark — 多 provider 多情境評測。

使用方式：
    python -m scripts.llm_benchmark

需要先設定環境變數（每個 provider 各跑一次）：
    LLM_PROVIDER=deepseek LLM_API_KEY=sk-... python -m scripts.llm_benchmark

輸出：
    - 終端顯示即時結果
    - 寫入 ./benchmark_results/<provider>_<timestamp>.json
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.agents import classify_intent, get_agent, get_tool_definitions, execute_tool, chat_completion


# ============================================================
# 10 個典型 ERP 評測題
# ============================================================
TEST_CASES = [
    {
        "id": "T01", "category": "simple_query", "difficulty": "easy",
        "q": "請列出庫存低於安全庫存的零件",
        "expect": {"tools": ["list_below_safety"], "min_tools": 1},
    },
    {
        "id": "T02", "category": "specific_lookup", "difficulty": "easy",
        "q": "幫我查 M6-BOLT-20 還剩多少",
        "expect": {"tools": ["query_inventory"], "min_tools": 1},
    },
    {
        "id": "T03", "category": "fuzzy_query", "difficulty": "medium",
        "q": "我們倉庫現在缺什麼料?",
        "expect": {"tools": ["list_below_safety", "list_parts"], "min_tools": 1},
    },
    {
        "id": "T04", "category": "multi_step", "difficulty": "hard",
        "q": "如果客戶要訂 100 台變速齒輪組 A,我們現在可以做嗎?要先檢查什麼?",
        "expect": {"tools": ["list_products_tool", "get_bom", "query_inventory"], "min_tools": 2},
    },
    {
        "id": "T05", "category": "cross_domain", "difficulty": "hard",
        "q": "今天工廠營運狀況如何?簡單總結",
        "expect": {"tools": ["list_below_safety", "query_work_order"], "min_tools": 2},
    },
    {
        "id": "T06", "category": "business_scenario", "difficulty": "medium",
        "q": "A 客戶 PRD-GEAR-A 最近的單價?",
        "expect": {"tools": ["query_sales_order", "list_customers"], "min_tools": 1},
    },
    {
        "id": "T07", "category": "typo_tolerance", "difficulty": "medium",
        "q": "礦存還剩多少 M6 螺絲?",  # 「礦存」是錯字
        "expect": {"tools": ["query_inventory", "list_below_safety"], "min_tools": 1,
                   "note": "錯字容錯：應理解為「庫存」"},
    },
    {
        "id": "T08", "category": "open_dialog", "difficulty": "medium",
        "q": "給我一些改善庫存周轉的建議",
        "expect": {"min_tools": 0, "note": "純對話、不一定需要 tool"},
    },
    {
        "id": "T09", "category": "supplier_query", "difficulty": "easy",
        "q": "查一下我們的供應商有哪些",
        "expect": {"tools": ["query_supplier"], "min_tools": 1},
    },
    {
        "id": "T10", "category": "quality_query", "difficulty": "medium",
        "q": "最近有哪些不良品?品質狀況如何?",
        "expect": {"tools": ["list_non_conformances", "list_inspections"], "min_tools": 1},
    },
]


# ============================================================
# 評測核心：模擬 chat-v2 但取得 metadata
# ============================================================

class BenchmarkResult:
    def __init__(self):
        self.cases = []

    def add(self, case_id, **kwargs):
        self.cases.append({"id": case_id, **kwargs})

    def summary(self):
        n = len(self.cases)
        succ = sum(1 for c in self.cases if c.get("success"))
        avg_time = sum(c.get("elapsed_sec", 0) for c in self.cases) / max(n, 1)
        total_tools = sum(c.get("tool_count", 0) for c in self.cases)
        return {
            "total": n, "success": succ, "success_rate": succ / max(n, 1),
            "avg_time_sec": round(avg_time, 2),
            "total_tools_called": total_tools,
            "avg_tools_per_query": round(total_tools / max(n, 1), 1),
        }


async def run_single_case(case: dict, user_info: dict) -> dict:
    """模擬 chat-v2 對單一 case 跑完整 multi-agent loop。"""
    t0 = time.time()
    intent = classify_intent(case["q"])
    agent = get_agent(intent) or get_agent("general")

    if not agent:
        return {"intent": intent, "elapsed_sec": time.time() - t0,
                "success": False, "error": "no agent"}

    system_msg = {
        "role": "system",
        "content": agent["system_prompt"] + f"\n\n當前使用者: 測試 | 角色: ['admin']",
    }
    messages = [system_msg, {"role": "user", "content": case["q"]}]
    tools = get_tool_definitions(agent["tool_names"]) if agent.get("tool_names") else None

    tool_calls_log = []
    reply = ""
    error = None

    async with AsyncSessionLocal() as db:
        for round_idx in range(5):  # max 5 rounds
            try:
                resp = await chat_completion(messages, tools)
            except Exception as e:
                error = str(e)
                break

            tc_list = resp.get("tool_calls", []) or []
            if not tc_list:
                reply = resp.get("content", "") or "(no reply)"
                break

            for tc in tc_list:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments", "{}")) if isinstance(fn.get("arguments"), str) else fn.get("arguments", {})
                except Exception:
                    args = {}
                result = await execute_tool(fn_name, args, db=db, user=user_info)
                tool_calls_log.append({"tool": fn_name, "args": args})
                messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                messages.append({"role": "tool", "tool_call_id": tc.get("id", fn_name), "content": result})
        else:
            error = "max rounds reached"

    elapsed = time.time() - t0
    tool_names = [tc["tool"] for tc in tool_calls_log]

    # 自動評估
    expected_tools = case["expect"].get("tools", [])
    min_tools = case["expect"].get("min_tools", 0)
    expected_match = any(t in tool_names for t in expected_tools) if expected_tools else True
    tools_count_ok = len(tool_calls_log) >= min_tools

    success = error is None and (expected_match or tools_count_ok) and len(reply) > 10

    return {
        "intent": intent,
        "elapsed_sec": round(elapsed, 2),
        "tool_count": len(tool_calls_log),
        "tools_called": tool_names,
        "expected_tools": expected_tools,
        "expected_match": expected_match,
        "reply_chars": len(reply),
        "reply_preview": reply[:300],
        "success": success,
        "error": error,
    }


async def run_benchmark(provider_label: str) -> dict:
    from app.config import settings
    print(f"\n{'=' * 70}")
    print(f"  LLM Benchmark — {provider_label}")
    print(f"  Provider: {settings.LLM_PROVIDER} | Model: {settings.LLM_MODEL}")
    print(f"{'=' * 70}\n")

    result = BenchmarkResult()
    user_info = {"employee_id": "bench", "username": "bench", "roles": ["admin"]}

    for case in TEST_CASES:
        print(f"  [{case['id']}] [{case['difficulty']:6}] {case['q']}")
        r = await run_single_case(case, user_info)
        status = "✓" if r["success"] else ("✗" if r.get("error") else "△")
        print(f"     {status} {r['elapsed_sec']:.2f}s | tools={r['tool_count']} ({','.join(r['tools_called'][:3])}) | reply={r['reply_chars']} chars")
        if r.get("error"):
            print(f"     ERROR: {r['error']}")
        result.add(case["id"], **r, query=case["q"], category=case["category"], difficulty=case["difficulty"])

    summary = result.summary()
    print(f"\n  📊 Summary: {summary['success']}/{summary['total']} success ({summary['success_rate']*100:.0f}%) | "
          f"avg {summary['avg_time_sec']}s | tools/q={summary['avg_tools_per_query']}")

    # 儲存結果
    out_dir = Path("benchmark_results")
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"{settings.LLM_PROVIDER}_{ts}.json"
    payload = {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "timestamp": datetime.now().isoformat(),
        "label": provider_label,
        "summary": summary,
        "cases": result.cases,
    }
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  💾 Saved to: {out_file}\n")
    return payload


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "default"
    asyncio.run(run_benchmark(label))
