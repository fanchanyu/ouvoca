"""
Smoke: 家規 (House Rules) Policy Engine (Sprint S v3.25)

對應使用者「不寫死 BOM 規則，做彈性 API + LLM 客製化」需求。

驗證：
  - PolicyRule CRUD
  - PolicyEngine evaluate (always / has_bom / field_compare / count_check)
  - WO release 改用 PolicyEngine（取代寫死的 BOM 檢查）
  - Audit log 記每次評估
"""
from __future__ import annotations


def _cleanup_custom_rules(client, headers):
    """每個 evaluate test 開頭清掉 custom trigger 規則避免互相污染。"""
    rules = client.get("/api/policies/rules?trigger=custom", headers=headers).json()
    for r in rules:
        client.delete(f"/api/policies/rules/{r['id']}", headers=headers)


# ─── Meta endpoints ─────────────────────────────────────
def test_list_triggers_public(seeded_client):
    r = seeded_client.get("/api/policies/triggers")
    assert r.status_code in (200, 401)  # 可能要登入，目前 require_permission
    # 主要驗證 endpoint 存在


def test_list_conditions(seeded_client, admin_headers):
    r = seeded_client.get("/api/policies/conditions", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "condition_types" in body
    assert "always" in body["condition_types"]
    assert "has_bom" in body["condition_types"]
    assert "field_compare" in body["condition_types"]
    assert "actions" in body
    assert "block" in body["actions"]


# ─── CRUD ────────────────────────────────────────────────
def test_create_simple_rule(seeded_client, admin_headers):
    r = seeded_client.post("/api/policies/rules", headers=admin_headers, json={
        "name": "測試規則 A",
        "trigger": "wo.release",
        "condition_type": "always",
        "action": "warn",
        "message": "這是測試提醒",
    })
    assert r.status_code == 201, r.text
    rule = r.json()
    assert rule["name"] == "測試規則 A"
    assert rule["is_active"] is True


def test_create_with_invalid_trigger_rejected(seeded_client, admin_headers):
    r = seeded_client.post("/api/policies/rules", headers=admin_headers, json={
        "name": "壞規則", "trigger": "totally.fake",
        "condition_type": "always", "action": "block", "message": "x",
    })
    assert r.status_code == 400


def test_patch_rule_toggle_active(seeded_client, admin_headers):
    # 建一條
    r = seeded_client.post("/api/policies/rules", headers=admin_headers, json={
        "name": "可關閉的規則", "trigger": "po.create",
        "condition_type": "always", "action": "warn", "message": "x",
    })
    rule_id = r.json()["id"]

    # 關掉
    r = seeded_client.patch(f"/api/policies/rules/{rule_id}", headers=admin_headers,
                            json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # 開回來
    r = seeded_client.patch(f"/api/policies/rules/{rule_id}", headers=admin_headers,
                            json={"is_active": True})
    assert r.json()["is_active"] is True


def test_delete_rule(seeded_client, admin_headers):
    r = seeded_client.post("/api/policies/rules", headers=admin_headers, json={
        "name": "刪除測試", "trigger": "so.confirm",
        "condition_type": "always", "action": "warn", "message": "x",
    })
    rid = r.json()["id"]
    r = seeded_client.delete(f"/api/policies/rules/{rid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["deleted"] is True


# ─── Seed defaults ───────────────────────────────────────
def test_seed_defaults_idempotent(seeded_client, admin_headers):
    # 第一次
    r = seeded_client.post("/api/policies/seed-defaults", headers=admin_headers)
    assert r.status_code == 200
    # 第二次（不重複）
    r = seeded_client.post("/api/policies/seed-defaults", headers=admin_headers)
    assert r.status_code == 200

    # 應該有預設規則
    r = seeded_client.get("/api/policies/rules?trigger=wo.release", headers=admin_headers)
    rules = r.json()
    assert any("做法" in rule["name"] or "Recipe" in rule["name"] for rule in rules)


# ─── PolicyEngine 直接 evaluate ─────────────────────────
def test_evaluate_field_compare(seeded_client, admin_headers):
    """測 field_compare：amount > 100k 應觸發。"""
    _cleanup_custom_rules(seeded_client, admin_headers)
    # 建一條: PO 必須 amount <= 1000（測試用，給小數字）
    seeded_client.post("/api/policies/rules", headers=admin_headers, json={
        "name": "小額 PO 限制",
        "trigger": "custom",
        "condition_type": "field_compare",
        "condition_params": {"field": "amount", "op": "lte", "value": 1000},
        "action": "block",
        "message": "PO 金額不能超過 1000",
    })

    # context.amount = 500 → 條件 (500 <= 1000) 成立 → 規則通過 → allow
    r = seeded_client.post("/api/policies/evaluate", headers=admin_headers, json={
        "trigger": "custom",
        "context": {"amount": 500},
    })
    body = r.json()
    assert body["action"] == "allow"

    # context.amount = 2000 → 條件 (2000 <= 1000) 不成立 → 觸發 block
    r = seeded_client.post("/api/policies/evaluate", headers=admin_headers, json={
        "trigger": "custom",
        "context": {"amount": 2000},
    })
    body = r.json()
    assert body["action"] == "block"
    assert "1000" in body["message"]


def test_evaluate_count_check(seeded_client, admin_headers):
    """count_check：items 至少 1 個。"""
    _cleanup_custom_rules(seeded_client, admin_headers)
    seeded_client.post("/api/policies/rules", headers=admin_headers, json={
        "name": "至少 1 項目",
        "trigger": "custom",
        "condition_type": "count_check",
        "condition_params": {"field": "items", "op": "gte", "value": 1},
        "action": "block",
        "message": "必須至少 1 個項目",
    })

    # 有 2 項 → allow
    r = seeded_client.post("/api/policies/evaluate", headers=admin_headers, json={
        "trigger": "custom", "context": {"items": ["a", "b"]},
    })
    assert r.json()["action"] == "allow"

    # 空 list → block
    r = seeded_client.post("/api/policies/evaluate", headers=admin_headers, json={
        "trigger": "custom", "context": {"items": []},
    })
    assert r.json()["action"] == "block"


def test_evaluate_warn_does_not_block(seeded_client, admin_headers):
    """action=warn 不擋，但有 message。"""
    _cleanup_custom_rules(seeded_client, admin_headers)
    seeded_client.post("/api/policies/rules", headers=admin_headers, json={
        "name": "金額大於 100 警告",
        "trigger": "custom",
        "condition_type": "field_compare",
        "condition_params": {"field": "amount", "op": "lte", "value": 100},
        "action": "warn",
        "message": "金額超過 100，請確認",
    })

    r = seeded_client.post("/api/policies/evaluate", headers=admin_headers, json={
        "trigger": "custom", "context": {"amount": 200},
    })
    body = r.json()
    assert body["action"] == "warn"
    assert "100" in body["message"]


# ─── 真實場景：WO release 走 PolicyEngine ─────────────
def test_wo_release_blocked_by_default_recipe_rule(seeded_client, admin_headers):
    """預設家規 WO release 需有做法 (Recipe)，應該 block 無 BOM 的 WO。"""
    # 確保預設規則裝好
    seeded_client.post("/api/policies/seed-defaults", headers=admin_headers)

    # 建一個產品（無 BOM）
    prod = seeded_client.post("/api/production/products", headers=admin_headers,
                              json={"product_no": "POL-NOBOM", "name": "無 BOM 產品"}).json()
    # 建 WO
    wo = seeded_client.post("/api/production/work-orders", headers=admin_headers,
                            json={"product_id": prod["id"], "ordered_qty": 10}).json()

    # Release 應該被擋
    r = seeded_client.post(f"/api/production/work-orders/{wo['id']}/release", headers=admin_headers)
    assert r.status_code == 422
    detail = r.json().get("detail", "")
    if isinstance(detail, dict):
        # exception handler 可能包成 dict
        text = str(detail)
    else:
        text = detail
    assert "做法" in text or "Recipe" in text or "bom" in text.lower()


def test_wo_release_unblocked_when_rule_disabled(seeded_client, admin_headers):
    """關掉「需做法」規則 → 同樣的 WO 可以 release（彈性的核心）。"""
    # 確保預設規則裝好
    seeded_client.post("/api/policies/seed-defaults", headers=admin_headers)

    # 找到該規則
    rules = seeded_client.get("/api/policies/rules?trigger=wo.release",
                              headers=admin_headers).json()
    recipe_rule = next((r for r in rules if "做法" in r["name"] or "Recipe" in r["name"]), None)
    assert recipe_rule is not None, "預設規則應存在"

    # 關掉
    seeded_client.patch(f"/api/policies/rules/{recipe_rule['id']}", headers=admin_headers,
                        json={"is_active": False})

    # 建產品 + WO
    prod = seeded_client.post("/api/production/products", headers=admin_headers,
                              json={"product_no": "POL-FLEX", "name": "彈性釋放產品"}).json()
    wo = seeded_client.post("/api/production/work-orders", headers=admin_headers,
                            json={"product_id": prod["id"], "ordered_qty": 5}).json()

    # 規則關了 → release 應該成功
    r = seeded_client.post(f"/api/production/work-orders/{wo['id']}/release", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "released"

    # 還原規則（避免污染其他 test）
    seeded_client.patch(f"/api/policies/rules/{recipe_rule['id']}", headers=admin_headers,
                        json={"is_active": True})


# ─── Audit log ────────────────────────────────────────
def test_audit_log_records_evaluation(seeded_client, admin_headers):
    """每次規則觸發應寫 audit log。"""
    _cleanup_custom_rules(seeded_client, admin_headers)
    # 建一條會觸發的規則
    r = seeded_client.post("/api/policies/rules", headers=admin_headers, json={
        "name": "Audit 測試規則",
        "trigger": "custom",
        "condition_type": "field_compare",
        "condition_params": {"field": "x", "op": "lte", "value": 10},
        "action": "block",
        "message": "x > 10",
    })
    rule_id = r.json()["id"]

    # 觸發
    seeded_client.post("/api/policies/evaluate", headers=admin_headers, json={
        "trigger": "custom", "context": {"x": 999},
    })

    # 查 audit
    r = seeded_client.get(f"/api/policies/audit?rule_id={rule_id}", headers=admin_headers)
    audit = r.json()
    assert len(audit) >= 1
    assert audit[0]["action_taken"] in ("blocked", "block")


def test_unauthorized_rejected(seeded_client):
    r = seeded_client.post("/api/policies/rules", json={"name": "x", "trigger": "wo.release",
                                                        "condition_type": "always", "action": "block",
                                                        "message": "x"})
    assert r.status_code == 401
