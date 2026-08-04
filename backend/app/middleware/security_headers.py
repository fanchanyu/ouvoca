"""
SecurityHeadersMiddleware — OWASP 對齊的 HTTP 安全標頭。

防護面：
- HSTS：強制 HTTPS（防降級攻擊）
- X-Frame-Options：防 clickjacking
- X-Content-Type-Options：防 MIME 嗅探
- Referrer-Policy：限制 referrer 資料外流
- Permissions-Policy：禁用敏感瀏覽器 API
- CSP（選用）：強制資源來源白名單，需依前端調整
- X-XSS-Protection（舊瀏覽器）+ Cross-Origin-* 套組

設計：
- 預設「合理嚴格」（不影響 LLM-ERP 正常運作）
- CSP 預設關閉（避免破壞前端），開發者可透過 env 開啟
"""
from __future__ import annotations
import os
from starlette.types import ASGIApp, Receive, Scope, Send, Message


# 預設 CSP（保守，可能需要客製化）
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://api.anthropic.com https://api.openai.com "
    "https://api.deepseek.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)


class SecurityHeadersMiddleware:
    """設好幾乎所有 OWASP 推薦的 security headers。

    可透過 env 微調：
    - SECURITY_CSP_ENABLED=true (default false)
    - SECURITY_CSP_VALUE=...（自訂）
    - SECURITY_HSTS_MAX_AGE=31536000（1 年，default）

    v3.69（效能健檢 ②）：pure ASGI — 不經 BaseHTTPMiddleware 的
    anyio task group + 雙向 stream 慢路徑，純加 header 幾乎零開銷。
    """
    def __init__(self, app: ASGIApp):
        self.app = app
        self.hsts_max_age = int(os.getenv("SECURITY_HSTS_MAX_AGE", "31536000"))
        self.csp_enabled = os.getenv("SECURITY_CSP_ENABLED", "false").lower() == "true"
        self.csp_value = os.getenv("SECURITY_CSP_VALUE", _DEFAULT_CSP)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                extra = {
                    b"strict-transport-security":
                        f"max-age={self.hsts_max_age}; includeSubDomains".encode(),
                    b"x-frame-options": b"DENY",
                    b"x-content-type-options": b"nosniff",
                    b"referrer-policy": b"strict-origin-when-cross-origin",
                    b"permissions-policy":
                        b"geolocation=(), microphone=(), camera=(), "
                        b"payment=(), usb=(), magnetometer=(), gyroscope=()",
                    b"cross-origin-opener-policy": b"same-origin",
                    b"cross-origin-resource-policy": b"same-origin",
                }
                if self.csp_enabled:
                    extra[b"content-security-policy"] = self.csp_value.encode()
                seen = {k.lower() for k, _ in headers}
                merged = list(headers) + [
                    (k, v) for k, v in extra.items() if k not in seen
                ]
                message["headers"] = merged
            await send(message)

        await self.app(scope, receive, send_with_headers)
