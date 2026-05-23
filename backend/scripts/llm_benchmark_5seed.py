"""5-seed benchmark runner with bootstrap 95% CI + permutation test.

Extends scripts.llm_benchmark to run N seeds (default 5) per provider with
controlled `seed` parameter passed to the DeepSeek API, then aggregates per-case
statistics with bootstrap confidence intervals.

Usage:
    python -m scripts.llm_benchmark_5seed                  # 5 seeds, deepseek
    python -m scripts.llm_benchmark_5seed --seeds 5        # explicit
    python -m scripts.llm_benchmark_5seed --seeds 1,2,3    # explicit seed list

Output (in ./benchmark_results/):
    <provider>_5seed_<timestamp>/
        seed_<n>.json            -- per-seed raw results
        aggregate.json           -- per-case stats + bootstrap CI
        aggregate.csv            -- same as CSV for paper-Section-4 ingestion
        permutation_test.json    -- pre-vs-post-improvement test (if baseline present)

Pre-registration: see CII 投稿/eval/PRE_REGISTRATION.md.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from app.config import settings
from app.database import AsyncSessionLocal
from app.agents import classify_intent, get_agent, get_tool_definitions, execute_tool
from scripts.llm_benchmark import TEST_CASES


# ----------------------------------------------------------------------------
# LLM call with seed parameter (DeepSeek + OpenAI accept `seed`)
# ----------------------------------------------------------------------------

async def chat_completion_with_seed(messages: list[dict], tools: list[dict] | None,
                                     seed: int) -> dict:
    """Drop-in replacement for engine.chat_completion that also passes `seed`."""
    provider = settings.LLM_PROVIDER
    if provider == "deepseek":
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS,
                                      verify=settings.LLM_VERIFY_SSL) as client:
            payload: dict[str, Any] = {
                "model": settings.LLM_MODEL or "deepseek-chat",
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096,
                "seed": seed,
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
    if provider == "openai":
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS,
                                      verify=settings.LLM_VERIFY_SSL) as client:
            payload = {
                "model": settings.LLM_MODEL or "gpt-4o",
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096,
                "seed": seed,
            }
            if tools:
                payload["tools"] = tools
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.LLM_API_KEY}",
                         "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            choice = resp.json()["choices"][0]["message"]
            return {"content": choice.get("content", ""),
                    "tool_calls": choice.get("tool_calls", [])}
    raise NotImplementedError(f"Seed not supported for provider={provider}")


# ----------------------------------------------------------------------------
# Single-case runner (mirrors scripts.llm_benchmark.run_single_case but with seed)
# ----------------------------------------------------------------------------

async def run_single_case(case: dict, user_info: dict, seed: int) -> dict:
    t0 = time.time()
    intent = classify_intent(case["q"])
    agent = get_agent(intent) or get_agent("general")
    if not agent:
        return {"intent": intent, "elapsed_sec": time.time() - t0,
                "success": False, "error": "no agent", "seed": seed}

    system_msg = {
        "role": "system",
        "content": agent["system_prompt"] + "\n\n當前使用者: 測試 | 角色: ['admin']",
    }
    messages = [system_msg, {"role": "user", "content": case["q"]}]
    tools = get_tool_definitions(agent["tool_names"]) if agent.get("tool_names") else None

    tool_calls_log: list[dict] = []
    reply = ""
    error: str | None = None

    async with AsyncSessionLocal() as db:
        for _ in range(5):  # max 5 rounds
            try:
                resp = await chat_completion_with_seed(messages, tools, seed)
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
                    args = (json.loads(fn.get("arguments", "{}"))
                            if isinstance(fn.get("arguments"), str)
                            else fn.get("arguments", {}))
                except Exception:
                    args = {}
                result = await execute_tool(fn_name, args, db=db, user=user_info)
                tool_calls_log.append({"tool": fn_name, "args": args})
                messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                messages.append({"role": "tool",
                                 "tool_call_id": tc.get("id", fn_name),
                                 "content": result})
        else:
            error = "max rounds reached"

    elapsed = time.time() - t0
    tool_names = [tc["tool"] for tc in tool_calls_log]
    expected_tools = case["expect"].get("tools", [])
    min_tools = case["expect"].get("min_tools", 0)

    expected_match = (any(t in tool_names for t in expected_tools)
                       if expected_tools else True)
    tools_count_ok = len(tool_calls_log) >= min_tools
    reply_quality_ok = error is None and len(reply) > 10

    # Strict pass per pre-registration: intent + tool-set + reply quality
    strict_pass = (intent == case["expect"].get("expected_intent", intent)
                    and expected_match and reply_quality_ok)
    # Loose pass: routing + reply + >=1 tool (or open-ended)
    loose_pass = (intent == case["expect"].get("expected_intent", intent)
                   and reply_quality_ok and (tools_count_ok or not expected_tools))

    return {
        "case_id": case["id"],
        "seed": seed,
        "intent": intent,
        "elapsed_sec": round(elapsed, 3),
        "tool_count": len(tool_calls_log),
        "tools_called": tool_names,
        "expected_tools": expected_tools,
        "expected_match": expected_match,
        "reply_chars": len(reply),
        "reply_preview": reply[:300],
        "strict_pass": strict_pass,
        "loose_pass": loose_pass,
        "error": error,
    }


# ----------------------------------------------------------------------------
# Bootstrap CI
# ----------------------------------------------------------------------------

def bootstrap_ci(values: list[float], n_resamples: int = 10_000,
                  alpha: float = 0.05, rng_seed: int = 42) -> tuple[float, float]:
    """Percentile bootstrap 95% CI on the mean of values."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(rng_seed)
    n = len(values)
    means = []
    for _ in range(n_resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(n_resamples * (alpha / 2))]
    hi = means[int(n_resamples * (1 - alpha / 2))]
    return (lo, hi)


def proportion_bootstrap_ci(successes: int, n: int, n_resamples: int = 10_000,
                              alpha: float = 0.05,
                              rng_seed: int = 42) -> tuple[float, float]:
    """Bootstrap CI on a proportion. successes ≤ n."""
    if n == 0:
        return (0.0, 0.0)
    data = [1] * successes + [0] * (n - successes)
    return bootstrap_ci(data, n_resamples, alpha, rng_seed)


def permutation_test(group_a: list[float], group_b: list[float],
                       n_resamples: int = 10_000,
                       rng_seed: int = 42) -> dict:
    """Two-sample permutation test on the mean difference. Two-sided p-value."""
    if not group_a or not group_b:
        return {"observed_diff": 0.0, "p_value": 1.0, "n_a": len(group_a),
                "n_b": len(group_b)}
    rng = random.Random(rng_seed)
    obs_diff = (sum(group_a) / len(group_a)) - (sum(group_b) / len(group_b))
    combined = group_a + group_b
    n_a = len(group_a)
    extreme = 0
    for _ in range(n_resamples):
        rng.shuffle(combined)
        a = combined[:n_a]
        b = combined[n_a:]
        diff = (sum(a) / len(a)) - (sum(b) / len(b))
        if abs(diff) >= abs(obs_diff):
            extreme += 1
    return {
        "observed_diff": round(obs_diff, 4),
        "p_value": round((extreme + 1) / (n_resamples + 1), 4),
        "n_a": n_a,
        "n_b": len(group_b),
        "n_resamples": n_resamples,
    }


# ----------------------------------------------------------------------------
# Aggregator
# ----------------------------------------------------------------------------

EXPECTED_INTENT = {
    "T01": "inventory", "T02": "inventory", "T03": "inventory",
    "T04": "production", "T05": "general", "T06": "crm",
    "T07": "inventory", "T08": "inventory", "T09": "purchase", "T10": "quality",
}


def aggregate(per_seed_results: list[list[dict]]) -> dict:
    """Aggregate per-case across seeds. Each inner list is one seed's 10 cases."""
    by_case: dict[str, list[dict]] = {c["id"]: [] for c in TEST_CASES}
    for seed_results in per_seed_results:
        for r in seed_results:
            by_case[r["case_id"]].append(r)

    n_seeds = len(per_seed_results)
    cases: list[dict] = []
    for case_meta in TEST_CASES:
        cid = case_meta["id"]
        runs = by_case[cid]
        strict = [int(r["strict_pass"]) for r in runs]
        loose = [int(r["loose_pass"]) for r in runs]
        latencies = [r["elapsed_sec"] for r in runs]
        tool_counts = [r["tool_count"] for r in runs]
        intents = [r["intent"] for r in runs]
        strict_ci = proportion_bootstrap_ci(sum(strict), n_seeds)
        loose_ci = proportion_bootstrap_ci(sum(loose), n_seeds)
        lat_ci = bootstrap_ci(latencies)
        cases.append({
            "case_id": cid,
            "category": case_meta["category"],
            "difficulty": case_meta["difficulty"],
            "expected_intent": EXPECTED_INTENT.get(cid, "?"),
            "intent_correct_all_seeds": all(i == EXPECTED_INTENT.get(cid, i)
                                              for i in intents),
            "strict_pass_count": sum(strict),
            "strict_pass_rate": sum(strict) / n_seeds,
            "strict_pass_rate_ci_lo": strict_ci[0],
            "strict_pass_rate_ci_hi": strict_ci[1],
            "loose_pass_count": sum(loose),
            "loose_pass_rate": sum(loose) / n_seeds,
            "loose_pass_rate_ci_lo": loose_ci[0],
            "loose_pass_rate_ci_hi": loose_ci[1],
            "mean_latency_sec": statistics.mean(latencies) if latencies else 0.0,
            "stdev_latency_sec": (statistics.stdev(latencies)
                                   if len(latencies) > 1 else 0.0),
            "latency_ci_lo": lat_ci[0],
            "latency_ci_hi": lat_ci[1],
            "mean_tool_count": statistics.mean(tool_counts) if tool_counts else 0.0,
        })

    overall = {
        "n_seeds": n_seeds,
        "n_cases": len(cases),
        "strict_pass_overall": sum(c["strict_pass_count"] for c in cases)
                                 / max(1, n_seeds * len(cases)),
        "loose_pass_overall": sum(c["loose_pass_count"] for c in cases)
                                / max(1, n_seeds * len(cases)),
        "mean_latency_overall_sec": statistics.mean(
            [c["mean_latency_sec"] for c in cases]) if cases else 0.0,
    }
    return {"cases": cases, "overall": overall}


def write_csv(agg: dict, path: Path) -> None:
    headers = [
        "case_id", "category", "difficulty", "expected_intent",
        "intent_correct_all_seeds",
        "strict_pass_count", "strict_pass_rate",
        "strict_pass_rate_ci_lo", "strict_pass_rate_ci_hi",
        "loose_pass_count", "loose_pass_rate",
        "loose_pass_rate_ci_lo", "loose_pass_rate_ci_hi",
        "mean_latency_sec", "stdev_latency_sec",
        "latency_ci_lo", "latency_ci_hi",
        "mean_tool_count",
    ]
    lines = [",".join(headers)]
    for c in agg["cases"]:
        row = [str(c.get(h, "")) for h in headers]
        lines.append(",".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

async def run_seeds(seeds: list[int], label: str) -> dict:
    user_info = {"employee_id": "bench", "username": "bench", "roles": ["admin"]}
    per_seed: list[list[dict]] = []

    out_root = Path("benchmark_results") / f"{settings.LLM_PROVIDER}_5seed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 70}")
    print(f"  5-Seed LLM Benchmark — {label}")
    print(f"  Provider: {settings.LLM_PROVIDER} | Model: {settings.LLM_MODEL}")
    print(f"  Seeds: {seeds}")
    print(f"  Output: {out_root}")
    print(f"{'=' * 70}\n")

    for seed in seeds:
        print(f"\n--- Seed {seed} ---")
        case_results: list[dict] = []
        for case in TEST_CASES:
            print(f"  [{case['id']}] {case['q']}")
            r = await run_single_case(case, user_info, seed)
            tag = "PASS" if r["strict_pass"] else ("LOOSE" if r["loose_pass"] else "FAIL")
            print(f"     {tag} {r['elapsed_sec']:.2f}s | tools={r['tool_count']} "
                  f"({','.join(r['tools_called'][:3])})")
            if r.get("error"):
                print(f"     ERROR: {r['error']}")
            case_results.append(r)
        per_seed.append(case_results)
        (out_root / f"seed_{seed}.json").write_text(
            json.dumps({"seed": seed, "cases": case_results},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    agg = aggregate(per_seed)
    (out_root / "aggregate.json").write_text(
        json.dumps(agg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(agg, out_root / "aggregate.csv")

    # Permutation test vs the existing single-run baseline (if present)
    baseline_path = Path("benchmark_results") / "deepseek_20260514_153103.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        # Use expected_match as the baseline strict-pass proxy (it has no intent check)
        base_scores = [int(c.get("expected_match", False))
                        for c in baseline.get("cases", [])]
        post_scores = []
        for seed_results in per_seed:
            for r in seed_results:
                post_scores.append(int(r["strict_pass"]))
        perm = permutation_test(post_scores, base_scores)
        (out_root / "permutation_test.json").write_text(
            json.dumps({
                "test": "permutation, two-sided, mean of indicator (post - pre)",
                "post_n": len(post_scores),
                "pre_n": len(base_scores),
                "result": perm,
                "note": "Pre is a single run; the test is exploratory.",
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"\n{'=' * 70}")
    print(f"  Aggregate (5 seeds, {len(TEST_CASES)} cases):")
    print(f"  Strict pass overall: {agg['overall']['strict_pass_overall']*100:.1f}%")
    print(f"  Loose pass overall:  {agg['overall']['loose_pass_overall']*100:.1f}%")
    print(f"  Mean latency:        {agg['overall']['mean_latency_overall_sec']:.2f} s")
    print(f"  Output: {out_root}")
    print(f"{'=' * 70}\n")
    return agg


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", default="1,2,3,4,5",
                    help="Comma-separated list of seeds, or an integer N for 1..N")
    p.add_argument("--label", default="post-routing-improvement")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    seeds_arg = args.seeds.strip()
    if "," in seeds_arg:
        seeds = [int(s) for s in seeds_arg.split(",")]
    else:
        n = int(seeds_arg)
        seeds = list(range(1, n + 1))
    asyncio.run(run_seeds(seeds, args.label))
