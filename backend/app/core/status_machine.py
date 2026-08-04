"""狀態機框架（Phase C2）— 單據 status 不再只是自由字串。

問題：status 全是自由字串（"draft"/"shipped"...），沒有允許轉換驗證，
表單可以被非法路徑推進（如未審核直接出貨）。解法：
  - 每類單據定義 allowed transitions（draft→approved→shipped→invoiced→closed）
  - assert_transition() 在 service 寫入 status 前檢查，非法轉換拋 BusinessRuleError
  - can_transition() / allowed_next() 給前端動態隱藏不可能的操作
  - 未來可把此表資料化為 status_transitions DB 表 + 家規掛勾
"""
from __future__ import annotations

from app.core.exceptions import BusinessRuleError

# 單據類型 → { from_status: [to_status, ...] }
# 初始狀態（建單時）不在 key 內，但會出現在其它狀態的 to 清單。
TRANSITIONS: dict[str, dict[str, list[str]]] = {
    "SO": {
        "draft": ["confirmed", "cancelled"],
        "confirmed": ["production", "ready_to_ship", "shipped", "cancelled"],
        "production": ["ready_to_ship", "shipped", "cancelled"],
        "ready_to_ship": ["shipped", "cancelled"],
        "shipped": ["invoiced", "closed"],
        "invoiced": ["closed"],
        "closed": [],
        "cancelled": [],
    },
    "PO": {
        "draft": ["pending", "approved", "cancelled"],
        "pending": ["approved", "cancelled"],
        "approved": ["sent", "received", "partial_received", "cancelled"],
        "sent": ["received", "partial_received", "cancelled"],
        "partial_received": ["partial_received", "received", "cancelled"],
        "received": ["closed"],
        "closed": [],
        "cancelled": [],
    },
    "WO": {  # production order
        "draft": ["released", "cancelled"],
        "released": ["in_progress", "completed", "cancelled"],
        "in_progress": ["completed", "cancelled"],
        "completed": ["closed"],
        "closed": [],
        "cancelled": [],
    },
    "DN": {
        "draft": ["shipped", "cancelled"],
        "shipped": ["invoiced"],
        "invoiced": ["closed"],
        "closed": [],
        "cancelled": [],
    },
    "JE": {
        "draft": ["posted", "reversed"],
        "posted": ["reversed"],
        "reversed": [],
    },
    "STOCK_COUNT": {
        "draft": ["counting", "cancelled"],
        "counting": ["adjusted", "completed"],
        "completed": ["adjusted", "posted"],
        "adjusted": ["posted"],
        "posted": [],
        "cancelled": [],
    },
    "INSPECTION": {
        "draft": ["completed", "rejected"],
        "completed": [],
        "rejected": [],
    },
    "QUOTATION": {
        "draft": ["confirmed", "converted", "cancelled"],
        "confirmed": ["converted", "cancelled"],
        "converted": ["closed"],
        "closed": [],
        "cancelled": [],
    },
}


def can_transition(doc_type: str, from_status: str | None, to_status: str) -> bool:
    """檢查 from → to 是否合法（from 為 None 表示新建單，預設允許）。"""
    if from_status is None:
        return True
    allowed = TRANSITIONS.get(doc_type, {}).get(from_status, [])
    return to_status in allowed


def assert_transition(doc_type: str, from_status: str | None, to_status: str, doc_no: str | None = None) -> None:
    """非法轉換直接拋 BusinessRuleError（service 層最後防線）。"""
    if not can_transition(doc_type, from_status, to_status):
        label = f"（{doc_no}）" if doc_no else ""
        raise BusinessRuleError(
            f"{doc_type} 狀態不允許由 {from_status!r} 轉為 {to_status!r}{label}。"
            f"合法目標：{allowed_next(doc_type, from_status) or '（無，此狀態已終結）'}",
            doc_type=doc_type,
            from_status=from_status,
            to_status=to_status,
        )


def allowed_next(doc_type: str, from_status: str | None) -> list[str]:
    """列出 from_status 可轉到的所有目標（前端按此隱藏按鈕）。"""
    if from_status is None:
        return sorted({t for targets in TRANSITIONS.get(doc_type, {}).values() for t in targets})
    return list(TRANSITIONS.get(doc_type, {}).get(from_status, []))
