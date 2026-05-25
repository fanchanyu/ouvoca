"""v3.53 — verify inventory updates are atomic (no lost update race) and
service does NOT commit (caller controls the transaction boundary).

Audit context: 早期 inventory.add_inventory_transaction 用 Python read-modify-write
（inv.qty_on_hand += qty），早上的 PO 收貨與下午的 SO 出貨同時跑時，兩個 transaction
都讀到 qty=50、各自 +/- 後寫回 → 一筆更新被覆蓋（lost update）。同時 service 自己
commit，導致 PO 收貨「批次三行」其實是三次 commit，無法整批 rollback。

本檔對三件事下 guard，避免回頭路：
  A1/A2 — 庫存算式用 SQL 算術（race-safe）
  A3    — service 不 commit，由 caller 統一 commit
  +     — receive_purchase_order 只能有一次 commit
"""
import pathlib
import re

import pytest


_BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (_BACKEND_ROOT / rel).read_text(encoding="utf-8")


def test_inventory_service_uses_atomic_update():
    """inventory.py 必須使用 SQL 算術 (Inventory.qty_on_hand +/- delta)，
    不可再用 Python `inv.qty_on_hand +=` read-modify-write（會 lost update）。"""
    src = _read("app/services/inventory.py")
    assert (
        "Inventory.qty_on_hand + " in src or "Inventory.qty_on_hand - " in src
    ), (
        "inventory.py must use SQL arithmetic (Inventory.qty_on_hand +/- delta) "
        "for atomic update, not Python += which causes lost updates under concurrency."
    )
    # 反向：read-modify-write pattern 必須移除
    assert "inv.qty_on_hand += qty" not in src, (
        "Found legacy Python read-modify-write `inv.qty_on_hand += qty`. "
        "This causes lost updates and must be replaced by SQL UPDATE arithmetic."
    )
    assert "inv.qty_on_hand -= qty" not in src, (
        "Found legacy Python read-modify-write `inv.qty_on_hand -= qty`. "
        "This causes lost updates and must be replaced by SQL UPDATE arithmetic."
    )


def test_add_inventory_transaction_does_not_commit():
    """add_inventory_transaction 內部不可有 `await db.commit()`，
    交易邊界由 caller（API endpoint / 多行操作 service）負責。"""
    src = _read("app/services/inventory.py")
    # 抓 add_inventory_transaction 函式的 body（到下一個 def / 檔尾為止）
    m = re.search(
        r"async def add_inventory_transaction\([^)]*\)[^:]*:\s*\n(.*?)(?=\nasync def |\ndef |\Z)",
        src,
        re.DOTALL,
    )
    assert m, "找不到 add_inventory_transaction 函式定義"
    body = m.group(1)
    assert "await db.commit()" not in body, (
        "add_inventory_transaction 內部不可呼叫 db.commit()。"
        "改用 db.flush()；commit 由 caller 負責，這樣 PO 收貨等多行操作才能整批原子化。"
    )
    # 必須有 flush
    assert "await db.flush()" in body, (
        "add_inventory_transaction 必須呼叫 db.flush() 讓變更可見於同 session 後續查詢。"
    )


def test_purchase_receive_is_single_transaction():
    """receive_purchase_order 應該只有 1 個 commit（位於函式尾），
    過去 inventory.add_inventory_transaction 自己 commit + 結尾再 commit 是 nested commit bug。"""
    src = _read("app/services/purchase.py")
    m = re.search(
        r"async def receive_purchase_order\([^)]*\)[^:]*:\s*\n(.*?)(?=\nasync def |\ndef |\Z)",
        src,
        re.DOTALL,
    )
    assert m, "找不到 receive_purchase_order 函式定義"
    body = m.group(1)
    commit_count = body.count("await db.commit()")
    assert commit_count == 1, (
        f"receive_purchase_order 應只有 1 次 db.commit()，現在有 {commit_count} 次。"
        "多行收貨應為單一 transaction，避免半成功狀態。"
    )


def test_ship_sales_order_is_single_transaction():
    """ship_sales_order 應該只有 1 個 commit（位於函式尾）。"""
    src = _read("app/services/sales.py")
    m = re.search(
        r"async def ship_sales_order\([^)]*\)[^:]*:\s*\n(.*?)(?=\nasync def |\ndef |\Z)",
        src,
        re.DOTALL,
    )
    assert m, "找不到 ship_sales_order 函式定義"
    body = m.group(1)
    commit_count = body.count("await db.commit()")
    assert commit_count == 1, (
        f"ship_sales_order 應只有 1 次 db.commit()，現在有 {commit_count} 次。"
    )


def test_complete_production_order_is_single_transaction():
    """complete_production_order 應該只有 1 個 commit（位於函式尾）。"""
    src = _read("app/services/production.py")
    m = re.search(
        r"async def complete_production_order\([^)]*\)[^:]*:\s*\n(.*?)(?=\nasync def |\ndef |\Z)",
        src,
        re.DOTALL,
    )
    assert m, "找不到 complete_production_order 函式定義"
    body = m.group(1)
    commit_count = body.count("await db.commit()")
    assert commit_count == 1, (
        f"complete_production_order 應只有 1 次 db.commit()，現在有 {commit_count} 次。"
    )
