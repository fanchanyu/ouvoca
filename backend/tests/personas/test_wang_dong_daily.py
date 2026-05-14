"""
Persona test：王董的一天 — 端到端業務生命週期

這支測試模擬一個 50-100 人工廠老闆一天會走的關鍵路徑，
跑過 = 我們有資格說「能 demo」。跑不過 = 立刻 issue。

時程：
  06:30  王董問「今天狀況」      → AI 助手回應
  09:00  小陳查 M6 庫存          → 3 秒內回應
  10:30  林廠長建工單             → 200
  10:31  林廠長 release 工單      → 觸發 event
  14:00  阿玲建供應商 + 採購單   → 200
  18:00  王董看 below-safety     → 應看到 M6 警示
"""
from __future__ import annotations
import uuid
import pytest


@pytest.fixture(scope="module")
def wang_dong_token(seeded_client) -> str:
    """共用 testadmin（superuser）模擬王董。"""
    r = seeded_client.post("/api/auth/login", json={
        "username": "testadmin", "password": "TestPass123!",
    })
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(wang_dong_token) -> dict:
    return {"Authorization": f"Bearer {wang_dong_token}"}


@pytest.fixture(scope="module")
def m6_bolt(seeded_client, headers) -> dict:
    """建一個 M6 螺絲（安全庫存 1000）— 後續所有測試的基準資料。"""
    pn = f"M6-BOLT-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "part_no": pn,
        "name": "M6 不鏽鋼螺絲 / M6 SS Bolt",
        "category": "raw",
        "safety_stock": 1000,
        "unit_cost": 0.5,
    }
    r = seeded_client.post("/api/inventory/parts", json=payload, headers=headers)
    assert r.status_code in (200, 201), f"建零件失敗：{r.status_code} {r.text}"
    return r.json()


# ─── 06:30 王董問「今天狀況」 ──────────────────────────────

def test_0630_wang_dong_asks_today_status(seeded_client, headers):
    """王董透過 chat 問「今天工廠狀況」— 應在 30 秒內回應。
    沒有 LLM_API_KEY 時走 demo 模式，回 'demo' 標籤；有 key 走真實 LLM。
    """
    r = seeded_client.post(
        "/api/chat-v2",
        json={"message": "今天工廠運營狀況", "session_id": "wang-daily"},
        headers=headers,
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    for k in ("reply", "agent", "session_id"):
        assert k in data, f"chat 缺欄位 {k}"
    assert data["session_id"] == "wang-daily"


# ─── 09:00 小陳查 M6 庫存 ─────────────────────────────────

def test_0900_sales_chen_searches_m6_inventory(seeded_client, headers, m6_bolt):
    """小陳在客戶面前查 M6 — 3 秒內要拿到結果。"""
    import time
    t0 = time.time()
    r = seeded_client.get("/api/inventory/parts", headers=headers)
    dt = time.time() - t0
    assert r.status_code == 200
    assert dt < 3.0, f"查庫存超過 3 秒：{dt:.2f}s — 業務在客戶面前會冷場"

    # 確認 M6 在清單中
    found = next((p for p in r.json() if p["part_no"] == m6_bolt["part_no"]), None)
    assert found is not None, "剛建的 M6 螺絲不在清單"
    assert found["safety_stock"] == 1000


# ─── 10:30 林廠長建工單 ───────────────────────────────────

def test_1030_factory_manager_creates_work_order(seeded_client, headers, m6_bolt):
    """林廠長建一個成品 + BOM + 工單。"""
    # 1. 建成品（finished good）
    fg_pn = f"FG-{uuid.uuid4().hex[:6].upper()}"
    r = seeded_client.post("/api/inventory/parts", json={
        "part_no": fg_pn, "name": "成品 A",
        "category": "finished", "safety_stock": 0, "unit_cost": 100.0,
    }, headers=headers)
    assert r.status_code in (200, 201)
    fg_id = r.json()["id"]

    # 2. 建 Product（生產用）
    r = seeded_client.post("/api/production/products", json={
        "product_no": fg_pn, "name": "成品 A",
    }, headers=headers)
    # 200/201 ok；422 可能因 schema 差異，列出有用診斷
    assert r.status_code in (200, 201), f"建產品失敗：{r.status_code} {r.text[:200]}"
    product_id = r.json()["id"]

    # 3. 建工單
    r = seeded_client.post("/api/production/work-orders", json={
        "product_id": product_id,
        "ordered_qty": 100,
        "priority": 1,
    }, headers=headers)
    assert r.status_code in (200, 201), f"建工單失敗：{r.status_code} {r.text[:200]}"
    wo = r.json()
    assert wo["ordered_qty"] == 100
    assert wo["status"] in ("draft", "planned", "released", "DRAFT", "PLANNED")


def test_1031_wo_list_visible(seeded_client, headers):
    """工單建完，列表應看得到（Mobile dashboard 用）。"""
    r = seeded_client.get("/api/production/work-orders", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1, "至少要有剛建的工單"


# ─── 14:00 阿玲建供應商 + 採購單 ──────────────────────────

def test_1400_purchaser_creates_supplier_and_po(seeded_client, headers, m6_bolt):
    """阿玲建供應商 + 採購單補 M6 螺絲。
    Schema 對齊：SupplierCreate.code + PurchaseOrderItemCreate.ordered_qty
    """
    # 1. 建供應商
    sup_code = f"SUP-{uuid.uuid4().hex[:6].upper()}"
    r = seeded_client.post("/api/purchase/suppliers", json={
        "code": sup_code, "name": "中鋼公司", "tier": "T1",
    }, headers=headers)
    assert r.status_code in (200, 201), f"建供應商失敗：{r.status_code} {r.text[:200]}"
    supplier_id = r.json()["id"]

    # 2. 建採購單
    r = seeded_client.post("/api/purchase/orders", json={
        "supplier_id": supplier_id,
        "items": [
            {"part_id": m6_bolt["id"], "ordered_qty": 5000, "unit_price": 0.5},
        ],
    }, headers=headers)
    assert r.status_code in (200, 201), f"建 PO 失敗：{r.status_code} {r.text[:200]}"


# ─── 18:00 王董看 below-safety ────────────────────────────

def test_1800_wang_dong_checks_below_safety(seeded_client, headers, m6_bolt):
    """王董看「哪些庫存低於安全」— Mobile dashboard 主秀。
    M6 安全庫存 1000，沒有任何入庫 → 應出現在警示清單。
    """
    r = seeded_client.get("/api/inventory/below-safety", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

    # 找 M6
    m6 = next((d for d in data if d["part_no"] == m6_bolt["part_no"]), None)
    assert m6 is not None, f"M6（safety 1000, 在庫 0）應出現在警示，但 list 中沒有：{[d['part_no'] for d in data]}"
    assert m6["qty_available"] < m6["safety_stock"]
    assert m6["shortage"] > 0
