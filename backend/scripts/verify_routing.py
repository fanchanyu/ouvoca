"""Verify routing patch — checks that all 10 benchmark cases route to expected intent.

This is the pre-LLM step: confirm intent classification picks the right agent.
Run BEFORE the full benchmark so we know routing is sound without spending API tokens.
"""
from __future__ import annotations
import os
import sys

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.engine import classify_intent

CASES = [
    ("T01", "請列出庫存低於安全庫存的零件", "inventory"),
    ("T02", "幫我查 M6-BOLT-20 還剩多少", "inventory"),
    ("T03", "我們倉庫現在缺什麼料?", "inventory"),
    ("T04", "如果客戶要訂 100 台變速齒輪組 A,我們現在可以做嗎?要先檢查什麼?", "production"),
    ("T05", "今天工廠營運狀況如何?簡單總結", "general"),
    ("T06", "A 客戶 PRD-GEAR-A 最近的單價?", "crm"),
    ("T07", "礦存還剩多少 M6 螺絲?", "inventory"),
    ("T08", "給我一些改善庫存周轉的建議", "inventory"),
    ("T09", "查一下我們的供應商有哪些", "purchase"),
    ("T10", "最近有哪些不良品?品質狀況如何?", "quality"),
]


def main() -> int:
    print()
    print(f"{'Case':6} {'Got':12} {'Expected':12} {'Result':6}")
    print("-" * 70)
    ok = 0
    fails = []
    for case_id, q, expected in CASES:
        got = classify_intent(q)
        match = got == expected
        if match:
            ok += 1
            tag = "PASS"
        else:
            fails.append((case_id, q, got, expected))
            tag = "FAIL"
        print(f"{case_id:6} {got:12} {expected:12} {tag:6}")
    print("-" * 70)
    print(f"Intent classification: {ok}/{len(CASES)} cases correct")
    if fails:
        print("\nFailures:")
        for cid, q, got, exp in fails:
            print(f"  {cid}: '{q}' -> {got} (expected {exp})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
