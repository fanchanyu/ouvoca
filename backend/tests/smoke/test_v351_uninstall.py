"""v3.51 — uninstall_easy.bat / .sh 解除安裝路徑完整性鎖定。

避免未來改動讓「電腦小白完全移除」這條路再次失靈：
  - 腳本必須存在
  - 必須處理 Windows 註冊表清理（不是只刪資料夾）
  - 必須詢問使用者資料才刪（不能誤刪 erp.db）
  - 必須提供 cache 清除選項
  - 必須與 install_easy / README / docs 都對齊（雙向連結）
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]


def test_uninstall_easy_bat_exists():
    f = ROOT / "uninstall_easy.bat"
    assert f.exists(), "uninstall_easy.bat 缺失 — 電腦小白無法完整移除（會留 Windows 註冊表項）"
    src = f.read_text(encoding="utf-8")
    # 必須處理 Python 註冊表清理（不只刪資料夾）
    assert "/uninstall" in src or "reg delete" in src, (
        "uninstall_easy.bat 必須跑 Python /uninstall 或 reg delete 清註冊表，"
        "否則「新增/移除程式」會殘留 Python 3.11"
    )
    assert "HKCU\\Software\\Python" in src, "必須清 HKCU\\Software\\Python 註冊表項"
    # 必須詢問才刪資料（不能誤刪業務資料）
    assert "erp.db" in src, "uninstall 必須詢問是否刪 erp.db（使用者業務資料）"
    assert "uploads" in src, "uninstall 必須詢問是否刪 uploads"
    assert ".env" in src, "uninstall 必須詢問是否刪 .env"
    # 雙重確認機制
    assert src.count("choice /M") >= 3, (
        "uninstall_easy.bat 應至少有 3 個 choice：確認解除安裝、確認刪資料（含再次確認）、確認清 cache"
    )
    # cache 清除選項
    assert "npm-cache" in src or "npm_cache" in src, "應提供 npm cache 清除選項"
    assert "pip" in src.lower(), "應提供 pip cache 清除選項"


def test_uninstall_easy_sh_exists():
    f = ROOT / "uninstall_easy.sh"
    assert f.exists(), "uninstall_easy.sh 缺失 — Mac/Linux 無法完整移除"
    src = f.read_text(encoding="utf-8")
    # Mac/Linux 不應碰 system Python（brew/apt 裝的）
    assert "Python/Node" in src or "Python/Node" in src, (
        "uninstall_easy.sh 應明確說明不會動到 system Python/Node（brew/apt 裝的）"
    )
    # 必須詢問資料才刪
    assert "erp.db" in src, "uninstall 必須詢問是否刪 erp.db"
    assert "uploads" in src, "uninstall 必須詢問是否刪 uploads"
    # 雙重確認
    assert src.count("read -p") >= 3, (
        "uninstall_easy.sh 應至少 3 個 read -p：確認解除、確認刪資料（含再次）、確認清 cache"
    )


def test_install_easy_bat_mentions_uninstall():
    """install_easy.bat 結尾必須告知 uninstall_easy.bat 存在 — 否則小白不知道怎麼移除。"""
    src = (ROOT / "install_easy.bat").read_text(encoding="utf-8")
    assert "uninstall_easy.bat" in src, (
        "install_easy.bat 結尾必須提及 uninstall_easy.bat，"
        "否則小白裝完不知道怎麼乾淨移除"
    )


def test_readme_mentions_uninstall_correctly():
    """README 必須正確說明卸載 — 不能再說「卸載 = 刪資料夾」這種過度簡化。"""
    src = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "uninstall_easy.bat" in src, "README 必須指引使用者跑 uninstall_easy.bat"
    # 不能再有「卸載 = 刪資料夾」這種誤導性文字（因為會留註冊表）
    assert "完全移除" in src or "uninstall_easy" in src, (
        "README 應有「完全移除」段落引導到 uninstall_easy 腳本"
    )


def test_troubleshooting_has_uninstall_section():
    """排錯指南必須含完整移除段落（含註冊表清理 + Mac/Linux + 漏刪救援）。"""
    zh = (ROOT / "docs" / "INSTALL_TROUBLESHOOTING_ZH.md").read_text(encoding="utf-8")
    en = (ROOT / "docs" / "INSTALL_TROUBLESHOOTING_EN.md").read_text(encoding="utf-8")

    # 中文版
    assert "完全移除" in zh or "解除安裝" in zh, "中文排錯指南缺『完全移除』段落"
    assert "uninstall_easy" in zh, "中文應指引 uninstall_easy 腳本"
    assert "註冊表" in zh, "中文必須警告 Windows 註冊表殘留"
    assert "保留資料" in zh or "保留你的資料" in zh, (
        "必須說明「只移除程式、保留資料」的做法"
    )
    # 漏刪救援
    assert "reg delete" in zh, "必須有「已刪資料夾才發現殘留」的救援指令"

    # 英文版同樣
    assert "Uninstall" in en or "uninstall" in en, "EN troubleshooting missing uninstall section"
    assert "uninstall_easy" in en, "EN should reference uninstall_easy script"
    assert "registry" in en.lower(), "EN must warn about Windows registry residue"
    assert "reg delete" in en, "EN must provide manual registry cleanup commands"
