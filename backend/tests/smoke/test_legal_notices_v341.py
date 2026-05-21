"""v3.34.1: 雙語法律聲明完整性驗證

確認所有法律聲明檔案存在且含關鍵條款（TMEPL / cumulatively / non-legal-advice）。
"""
import os
import pytest


LEGAL_NOTICE_FILES = [
    # v3.25.4
    "EXTERNAL_DB_LICENSING_NOTICE_ZH.md",
    "EXTERNAL_DB_LICENSING_NOTICE_EN.md",
    # v3.32/v3.33
    "INVENTORY_SALES_LEGAL_NOTICE_ZH.md",
    "INVENTORY_SALES_LEGAL_NOTICE_EN.md",
    # v3.34 (新)
    "TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md",
    "TAX_ACCOUNTING_LEGAL_NOTICE_EN.md",
]


def _docs_dir():
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.abspath(os.path.join(base, "..", "docs"))


def test_all_legal_notices_exist():
    """6 份雙語法律聲明檔案必須存在。"""
    d = _docs_dir()
    for name in LEGAL_NOTICE_FILES:
        path = os.path.join(d, name)
        assert os.path.exists(path), f"缺：{path}"


def test_tax_accounting_zh_has_key_clauses():
    """v3.34 中文法律聲明必含關鍵段落。"""
    d = _docs_dir()
    path = os.path.join(d, "TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    # 關鍵字檢查
    must_have = [
        "適用法律所允許之最大範圍",  # TMEPL
        "累積適用",                  # cumulative
        "不構成稅務",                # not tax advice
        "法律意見",                  # legal advice mentioned
        "CPA",
        "雲端發票",
        "24 小時",                   # void window
        "maker-checker",
        "GAAP",
    ]
    missing = [k for k in must_have if k not in content]
    assert not missing, f"中文法律聲明缺關鍵段落：{missing}"


def test_tax_accounting_en_has_key_clauses():
    """v3.34 英文法律聲明必含關鍵段落。"""
    d = _docs_dir()
    path = os.path.join(d, "TAX_ACCOUNTING_LEGAL_NOTICE_EN.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    must_have = [
        "maximum extent permitted by applicable law",
        "cumulatively",
        "NOT constitute",
        "CPA",
        "GAAP",
        "24-hour",
        "maker-checker",
        "Form 401",
    ]
    missing = [k for k in must_have if k not in content]
    assert not missing, f"英文法律聲明缺關鍵段落：{missing}"


def test_tax_accounting_bilingual_cross_links():
    """中英文檔案必互相連結（cross-reference）。"""
    d = _docs_dir()
    with open(os.path.join(d, "TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md"), encoding="utf-8") as f:
        zh = f.read()
    with open(os.path.join(d, "TAX_ACCOUNTING_LEGAL_NOTICE_EN.md"), encoding="utf-8") as f:
        en = f.read()
    assert "TAX_ACCOUNTING_LEGAL_NOTICE_EN.md" in zh, "中文檔未連結到英文版"
    assert "TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md" in en, "英文檔未連結到中文版"


def test_pdf_builder_includes_legal_notices():
    """build.mjs 必須包含 v3.34 法律聲明 entry。"""
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    builder = os.path.abspath(os.path.join(base, "..", "scripts", "build-pdfs", "build.mjs"))
    with open(builder, encoding="utf-8") as f:
        content = f.read()
    assert "TAX_ACCOUNTING_LEGAL_NOTICE_ZH.md" in content
    assert "TAX_ACCOUNTING_LEGAL_NOTICE_EN.md" in content
