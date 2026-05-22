"""v3.45 修補驗證

P1-1: ChatResponse schema 加入 needs_slot_input + slot_ask 欄位
P1-2: chat.py 從 tool_calls_log 偵測 needs_input 並設頂層 flag
P1-3: api.ts ChatResponse interface 加 needs_slot_input / slot_ask
P1-4: Chat.tsx 加 slotAsk state + textarea 樣式分支
P1-5: undo_tools.py 補 undo_last_sales_order + undo_last_work_order
"""
from __future__ import annotations

import pathlib
import ast
import json

ROOT = pathlib.Path(__file__).resolve().parents[3]


# ════════════════════════════════════════════════════════════════════
# P1-1: ChatResponse schema 含新欄位
# ════════════════════════════════════════════════════════════════════

def test_chat_schema_has_slot_fields():
    src = (ROOT / "backend/app/schemas/chat.py").read_text(encoding="utf-8")
    assert "needs_slot_input" in src, "schemas/chat.py 缺 needs_slot_input"
    assert "slot_ask" in src, "schemas/chat.py 缺 slot_ask"


# ════════════════════════════════════════════════════════════════════
# P1-2: chat.py 有 needs_input 偵測邏輯
# ════════════════════════════════════════════════════════════════════

def test_chat_api_detects_needs_input():
    src = (ROOT / "backend/app/api/chat.py").read_text(encoding="utf-8")
    assert "needs_input" in src, "chat.py 缺 needs_input 偵測"
    assert "needs_slot_input" in src, "chat.py ChatResponse 缺 needs_slot_input 欄位"
    assert "slot_ask" in src, "chat.py ChatResponse 缺 slot_ask 欄位"
    # 確保有從 tool_calls_log 掃描
    assert "tool_calls_log" in src and "needs_input" in src


# ════════════════════════════════════════════════════════════════════
# P1-3: api.ts 有新 interface 欄位
# ════════════════════════════════════════════════════════════════════

def test_api_ts_has_slot_fields():
    src = (ROOT / "frontend-desktop/src/lib/api.ts").read_text(encoding="utf-8")
    assert "needs_slot_input" in src, "api.ts ChatResponse 缺 needs_slot_input"
    assert "slot_ask" in src, "api.ts ChatResponse 缺 slot_ask"


# ════════════════════════════════════════════════════════════════════
# P1-4: Chat.tsx 有 slotAsk state + amber 樣式分支
# ════════════════════════════════════════════════════════════════════

def test_chat_tsx_has_slot_ux():
    src = (ROOT / "frontend-desktop/src/pages/Chat.tsx").read_text(encoding="utf-8")
    assert "slotAsk" in src, "Chat.tsx 缺 slotAsk state"
    assert "amber" in src, "Chat.tsx 缺 amber (slot-filling 高亮色)"
    assert "slot_ask" in src, "Chat.tsx 缺 slot_ask 使用"
    assert "setSlotAsk(null)" in src, "Chat.tsx 缺清除 slotAsk 邏輯"


# ════════════════════════════════════════════════════════════════════
# P1-5: undo_tools.py 含 SO + WO undo
# ════════════════════════════════════════════════════════════════════

def test_undo_tools_has_so_and_wo():
    src = (ROOT / "backend/app/agents/domains/undo_tools.py").read_text(encoding="utf-8")
    assert "undo_last_sales_order" in src, "undo_tools.py 缺 undo_last_sales_order"
    assert "undo_last_work_order" in src, "undo_tools.py 缺 undo_last_work_order"
    # 確認都有正確 ConfirmCard 鏈
    assert src.count("make_card") >= 3, "應有 3 個 make_card (PO + SO + WO)"
    assert src.count("stash_card") >= 3, "應有 3 個 stash_card"


def test_undo_tools_registers_all_agents():
    src = (ROOT / "backend/app/agents/domains/undo_tools.py").read_text(encoding="utf-8")
    assert '"purchase"' in src and '"sales"' in src and '"production"' in src, \
        "undo_tools 缺對 purchase/sales/production 3 個 agent registry 的注冊"


def test_undo_tools_imports_models():
    src = (ROOT / "backend/app/agents/domains/undo_tools.py").read_text(encoding="utf-8")
    assert "from app.models.crm_sales import SalesOrder" in src
    assert "from app.models.production import WorkOrder" in src
