"""
Smoke: /api/analytics/* — 6 個 KPI endpoint 都要能跑。
覆蓋：dso / inventory-turn / gross-margin / oee / purchase-concentration / ai-cost / summary
"""
import pytest


KPI_ENDPOINTS = [
    "/api/analytics/dso",
    "/api/analytics/inventory-turn",
    "/api/analytics/gross-margin",
    "/api/analytics/oee",
    "/api/analytics/purchase-concentration",
    "/api/analytics/ai-cost",
    "/api/analytics/summary",
]


@pytest.mark.parametrize("path", KPI_ENDPOINTS)
def test_analytics_endpoint_responds(path, seeded_client, admin_headers):
    """每個 KPI endpoint 都要回 200 + 有 metric 名稱 + generated_at 時戳。"""
    r = seeded_client.get(path, headers=admin_headers)
    assert r.status_code == 200, f"{path} → {r.status_code} {r.text[:200]}"
    j = r.json()
    assert "metric" in j, f"{path} 缺 metric: {j}"
    assert "generated_at" in j, f"{path} 缺 generated_at"


def test_analytics_dso_structure(seeded_client, admin_headers):
    r = seeded_client.get("/api/analytics/dso?period_days=30", headers=admin_headers)
    j = r.json()
    assert j["metric"] == "dso"
    assert j["unit"] == "days"
    assert "breakdown" in j
    for k in ("ar_outstanding", "sales_in_period", "period_days"):
        assert k in j["breakdown"], f"DSO breakdown 缺 {k}"


def test_analytics_summary_includes_all_kpis(seeded_client, admin_headers):
    r = seeded_client.get("/api/analytics/summary", headers=admin_headers)
    j = r.json()
    assert "kpis" in j
    expected = {"dso", "inventory_turn", "gross_margin", "oee",
                "purchase_concentration", "ai_cost"}
    actual = set(j["kpis"].keys())
    missing = expected - actual
    assert not missing, f"summary 缺 KPI: {missing}"


def test_analytics_requires_auth(client):
    """analytics 受 RBAC 保護，沒 token 應 401。"""
    r = client.get("/api/analytics/dso")
    assert r.status_code == 401
