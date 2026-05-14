"""
Smoke: Demo Bypass 行為
驗收：當 JWT_SECRET 為預設值，Bearer 'demo' 可當超管使用；
       當 JWT_SECRET 已設定（如本測試 session），demo bypass 必須自動關閉。
"""


def test_demo_bypass_disabled_in_test_env(client):
    """測試環境 JWT_SECRET 已設定 → demo bypass 應該關閉。"""
    r = client.get("/api/health")
    assert r.json()["demo_bypass"] is False, \
        "JWT_SECRET 已設定但 demo_bypass 仍 active — 安全風險！"


def test_demo_token_rejected_when_disabled(client):
    """JWT_SECRET 已設定時，'Bearer demo' 應該被拒。"""
    r = client.get("/api/inventory/parts", headers={"Authorization": "Bearer demo"})
    assert r.status_code == 401, f"應 401，得 {r.status_code}"


def test_missing_authorization_header(client):
    r = client.get("/api/inventory/parts")
    assert r.status_code == 401
    assert "Authorization" in r.json().get("detail", "") or \
           "未登入" in r.json().get("detail", "") or \
           "Token" in r.json().get("detail", "") or \
           "缺少" in r.json().get("detail", "")


def test_invalid_jwt_rejected(client):
    """偽造或過期的 JWT 應被拒。"""
    r = client.get("/api/inventory/parts", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401
