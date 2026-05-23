"""v3.49 — 「可上線優先」原則同步驗證 (Deployability First Principle Sync)

「能上線才是王道」是范展裕 2026-05-22 凍結的核心開發原則。
這份 test 確保四份關鍵文件對此原則的描述「同步且一致」。

若有 PR 在某一份文件刪掉原則卻沒同步刪其他份 → 這 test 應該失敗
（強制讓 reviewer 看見並決定要不要全部刪）。
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]


def test_readme_has_deployability_first_section():
    """README 必須有「設計優先順序」段落，且第 1 條是電腦小白裝得起來。"""
    src = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "設計優先順序" in src, "README 缺『設計優先順序』段落"
    assert "能上線才是王道" in src, "README 缺核心宣言「能上線才是王道」"
    assert "Deployability first" in src, "README 缺英文翻譯 Deployability first"
    # 電腦小白裝得起來必須是 #1 優先
    idx_install = src.find("電腦小白裝得起來")
    idx_priority1 = src.find("**1**")
    assert idx_install > 0, "README 應提及『電腦小白裝得起來』"
    assert idx_priority1 > 0 and idx_priority1 < idx_install, (
        "『電腦小白裝得起來』必須是 priority #1，不能降級為 2/3/4/5"
    )


def test_contributing_locks_deployability():
    """CONTRIBUTING.md 必須要求貢獻者過「電腦小白裝得起來」測試。"""
    src = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "可上線優先" in src or "Deployability First" in src, (
        "CONTRIBUTING.md 缺『可上線優先』段落 — 貢獻者可能不知此原則"
    )
    assert "install_easy" in src, "CONTRIBUTING.md 應提及 install_easy"
    assert "電腦小白" in src, "CONTRIBUTING.md 應用「電腦小白」白話描述"


def test_development_sop_has_deployability_checklist():
    """docs/DEVELOPMENT_SOP.md 必須有可上線優先檢查單。"""
    src = (ROOT / "docs" / "DEVELOPMENT_SOP.md").read_text(encoding="utf-8")
    assert "SOP-7.5" in src or "可上線優先" in src, (
        "DEVELOPMENT_SOP.md 缺『可上線優先檢查』SOP"
    )
    assert "requirements.txt" in src, "SOP 應列觸發場景（修改 requirements.txt 等）"
    assert "電腦小白" in src, "SOP 檢查單應用「電腦小白」白話描述"


def test_install_easy_files_still_exist():
    """可上線優先原則的具體體現 — install_easy 系列不能消失。"""
    assert (ROOT / "install_easy.bat").exists(), "install_easy.bat 消失了！原則破功"
    assert (ROOT / "install_easy.sh").exists(), "install_easy.sh 消失了！原則破功"
    assert (ROOT / "start.bat").exists(), "start.bat 消失了！二次啟動破功"
    assert (ROOT / "start.sh").exists(), "start.sh 消失了！二次啟動破功"


def test_requirements_no_uncovered_native_deps():
    """requirements.txt 不應加無 wheel 的 native 依賴。

    如果未來有 PR 加了某個只能 source-compile 的套件（如某些 C extension），
    這 test 會失敗，提醒 reviewer 評估是否會破壞電腦小白安裝。

    目前的 disallowlist：known-problematic packages that need build tools.
    """
    req = (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8")
    forbidden = {
        # 範例：這些套件在 Windows 沒 wheel 時需要 Visual Studio Build Tools
        # 「possible 跳出加入時請務必確認 Windows / macOS 都有 prebuilt wheel」
        # （目前 disallowlist 為空 — 列出當有 PR 真的加了問題依賴時用）
    }
    for pkg in forbidden:
        assert pkg.lower() not in req.lower(), (
            f"{pkg} 加入 requirements.txt — 此套件在 Windows 沒 prebuilt wheel，"
            f"電腦小白安裝會失敗。請改用替代方案或確認所有平台都有 wheel。"
        )
