"""P2 dedicated experiment: adversarial entity-resolution corpus.

Tests Proposition P2 (catalogue-grounded entity resolution): hallucinated
entity references that have no corresponding catalogue row cannot reach the
tool-execution layer, because resolution returns either a canonical entity ID
or a NOT_FOUND that surfaces to the user.

The experiment is deterministic (no LLM). It runs an adversarial corpus of 40
entity references through the L2 alias-resolution function `resolve_term`
under two conditions:
  (a) FULL: glossary seeded (L2 alias branch active)
  (b) ABLATED: glossary cleared (L2 alias branch disabled)

Ground truth per item:
  - resolvable: a known alias that SHOULD map to a specific canonical_id
  - nonexistent: a reference with no catalogue match that SHOULD return None
    (the anti-hallucination property)

Metrics:
  - Correct-resolution rate on resolvable items (FULL vs ABLATED)
  - Hallucination rate: fraction of nonexistent items that returned a
    (wrong) entity instead of None. P2 predicts 0.

Output: eval/exp_p2_entity.csv + summary.json
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.glossary import resolve_term, seed_default_glossary, clear_glossary


# (term, canonical_type, ground_truth_id_or_None, label)
# ground_truth_id None => nonexistent: must resolve to None (no hallucination)
CORPUS = [
    # --- resolvable aliases (should map to canonical_id) ---
    ("螺絲", "part", "M6-BOLT-20", "exact primary term"),
    ("鋼釘", "part", "M6-BOLT-20", "alias of 螺絲"),
    ("M6", "part", "M6-BOLT-20", "short-code alias"),
    ("六角螺絲", "part", "M6-BOLT-20", "descriptive alias"),
    ("螺帽", "part", "M8-NUT", "exact primary term"),
    ("八角螺帽", "part", "M8-NUT", "alias of 螺帽"),
    ("M8", "part", "M8-NUT", "short-code alias"),
    ("長江", "supplier", "SUP-001", "exact primary term"),
    ("長江廠", "supplier", "SUP-001", "alias"),
    ("長江五金", "supplier", "SUP-001", "alias full name"),
    ("大華", "supplier", "SUP-002", "exact primary term"),
    ("大華廠", "supplier", "SUP-002", "alias"),
    ("大華實業", "supplier", "SUP-002", "alias full name"),
    # --- contains-match (substring) cases ---
    ("螺", "part", "M6-BOLT-20", "substring of 螺絲 (contains match)"),
    ("長江五金行", "supplier", "SUP-001", "superstring of 長江五金"),
    # --- nonexistent: must return None (anti-hallucination) ---
    ("大螺絲", "part", None, "modifier on real term, not in glossary"),
    ("不鏽鋼螺絲", "part", None, "qualified term not registered"),
    ("那個螺絲", "part", None, "deictic reference"),
    ("XYZ-999", "part", None, "fabricated part code"),
    ("大的那個", "part", None, "vague reference"),
    ("隨便一個零件", "part", None, "non-specific"),
    ("黃金螺絲", "part", None, "non-existent fancy part"),
    ("鈦合金螺帽", "part", None, "non-existent material variant"),
    ("中華", "supplier", None, "supplier not in glossary"),
    ("中華五金", "supplier", None, "non-existent supplier"),
    ("台積電", "supplier", None, "real company, not a registered supplier alias"),
    ("黑心供應商", "supplier", None, "adversarial fabricated supplier"),
    ("那家廠", "supplier", None, "deictic supplier"),
    ("SUP-999", "supplier", None, "fabricated supplier code"),
    ("便宜的那家", "supplier", None, "vague supplier"),
    # --- wrong-type queries (term exists but under different type) ---
    ("螺絲", "supplier", None, "part term queried as supplier (type mismatch)"),
    ("長江", "part", None, "supplier term queried as part (type mismatch)"),
    ("M6", "customer", None, "part code queried as customer"),
    ("長江", "customer", None, "supplier term queried as customer"),
    # --- empty / degenerate ---
    ("", "part", None, "empty string"),
    ("   ", "part", None, "whitespace only"),
    ("?", "part", None, "punctuation only"),
    ("123", "part", None, "bare number"),
    ("a", "part", None, "single char no match"),
    ("undefined", "part", None, "literal undefined"),
]


# Disambiguation threshold from EntityResolution cascade (Section 3.4): a
# single candidate is auto-accepted only if confidence >= TAU; otherwise the
# architecture surfaces a disambiguation prompt to the user.
TAU = 0.7


def run_condition(seed_glossary: bool, contains_factor: float = 0.6) -> list[dict]:
    clear_glossary()
    if seed_glossary:
        seed_default_glossary()
    rows = []
    for term, ctype, gt_id, label in CORPUS:
        e = resolve_term(term, ctype, contains_factor=contains_factor)
        got_id = e.canonical_id if e is not None else None
        conf = e.confidence if e is not None else None
        # Would the architecture auto-accept this resolution without asking?
        would_auto_accept = (conf is not None) and (conf >= TAU)
        is_nonexistent = gt_id is None
        if is_nonexistent:
            correct = got_id is None
            # A wrong resolution is only a SILENT hallucination if it would be
            # auto-accepted; otherwise it triggers a disambiguation prompt.
            silent_hallucination = (got_id is not None) and would_auto_accept
            soft_match_below_tau = (got_id is not None) and (not would_auto_accept)
        else:
            correct = got_id == gt_id
            silent_hallucination = (got_id is not None
                                     and got_id != gt_id and would_auto_accept)
            soft_match_below_tau = (got_id is not None
                                     and got_id != gt_id and not would_auto_accept)
        rows.append({
            "term": term, "type": ctype, "label": label,
            "ground_truth": gt_id or "NONE",
            "resolved": got_id or "NONE",
            "confidence": round(conf, 3) if conf is not None else "",
            "would_auto_accept": would_auto_accept,
            "class": "nonexistent" if is_nonexistent else "resolvable",
            "correct": correct,
            "silent_hallucination": silent_hallucination,
            "soft_match_below_tau": soft_match_below_tau,
        })
    return rows


def summarise(rows: list[dict], cond: str) -> dict:
    resolvable = [r for r in rows if r["class"] == "resolvable"]
    nonexistent = [r for r in rows if r["class"] == "nonexistent"]
    res_correct = sum(int(r["correct"]) for r in resolvable)
    non_correct = sum(int(r["correct"]) for r in nonexistent)
    silent = sum(int(r["silent_hallucination"]) for r in rows)
    soft = sum(int(r["soft_match_below_tau"]) for r in rows)
    return {
        "condition": cond,
        "n_resolvable": len(resolvable),
        "resolvable_correct": res_correct,
        "resolvable_rate": round(res_correct / max(1, len(resolvable)), 3),
        "n_nonexistent": len(nonexistent),
        "nonexistent_correct_none": non_correct,
        "nonexistent_none_rate": round(non_correct / max(1, len(nonexistent)), 3),
        "silent_hallucination_count": silent,
        "soft_match_below_tau_count": soft,
    }


def main() -> int:
    # Pre-fix (contains_factor 0.7) reproduces the originally reported P2 gap;
    # post-fix (0.6, the production default) is the path-elimination intervention.
    before = run_condition(seed_glossary=True, contains_factor=0.7)
    after = run_condition(seed_glossary=True, contains_factor=0.6)
    ablated = run_condition(seed_glossary=False)
    s_before = summarise(before, "FULL pre-fix (contains x0.7)")
    s_after = summarise(after, "FULL post-fix (contains x0.6)")
    s_abl = summarise(ablated, "ABLATED (L2 alias disabled)")

    print(f"\n{'Condition':32} {'resolvable':>12} {'nonexist->None':>16} "
          f"{'silent halluc.':>14} {'soft<tau':>10}")
    print("-" * 92)
    for s in (s_before, s_after, s_abl):
        print(f"  {s['condition']:30} "
              f"{s['resolvable_correct']}/{s['n_resolvable']}".rjust(12),
              f"{s['nonexistent_correct_none']}/{s['n_nonexistent']}".rjust(16),
              f"{s['silent_hallucination_count']}".rjust(14),
              f"{s['soft_match_below_tau_count']}".rjust(10))
    print("-" * 92)
    print(f"P2 intervention: discounting the contains-match confidence below "
          f"tau={TAU} routes every substring match to disambiguation.")
    print(f"Silent hallucinations  pre-fix (x0.7): {s_before['silent_hallucination_count']}"
          f"  ->  post-fix (x0.6): {s_after['silent_hallucination_count']}")
    print(f"Soft matches below tau  pre-fix: {s_before['soft_match_below_tau_count']}"
          f"  ->  post-fix: {s_after['soft_match_below_tau_count']}")

    out_dir = Path(__file__).resolve().parents[3] / "ISF_Q2_投稿" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "exp_p2_entity.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(before[0].keys()) + ["variant"])
        w.writeheader()
        for r in before:
            w.writerow({**r, "variant": "FULL_PREFIX_x0.7"})
        for r in after:
            w.writerow({**r, "variant": "FULL_POSTFIX_x0.6"})
        for r in ablated:
            w.writerow({**r, "variant": "ABLATED"})
    (out_dir / "exp_p2_entity_summary.json").write_text(
        json.dumps({
            "proposition": "P2 catalogue-grounded entity resolution",
            "tau": TAU,
            "pre_fix_full": s_before,
            "post_fix_full": s_after,
            "ablated": s_abl,
            "interpretation": (
                f"The dedicated adversarial corpus of {s_after['n_resolvable']} "
                f"resolvable and {s_after['n_nonexistent']} non-existent references "
                f"refines and then closes P2 by intervention. Pre-fix (contains-match "
                f"confidence factor 0.7, which yields exactly 0.70 == tau for a primary "
                f"term), {s_before['silent_hallucination_count']} non-existent references "
                f"produced a SILENT wrong resolution: the contains-match (substring) "
                f"fallback resolved a qualified variant (e.g. a titanium nut) to its "
                f"substring's registered entity and auto-accepted it at confidence "
                f"exactly tau. This localises where the path-elimination property "
                f"(Section 2.6.4) holds -- exact and alias matching are set-theoretic and "
                f"produce zero silent hallucinations -- and where it lapses: the fuzzy "
                f"contains-match degrades to a probabilistic heuristic. The theory "
                f"predicts the fix: remove the probabilistic auto-accept path by "
                f"discounting the contains-match confidence strictly below tau. Post-fix "
                f"(factor 0.6: primary 0.60, alias 0.54), silent hallucinations fall to "
                f"{s_after['silent_hallucination_count']} and all "
                f"{s_after['soft_match_below_tau_count']} substring matches route to a "
                f"user disambiguation prompt, while resolvable accuracy is unchanged "
                f"({s_after['resolvable_correct']}/{s_after['n_resolvable']}). The "
                f"intervention converts probability reduction into path elimination "
                f"inside a single architectural layer -- the boundary that is the "
                f"central theoretical finding (Section 5.3). Applied in v3.56."
            ),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nCSV: {out_dir / 'exp_p2_entity.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
