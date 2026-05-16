"""
Smoke: CRM (Sprint I v3.15)

驗收：Lead lifecycle / Opportunity stage flow / CRM events
"""
from __future__ import annotations


def _create_customer(client, headers, code="CRM-CUST-001"):
    r = client.post("/api/sales/customers", headers=headers,
                    json={"code": code, "name": f"測試客戶 {code}"})
    assert r.status_code in (200, 201), r.text
    return r.json()


# ── Lead ──────────────────────────────────────────────────
def test_create_and_list_lead(seeded_client, admin_headers):
    r = seeded_client.post("/api/crm/leads", headers=admin_headers, json={
        "company_name": "新進公司 A", "contact_person": "王經理",
        "contact_phone": "0912-345-678", "source": "展會",
    })
    assert r.status_code == 200, r.text
    lead = r.json()
    assert lead["company_name"] == "新進公司 A"
    assert lead["status"] == "new"

    # list
    r = seeded_client.get("/api/crm/leads", headers=admin_headers)
    assert r.status_code == 200
    assert any(l["id"] == lead["id"] for l in r.json())


def test_convert_lead_to_customer(seeded_client, admin_headers):
    r = seeded_client.post("/api/crm/leads", headers=admin_headers, json={
        "company_name": "待轉公司 B",
    })
    lead = r.json()

    r = seeded_client.post(
        f"/api/crm/leads/{lead['id']}/convert", headers=admin_headers,
        json={"customer": {"code": "CONVERTED-001", "name": "已轉客戶 B"}},
    )
    assert r.status_code == 200, r.text
    customer = r.json()
    assert customer["code"] == "CONVERTED-001"


# ── Opportunity ───────────────────────────────────────────
def test_create_opportunity_and_move_stage(seeded_client, admin_headers):
    customer = _create_customer(seeded_client, admin_headers, "CRM-CUST-OPP")

    r = seeded_client.post("/api/crm/opportunities", headers=admin_headers, json={
        "customer_id": customer["id"],
        "name": "Q3 大訂單機會",
        "amount": 500000, "probability": 60,
    })
    assert r.status_code == 200, r.text
    opp = r.json()
    assert opp["amount"] == 500000
    assert opp["stage"] == "prospect"

    # 階段推進
    r = seeded_client.post(
        f"/api/crm/opportunities/{opp['id']}/stage", headers=admin_headers,
        json={"stage": "proposal"},
    )
    assert r.status_code == 200
    assert r.json()["stage"] == "proposal"


def test_list_opportunities_filter_by_stage(seeded_client, admin_headers):
    r = seeded_client.get("/api/crm/opportunities?stage=prospect", headers=admin_headers)
    assert r.status_code == 200
    for o in r.json():
        assert o["stage"] == "prospect"


# ── CrmEvent ──────────────────────────────────────────────
def test_create_and_list_crm_event(seeded_client, admin_headers):
    customer = _create_customer(seeded_client, admin_headers, "CRM-CUST-EVT")

    r = seeded_client.post("/api/crm/events", headers=admin_headers, json={
        "customer_id": customer["id"],
        "event_type": "call",
        "subject": "電話拜訪：詢問報價",
        "description": "客戶想要 100 個 M6 螺絲報價，明天回",
    })
    assert r.status_code == 200, r.text
    event = r.json()
    assert event["subject"] == "電話拜訪：詢問報價"

    # 用 customer_id filter
    r = seeded_client.get(
        f"/api/crm/events?customer_id={customer['id']}", headers=admin_headers,
    )
    assert r.status_code == 200
    events = r.json()
    assert any(e["id"] == event["id"] for e in events)


def test_unauthorized_crm_access_rejected(seeded_client):
    r = seeded_client.get("/api/crm/leads")
    assert r.status_code == 401
