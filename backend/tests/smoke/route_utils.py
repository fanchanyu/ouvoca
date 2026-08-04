"""Route inspection helpers — FastAPI 0.128+ lazy-router 相容層。

新版 FastAPI/Starlette 的 include_router 改為 lazy：app.routes 存放
_IncludedRouter placeholder，直到 ASGI 呼叫才展開 effective routes。
直接 inspect app.routes 只會看到 placeholder（沒有 .path）。
此 helper 遞迴展開，讓 route-inspection 測試跨 FastAPI 版本穩定。
"""
from __future__ import annotations


def flatten_app_routes(routes) -> list:
    """展開 app.routes（含 _IncludedRouter placeholder）。"""
    try:
        from fastapi.routing import _IncludedRouter
    except ImportError:  # 舊版 FastAPI：沒有 lazy router，直接回傳
        return list(routes)

    out: list = []
    for r in routes:
        if isinstance(r, _IncludedRouter):
            out.extend(flatten_app_routes(r.effective_candidates()))
        else:
            out.append(r)
    return out
