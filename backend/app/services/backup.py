"""備份服務（審計 P1-7）— SQLite 檔案快照 + 保留策略 + 還原。

設計：
  - 備份 = 目前 SQLite DB 檔的安全複製（先 WAL checkpoint 再 copy）
  - 檔名：backup-YYYYMMDD-HHMMSS-{db 名稱}.db
  - 保留策略：超過 retention_days 的舊備份自動刪除
  - 還原 = 以備份檔覆蓋現行 DB（**破壞性**，API 需權限 + 確認；AI tool 走 ConfirmCard）
  - PostgreSQL 環境：記錄「不支援檔案快照」並建議用資料庫原生備份
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "backups"
BACKUP_NAME_RE = re.compile(r"^backup-\d{8}-\d{6}-[A-Za-z0-9._-]+\.db$")


def _sqlite_db_path() -> Optional[Path]:
    url = settings.effective_db_url
    if not url.startswith("sqlite"):
        return None
    after = url.split(":///", 1)[-1] if ":///" in url else url.split("://", 1)[-1]
    path = Path("/" + after) if after.startswith("/") else Path(after)
    return path


async def create_backup(db: AsyncSession, *, reason: str = "manual") -> dict:
    """建立一個 DB 快照備份。回傳備份資訊。"""
    db_path = _sqlite_db_path()
    if db_path is None:
        return {
            "created": False,
            "reason": "PostgreSQL 環境不支援檔案快照；請使用資料庫原生備份（pg_dump）。",
        }
    if not db_path.exists():
        return {"created": False, "reason": f"DB 檔案不存在：{db_path}"}

    # WAL checkpoint 確保快照一致
    try:
        conn = await db.connection()
        await conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception as exc:
        log.warning("WAL checkpoint failed（繼續備份）: %s", exc)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).replace(tzinfo=None)
    name = f"backup-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{db_path.stem}.db"
    dest = BACKUP_DIR / name
    shutil.copy2(db_path, dest)

    meta = {
        "name": name,
        "created_at": now.isoformat(),
        "size_bytes": dest.stat().st_size,
        "db": db_path.name,
        "reason": reason,
    }
    (dest.with_suffix(".json")).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    log.info("Backup created: %s (%d bytes)", name, dest.stat().st_size)
    return {"created": True, **meta}


def list_backups() -> list[dict]:
    """列出全部備份（含大小/日期/可還原性）。"""
    if not BACKUP_DIR.exists():
        return []
    out = []
    for f in sorted(BACKUP_DIR.glob("backup-*.db"), reverse=True):
        m = BACKUP_NAME_RE.match(f.name)
        meta = {"name": f.name, "size_bytes": f.stat().st_size}
        json_path = f.with_suffix(".json")
        if json_path.exists():
            try:
                meta.update(json.loads(json_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        meta["valid_sqlite"] = _is_valid_sqlite(f)
        out.append(meta)
    return out


def _is_valid_sqlite(path: Path) -> bool:
    conn = None
    try:
        # 健檢 #6：sqlite3 context manager 只管 transaction 不會關連線 —
        # Windows 上 handle 懸著會讓檔案刪不掉，必須 try/finally 顯式 close。
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.execute("PRAGMA integrity_check").fetchone()
        return True
    except Exception:
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _safe_backup_name(name: str) -> bool:
    """健檢 #7：檔名白名單 — 拒絕路徑分隔符（含 Windows 反斜線）與穿越。"""
    if not BACKUP_NAME_RE.match(name):
        return False
    return Path(name).name == name  # 任何 / 或 \ 都會讓 name != Path(name).name


def delete_backup(name: str) -> bool:
    """刪除單一備份（含 metadata）。"""
    if not _safe_backup_name(name):
        return False
    target = BACKUP_DIR / name
    if not target.exists():
        return False
    target.unlink()
    json_path = target.with_suffix(".json")
    if json_path.exists():
        json_path.unlink()
    log.info("Backup deleted: %s", name)
    return True


def cleanup_old_backups(retention_days: int = 30) -> int:
    """刪除超過保留天數的備份。回傳刪除筆數。"""
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=retention_days)
    removed = 0
    for meta in list_backups():
        created = meta.get("created_at", "")
        if not created:
            continue
        try:
            created_dt = datetime.fromisoformat(created)
            if created_dt < cutoff:
                if delete_backup(meta["name"]):
                    removed += 1
        except Exception:
            continue
    return removed


def restore_backup(name: str) -> dict:
    """以備份檔覆蓋現行 DB（破壞性）。僅 SQLite、且備份需通過完整性檢查。"""
    db_path = _sqlite_db_path()
    if db_path is None:
        return {"restored": False, "reason": "PostgreSQL 不支援檔案還原"}
    if not _safe_backup_name(name):
        return {"restored": False, "reason": f"備份檔名不合法：{name}"}
    src = BACKUP_DIR / name
    if not src.exists():
        return {"restored": False, "reason": f"備份不存在：{name}"}
    if not _is_valid_sqlite(src):
        return {"restored": False, "reason": "備份檔不是有效的 SQLite 資料庫，拒絕還原"}
    # 先備份現行 DB 到 .pre-restore 暫存（可救援）
    rescue = BACKUP_DIR / f"pre-restore-{db_path.stem}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.db"
    if db_path.exists():
        shutil.copy2(db_path, rescue)
    shutil.copy2(src, db_path)
    # 健檢 #14：還原後清除舊 DB 的 WAL/SHM — 殘留 WAL 會覆蓋新檔造成資料損壞
    for suffix in ("-wal", "-shm"):
        stale = Path(str(db_path) + suffix)
        if stale.exists():
            try:
                stale.unlink()
            except Exception as exc:
                log.warning("無法清除 %s：%s", stale, exc)
    log.warning("DB restored from backup %s（救援檔 %s）", name, rescue.name)
    return {
        "restored": True,
        "name": name,
        "rescue_file": rescue.name,
        "note": "還原成功。請重新啟動服務並確認資料。",
    }
