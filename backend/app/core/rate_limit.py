"""
Rate limiting — 防止 LLM 費用被攻擊炸光 + 防止暴力登入。

設計原則：
- 對 LLM endpoint（最貴）嚴格限制
- 對登入（敏感）防暴力破解
- 對其他 endpoint 寬鬆但有上限（防止單一 client 把資源吃光）
- 可透過 env 整體停用（開發 / 測試環境）

實作：slowapi (FastAPI + redis/memory backend)，預設 in-memory 適合單機部署，
       多 replicas 部署時可換 redis backend（不在本檔範圍）。
"""
from __future__ import annotations
import os
from slowapi import Limiter
from slowapi.util import get_remote_address


# 可透過 env 停用（CI / 測試 / 開發）
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"


def _key_func(request):
    """先用 user_id（若已驗證），否則退而求其次用 IP。"""
    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        uid = user.get("employee_id") or user.get("sub")
        if uid:
            return f"user:{uid}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_key_func,
    enabled=RATE_LIMIT_ENABLED,
    default_limits=["1000/hour"],  # 全域天花板（單一 client）
    headers_enabled=True,           # 加 X-RateLimit-* response header
)


# 各 endpoint 類別的建議速率（可被個別 endpoint 覆蓋）
RATE_LIMITS = {
    "auth_login": "10/minute",      # 防暴力破解
    "auth_register": "5/hour",
    "llm_chat": "30/minute",        # LLM 最貴：每分 30 次 = 約 NT$ 1-3
    "mutation": "60/minute",         # POST/PUT/DELETE 預設
    "query": "300/minute",           # GET 預設（給人類用合理）
    "factory_register": "60/minute", # factory_node 啟動可能重試
    "mesh_aggregate": "30/minute",   # 跨廠查詢有成本
}
