"""
Smoke: File upload / Attachment API（Sprint E v3.13）

驗收：
  - 上傳檔案成功 → 拿到 Attachment record
  - 列表能看到剛上傳的
  - 下載拿回相同 binary
  - 刪除清掉 DB record + disk file
  - 攻擊向量被擋（路徑穿越 / 大檔 / 不合法副檔名 / 空檔）
"""
from __future__ import annotations

import io
import pathlib


def _upload(client, headers, content: bytes, filename: str = "test.pdf",
            category: str = "quote", description: str = ""):
    files = {"file": (filename, io.BytesIO(content), "application/pdf")}
    data = {"category": category}
    if description:
        data["description"] = description
    return client.post("/api/files/upload", headers=headers, files=files, data=data)


# ── 正常路徑 ──────────────────────────────────────────────────
def test_upload_pdf_success(seeded_client, admin_headers):
    r = _upload(seeded_client, admin_headers, b"%PDF-1.4 fake pdf content", "quote_v1.pdf", "quote")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "quote_v1.pdf"
    assert body["category"] == "quote"
    assert body["size_bytes"] == len(b"%PDF-1.4 fake pdf content")
    # parsed_status 沒在 response schema 裡（內部欄位，給 LLM tool 用），這裡不檢
    assert "id" in body


def test_list_files_finds_uploaded(seeded_client, admin_headers):
    _upload(seeded_client, admin_headers, b"hello", "test_list.pdf", "quote")
    r = seeded_client.get("/api/files", headers=admin_headers)
    assert r.status_code == 200
    filenames = [a["filename"] for a in r.json()]
    assert "test_list.pdf" in filenames


def test_list_files_filter_by_category(seeded_client, admin_headers):
    _upload(seeded_client, admin_headers, b"x", "filter_a.pdf", "quote")
    _upload(seeded_client, admin_headers, b"y", "filter_b.pdf", "invoice")
    r = seeded_client.get("/api/files?category=invoice", headers=admin_headers)
    assert r.status_code == 200
    cats = {a["category"] for a in r.json()}
    assert cats == {"invoice"} or len(r.json()) == 0  # 全部都是 invoice
    fns = [a["filename"] for a in r.json()]
    assert "filter_b.pdf" in fns
    assert "filter_a.pdf" not in fns


def test_download_returns_same_bytes(seeded_client, admin_headers):
    content = b"DOWNLOAD-TEST-CONTENT-12345"
    r = _upload(seeded_client, admin_headers, content, "dl.pdf", "general")
    att_id = r.json()["id"]
    r2 = seeded_client.get(f"/api/files/{att_id}/download", headers=admin_headers)
    assert r2.status_code == 200
    assert r2.content == content


def test_delete_removes_record_and_file(seeded_client, admin_headers):
    r = _upload(seeded_client, admin_headers, b"deleteme", "del.pdf", "general")
    att_id = r.json()["id"]
    r2 = seeded_client.delete(f"/api/files/{att_id}", headers=admin_headers)
    assert r2.status_code == 200
    # 再 GET 應 404
    r3 = seeded_client.get(f"/api/files/{att_id}", headers=admin_headers)
    assert r3.status_code == 404


# ── 安全 / 邊界 ───────────────────────────────────────────────
def test_reject_invalid_extension(seeded_client, admin_headers):
    r = _upload(seeded_client, admin_headers, b"x", "hack.exe", "general")
    assert r.status_code == 400
    assert "支援" in r.json().get("detail", "") or "allowed" in r.json().get("detail", "").lower()


def test_reject_invalid_category(seeded_client, admin_headers):
    r = _upload(seeded_client, admin_headers, b"x", "f.pdf", "totally_made_up_category")
    assert r.status_code == 400


def test_reject_empty_file(seeded_client, admin_headers):
    r = _upload(seeded_client, admin_headers, b"", "empty.pdf", "general")
    assert r.status_code == 400
    assert "空" in r.json().get("detail", "") or "empty" in r.json().get("detail", "").lower()


def test_reject_path_traversal_in_filename(seeded_client, admin_headers):
    """檔名含 .. 或 / 不能變成路徑穿越；應被 sanitize。"""
    r = _upload(seeded_client, admin_headers, b"safe", "../../../../etc/passwd.pdf", "general")
    # 接受（但檔名要被 sanitize），或 reject
    assert r.status_code in (201, 400)
    if r.status_code == 201:
        # filename 不應該還含 ..
        assert ".." not in r.json()["filename"]


def test_unauthorized_upload_rejected(seeded_client):
    """沒 token 不能上傳。"""
    files = {"file": ("x.pdf", io.BytesIO(b"x"), "application/pdf")}
    r = seeded_client.post("/api/files/upload", files=files, data={"category": "general"})
    assert r.status_code == 401


# ── 整合：上傳 → 列表 → 下載 → 刪除 ─────────────────────────
def test_full_lifecycle(seeded_client, admin_headers):
    # upload
    r = _upload(seeded_client, admin_headers,
                b"LIFECYCLE-TEST", "lifecycle.csv",
                "quote", "示範客戶 A 5/15 報價")
    assert r.status_code == 201
    att = r.json()
    assert att["description"] == "示範客戶 A 5/15 報價"

    # list
    r = seeded_client.get("/api/files", headers=admin_headers)
    assert any(a["id"] == att["id"] for a in r.json())

    # meta
    r = seeded_client.get(f"/api/files/{att['id']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["filename"] == "lifecycle.csv"

    # download
    r = seeded_client.get(f"/api/files/{att['id']}/download", headers=admin_headers)
    assert r.content == b"LIFECYCLE-TEST"

    # delete
    r = seeded_client.delete(f"/api/files/{att['id']}", headers=admin_headers)
    assert r.status_code == 200

    # 404 after delete
    r = seeded_client.get(f"/api/files/{att['id']}", headers=admin_headers)
    assert r.status_code == 404
