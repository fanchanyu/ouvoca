"""
RequestID middleware smoke tests:
- 沒帶 → 自動生成
- 帶了 → 沿用
- response header 一定有
"""
import uuid


def test_request_id_auto_generated(client):
    r = client.get("/api/health")
    rid = r.headers.get("X-Request-ID")
    assert rid, "response 一定要有 X-Request-ID"
    # 應為 UUID 格式
    uuid.UUID(rid)


def test_request_id_passed_through(client):
    given = "my-correlation-id-12345"
    r = client.get("/api/health", headers={"X-Request-ID": given})
    assert r.headers.get("X-Request-ID") == given


def test_request_id_different_per_request(client):
    r1 = client.get("/api/health")
    r2 = client.get("/api/health")
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"], \
        "兩次請求應有不同 request_id"
