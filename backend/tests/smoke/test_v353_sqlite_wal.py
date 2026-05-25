"""v3.53: SQLite 並發安全（WAL）+ production fail-fast 驗證

兩個 P0 修復（audit findings A4 & C4）：

A4 — backend/app/database.py 對每條 SQLite 連線啟用 WAL：
   PRAGMA journal_mode=WAL / synchronous=NORMAL / busy_timeout=5000 / foreign_keys=ON
   解決 50 人並發時的「database is locked」災難。

C4 — backend/app/main.py 在 production（非 DEBUG）模式下若 DATABASE_DRIVER=sqlite
   直接 FATAL 退出（加進 fatal_errors → raise SystemExit(1)），而不只是 log warning。
"""
import os


def _backend_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_database_py_enables_wal():
    """database.py 必須對 SQLite 設 journal_mode=WAL 與相關 pragma。"""
    path = os.path.join(_backend_dir(), "app", "database.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()

    must_have = [
        "journal_mode=WAL",
        "synchronous=NORMAL",
        "busy_timeout=5000",
        "foreign_keys=ON",
        # 必須掛 event listener 才會真的執行
        'event.listen',
        '"connect"',
    ]
    missing = [k for k in must_have if k not in content]
    assert not missing, f"database.py 缺 SQLite WAL pragma 設定：{missing}"


def test_main_py_fails_fast_on_sqlite_production():
    """main.py 必須在 production（非 DEBUG）時把 SQLite 加進 fatal_errors。"""
    path = os.path.join(_backend_dir(), "app", "main.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # 必須出現在 fatal_errors.append(...) 區塊內，且訊息含 DATABASE_DRIVER=sqlite
    assert "DATABASE_DRIVER=sqlite" in content, \
        "main.py 找不到 'DATABASE_DRIVER=sqlite' 字串（fatal error 訊息）"

    # 找到該訊息的位置，往回看 200 字元內必含 fatal_errors.append
    idx = content.find("DATABASE_DRIVER=sqlite 不能用於 production")
    assert idx > 0, "main.py 找不到 SQLite production 拒絕啟動的中文訊息"
    window = content[max(0, idx - 300):idx]
    assert "fatal_errors.append" in window, \
        "SQLite production 訊息必須透過 fatal_errors.append 註冊（重用既有 SystemExit 機制）"

    # 確保舊的 warning-only 程式碼已移除（避免 fatal 和 warning 並存的混淆）
    assert "Using SQLite in non-debug mode. Consider PostgreSQL" not in content, \
        "舊的 SQLite warning-only log 應已移除（被升級為 fatal_errors）"
