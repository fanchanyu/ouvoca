"""v3.52 — update.bat / update.sh 一鍵更新合約鎖定。

避免未來改動讓「電腦小白安全更新」這條路再次失靈：
  - 腳本必須存在
  - 必須先備份再更新（不能直接覆蓋）
  - 必須跨安裝方式相容（git pull / zip 下載）
  - 必須跑 alembic upgrade（資料庫結構升級）
  - 必須保留使用者資料（erp.db / .env / uploads / venv / node_modules）
  - 必須與 README / docs 都對齊
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]


def test_update_bat_exists():
    f = ROOT / "update.bat"
    assert f.exists(), "update.bat 缺失 — 電腦小白無法安全更新（會手動覆蓋誤刪資料）"
    src = f.read_text(encoding="utf-8")

    # 必須備份
    assert "backups\\" in src or "backup" in src.lower(), (
        "update.bat 必須先備份再更新，不能直接覆蓋資料"
    )
    assert "erp.db" in src, "必須備份 erp.db"
    assert ".env" in src, "必須備份 .env（含 JWT_SECRET + LLM API Key）"
    assert "uploads" in src, "必須備份 uploads"

    # 跨安裝方式相容
    assert "git pull" in src, "必須支援 git pull 路徑（git clone 安裝者）"
    assert "curl" in src and "zip" in src.lower(), "必須支援 zip 下載路徑（zip 安裝者）"
    assert "main.zip" in src or "archive" in src, "必須從 GitHub archive 下載"

    # DB 結構升級
    assert "alembic" in src.lower(), "必須跑 alembic upgrade（資料庫結構升級）"

    # 保留使用者資料（robocopy 排除清單）
    assert "/XF" in src or "exclude" in src.lower(), (
        "覆蓋新檔時必須排除使用者資料 (erp.db / .env / uploads)"
    )

    # 重啟
    assert "start.bat" in src, "更新完成後必須能重啟"


def test_update_sh_exists():
    f = ROOT / "update.sh"
    assert f.exists(), "update.sh 缺失 — Mac/Linux 無法安全更新"
    src = f.read_text(encoding="utf-8")

    assert "backups/" in src or "backup" in src.lower(), "必須先備份"
    assert "erp.db" in src
    assert ".env" in src
    assert "uploads" in src
    assert "git pull" in src
    assert "rsync" in src or "cp" in src, "zip 路徑必須有檔案複製方法"
    assert "alembic" in src.lower(), "必須跑 alembic"
    assert "start.sh" in src


def test_gitignore_excludes_backups():
    """backups/ 含使用者業務資料 + .env (JWT/API Key)，絕對不可推。"""
    src = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "backups/" in src, (
        ".gitignore 必須排除 backups/ — 否則 update.bat 的備份會把 erp.db / .env "
        "(含 JWT_SECRET / LLM API Key) 推到 GitHub，安全災難"
    )


def test_readme_documents_update_path():
    """README 必須清楚告訴小白怎麼更新。"""
    src = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "update.bat" in src, "README 必須指引 update.bat"
    assert "更新到新版" in src or "🆙" in src, "README 應有更新章節標題"


def test_troubleshooting_has_upgrade_section():
    """排錯指南必須有「我昨天裝今天有新版怎麼辦」章節。"""
    zh = (ROOT / "docs" / "INSTALL_TROUBLESHOOTING_ZH.md").read_text(encoding="utf-8")
    en = (ROOT / "docs" / "INSTALL_TROUBLESHOOTING_EN.md").read_text(encoding="utf-8")

    # 中文
    assert "update.bat" in zh, "中文排錯指南缺 update.bat 說明"
    assert "備份" in zh, "必須提及備份機制"
    assert "還原" in zh, "必須提及還原方法"
    assert "不要重裝" in zh or "Do NOT" in zh.upper(), (
        "必須警告「不要重裝」會丟資料"
    )

    # 英文
    assert "update.bat" in en
    assert "backup" in en.lower()
    assert "rollback" in en.lower() or "restore" in en.lower(), (
        "EN must mention rollback/restore path"
    )


def test_install_easy_does_not_overwrite_existing_data():
    """install_easy.bat 對既有 erp.db / .env 應跳過，不覆蓋。

    確保使用者跑 update.bat 後不會被 install_easy 衝爛資料。
    """
    src = (ROOT / "install_easy.bat").read_text(encoding="utf-8")
    # .env 邏輯：應只在 not exist 時建立
    assert 'if not exist "backend\\.env"' in src or "if not exist backend\\.env" in src, (
        "install_easy.bat 對既有 backend\\.env 必須跳過（否則 update 後重跑 install_easy "
        "會把 JWT_SECRET 重新隨機產生，使用者所有 token 失效）"
    )
    # venv 同樣
    assert 'if not exist "backend\\venv"' in src or "if not exist backend\\venv" in src, (
        "install_easy.bat 對既有 venv 必須跳過"
    )
