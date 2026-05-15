"""Schema Mapping AI — 對映外部 DB schema → LLM-ERP domain（v3.4）。

設計目標（demo moment 3 解鎖）：
  使用者：「把鼎新的客戶搬過來」
  AI：
    1. 取鼎新 Customer table 的 schema → [CustNo, CustName, Grade, Phone, ...]
    2. 比對 LLM-ERP Customer 標準欄位 → 自動推薦 mapping
       CustNo  → code   (confidence 0.95)
       CustName → name   (confidence 0.95)
       Grade   → grade  (confidence 1.0)
       Phone   → contact_phone (confidence 0.85)
    3. 出 ConfirmCard 讓使用者點確認後執行 migration

推薦演算法（PoC）：
  - exact name match → 1.0
  - 別名 match → 0.9（透過 alias dict）
  - substring match → 0.7
  - LLM 推測 → 0.6（Phase 2 才加，PoC 用規則式）

設計：see docs/EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md §7
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FieldMapping:
    """單一欄位對映建議。"""
    target_field: str          # LLM-ERP 標準欄位名
    target_type: str           # 預期型別
    source_field: Optional[str]  # 外部 DB 對應欄位（None = 找不到）
    source_type: Optional[str]
    confidence: float          # 0.0-1.0
    reason: str = ""           # 為什麼這樣對映（給 ConfirmCard 顯示用）
    required: bool = False     # 此欄位是否 LLM-ERP 必填


# ────────────────────────────────────────────────────────────
# 目標 domain schema + 別名定義（給對映 AI 用）
# ────────────────────────────────────────────────────────────

# 每個 entry：(target_field, type, aliases, required, note)
TARGET_SCHEMAS: dict[str, list[tuple[str, str, list[str], bool, str]]] = {
    "customer": [
        ("code",          "string", ["custno", "customer_no", "cust_no", "code", "客戶編號"], True,  "客戶唯一編號"),
        ("name",          "string", ["custname", "customer_name", "cust_name", "name", "客戶名稱"], True,  "客戶名稱"),
        ("grade",         "string", ["grade", "level", "tier", "等級", "客戶等級"], False, "客戶分級 A/B/C/D"),
        ("contact_person","string", ["contact", "contact_person", "contact_name", "聯絡人"], False, "聯絡人姓名"),
        ("contact_email", "string", ["email", "mail", "contact_email", "電子郵件"], False, "電子郵件"),
        ("contact_phone", "string", ["phone", "tel", "telephone", "contact_phone", "電話"], False, "電話"),
        ("address",       "string", ["address", "addr", "location", "地址"], False, "地址"),
        ("payment_terms", "string", ["payment_terms", "terms", "payment", "付款條件"], False, "付款條件"),
        ("credit_limit",  "float",  ["credit_limit", "credit", "limit", "信用額度"], False, "信用額度"),
    ],
    "supplier": [
        ("code",          "string", ["supplierno", "supplier_no", "code", "供應商編號"], True,  "供應商唯一編號"),
        ("name",          "string", ["suppliername", "supplier_name", "name", "供應商名稱"], True,  "供應商名稱"),
        ("tier",          "string", ["tier", "level", "rank", "等級", "供應商等級"], False, "供應商分級 T1/T2/T3"),
        ("contact_person","string", ["contact", "contact_person", "聯絡人"], False, "聯絡人"),
        ("contact_email", "string", ["email", "contact_email"], False, "Email"),
        ("contact_phone", "string", ["phone", "tel", "contact_phone"], False, "電話"),
        ("address",       "string", ["address", "addr", "地址"], False, "地址"),
        ("payment_terms", "string", ["payment_terms", "terms", "付款條件"], False, "付款條件"),
        ("lead_time_days","integer",["lead_time", "lead_time_days", "leadtime", "交期天數"], False, "預設交期"),
        ("is_approved",   "boolean",["approved", "is_approved", "active", "已核准"], False, "是否已核准"),
    ],
    "part": [
        ("part_no",       "string", ["partno", "part_no", "item_no", "sku", "料號"], True,  "料件編號"),
        ("name",          "string", ["partname", "part_name", "item_name", "name", "料件名稱"], True,  "料件名稱"),
        ("description",   "string", ["description", "desc", "說明"], False, "說明"),
        ("category",      "string", ["category", "type", "class", "類別"], False, "類別"),
        ("unit",          "string", ["unit", "uom", "單位"], False, "計量單位"),
        ("safety_stock",  "float",  ["safety_stock", "safetystock", "min_qty", "安全庫存"], False, "安全庫存"),
        ("unit_cost",     "float",  ["unit_cost", "cost", "price", "標準成本"], False, "標準成本"),
        ("lead_time_days","integer",["lead_time", "lead_time_days", "交期"], False, "採購交期"),
    ],
}


def get_target_schema(domain: str) -> Optional[list[tuple]]:
    return TARGET_SCHEMAS.get(domain)


def list_supported_domains() -> list[str]:
    return sorted(TARGET_SCHEMAS.keys())


# ────────────────────────────────────────────────────────────
# Mapping AI 演算法
# ────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    """欄位名 normalize：lower、移除底線。"""
    return s.lower().replace("_", "").strip()


def suggest_mapping(
    source_schema: list[dict],
    target_domain: str,
) -> dict:
    """為 source_schema 推薦對應 target_domain 的欄位 mapping。

    Args:
        source_schema: [{name, type, nullable?, ...}, ...]
        target_domain: "customer" | "supplier" | "part"

    Returns:
        {
            "mappings": list[FieldMapping as dict],
            "unmapped_source_fields": list[dict],
            "confidence_summary": {high, medium, low, missing},
            "required_satisfied": bool,
        }
    """
    target = get_target_schema(target_domain)
    if target is None:
        return {
            "error": f"未支援的 target_domain: {target_domain}",
            "supported": list_supported_domains(),
        }

    # source 欄位 normalized lookup
    source_by_norm: dict[str, dict] = {_normalize(s["name"]): s for s in source_schema}
    source_by_orig: dict[str, dict] = {s["name"]: s for s in source_schema}

    mappings: list[dict] = []
    used_source_fields: set[str] = set()

    for target_field, target_type, aliases, required, note in target:
        match: Optional[str] = None
        confidence = 0.0
        reason = ""
        source_type: Optional[str] = None

        target_norm = _normalize(target_field)
        alias_norms = [_normalize(a) for a in aliases]

        # 1. exact match（normalized）
        for src_field in source_schema:
            sn = _normalize(src_field["name"])
            if sn == target_norm:
                match, confidence, reason = src_field["name"], 1.0, f"精確匹配 {target_field}"
                source_type = src_field.get("type")
                break

        # 2. alias match
        if match is None:
            for src_field in source_schema:
                sn = _normalize(src_field["name"])
                if sn in alias_norms:
                    match, confidence, reason = src_field["name"], 0.9, f"已知別名「{src_field['name']}」"
                    source_type = src_field.get("type")
                    break

        # 3. substring match（target_norm 是 source 的子字串，或反之）
        if match is None:
            best_partial: Optional[tuple[str, float, str, str]] = None
            for src_field in source_schema:
                sn = _normalize(src_field["name"])
                if sn in used_source_fields:
                    continue
                if target_norm and target_norm in sn:
                    score = 0.7 + 0.1 * (len(target_norm) / max(len(sn), 1))
                    if best_partial is None or score > best_partial[1]:
                        best_partial = (
                            src_field["name"], score,
                            f"包含關鍵字「{target_field}」", src_field.get("type", "")
                        )
                # 或 alias 的子字串
                for a in alias_norms:
                    if a and (a in sn or sn in a):
                        score = 0.65
                        if best_partial is None or score > best_partial[1]:
                            best_partial = (
                                src_field["name"], score,
                                f"與別名「{a}」相似", src_field.get("type", "")
                            )
            if best_partial:
                match, confidence, reason, source_type = best_partial

        if match is not None:
            used_source_fields.add(_normalize(match))

        mappings.append({
            "target_field": target_field,
            "target_type": target_type,
            "source_field": match,
            "source_type": source_type,
            "confidence": round(confidence, 2),
            "reason": reason or "找不到對應欄位",
            "required": required,
            "note": note,
        })

    # unmapped source fields
    unmapped = [
        s for s in source_schema
        if _normalize(s["name"]) not in used_source_fields
    ]

    # confidence summary
    high = sum(1 for m in mappings if m["confidence"] >= 0.9)
    medium = sum(1 for m in mappings if 0.6 <= m["confidence"] < 0.9)
    low = sum(1 for m in mappings if 0 < m["confidence"] < 0.6)
    missing = sum(1 for m in mappings if m["confidence"] == 0)

    # required satisfied?
    required_satisfied = all(
        m["confidence"] > 0 for m in mappings if m["required"]
    )

    return {
        "target_domain": target_domain,
        "total_target_fields": len(mappings),
        "mappings": mappings,
        "unmapped_source_fields": unmapped,
        "confidence_summary": {
            "high": high,
            "medium": medium,
            "low": low,
            "missing": missing,
        },
        "required_satisfied": required_satisfied,
    }
