"""G3: capture the real reasoning trace for T04 (mechanism-level evidence).

Runs the T04 production-feasibility scenario through the full pipeline and
captures the complete message transcript: every assistant turn (content plus
tool calls), every tool result, and the final reply. The captured trace is the
*actual* multi-step reasoning the LLM performed, not a reconstruction.

T04: "如果客戶要訂 100 台變速齒輪組 A,我們現在可以做嗎?要先檢查什麼?"
(If a customer orders 100 units of Gear-Assembly A, can we produce them now?
What should we check first?)

Output: eval/exp_g3_t04_trace.json (full transcript) + a readable summary.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from app.config import settings
from app.database import AsyncSessionLocal
from app.agents import classify_intent, get_agent, get_tool_definitions, execute_tool

T04_QUERY = "如果客戶要訂 100 台變速齒輪組 A,我們現在可以做嗎?要先檢查什麼?"
SEED = 1


async def _chat(messages, tools, seed):
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS,
                                  verify=settings.LLM_VERIFY_SSL) as client:
        payload = {"model": settings.LLM_MODEL or "deepseek-chat",
                   "messages": messages, "temperature": 0.3,
                   "max_tokens": 4096, "seed": seed}
        if tools:
            payload["tools"] = tools
        resp = await client.post(
            settings.LLM_BASE_URL + "/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}",
                     "Content-Type": "application/json"},
            json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]


async def main() -> int:
    intent = classify_intent(T04_QUERY)
    agent = get_agent(intent)
    transcript = [{"role": "user", "content": T04_QUERY}]
    tools = get_tool_definitions(agent["tool_names"]) if agent.get("tool_names") else None
    messages = [
        {"role": "system", "content": agent["system_prompt"]
            + "\n\nUser context: test admin"},
        {"role": "user", "content": T04_QUERY},
    ]
    user_info = {"employee_id": "g3", "username": "g3", "roles": ["admin"]}
    steps = []
    async with AsyncSessionLocal() as db:
        for round_idx in range(5):
            msg = await _chat(messages, tools, SEED)
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                transcript.append({"role": "assistant_final", "content": content})
                steps.append({"step": round_idx + 1, "type": "final_reply",
                               "content": content})
                break
            for tc in tool_calls:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                try:
                    args = (json.loads(fn.get("arguments", "{}"))
                            if isinstance(fn.get("arguments"), str)
                            else fn.get("arguments", {}))
                except Exception:
                    args = {}
                result = await execute_tool(fn_name, args, db=db, user=user_info)
                # store a trimmed result for readability
                try:
                    parsed = json.loads(result)
                    result_summary = json.dumps(parsed, ensure_ascii=False)[:300]
                except Exception:
                    result_summary = str(result)[:300]
                steps.append({
                    "step": round_idx + 1,
                    "type": "tool_call",
                    "assistant_reasoning": content,
                    "tool": fn_name,
                    "args": args,
                    "tool_result_excerpt": result_summary,
                })
                messages.append({"role": "assistant", "content": content or None,
                                  "tool_calls": [tc]})
                messages.append({"role": "tool",
                                  "tool_call_id": tc.get("id", fn_name),
                                  "content": result})

    out_dir = Path(__file__).resolve().parents[3] / "ISF_Q2_投稿" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "exp_g3_t04_trace.json").write_text(
        json.dumps({"query": T04_QUERY, "intent": intent, "seed": SEED,
                    "steps": steps}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    print(f"\n=== T04 reasoning trace (intent={intent}, seed={SEED}) ===")
    print(f"Query: {T04_QUERY}\n")
    for s in steps:
        if s["type"] == "tool_call":
            print(f"[Step {s['step']}] TOOL {s['tool']}({s['args']})")
            if s["assistant_reasoning"]:
                print(f"   reasoning: {s['assistant_reasoning'][:120]}")
            print(f"   result: {s['tool_result_excerpt'][:120]}")
        else:
            print(f"[Step {s['step']}] FINAL REPLY:")
            print(f"   {s['content'][:300]}")
    print(f"\nFull transcript: {out_dir / 'exp_g3_t04_trace.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
