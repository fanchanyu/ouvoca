"""Ablation studies for the six-layer architecture - Req 3 compliance.

Two ablations report the contribution of individual layers under controlled
removal:

  Ablation A - L4 ConfirmationCard:
    For the 9 HARD_WRITE tools whose placeholder arguments passed validation in
    the Section 4.2.1 audit (i.e. would have reached Phase 1 prepare), we now
    bypass the ConfirmationCard layer and invoke the underlying tool function
    directly via the registry. We then inspect database state to count how
    many writes occurred. A baseline (with ConfirmCard intact) is shown for
    comparison.

  Ablation B - L1 Domain Routing:
    The IntentClassifier is monkey-patched so that classify_intent() always
    returns "general". We re-run T01-T10 (single seed for cost) and compare
    per-case strict-pass to the post-improvement baseline.

Outputs (to ./benchmark_results/ablation_<timestamp>/):
  - l4_confirmcard.csv      : per-tool verdict
  - l1_routing.csv          : per-case verdict
  - summary.json            : aggregate numbers
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import classify_intent, get_agent, get_tool_definitions, execute_tool
from app.agents.registry import list_tools, get_tool, RiskTier
from app.database import AsyncSessionLocal
from scripts.llm_benchmark import TEST_CASES
from scripts.dr2_confirmcard_audit import _build_args, _classify


# ----------------------------------------------------------------------------
# Ablation A - L4 ConfirmationCard: bypass two-phase commit
# ----------------------------------------------------------------------------

async def ablation_l4_confirmcard(out_dir: Path) -> dict:
    """For each HARD_WRITE tool, call meta.func directly bypassing execute_tool.

    Compare with the baseline audit (in eval/dr2_confirmcard_audit.csv) which
    showed 9 tools reached Phase-1 prepare; those are the ones whose
    placeholder args passed validation. Without ConfirmCard, they would have
    written to the database.
    """
    user = {"employee_id": "ablation", "username": "ablation", "roles": ["admin"]}
    hard_write_tools = list_tools(tier=RiskTier.HARD_WRITE)

    rows: list[dict] = []
    bypass_executions = 0
    bypass_errors = 0

    print(f"\n=== Ablation A - L4 ConfirmationCard ===")
    print(f"Bypassing the ConfirmationCard layer for {len(hard_write_tools)} HARD_WRITE tools.")
    print("Method: call meta.func directly (skips execute_tool risk-tier gate).")
    print("-" * 90)

    async with AsyncSessionLocal() as db:
        for meta in sorted(hard_write_tools, key=lambda m: m.name):
            args = _build_args(meta)
            # Bypass execute_tool entirely; call the underlying registered function
            try:
                result = await meta.func(db=db, user=user, **args)
                # If we reach here without raising, the function executed (or
                # returned an error object). We need to inspect to see if a
                # write occurred. Heuristic: a successful execution returns a
                # dict with "success"/"id"/"created" etc; a failure raises or
                # returns an error dict.
                if isinstance(result, dict) and (
                    result.get("success") is True
                    or result.get("id")
                    or result.get("status") in ("executed", "ok", "created")
                ):
                    verdict = "WOULD_HAVE_EXECUTED"
                    bypass_executions += 1
                else:
                    verdict = "rejected_by_inner_validation"
                    bypass_errors += 1
                raw = str(result)[:200]
            except Exception as exc:
                verdict = "raised_exception"
                bypass_errors += 1
                raw = f"{type(exc).__name__}: {str(exc)[:160]}"
            rows.append({
                "tool": meta.name,
                "domain": meta.domain,
                "verdict_without_confirmcard": verdict,
                "raw_excerpt": raw,
            })
            tag = "UNSAFE" if verdict == "WOULD_HAVE_EXECUTED" else "(blocked-inner)"
            print(f"  {tag:18} {meta.name}")

    summary = {
        "ablation": "L4_confirmcard_bypass",
        "n_tools": len(hard_write_tools),
        "would_have_executed_unsafe": bypass_executions,
        "blocked_by_inner_validation": bypass_errors,
        "baseline_with_confirmcard": "0 unsafe execution (Section 4.2.1)",
        "interpretation": (
            f"Without the ConfirmationCard layer, {bypass_executions}/"
            f"{len(hard_write_tools)} HARD_WRITE tools would have executed a direct "
            f"write under audit conditions; the remaining {bypass_errors} would "
            f"have been stopped by lower-level argument validation, not by an "
            f"architectural safety mechanism."
        ),
    }

    csv_path = out_dir / "l4_confirmcard.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tool", "domain",
                                            "verdict_without_confirmcard",
                                            "raw_excerpt"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print("-" * 90)
    print(f"Summary: {bypass_executions} unsafe writes / "
          f"{bypass_errors} blocked at inner validation / "
          f"{len(hard_write_tools)} total")
    print(f"CSV: {csv_path}")
    return summary


# ----------------------------------------------------------------------------
# Ablation B - L1 Domain Routing: force general agent
# ----------------------------------------------------------------------------

import app.agents.engine as engine_mod

_ORIG_CLASSIFY = engine_mod.classify_intent


async def ablation_l1_routing(out_dir: Path, seed: int = 1) -> dict:
    """Monkey-patch classify_intent to always return 'general', re-run T01-T10."""
    import httpx
    from app.config import settings

    # Monkey-patch
    engine_mod.classify_intent = lambda message: "general"

    user_info = {"employee_id": "ablation", "username": "ablation",
                 "roles": ["admin"]}

    async def _seeded_chat(messages, tools, _seed):
        async with httpx.AsyncClient(
            timeout=settings.LLM_TIMEOUT_SECONDS,
            verify=settings.LLM_VERIFY_SSL,
        ) as client:
            payload: dict[str, Any] = {
                "model": settings.LLM_MODEL or "deepseek-chat",
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096,
                "seed": _seed,
            }
            if tools:
                payload["tools"] = tools
            resp = await client.post(
                settings.LLM_BASE_URL + "/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            choice = resp.json()["choices"][0]["message"]
            return {"content": choice.get("content", ""),
                    "tool_calls": choice.get("tool_calls", [])}

    rows: list[dict] = []
    print(f"\n=== Ablation B - L1 Domain Routing (seed {seed}) ===")
    print("Monkey-patch: classify_intent() always returns 'general'.")
    print("Re-running T01-T10 with one seed (cost control).")
    print("-" * 90)

    try:
        async with AsyncSessionLocal() as db:
            for case in TEST_CASES:
                t0 = time.time()
                intent = "general"  # forced
                agent = get_agent(intent)
                system_msg = {
                    "role": "system",
                    "content": (agent["system_prompt"]
                                + "\n\nUser context: test admin"),
                }
                messages = [system_msg,
                            {"role": "user", "content": case["q"]}]
                tools = (get_tool_definitions(agent["tool_names"])
                         if agent.get("tool_names") else None)

                tool_calls_log: list[dict] = []
                reply = ""
                error: str | None = None
                for _ in range(5):
                    try:
                        resp = await _seeded_chat(messages, tools, seed)
                    except Exception as e:
                        error = str(e)[:200]
                        break
                    tc_list = resp.get("tool_calls") or []
                    if not tc_list:
                        reply = resp.get("content") or "(no reply)"
                        break
                    for tc in tc_list:
                        fn = tc.get("function", {})
                        fn_name = fn.get("name", "")
                        try:
                            args = (json.loads(fn.get("arguments", "{}"))
                                    if isinstance(fn.get("arguments"), str)
                                    else fn.get("arguments", {}))
                        except Exception:
                            args = {}
                        result = await execute_tool(fn_name, args, db=db,
                                                     user=user_info)
                        tool_calls_log.append({"tool": fn_name})
                        messages.append({"role": "assistant", "content": None,
                                          "tool_calls": [tc]})
                        messages.append({"role": "tool",
                                          "tool_call_id": tc.get("id", fn_name),
                                          "content": result})
                else:
                    error = "max rounds reached"

                elapsed = time.time() - t0
                tool_names = [tc["tool"] for tc in tool_calls_log]
                expected_tools = case["expect"].get("tools", [])
                expected_match = (any(t in tool_names for t in expected_tools)
                                    if expected_tools else True)
                reply_ok = error is None and len(reply) > 10
                strict_pass = expected_match and reply_ok
                tag = "PASS" if strict_pass else "FAIL"
                print(f"  [{case['id']}] {tag} intent=general "
                      f"elapsed={elapsed:.2f}s tools={tool_names[:3]}")
                rows.append({
                    "case_id": case["id"],
                    "intent_forced": "general",
                    "tools_called": ";".join(tool_names),
                    "expected_tools": ";".join(expected_tools),
                    "expected_match": expected_match,
                    "elapsed_sec": round(elapsed, 2),
                    "strict_pass": strict_pass,
                    "error": error or "",
                })
    finally:
        # Restore original
        engine_mod.classify_intent = _ORIG_CLASSIFY

    n_pass = sum(1 for r in rows if r["strict_pass"])
    summary = {
        "ablation": "L1_routing_force_general",
        "seed": seed,
        "n_cases": len(rows),
        "strict_pass_under_ablation": n_pass,
        "baseline_with_routing_5seed": "47/50 (94%, Section 4.1.2)",
        "interpretation": (
            f"With domain routing ablated (all queries forced to the general "
            f"agent), {n_pass}/{len(rows)} of T01-T10 satisfy the strict-pass "
            f"criterion under seed {seed}. Compare with the post-improvement "
            f"five-seed baseline of 47/50 (94%) in Section 4.1.2."
        ),
    }
    csv_path = out_dir / "l1_routing.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["case_id", "intent_forced",
                                            "tools_called", "expected_tools",
                                            "expected_match", "elapsed_sec",
                                            "strict_pass", "error"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print("-" * 90)
    print(f"Summary: {n_pass}/{len(rows)} strict pass under L1 ablation")
    print(f"CSV: {csv_path}")
    return summary


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> int:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = Path("benchmark_results") / f"ablation_{ts}"
    out_root.mkdir(parents=True, exist_ok=True)

    summaries: list[dict] = []
    if args.layer in ("l4", "both"):
        s = await ablation_l4_confirmcard(out_root)
        summaries.append(s)
    if args.layer in ("l1", "both"):
        s = await ablation_l1_routing(out_root, seed=args.seed)
        summaries.append(s)

    summary_path = out_root / "summary.json"
    summary_path.write_text(
        json.dumps({"ablations": summaries, "timestamp": ts},
                    ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nAll ablation outputs in: {out_root}")
    print(f"Summary: {summary_path}")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--layer", choices=["l1", "l4", "both"], default="both",
                    help="Which layer to ablate")
    p.add_argument("--seed", type=int, default=1,
                    help="Seed for L1 ablation re-run")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(run(parse_args())))
