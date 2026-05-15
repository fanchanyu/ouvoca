"""
Integration: MESH 跨廠真實聚合測試

跑 1 HQ (in-process TestClient) + 2 factory_node (subprocess)，
驗證 HQ /api/factory/aggregate 真的拿到合計數字、且廠別資料不混淆。

這支測試「過了」= 我們有資格說 MESH 真實可用，不再是 stub。
"""
from __future__ import annotations
import os
import sys
import time
import socket
import subprocess
import shutil
import tempfile
from pathlib import Path

import pytest
import httpx


# ─── helpers ───────────────────────────────────────────────
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for(url: str, timeout: float = 15.0) -> bool:
    """polling 直到 url 回 200 或超時。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = httpx.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def two_factories(tmp_path_factory):
    """起兩個 factory_node subprocess，回傳 (info_a, info_b)。
    teardown 時殺掉 process + 清 DB。
    """
    backend_dir = Path(__file__).resolve().parents[2]
    factory_script = backend_dir / "factory_node.py"
    assert factory_script.exists(), f"找不到 {factory_script}"

    tmpdir = tmp_path_factory.mktemp("mesh")

    factories = []
    for i, (fid, fname) in enumerate([("ftest-a", "測試主廠"), ("ftest-b", "測試分廠")]):
        port = _free_port()
        db_path = tmpdir / f"{fid}.db"
        env = {
            **os.environ,
            "FACTORY_ID": fid,
            "FACTORY_NAME": fname,
            "PORT": str(port),
            "FACTORY_DB": str(db_path),
            "HQ_URL": "http://127.0.0.1:1",  # 故意指錯，整合測試自己手動 register
        }
        proc = subprocess.Popen(
            [sys.executable, str(factory_script)],
            env=env, cwd=str(backend_dir),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        url = f"http://127.0.0.1:{port}"
        assert _wait_for(f"{url}/api/factory/health"), \
            f"{fid} 起不來: stderr={proc.stderr.read(2000).decode(errors='ignore') if proc.stderr else ''}"
        factories.append({
            "factory_id": fid, "name": fname, "port": port,
            "url": url, "proc": proc, "db": db_path,
        })

    yield factories

    # teardown
    for f in factories:
        try:
            f["proc"].terminate()
            f["proc"].wait(timeout=5)
        except Exception:
            f["proc"].kill()


# ─── tests ─────────────────────────────────────────────────
def test_factory_health_real_db(two_factories):
    """factory_node 起來且有真實 SQLite。"""
    for f in two_factories:
        r = httpx.get(f"{f['url']}/api/factory/health")
        assert r.status_code == 200
        j = r.json()
        assert j["factory_id"] == f["factory_id"]
        assert j["status"] == "online"
        assert j["local_inventory_count"] == 0  # 還沒寫入


def test_factory_insert_then_aggregate_locally(two_factories):
    """每廠各寫不同數量，本機查能拿到聚合數字。"""
    a, b = two_factories
    # 主廠 M6 = 3000
    httpx.post(f"{a['url']}/api/factory/inventory/upsert",
               json={"part_no": "M6-BOLT", "qty_on_hand": 3000})
    # 主廠 M8 = 500
    httpx.post(f"{a['url']}/api/factory/inventory/upsert",
               json={"part_no": "M8-BOLT", "qty_on_hand": 500})
    # 分廠 M6 = 1500
    httpx.post(f"{b['url']}/api/factory/inventory/upsert",
               json={"part_no": "M6-BOLT", "qty_on_hand": 1500})

    # 各自查
    ra = httpx.get(f"{a['url']}/api/factory/mesh/query",
                   params={"domain": "inventory", "part_no": "M6-BOLT"})
    assert ra.json()["results"]["total"] == 3000, ra.text

    rb = httpx.get(f"{b['url']}/api/factory/mesh/query",
                   params={"domain": "inventory", "part_no": "M6-BOLT"})
    assert rb.json()["results"]["total"] == 1500, rb.text


def test_hq_aggregate_across_factories(two_factories, client):
    """HQ 註冊兩廠後，呼叫 /aggregate 應拿到合計 4500（不含 M8）。
    這是 MESH 的核心承諾：跨廠聚合。
    """
    # 清舊 registry（測試之間污染防線）
    client.post("/api/factory/_reset")

    # 註冊兩廠到 HQ
    for f in two_factories:
        r = client.post("/api/factory/register", json={
            "factory_id": f["factory_id"],
            "name": f["name"],
            "endpoint": f["url"],
        })
        assert r.status_code == 200, r.text

    # 列表確認
    r = client.get("/api/factory/list")
    assert r.status_code == 200
    ids = {item["factory_id"] for item in r.json()}
    assert {"ftest-a", "ftest-b"}.issubset(ids)

    # 跨廠聚合 M6
    r = client.post("/api/factory/aggregate",
                    params={"domain": "inventory", "part_no": "M6-BOLT"})
    assert r.status_code == 200, r.text
    data = r.json()

    # 主廠 3000 + 分廠 1500 = 4500
    assert data["total"] == 4500, f"聚合錯誤：期望 4500，實得 {data['total']}, per_factory={data['per_factory']}"
    assert data["factories_queried"] == 2
    assert data["factories_responded"] == 2
    assert data["per_factory"]["ftest-a"] == 3000
    assert data["per_factory"]["ftest-b"] == 1500
    assert data["elapsed_ms"] < 10000, f"聚合太慢：{data['elapsed_ms']}ms"


def test_hq_aggregate_handles_offline_factory(two_factories, client):
    """若某廠斷線，HQ 應該回 partial 結果（不是整個 fail）。"""
    client.post("/api/factory/_reset")

    a, b = two_factories
    # 註冊兩廠，但把 b 的 endpoint 改成壞掉的
    client.post("/api/factory/register", json={
        "factory_id": a["factory_id"], "name": a["name"], "endpoint": a["url"],
    })
    client.post("/api/factory/register", json={
        "factory_id": b["factory_id"], "name": b["name"],
        "endpoint": "http://127.0.0.1:1",  # 故意壞掉的 port
    })

    r = client.post("/api/factory/aggregate",
                    params={"domain": "inventory", "part_no": "M6-BOLT", "timeout_seconds": 1.0})
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["factories_queried"] == 2
    assert data["factories_responded"] == 1, "應該只有 a 回應"
    assert data["per_factory"][a["factory_id"]] == 3000
    assert data["per_factory"][b["factory_id"]] is None
    # 總計只算響應的廠
    assert data["total"] == 3000


def test_hq_aggregate_does_not_leak_raw_data(two_factories, client):
    """資料主權核心驗證：HQ 從 /aggregate 拿不到任何原始 row。"""
    client.post("/api/factory/_reset")
    for f in two_factories:
        client.post("/api/factory/register", json={
            "factory_id": f["factory_id"], "name": f["name"], "endpoint": f["url"],
        })

    r = client.post("/api/factory/aggregate",
                    params={"domain": "inventory", "part_no": "M6-BOLT"})
    body = r.text.lower()

    # 不可以包含這些「原始資料的字眼」
    for forbidden in ("created_at", "updated_at", "qty_available", "items", "rows"):
        assert forbidden not in body, \
            f"aggregate 不應出現 {forbidden!r}（疑似原始 row 外流）：{body[:300]}"
