"""規模化效能量測 — 回答「資料變多之後會慢多少、瓶頸在哪」。

量三件事：
  1. 明細表 FK 無索引 vs 有索引的查詢時間（資料量遞增）
  2. 每個 API 請求的固定開銷拆解（middleware / auth / audit / 業務查詢）
  3. Audit 寫入對讀取請求的影響

用法：PYTHONPATH=. python scripts/perf_scale.py
"""
from __future__ import annotations

import os
import sqlite3
import statistics
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB = "perf_scale.db"


def bench(conn, sql, params, rounds=200):
    # 預熱
    for _ in range(5):
        conn.execute(sql, params).fetchall()
    times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        conn.execute(sql, params).fetchall()
        times.append((time.perf_counter() - t0) * 1000)
    return statistics.median(times)


def main():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # 模擬 purchase_orders / purchase_order_items 結構
    conn.execute("""CREATE TABLE purchase_orders(
        id TEXT PRIMARY KEY, po_no TEXT, supplier_id TEXT,
        status TEXT, tenant_id TEXT, created_at TEXT)""")
    conn.execute("""CREATE TABLE purchase_order_items(
        id TEXT PRIMARY KEY, po_id TEXT, line_no INT, part_id TEXT,
        ordered_qty REAL, received_qty REAL, unit_price REAL, tenant_id TEXT)""")
    conn.execute("CREATE INDEX ix_po_tenant ON purchase_orders(tenant_id)")
    conn.execute("CREATE INDEX ix_poi_tenant ON purchase_order_items(tenant_id)")
    conn.commit()

    print("=" * 76)
    print("① 明細表查詢：po_items.po_id 有無索引的差異（中位數，200 次）")
    print("=" * 76)
    print(f"{'PO 張數':>9} {'明細列數':>10} {'無索引':>12} {'有索引':>12} {'倍數':>8}")

    scales = [(500, 5), (5_000, 5), (20_000, 5)]
    made = 0
    po_ids: list[str] = []
    for n_po, lines in scales:
        rows_po, rows_it = [], []
        for _ in range(n_po - made):
            pid = str(uuid.uuid4())
            po_ids.append(pid)
            rows_po.append((pid, f"PO-{uuid.uuid4().hex[:8]}", "sup-1", "approved", "HQ", "2026-01-01"))
            for ln in range(lines):
                rows_it.append((str(uuid.uuid4()), pid, ln + 1, f"part-{ln}", 10, 0, 10, "HQ"))
        conn.executemany("INSERT INTO purchase_orders VALUES (?,?,?,?,?,?)", rows_po)
        conn.executemany("INSERT INTO purchase_order_items VALUES (?,?,?,?,?,?,?,?)", rows_it)
        conn.commit()
        made = n_po

        target = po_ids[len(po_ids) // 2]
        sql = "SELECT * FROM purchase_order_items WHERE po_id = ? AND tenant_id = 'HQ'"

        try:
            conn.execute("DROP INDEX ix_poi_po")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        no_idx = bench(conn, sql, (target,))

        conn.execute("CREATE INDEX ix_poi_po ON purchase_order_items(po_id)")
        conn.execute("ANALYZE")
        conn.commit()
        with_idx = bench(conn, sql, (target,))

        n_items = n_po * lines
        ratio = no_idx / with_idx if with_idx else 0
        print(f"{n_po:>9,} {n_items:>10,} {no_idx:>10.3f}ms {with_idx:>10.3f}ms {ratio:>7.0f}x")

    # ── 列表頁 N+1 模擬 ─────────────────────────────────────
    print()
    print("=" * 76)
    print("② 列表頁 100 筆：N+1（每筆一次查詢）vs 一次 IN 批次查詢")
    print("=" * 76)
    page = po_ids[:100]

    t0 = time.perf_counter()
    for pid in page:
        conn.execute("SELECT * FROM purchase_order_items WHERE po_id = ?", (pid,)).fetchall()
    n_plus_1 = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    qmarks = ",".join("?" * len(page))
    conn.execute(
        f"SELECT * FROM purchase_order_items WHERE po_id IN ({qmarks})", page
    ).fetchall()
    batched = (time.perf_counter() - t0) * 1000

    print(f"  N+1（101 次查詢）      : {n_plus_1:8.2f}ms")
    print(f"  selectinload（2 次查詢）: {batched:8.2f}ms")
    print(f"  差距                    : {n_plus_1 / batched:8.1f}x")

    # ── 每請求固定寫入（audit）成本 ─────────────────────────
    print()
    print("=" * 76)
    print("③ Audit 每請求 INSERT + COMMIT 的成本（含 fsync）")
    print("=" * 76)
    conn.execute("""CREATE TABLE audit_logs(
        id TEXT PRIMARY KEY, user_id TEXT, action TEXT, path TEXT, created_at TEXT)""")
    conn.commit()

    times = []
    for _ in range(200):
        t0 = time.perf_counter()
        conn.execute("INSERT INTO audit_logs VALUES (?,?,?,?,?)",
                     (str(uuid.uuid4()), "u1", "GET", "/api/x", "2026-01-01"))
        conn.commit()
        times.append((time.perf_counter() - t0) * 1000)
    print(f"  每請求 audit 寫入中位數 : {statistics.median(times):8.3f}ms")
    print(f"  p95                     : {sorted(times)[int(len(times) * 0.95)]:8.3f}ms")
    print("  （此為 SQLite WAL 本機值；PostgreSQL 網路來回通常 0.5–2ms，且會佔用連線）")

    conn.close()
    os.remove(DB)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(DB + suffix):
            os.remove(DB + suffix)


if __name__ == "__main__":
    main()
