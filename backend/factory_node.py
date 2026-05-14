"""Factory MESH node — lightweight local FastAPI service.

每個 factory 跑這支 process，持有「本廠的」SQLite，HQ 透過
/api/factory/mesh/query 拉聚合數字。**原始 row 不會離開本廠**。

啟動：
    FACTORY_ID=a FACTORY_NAME='主廠' PORT=8001 \
        HQ_URL=http://localhost:8000 python factory_node.py

設計：
- 用 SQLite 模擬「廠級本地 DB」（生產可換 PostgreSQL）
- 啟動時自動 register 給 HQ（fire-and-forget，HQ 沒起也不擋本廠運行）
- /mesh/query?agg=sum 只回聚合數字（防資料外流到 HQ）
"""
from __future__ import annotations
import os
import asyncio
import sqlite3
import uuid
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


FACTORY_ID = os.getenv("FACTORY_ID", "factory-a")
FACTORY_NAME = os.getenv("FACTORY_NAME", "Factory A")
HQ_URL = os.getenv("HQ_URL", "http://localhost:8000")
PORT = int(os.getenv("PORT", 8001))
DB_PATH = Path(os.getenv("FACTORY_DB", f"./factory_{FACTORY_ID}.db"))


# ─── DB 層（簡單同步 sqlite3，避免重型 dependency）────────
@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """建表（idempotent）。"""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS local_inventory (
                id TEXT PRIMARY KEY,
                part_no TEXT NOT NULL,
                qty_on_hand REAL NOT NULL DEFAULT 0,
                qty_available REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_inv_part_no ON local_inventory(part_no);
        """)
        conn.commit()


def upsert_inventory(part_no: str, qty_on_hand: float, qty_available: float | None = None):
    if qty_available is None:
        qty_available = qty_on_hand
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM local_inventory WHERE part_no = ?", (part_no,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE local_inventory SET qty_on_hand=?, qty_available=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (qty_on_hand, qty_available, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO local_inventory (id, part_no, qty_on_hand, qty_available) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), part_no, qty_on_hand, qty_available),
            )
        conn.commit()


# ─── App lifespan ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(_register_with_hq())  # fire-and-forget
    yield


async def _register_with_hq():
    """重試最多 10 次。HQ 沒起來不擋本廠。"""
    payload = {
        "factory_id": FACTORY_ID,
        "name": FACTORY_NAME,
        "endpoint": f"http://127.0.0.1:{PORT}",
    }
    for attempt in range(10):
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.post(f"{HQ_URL}/api/factory/register", json=payload)
            if r.status_code == 200:
                return
        except Exception:
            pass
        await asyncio.sleep(3 * (attempt + 1))


app = FastAPI(
    title=f"LLM-ERP Factory Node ({FACTORY_ID})",
    version="2.0.0",
    lifespan=lifespan,
)


# ─── Endpoints ─────────────────────────────────────────────
@app.get("/api/factory/health")
async def health():
    with get_conn() as conn:
        row_count = conn.execute("SELECT COUNT(*) AS c FROM local_inventory").fetchone()["c"]
    return {
        "factory_id": FACTORY_ID,
        "name": FACTORY_NAME,
        "status": "online",
        "local_inventory_count": row_count,
        "db_path": str(DB_PATH.resolve()),
    }


class UpsertInventoryRequest(BaseModel):
    part_no: str
    qty_on_hand: float
    qty_available: Optional[float] = None


@app.post("/api/factory/inventory/upsert")
async def upsert(req: UpsertInventoryRequest):
    """測試/管理：寫入本廠庫存（生產通常從 ERP 同步或本地操作）。"""
    upsert_inventory(req.part_no, req.qty_on_hand, req.qty_available)
    return {"detail": "ok"}


@app.get("/api/factory/inventory")
async def local_inventory(part_no: Optional[str] = None):
    """**原始 row** — 僅供本廠或同 VPN 用，不會給 HQ。"""
    with get_conn() as conn:
        if part_no:
            rows = conn.execute(
                "SELECT * FROM local_inventory WHERE part_no = ?", (part_no,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM local_inventory").fetchall()
    return {
        "factory_id": FACTORY_ID,
        "inventory": [dict(r) for r in rows],
    }


@app.get("/api/factory/mesh/query")
async def mesh_query(
    domain: str = "inventory",
    part_no: Optional[str] = None,
    agg: str = "sum",
):
    """
    HQ 拉聚合用的 endpoint。**只回聚合數字**，不回原始 row。

    - domain=inventory: 加總 qty_on_hand
    - 其他 domain 目前未實作
    """
    if domain != "inventory":
        raise HTTPException(400, f"不支援的 domain: {domain}")
    if agg not in ("sum", "count"):
        raise HTTPException(400, f"不支援的 agg: {agg}")

    with get_conn() as conn:
        if part_no:
            sql = "SELECT COALESCE(SUM(qty_on_hand), 0) AS total, COUNT(*) AS cnt FROM local_inventory WHERE part_no = ?"
            row = conn.execute(sql, (part_no,)).fetchone()
        else:
            sql = "SELECT COALESCE(SUM(qty_on_hand), 0) AS total, COUNT(*) AS cnt FROM local_inventory"
            row = conn.execute(sql).fetchone()

    total = float(row["total"])
    count = int(row["cnt"])

    return {
        "factory_id": FACTORY_ID,
        "domain": domain,
        "query": {"part_no": part_no, "agg": agg},
        "results": {
            "total": total if agg == "sum" else count,
            "count": count,
            # ⚠️ 重點：永遠不放原始 items
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("factory_node:app", host="0.0.0.0", port=PORT)
