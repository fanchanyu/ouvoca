"""Multi-country tax ID validators (Sprint N v3.20).

對應使用者「嚴格驗證台灣統編 checksum，但不見得客戶只有台灣，這個應該要能客製化」

設計：
  - 每個國家一個 validator function
  - 統一介面：validate(tax_id: str) -> ValidationResult
  - 用 registry pattern 註冊，方便擴充
  - 預設用環境變數 TAX_ID_COUNTRY 決定 default
  - frontend 可指定 country code 呼叫
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ValidationResult:
    valid: bool
    country: str
    message: str = ""        # 驗證細節（給 UI 顯示）
    formatted: str = ""      # 標準化格式（含 dash 等）


# ─── 個別國家 validator ───────────────────────────────────

def _validate_tw(tax_id: str) -> ValidationResult:
    """台灣統一編號：8 碼數字 + 檢查碼。"""
    cleaned = re.sub(r"[\s\-]", "", tax_id)
    if not re.fullmatch(r"\d{8}", cleaned):
        return ValidationResult(False, "TW", "台灣統編需 8 位數字")
    if len(set(cleaned)) == 1:
        return ValidationResult(False, "TW", "不可全部相同數字")

    weights = [1, 2, 1, 2, 1, 2, 4, 1]
    total = 0
    for i, digit in enumerate(cleaned):
        product = int(digit) * weights[i]
        total += sum(int(d) for d in str(product))

    if cleaned[6] == "7":
        ok = total % 10 == 0 or (total + 1) % 10 == 0
    else:
        ok = total % 10 == 0

    return ValidationResult(
        ok, "TW",
        "格式 + checksum 通過" if ok else "checksum 不符",
        cleaned,
    )


def _validate_cn(tax_id: str) -> ValidationResult:
    """中國統一社會信用代碼：18 碼。"""
    cleaned = re.sub(r"[\s\-]", "", tax_id).upper()
    if not re.fullmatch(r"[0-9A-HJ-NPQRTUWXY]{18}", cleaned):
        return ValidationResult(False, "CN", "中國統一社會信用代碼需 18 位（含字母+數字）")
    # 完整 checksum 算法複雜（GB 32100-2015），這邊做基本格式檢查
    # 完整版可參考 https://github.com/cn-tools/gb32100
    return ValidationResult(True, "CN", "格式通過（完整 checksum 需 GB 32100-2015）", cleaned)


def _validate_us(tax_id: str) -> ValidationResult:
    """美國 EIN：XX-XXXXXXX 9 位數字。"""
    cleaned = re.sub(r"[\s\-]", "", tax_id)
    if not re.fullmatch(r"\d{9}", cleaned):
        return ValidationResult(False, "US", "美國 EIN 需 9 位數字（格式 XX-XXXXXXX）")
    # 前兩碼是 IRS 分配代碼，有效範圍見 IRS Pub 1635
    # 簡化檢查：排除全 0、全 9
    if cleaned in ("000000000", "999999999"):
        return ValidationResult(False, "US", "EIN 不可為全 0 或全 9")
    formatted = f"{cleaned[:2]}-{cleaned[2:]}"
    return ValidationResult(True, "US", "格式通過", formatted)


def _validate_jp(tax_id: str) -> ValidationResult:
    """日本法人番號：13 位數字 + checksum。"""
    cleaned = re.sub(r"[\s\-]", "", tax_id)
    if not re.fullmatch(r"\d{13}", cleaned):
        return ValidationResult(False, "JP", "日本法人番號需 13 位數字")
    # checksum: 第 1 位 = 9 - ((Σ_{i=2}^{13} P_n * Q_n) mod 9)
    # P = 2,1,2,1,2,1,2,1,2,1,2,1 (倒序)
    # 因為實際 demo 沒場景，暫做格式檢查
    return ValidationResult(True, "JP", "格式通過", cleaned)


def _validate_eu_vat(tax_id: str) -> ValidationResult:
    """EU VAT number：國家碼 2 字母 + 數字（長度依國家）。"""
    cleaned = re.sub(r"[\s\-]", "", tax_id).upper()
    m = re.fullmatch(r"([A-Z]{2})([0-9A-Z]+)", cleaned)
    if not m:
        return ValidationResult(False, "EU", "EU VAT 需國家碼 + 數字（如 DE123456789）")
    country, num = m.group(1), m.group(2)
    valid_countries = {
        "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES",
        "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
        "NL", "PL", "PT", "RO", "SE", "SI", "SK", "XI",  # XI = N. Ireland
    }
    if country not in valid_countries:
        return ValidationResult(False, f"EU-{country}", f"{country} 不是有效 EU VAT 國家碼")
    # 完整 checksum 各國規則不同（DE 用 mod 11、FR 用 mod 97 等）
    return ValidationResult(True, f"EU-{country}", "格式通過（完整 checksum 各國不同）", cleaned)


def _validate_passthrough(tax_id: str) -> ValidationResult:
    """通用 / 不驗證：只去空白，永遠回 true。給未支援的國家或沒統編的客戶。"""
    cleaned = tax_id.strip()
    if not cleaned:
        return ValidationResult(False, "GENERIC", "不可為空")
    return ValidationResult(True, "GENERIC", "未做 checksum，僅去空白", cleaned)


# ─── Registry ─────────────────────────────────────────────

_REGISTRY: dict[str, Callable[[str], ValidationResult]] = {
    "TW": _validate_tw,
    "CN": _validate_cn,
    "US": _validate_us,
    "JP": _validate_jp,
    "EU": _validate_eu_vat,
    "GENERIC": _validate_passthrough,
}

# 支援國家列表 (給 frontend dropdown 用)
SUPPORTED_COUNTRIES = [
    {"code": "TW", "name": "🇹🇼 台灣 統一編號（8 碼）"},
    {"code": "CN", "name": "🇨🇳 中國 統一社會信用代碼（18 碼）"},
    {"code": "US", "name": "🇺🇸 美國 EIN（9 碼）"},
    {"code": "JP", "name": "🇯🇵 日本 法人番號（13 碼）"},
    {"code": "EU", "name": "🇪🇺 EU VAT（國家碼 + 數字）"},
    {"code": "GENERIC", "name": "🌐 通用（不驗證 checksum）"},
]


def validate(tax_id: str, country: str = "TW") -> ValidationResult:
    """主驗證入口。country 不在 registry → 走 GENERIC。"""
    if not tax_id:
        return ValidationResult(False, country, "不可為空")
    validator = _REGISTRY.get(country.upper(), _validate_passthrough)
    return validator(tax_id)


def register_validator(country: str, fn: Callable[[str], ValidationResult]) -> None:
    """讓 plugin / 客戶自定義國家 validator。

    Usage:
        from app.integrations.tax_id_validators import register_validator

        def my_ke_validator(tax_id: str) -> ValidationResult:
            ...
        register_validator("KE", my_ke_validator)  # 肯亞
    """
    _REGISTRY[country.upper()] = fn


def list_supported() -> list[dict]:
    """回支援國家列表（含未在 SUPPORTED_COUNTRIES 但被 register_validator 加入的）。"""
    extra = [c for c in _REGISTRY.keys() if c not in {x["code"] for x in SUPPORTED_COUNTRIES}]
    return SUPPORTED_COUNTRIES + [{"code": c, "name": f"🔌 {c}（自定義）"} for c in extra]
