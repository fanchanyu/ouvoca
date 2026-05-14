"""
RequestID middleware — 每個請求自動分配一個 ID，貫穿整個 log + response。

設計：
- 進來時：若 client 已帶 X-Request-ID，沿用；否則生成 UUID
- 過程中：放進 contextvars，所有 log 自動帶
- 出去時：回 header X-Request-ID 讓 client 對應

效益：
- production 出問題客戶說「16:23 的 request 壞了」，能直接撈 log
- 跨服務（HQ → factory_node）也能用同一個 request_id 串
"""
from __future__ import annotations
import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Context-var 讓任何地方的 log 都拿得到當前 request_id
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """log formatter 用：拿當前請求的 ID。"""
    return _request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        # 沿用 client 帶的，否則生成
        rid = request.headers.get(self.HEADER) or str(uuid.uuid4())
        token = _request_id_var.set(rid)
        try:
            request.state.request_id = rid
            response = await call_next(request)
            response.headers[self.HEADER] = rid
            return response
        finally:
            _request_id_var.reset(token)
