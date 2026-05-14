"""
Smoke: /api/auth/login + JWT 流程
驗收：
1. 錯誤密碼 → 401
2. 正確密碼 → 200 + access_token + user 物件
3. 帶 token 能存取受保護資源
4. 不帶 token 存取受保護資源 → 401
"""


def test_login_wrong_password(seeded_client):
    r = seeded_client.post("/api/auth/login", json={
        "username": "testadmin", "password": "WRONG",
    })
    assert r.status_code == 401, f"應 401 但得 {r.status_code}: {r.text}"


def test_login_unknown_user(seeded_client):
    r = seeded_client.post("/api/auth/login", json={
        "username": "ghost", "password": "anything",
    })
    assert r.status_code == 401


def test_login_returns_token_and_user(admin_token, seeded_client):
    """admin_token fixture 已驗證 200。這裡確認結構。"""
    assert isinstance(admin_token, str) and len(admin_token) > 50
    # 解 JWT header 看看（不驗證簽章，只看格式）
    parts = admin_token.split(".")
    assert len(parts) == 3, "JWT 應有 3 段"


def test_protected_endpoint_requires_auth(client):
    """不帶 token 存取 /api/inventory/parts 應 401."""
    r = client.get("/api/inventory/parts")
    assert r.status_code == 401, f"應 401 但得 {r.status_code}"


def test_protected_endpoint_with_token(seeded_client, admin_headers):
    r = seeded_client.get("/api/inventory/parts", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_register_requires_auth(client):
    """register 是受保護的（需 organization.user.read）→ 不帶 token 應 401。"""
    r = client.post("/api/auth/register", json={
        "username": "anyone", "password": "X1234567!", "employee_id": "X-001",
    })
    assert r.status_code == 401, f"應 401，得 {r.status_code}"


def test_register_duplicate_username(seeded_client, admin_headers):
    """以 superuser 帶 token 註冊重複帳號 → 應 4xx 拒絕。"""
    r = seeded_client.post("/api/auth/register", json={
        "username": "testadmin",
        "password": "AnotherPass1!",
        "employee_id": "DUP-001",
    }, headers=admin_headers)
    assert r.status_code in (400, 409, 422), f"應拒絕重複，得 {r.status_code}: {r.text}"
