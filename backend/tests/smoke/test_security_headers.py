"""
Security Headers — OWASP 對齊驗證

驗收：每個 response 都要有以下 header（且值合理）。
"""
import pytest


REQUIRED_HEADERS = {
    "Strict-Transport-Security": lambda v: "max-age=" in v and "includeSubDomains" in v,
    "X-Frame-Options": lambda v: v == "DENY",
    "X-Content-Type-Options": lambda v: v == "nosniff",
    "Referrer-Policy": lambda v: "strict-origin" in v,
    "Permissions-Policy": lambda v: "geolocation=()" in v,
    "Cross-Origin-Opener-Policy": lambda v: v == "same-origin",
    "Cross-Origin-Resource-Policy": lambda v: v == "same-origin",
}


@pytest.mark.parametrize("header,validator", list(REQUIRED_HEADERS.items()))
def test_security_header_present(header, validator, client):
    r = client.get("/api/health")
    val = r.headers.get(header)
    assert val, f"missing security header: {header}"
    assert validator(val), f"{header} value invalid: {val!r}"


def test_server_header_hidden(client):
    """Server / X-Powered-By 不該洩露版本資訊."""
    r = client.get("/api/health")
    # uvicorn 預設會送 server header；middleware 已移除
    assert "Server" not in r.headers or "uvicorn" not in r.headers.get("Server", "").lower()


def test_hsts_default_1year(client):
    r = client.get("/api/health")
    hsts = r.headers.get("Strict-Transport-Security", "")
    # 預設 31536000 = 1 年
    assert "31536000" in hsts


def test_csp_disabled_by_default(client):
    """預設不送 CSP（避免破壞前端開發）；正式部署透過 env 開啟。"""
    r = client.get("/api/health")
    assert "Content-Security-Policy" not in r.headers
