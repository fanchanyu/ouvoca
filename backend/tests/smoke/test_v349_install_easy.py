"""v3.49 — install_easy.bat / .sh bootstrap installer for non-tech users.

Locks down the contract:
  - install_easy.bat / start.bat exist for Windows
  - install_easy.sh / start.sh / stop.sh exist for Mac/Linux
  - .gitignore excludes tools/ directory (avoid committing ~750MB binaries)
  - README has the "電腦小白模式" section
  - install_easy scripts mention the right Python/Node versions
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]


def test_install_easy_bat_exists():
    f = ROOT / "install_easy.bat"
    assert f.exists(), "install_easy.bat 缺失 — 電腦小白安裝路徑會失效"
    src = f.read_text(encoding="utf-8")
    assert "python-3.11" in src, "install_easy.bat 應指定 Python 3.11"
    assert "node-v20" in src, "install_easy.bat 應指定 Node v20"
    assert "tools\\python" in src, "Python 應裝到 tools\\python"
    assert "tools\\node" in src, "Node 應裝到 tools\\node"


def test_start_bat_exists():
    f = ROOT / "start.bat"
    assert f.exists(), "start.bat 缺失 — 二次啟動會失敗"
    src = f.read_text(encoding="utf-8")
    assert "tools\\python" in src, "start.bat 應優先用 bundled Python"
    assert "tools\\node" in src, "start.bat 應優先用 bundled Node"
    assert "8000" in src and "5173" in src, "start.bat 應啟動 backend:8000 + frontend:5173"


def test_install_easy_sh_exists():
    f = ROOT / "install_easy.sh"
    assert f.exists(), "install_easy.sh 缺失 — Mac/Linux 安裝路徑會失效"
    src = f.read_text(encoding="utf-8")
    assert "python3.11" in src or "python3.12" in src, "應支援 Python 3.11+"
    assert "node" in src.lower(), "應檢查 Node"
    assert "brew" in src and "apt" in src, "應提示 Mac 用 brew、Linux 用 apt"


def test_start_stop_sh_exist():
    assert (ROOT / "start.sh").exists(), "start.sh 缺失"
    assert (ROOT / "stop.sh").exists(), "stop.sh 缺失"


def test_gitignore_excludes_tools_directory():
    """tools/ 目錄會放 ~750MB 的 Python/Node 二進位，絕對不能提交。"""
    src = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "tools/" in src, ".gitignore 必須包含 tools/ — 否則會提交 750MB 二進位"
    assert ".backend.pid" in src, ".gitignore 應排除 start.sh 產生的 PID 檔"
    assert "logs-backend.txt" in src, ".gitignore 應排除 log 檔"


def test_readme_has_easy_install_section():
    """README 必須把電腦小白模式列為首選。"""
    src = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "電腦小白模式" in src, "README 缺『電腦小白模式』章節"
    assert "install_easy.bat" in src, "README 應指引使用者跑 install_easy.bat"
    # 電腦小白模式應該排在 Docker 模式之前
    idx_easy = src.find("電腦小白模式")
    idx_docker = src.find("Docker 模式")
    assert idx_easy > 0 and idx_docker > 0, "兩段都應存在"
    assert idx_easy < idx_docker, "電腦小白模式應在 Docker 模式之前（推薦首選）"
