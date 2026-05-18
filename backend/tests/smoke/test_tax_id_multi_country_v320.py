"""
Smoke: 多國統編驗證 (Sprint N v3.20)

使用者「嚴格驗證台灣統編 checksum，但不見得客戶只有台灣，應該要能客製化」
"""
from __future__ import annotations

import pytest

from app.integrations.tax_id_validators import (
    validate, register_validator, list_supported,
    ValidationResult, _validate_tw,
)


# ─── 台灣 ─────────────────────────────────────────────────
class TestTaiwan:
    def test_acer_valid(self):
        """Acer 04595257 是已知有效統編"""
        r = validate("04595257", "TW")
        assert r.valid is True
        assert r.country == "TW"

    def test_asustek_valid(self):
        """Asustek 22099131"""
        r = validate("22099131", "TW")
        assert r.valid is True

    def test_with_dashes_cleaned(self):
        """格式容錯：04595257 / 04-59-52-57 都接受"""
        r = validate("04-59-52-57", "TW")
        assert r.valid is True
        assert r.formatted == "04595257"

    def test_all_zeros_rejected(self):
        assert validate("00000000", "TW").valid is False

    def test_all_same_rejected(self):
        assert validate("11111111", "TW").valid is False

    def test_too_short_rejected(self):
        r = validate("1234567", "TW")
        assert r.valid is False
        assert "8 位" in r.message

    def test_too_long_rejected(self):
        assert validate("123456789", "TW").valid is False

    def test_letters_rejected(self):
        assert validate("1234567A", "TW").valid is False

    def test_wrong_checksum_rejected(self):
        """12345678 是常被誤用的測試值，checksum 不對"""
        r = validate("12345678", "TW")
        assert r.valid is False
        assert "checksum" in r.message.lower() or "符" in r.message


# ─── 中國 ─────────────────────────────────────────────────
class TestChina:
    def test_18_digit_format_passes(self):
        # 18 碼，含字母 + 數字（GB 32100 格式）
        r = validate("91110000123456789X", "CN")
        assert r.valid is True
        assert r.country == "CN"

    def test_short_rejected(self):
        r = validate("12345", "CN")
        assert r.valid is False
        assert "18" in r.message

    def test_invalid_chars_rejected(self):
        r = validate("91110000123456789I", "CN")  # I 不在合法字元中
        assert r.valid is False


# ─── 美國 ─────────────────────────────────────────────────
class TestUS:
    def test_valid_ein(self):
        r = validate("123456789", "US")
        assert r.valid is True
        assert r.formatted == "12-3456789"

    def test_with_dash_cleaned(self):
        r = validate("12-3456789", "US")
        assert r.valid is True

    def test_all_zeros_rejected(self):
        assert validate("000000000", "US").valid is False

    def test_short_rejected(self):
        r = validate("12345", "US")
        assert r.valid is False
        assert "9" in r.message


# ─── 日本 ─────────────────────────────────────────────────
class TestJapan:
    def test_13_digit_format(self):
        r = validate("1234567890123", "JP")
        assert r.valid is True

    def test_short_rejected(self):
        assert validate("1234567", "JP").valid is False


# ─── EU VAT ──────────────────────────────────────────────
class TestEUVat:
    def test_germany(self):
        r = validate("DE123456789", "EU")
        assert r.valid is True
        assert r.country == "EU-DE"

    def test_france(self):
        r = validate("FR12345678901", "EU")
        assert r.valid is True
        assert r.country == "EU-FR"

    def test_invalid_country_code(self):
        r = validate("ZZ12345678", "EU")
        assert r.valid is False


# ─── 通用 / 容錯 ──────────────────────────────────────────
class TestGeneric:
    def test_unknown_country_falls_back(self):
        """未支援的國家 → 走 generic（永遠通過格式檢查）"""
        r = validate("anything-123", "ZW")  # 辛巴威，暫未支援
        assert r.valid is True
        assert r.country == "GENERIC"

    def test_empty_rejected(self):
        r = validate("", "TW")
        assert r.valid is False
        assert "空" in r.message


# ─── 客戶端註冊新國家 ─────────────────────────────────────
def test_register_custom_validator():
    """讓客戶能 plug-in 自定 validator（如肯亞 KRA PIN）。"""
    def validate_kenya_pin(tax_id: str) -> ValidationResult:
        # 肯亞 PIN: A + 9 數字 + 字母（簡化）
        import re
        if re.fullmatch(r"[A-Z]\d{9}[A-Z]", tax_id):
            return ValidationResult(True, "KE", "肯亞 PIN 格式 OK", tax_id)
        return ValidationResult(False, "KE", "肯亞 PIN 需 A123456789B 格式")

    register_validator("KE", validate_kenya_pin)

    r = validate("A123456789B", "KE")
    assert r.valid is True
    assert r.country == "KE"

    r = validate("invalid", "KE")
    assert r.valid is False


# ─── API endpoint ────────────────────────────────────────
def test_api_default_taiwan(seeded_client):
    """endpoint 預設 country=TW（向後相容）"""
    r = seeded_client.get("/api/tax/tw/validate-tax-id/04595257")
    assert r.status_code == 200
    assert r.json()["valid"] is True
    assert r.json()["country"] == "TW"


def test_api_explicit_us(seeded_client):
    r = seeded_client.get("/api/tax/tw/validate-tax-id/123456789?country=US")
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["country"] == "US"


def test_api_invalid_returns_supported_list(seeded_client):
    """無效時 response 帶 supported_countries 讓 UI 引導"""
    r = seeded_client.get("/api/tax/tw/validate-tax-id/12345678")
    body = r.json()
    assert body["valid"] is False
    assert body.get("supported_countries") is not None
    assert len(body["supported_countries"]) >= 5


def test_api_list_countries(seeded_client):
    r = seeded_client.get("/api/tax/tw/validate-tax-id-countries")
    assert r.status_code == 200
    body = r.json()
    assert len(body["countries"]) >= 5
    codes = {c["code"] for c in body["countries"]}
    assert "TW" in codes
    assert "US" in codes
    assert "JP" in codes
    assert "EU" in codes
