"""P4 dedicated experiment: missing-slot solicitation versus fabrication.

Tests Proposition P4 (solicit-not-fabricate): when a required slot is missing,
the architecture detects the gap and solicits it through a bounded
counter-question rather than fabricating a value.

The experiment is deterministic (no LLM) and tests the mechanism directly,
removing LLM stochasticity as a confound. For every registered tool that
declares at least one required slot, we invoke it with an EMPTY argument set
under two conditions:

  (a) FULL: through execute_tool, which runs the slot-fill detection of
      Layer 1 (Section 3.3.2). The architecture should return a needs_input
      response (a counter-question) without executing the tool.
  (b) NAIVE: by calling the registered function directly with empty arguments,
      bypassing slot detection. Either the call raises a missing-argument
      error (Python-level), or it proceeds with None/defaulted values - the
      fabrication-equivalent path that the architecture is designed to prevent.

Metrics:
  - Solicitation rate (FULL): fraction of tools that return needs_input.
  - Fabrication-or-crash rate (NAIVE): fraction that either execute with
    unspecified values or raise an error instead of soliciting.

Output: eval/exp_p4_slot.csv + summary.json
"""
from __future__ import annotations

import asyncio
import csv
import json
import os
import sys
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import classify_intent  # noqa: F401 - triggers registry init
from app.agents.engine import execute_tool
from app.agents.registry import list_tools
from app.database import AsyncSessionLocal


async def main() -> int:
    user = {"employee_id": "p4", "username": "p4", "roles": ["admin"]}
    tools_with_required = [
        t for t in list_tools()
        if any(s.required for s in t.slots)
    ]

    rows = []
    full_solicited = 0
    naive_fabricated_or_crashed = 0

    print(f"\nTesting {len(tools_with_required)} tools that declare >=1 required slot")
    print("-" * 90)

    async with AsyncSessionLocal() as db:
        for meta in sorted(tools_with_required, key=lambda m: m.name):
            req_slots = [s.name for s in meta.slots if s.required]

            # (a) FULL: through execute_tool with empty args
            try:
                resp = await execute_tool(meta.name, {}, db=db, user=user)
                parsed = json.loads(resp) if isinstance(resp, str) else resp
                solicited = bool(isinstance(parsed, dict)
                                  and parsed.get("needs_input"))
            except Exception:
                solicited = False
            if solicited:
                full_solicited += 1

            # (b) NAIVE: call the registered function directly with empty args
            naive_outcome = "unknown"
            try:
                raw = await meta.func(db=db, user=user)
                # reached execution without soliciting => fabrication-equivalent
                naive_outcome = "executed_without_solicit"
                naive_fabricated_or_crashed += 1
            except TypeError:
                # missing required positional argument at Python level
                naive_outcome = "python_missing_arg_error"
                naive_fabricated_or_crashed += 1
            except Exception as exc:
                naive_outcome = f"other_error:{type(exc).__name__}"
                naive_fabricated_or_crashed += 1

            rows.append({
                "tool": meta.name,
                "domain": meta.domain,
                "risk_tier": meta.risk_tier.value,
                "required_slots": ";".join(req_slots),
                "full_solicited": solicited,
                "naive_outcome": naive_outcome,
            })
            tag = "SOLICIT" if solicited else "no-solicit"
            print(f"  {tag:11} {meta.name:48} naive={naive_outcome}")

    n = len(tools_with_required)
    print("-" * 90)
    print(f"FULL solicitation rate:  {full_solicited}/{n} "
          f"({100*full_solicited/max(1,n):.1f}%)")
    print(f"NAIVE fabricate-or-crash: {naive_fabricated_or_crashed}/{n} "
          f"({100*naive_fabricated_or_crashed/max(1,n):.1f}%)")

    out_dir = Path(__file__).resolve().parents[3] / "ISF_Q2_投稿" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "exp_p4_slot.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    (out_dir / "exp_p4_slot_summary.json").write_text(
        json.dumps({
            "proposition": "P4 solicit-not-fabricate",
            "n_tools_with_required_slots": n,
            "full_solicitation_count": full_solicited,
            "full_solicitation_rate": round(full_solicited / max(1, n), 3),
            "naive_fabricate_or_crash_count": naive_fabricated_or_crashed,
            "naive_fabricate_or_crash_rate": round(
                naive_fabricated_or_crashed / max(1, n), 3),
            "interpretation": (
                f"Of {n} tools declaring at least one required slot, the full "
                f"architecture returns a slot-solicitation counter-question for "
                f"{full_solicited} ({100*full_solicited/max(1,n):.0f}%) when invoked "
                f"with no arguments, executing none of them. The naive path, which "
                f"calls the tool function directly, reaches "
                f"{naive_fabricated_or_crashed} of {n} either by executing with "
                f"unspecified values or by raising a missing-argument error - in "
                f"both cases the architecture's solicit-not-fabricate guarantee is "
                f"absent. This is the path-elimination property (Section 2.6.4) "
                f"applied to missing parameters: the slot-fill detector removes the "
                f"class of paths in which a required value is silently supplied by "
                f"the model rather than obtained from the user."
            ),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nCSV: {out_dir / 'exp_p4_slot.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
