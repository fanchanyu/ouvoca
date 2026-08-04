"""DB 效能探針 — 量測每個請求的 query 數量、耗時分佈、索引覆蓋率。

用法：PYTHONPATH=. python scripts/perf_probe.py
（唯讀量測，不改資料；使用獨立的 perf_probe.db）
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from collections import Counter
from datetime import datetime

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./perf_probe.db")
os.environ.setdefault("JWT_SECRET", "perf-probe-secret-" + "x" * 48)
os.environ.setdefault("DEBUG", "true")   # 繞過 production 的 SQLite 禁令
os.environ.setdefault("LOG_LEVEL", "ERROR")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import event  # noqa: E402


# ── SQL 收集器 ────────────────────────────────────────────────
class SqlRecorder:
    def __init__(self):
        self.statements: list[tuple[str, float]] = []
        self.enabled = False
        self._t0 = 0.0

    def install(self, engine):
        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def _before(conn, cursor, statement, params, context, executemany):
            self._t0 = time.perf_counter()

        @event.listens_for(engine.sync_engine, "after_cursor_execute")
        def _after(conn, cursor, statement, params, context, executemany):
            if self.enabled:
                self.statements.append((statement, time.perf_counter() - self._t0))

    def reset(self):
        self.statements.clear()

    @property
    def count(self):
        return len(self.statements)

    @property
    def total_ms(self):
        return sum(d for _, d in self.statements) * 1000

    def kinds(self):
        c = Counter()
        for s, _ in self.statements:
            head = s.strip().split()[0].upper()
            if head == "SELECT":
                # 抓 FROM 後的表名
                parts = s.replace("\n", " ").split()
                tbl = "?"
                for i, p in enumerate(parts):
                    if p.upper() == "FROM" and i + 1 < len(parts):
                        tbl = parts[i + 1]
                        break
                c[f"SELECT {tbl}"] += 1
            else:
                c[head] += 1
        return c


REC = SqlRecorder()


def main():
    from fastapi.testclient import TestClient

    from app.database import AsyncSessionLocal, engine
    from app.main import app
    from app.models.organization import Department, Employee, User
    from app.services.auth import hash_password

    # DEBUG=true 會開 SQL echo，會嚴重扭曲計時 → 關掉
    engine.echo = False
    engine.sync_engine.echo = False
    import logging as _lg
    _lg.getLogger("sqlalchemy.engine").setLevel(_lg.WARNING)

    REC.install(engine)

    import anyio

    async def seed():
        from app.core.tenant_context import set_current_tenant
        from app.models.inventory import Inventory, Part
        from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
        set_current_tenant("HQ")
        async with AsyncSessionLocal() as s:
            d = Department(id=str(uuid.uuid4()), code="PF", name="perf")
            s.add(d)
            await s.flush()
            e = Employee(id=str(uuid.uuid4()), employee_no="PF-1", name="perf",
                         email="perf@t.local", department_id=d.id, hire_date=datetime.utcnow())
            s.add(e)
            await s.flush()
            s.add(User(id=str(uuid.uuid4()), username="perfuser",
                       hashed_password=hash_password("Pw123456!"),
                       employee_id=e.id, is_superuser=True, is_active=True))
            await s.commit()

            sup = Supplier(id=str(uuid.uuid4()), code="PF-S", name="perf supplier",
                           tier="T2", is_approved=True)
            s.add(sup)
            await s.commit()
            # 200 料件 + 庫存
            parts = []
            for i in range(200):
                p = Part(id=str(uuid.uuid4()), part_no=f"PF-{i:04d}", name=f"料件{i}",
                         category="component", unit_cost=10)
                parts.append(p)
            s.add_all(parts)
            await s.commit()
            s.add_all([Inventory(id=str(uuid.uuid4()), part_id=p.id, qty_on_hand=100,
                                 qty_available=100) for p in parts])
            await s.commit()
            # 100 張 PO，每張 5 行
            pos = []
            for i in range(100):
                po = PurchaseOrder(id=str(uuid.uuid4()), po_no=f"PF-PO-{i:04d}",
                                   supplier_id=sup.id, status="approved", total_amount=500)
                pos.append(po)
            s.add_all(pos)
            await s.commit()
            items = []
            for po in pos:
                for ln in range(5):
                    items.append(PurchaseOrderItem(
                        id=str(uuid.uuid4()), po_id=po.id, line_no=ln + 1,
                        part_id=parts[ln].id, ordered_qty=10, received_qty=0,
                        unit_price=10, line_total=100))
            s.add_all(items)
            await s.commit()
            return pos[0].id

    with TestClient(app) as c:
        po_id = anyio.run(seed)

        tok = c.post("/api/auth/login",
                     json={"username": "perfuser", "password": "Pw123456!"}).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}

        targets = [
            ("GET  /api/health", lambda: c.get("/api/health")),
            ("GET  /api/inventory/parts", lambda: c.get("/api/inventory/parts", headers=h)),
            ("GET  /api/purchase/orders", lambda: c.get("/api/purchase/orders", headers=h)),
            (f"GET  /api/purchase/orders/{{id}}", lambda: c.get(f"/api/purchase/orders/{po_id}", headers=h)),
            ("GET  /api/sales/orders", lambda: c.get("/api/sales/orders", headers=h)),
            ("GET  /api/permission/me/effective", lambda: c.get("/api/permission/me/effective", headers=h)),
        ]

        print("=" * 78)
        print(f"{'endpoint':38} {'HTTP':5} {'wall':>8} {'SQL':>5} {'SQLms':>8}")
        print("=" * 78)
        detail = {}
        for name, fn in targets:
            fn()  # warm-up（避免 statement compile 一次性成本）
            REC.reset()
            REC.enabled = True
            t0 = time.perf_counter()
            r = fn()
            wall = (time.perf_counter() - t0) * 1000
            REC.enabled = False
            print(f"{name:38} {r.status_code:5} {wall:7.1f}ms {REC.count:5} {REC.total_ms:7.1f}ms")
            detail[name] = REC.kinds()

        print()
        for name, kinds in detail.items():
            top = [f"{k}×{v}" for k, v in kinds.most_common(6)]
            print(f"{name:38} {', '.join(top)}")

    # ── 索引覆蓋率 ───────────────────────────────────────────
    print()
    print("=" * 78)
    print("外鍵索引覆蓋率（PostgreSQL 不會自動為 FK 建索引）")
    print("=" * 78)
    from app.core.base import Base
    import app.models  # noqa: F401

    total_fk = 0
    unindexed: list[str] = []
    for tname, table in Base.metadata.tables.items():
        indexed_cols = set()
        for idx in table.indexes:
            cols = list(idx.columns)
            if cols:
                indexed_cols.add(cols[0].name)   # 只有前綴欄位可用
        for col in table.columns:
            if not col.foreign_keys:
                continue
            total_fk += 1
            if col.name in indexed_cols or col.index or col.primary_key or col.unique:
                continue
            unindexed.append(f"{tname}.{col.name}")

    print(f"FK 欄位總數 : {total_fk}")
    print(f"已建索引    : {total_fk - len(unindexed)}")
    print(f"缺索引      : {len(unindexed)}  ({len(unindexed) * 100 // max(total_fk, 1)}%)")
    print()
    print("最可能痛的（明細表 → 母單）：")
    hot = [u for u in unindexed if any(
        k in u for k in ("_items.", "_lines.", ".po_id", ".so_id", ".wo_id", ".rfq_id",
                         ".quote_id", ".invoice_id", ".part_id", ".product_id",
                         ".journal_entry_id", ".account_id", ".customer_id", ".supplier_id"))]
    for u in sorted(hot)[:40]:
        print("   -", u)
    if len(hot) > 40:
        print(f"   … 另外 {len(hot) - 40} 個")


if __name__ == "__main__":
    main()
