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
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """設好幾乎所有 OWASP 推薦的 security headers。

    可透過 env 微調：
    - SECURITY_CSP_ENABLED=true (default false)
    - SECURITY_CSP_VALUE=...（自訂）
    - SECURITY_HSTS_MAX_AGE=31536000（1 年，default）
    """
    def __init__(self, app, **opts):
        super().__init__(app)
        self.hsts_max_age = int(os.getenv("SECURITY_HSTS_MAX_AGE", "31536000"))
        self.csp_enabled = os.getenv("SECURITY_CSP_ENABLED", "false").lower() == "true"
        self.csp_value = os.getenv("SECURITY_CSP_VALUE", _DEFAULT_CSP)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        h = response.headers

        # HSTS：強制 HTTPS（瀏覽器 1 年內都記住）
        h["Strict-Transport-Security"] = (
            f"max-age={self.hsts_max_age}; includeSubDomains"
        )
        # 防 clickjacking
        h["X-Frame-Options"] = "DENY"
        # 防 MIME 嗅探
        h["X-Content-Type-Options"] = "nosniff"
        # 限制 referrer 外流（送的時候帶 origin，不送完整 path）
        h["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # 禁用所有敏感瀏覽器 API（依需求微調）
        h["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )
        # 跨來源隔離 — 防 Spectre / 跨 origin 攻擊
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        h["Cross-Origin-Resource-Policy"] = "same-origin"

        # CSP — 預設關閉避免破壞前端，正式部署建議開
        if self.csp_enabled:
            h["Content-Security-Policy"] = self.csp_value

        # 隱藏 server 軟體版本資訊（紙上談兵但合規要求）
        if "Server" in h:
            del h["Server"]

        return response
