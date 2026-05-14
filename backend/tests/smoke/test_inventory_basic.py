"""
Smoke: Inventory CRUD（Mobile 主要依賴）
驗收：
1. GET /api/inventory/parts → 200，回 list
2. POST /api/inventory/parts 建零件 → 200
3. GET /api/inventory/below-safety → 200，回 list（可能空）
"""
import uuid


def test_list_parts_returns_list(seeded_client, admin_headers):
    r = seeded_client.get("/api/inventory/parts", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


def test_create_part_then_list(seeded_client, admin_headers):
    pn = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "part_no": pn,
        "name": "測試零件 Test Part",
        "category": "raw",
        "safety_stock": 100,
        "unit_cost": 12.5,
    }
    r = seeded_client.post("/api/inventory/parts", json=payload, headers=admin_headers)
    assert r.status_code in (200, 201), f"create failed: {r.status_code} {r.text}"
    created = r.json()
    assert created["part_no"] == pn

    # 確認 list 看得到
    r = seeded_client.get("/api/inventory/parts", headers=admin_headers)
    part_nos = {p["part_no"] for p in r.json()}
    assert pn in part_nos, f"剛建的 {pn} 不在清單中"


def test_below_safety_endpoint(seeded_client, admin_headers):
    """Mobile dashboard 重點依賴。"""
    r = seeded_client.get("/api/inventory/below-safety", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # 每筆若有，結構應該有這些欄位（Mobile 的 Part interface）
    for item in data:
        for k in ("part_no", "name", "qty_available", "safety_stock", "shortage"):
            assert k in item, f"below-safety item 缺欄位 {k}: {item}"


def test_part_no_uniqueness(seeded_client, admin_headers):
    """同一個 part_no 不能建兩次。"""
    pn = f"DUP-{uuid.uuid4().hex[:8].upper()}"
    payload = {"part_no": pn, "name": "Dup", "category": "raw",
               "safety_stock": 0, "unit_cost": 1.0}

    r1 = seeded_client.post("/api/inventory/parts", json=payload, headers=admin_headers)
    assert r1.status_code in (200, 201)

    r2 = seeded_client.post("/api/inventory/parts", json=payload, headers=admin_headers)
    assert r2.status_code in (400, 409, 422), \
        f"重複 part_no 應被拒，得 {r2.status_code}"
