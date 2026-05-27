"""v3.54 P0: Taiwan e-invoice timestamp must use Taiwan TZ, not UTC.

統一發票使用辦法要求發票日期時間為發票實際開立時間（台灣時區）。
若使用 UTC，台灣凌晨 00:00-08:00 開立的發票會被打上前一天日期，
跨月時甚至影響營業稅期別歸屬，是直接的法規違反。
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]


def test_tax_tw_uses_taiwan_timezone_for_invoice_date():
    src = (ROOT / "backend/app/api/tax_tw.py").read_text(encoding="utf-8")
    # Must reference Asia/Taipei timezone
    assert "Asia/Taipei" in src or "TAIWAN_TZ" in src, (
        "tax_tw.py 必須用 Asia/Taipei 時區產生發票日期時間 "
        "（統一發票使用辦法要求台灣時間，違反會被稅捐機關處分）"
    )
    # Must NOT use plain UTC for invoice_date
    # Old buggy pattern: datetime.now(UTC)...strftime("%Y%m%d") 直接給 invoice_date
    # 修復後應該不再有此 pattern 在 invoice_date= 賦值附近
    # 直接抓 invoice_date= 那行，前後 5 行必須出現 TAIWAN_TZ 或 Asia/Taipei
    lines = src.split("\n")
    for i, line in enumerate(lines):
        if "invoice_date=" in line and ".strftime" in line:
            context = "\n".join(lines[max(0, i-10):i+1])
            assert "TAIWAN_TZ" in context or "Asia/Taipei" in context, (
                f"line {i+1}: invoice_date 賦值附近必須用 TAIWAN_TZ，目前可能還在用 UTC"
            )


def test_zoneinfo_import_present():
    src = (ROOT / "backend/app/api/tax_tw.py").read_text(encoding="utf-8")
    assert "from zoneinfo import" in src or "import zoneinfo" in src, (
        "tax_tw.py 應 import zoneinfo (Python 3.9+ stdlib)"
    )
