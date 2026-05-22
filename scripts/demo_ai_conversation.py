#!/usr/bin/env python
"""Ouvoca · 自然語言對話 demo（read-only 版）

跑一輪 12 個典型問題，把 AI 回應存成 Markdown，給：
  • 銷售：showcase 客戶看現有能力
  • 內部：發現哪個 domain 的 AI 答得好/不好

執行：
  cd backend
  PYTHONIOENCODING=utf-8 python ../scripts/demo_ai_conversation.py

輸出：
  docs/demos/ai_conversation_YYYYMMDD_HHMM.md
"""
from __future__ import annotations
import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 確保能找到 app
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import httpx

BASE_URL = os.getenv("ERP_BASE_URL", "http://localhost:8000")
USERNAME = os.getenv("ERP_USERNAME", "admin")
PASSWORD = os.getenv("ERP_PASSWORD", "admin123")
SESSION_ID = f"demo-{int(time.time())}"


# 12 個典型問題（涵蓋 6 個 domain）
QUERIES = [
    # 庫存
    ("Inventory", "今天哪些零件低於安全庫存？"),
    ("Inventory", "M6-BOLT-20 還有多少？"),
    ("Inventory", "列出所有原料類零件"),
    # 銷售
    ("Sales",     "我們有哪些客戶？"),
    ("Sales",     "最近的銷售訂單狀況"),
    # 採購
    ("Purchase",  "列出所有供應商"),
    ("Purchase",  "最近的採購單"),
    # 生產
    ("Production","目前進行中的工單"),
    ("Production","列出我們的產品"),
    # 品質
    ("Quality",   "最近的品檢狀況"),
    # 倉儲
    ("Warehouse", "倉庫有哪些區域？"),
    # 老闆視角
    ("Boss",      "今天工廠運營狀況如何？請彙整重點。"),
]


async def login(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def chat(client: httpx.AsyncClient, token: str, message: str) -> dict:
    t0 = time.time()
    r = await client.post(
        f"{BASE_URL}/api/chat-v2",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": message, "session_id": SESSION_ID},
        timeout=60,
    )
    dt = time.time() - t0
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:300]}", "elapsed_s": dt}
    data = r.json()
    data["elapsed_s"] = round(dt, 1)
    return data


async def main():
    out_dir = ROOT / "docs" / "demos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"ai_conversation_{datetime.now().strftime('%Y%m%d_%H%M')}.md"

    lines = [
        f"# Ouvoca AI 對話 demo · {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- Session: `{SESSION_ID}`",
        f"- Backend: `{BASE_URL}`",
        f"- 12 typical queries, 6 domains",
        "",
        "---",
        "",
    ]

    async with httpx.AsyncClient() as client:
        try:
            token = await login(client)
            lines.append(f"✓ Login as **{USERNAME}**\n")
        except Exception as e:
            lines.append(f"❌ Login failed: {e}\n")
            out_file.write_text("\n".join(lines), encoding="utf-8")
            print(f"❌ Login failed: {e}")
            return

        ok = bad = 0
        total_dt = 0.0
        for i, (domain, q) in enumerate(QUERIES, 1):
            print(f"[{i}/{len(QUERIES)}] {domain}: {q}")
            data = await chat(client, token, q)

            lines.append(f"## Q{i}. {domain}\n")
            lines.append(f"**問**：{q}\n")

            if "error" in data:
                lines.append(f"**❌ 失敗**：{data['error']}\n")
                lines.append(f"耗時：{data.get('elapsed_s', '?')}s\n\n---\n")
                bad += 1
                continue

            agent = data.get("agent", "?")
            tools = data.get("tool_calls") or []
            reply = data.get("reply", "(無)")
            dt = data.get("elapsed_s", 0)
            total_dt += dt

            lines.append(f"**Agent**: `{agent}` · **耗時**: {dt}s · **Tool calls**: {len(tools)}\n")
            if tools:
                tool_names = [t.get("tool", "?") for t in tools]
                lines.append(f"  - 呼叫工具：{', '.join(tool_names)}\n")
            lines.append(f"\n**答**：\n\n{reply}\n\n---\n")
            ok += 1

        # Summary
        avg_dt = total_dt / max(ok, 1)
        summary = [
            "",
            "## 📊 總結",
            "",
            f"- ✅ 成功：{ok} / {len(QUERIES)}",
            f"- ❌ 失敗：{bad} / {len(QUERIES)}",
            f"- ⏱  平均耗時：{avg_dt:.1f} 秒/題",
            f"- 💰 估成本（DeepSeek 單價）：< NT$ 0.05",
            "",
        ]
        # Insert summary right after the header
        for j, ln in enumerate(lines):
            if ln == "---":
                for s in reversed(summary):
                    lines.insert(j, s)
                break

        out_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n✓ 寫入 {out_file}")
        print(f"  成功: {ok}/{len(QUERIES)}, 失敗: {bad}, 平均: {avg_dt:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
