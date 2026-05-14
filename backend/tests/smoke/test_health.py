"""
Smoke: /api/health
驗收：未登入就能拿到 200 + 必要欄位
"""


def test_health_returns_200(client):
    r = client.get("/api/health")
    assert r.status_code == 200


def test_health_has_required_fields(client):
    r = client.get("/api/health")
    j = r.json()
    for k in ("status", "app", "version", "db", "llm_provider", "demo_bypass"):
        assert k in j, f"missing key {k!r} in /api/health response: {j}"


def test_health_db_ok(client):
    r = client.get("/api/health")
    assert r.json()["db"] == "ok"


def test_health_version_format(client):
    r = client.get("/api/health")
    v = r.json()["version"]
    assert isinstance(v, str) and len(v) >= 3, f"weird version: {v!r}"
