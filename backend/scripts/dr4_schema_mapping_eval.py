"""DR4 Schema-Mapping Evaluation — six legacy schemas, customer domain.

Pre-registered: see CII 投稿/eval/PRE_REGISTRATION.md (DR4 sub-section to be added).

Six simulated source schemas covering naming conventions found in Taiwanese SMM
environments are run through `suggest_mapping(source, "customer")`. The output
is dumped to `eval/dr4_schema_mapping_eval.csv` for paper Section 4.5.

Pre-registered metrics per schema:
  - mapped / target field coverage
  - high-confidence (>=0.9), medium (0.6..0.89), missing
  - required_satisfied (code + name both mapped)
  - per-field source -> target audit
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.schema_mapping import suggest_mapping, get_target_schema


# ----------------------------------------------------------------------------
# Six simulated legacy schemas (customer domain)
# ----------------------------------------------------------------------------

SCHEMAS: dict[str, list[dict]] = {
    "DingXin-style": [
        {"name": "CustNo", "type": "str"},
        {"name": "CustName", "type": "str"},
        {"name": "Grade", "type": "str"},
        {"name": "Phone", "type": "str"},
        {"name": "Mobile", "type": "str"},
        {"name": "Address", "type": "str"},
        {"name": "TaxNo", "type": "str"},
        {"name": "CreditLimit", "type": "float"},
        {"name": "PaymentTerms", "type": "str"},
        {"name": "ContactPerson", "type": "str"},
        {"name": "UnknownField", "type": "str"},
    ],
    "ZhengHang-style": [
        {"name": "客戶編號", "type": "str"},
        {"name": "客戶全名", "type": "str"},  # alias 表沒收這個，預期 fallback
        {"name": "等級", "type": "str"},
        {"name": "聯絡電話", "type": "str"},
        {"name": "地址", "type": "str"},
        {"name": "統編", "type": "str"},
        {"name": "信用額度", "type": "float"},
        {"name": "付款條件", "type": "str"},
        {"name": "聯絡人", "type": "str"},
        {"name": "備註", "type": "str"},
    ],
    "SAP-B1-style": [
        {"name": "card_code", "type": "str"},
        {"name": "card_name", "type": "str"},
        {"name": "group_code", "type": "str"},
        {"name": "phone_1", "type": "str"},
        {"name": "phone_2", "type": "str"},
        {"name": "address", "type": "str"},
        {"name": "license_num", "type": "str"},
        {"name": "credit_line", "type": "float"},
        {"name": "pymnt_group", "type": "str"},
        {"name": "cnt_prsn", "type": "str"},
    ],
    "Odoo-style": [
        {"name": "x_studio_partner_code", "type": "str"},
        {"name": "x_studio_partner_name", "type": "str"},
        {"name": "x_studio_partner_grade", "type": "str"},
        {"name": "x_studio_phone", "type": "str"},
        {"name": "x_studio_mobile", "type": "str"},
        {"name": "x_studio_address", "type": "str"},
        {"name": "x_studio_vat", "type": "str"},
        {"name": "x_studio_credit_limit", "type": "float"},
        {"name": "x_studio_payment_term", "type": "str"},
    ],
    "Excel-export": [
        {"name": "code", "type": "str"},
        {"name": "name", "type": "str"},
        {"name": "grade", "type": "str"},
        {"name": "phone", "type": "str"},
        {"name": "mobile", "type": "str"},
        {"name": "address", "type": "str"},
        {"name": "tax_id", "type": "str"},
        {"name": "credit", "type": "float"},
        {"name": "payment", "type": "str"},
        {"name": "contact", "type": "str"},
    ],
    "Minimal": [
        {"name": "id", "type": "str"},
        {"name": "name", "type": "str"},
        {"name": "phone", "type": "str"},
    ],
}


# ----------------------------------------------------------------------------
# Evaluator
# ----------------------------------------------------------------------------

def evaluate_schema(label: str, fields: list[dict]) -> dict:
    target_schema = get_target_schema("customer")
    target_field_names = [t[0] for t in target_schema]
    n_target = len(target_field_names)

    r = suggest_mapping(fields, "customer")
    mappings = r["mappings"]
    required_satisfied = r.get("required_satisfied", False)
    unmapped = r.get("unmapped_source_fields", [])

    by_target = {m["target_field"]: m for m in mappings}
    high = sum(1 for m in mappings if m["confidence"] >= 0.9)
    medium = sum(1 for m in mappings if 0.6 <= m["confidence"] < 0.9)
    low = sum(1 for m in mappings if 0.0 < m["confidence"] < 0.6)
    mapped_targets = set(by_target.keys())
    missing_targets = [t for t in target_field_names if t not in mapped_targets]

    coverage = len(mapped_targets) / n_target if n_target else 0.0
    return {
        "schema": label,
        "source_fields": len(fields),
        "target_fields": n_target,
        "mapped_count": len(mapped_targets),
        "coverage_pct": round(coverage * 100, 1),
        "high_confidence": high,
        "medium_confidence": medium,
        "low_confidence": low,
        "missing_targets": missing_targets,
        "unmapped_source": [u.get("name") if isinstance(u, dict) else u for u in unmapped],
        "required_satisfied": required_satisfied,
        "per_field": {
            tname: {
                "source": by_target[tname]["source_field"],
                "confidence": by_target[tname]["confidence"],
            }
            for tname in by_target
        },
    }


def main() -> int:
    out_dir = Path(__file__).resolve().parents[2] / "CII 投稿" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    print(f"\n{'Schema':16} {'src':4} {'mapped':6} {'cov%':6} {'high':5} {'med':5} {'req?':5}")
    print("-" * 70)
    for label, fields in SCHEMAS.items():
        r = evaluate_schema(label, fields)
        results.append(r)
        print(f"  {label:14} {r['source_fields']:>4} {r['mapped_count']:>6} "
              f"{r['coverage_pct']:>5.1f} {r['high_confidence']:>5} "
              f"{r['medium_confidence']:>5} {str(r['required_satisfied']):>5}")
    print("-" * 70)

    # Overall (exclude Minimal as the manuscript does)
    realistic = [r for r in results if r["schema"] != "Minimal"]
    total_mapped = sum(r["mapped_count"] for r in realistic)
    total_target = sum(r["target_fields"] for r in realistic)
    realistic_required_ok = sum(1 for r in realistic if r["required_satisfied"])
    print(f"\nExcluding Minimal:")
    print(f"  Total mapped:        {total_mapped}/{total_target} "
          f"({100 * total_mapped / max(1, total_target):.1f}%)")
    print(f"  Required satisfied:  {realistic_required_ok}/{len(realistic)}")

    # CSV export
    csv_path = out_dir / "dr4_schema_mapping_eval.csv"
    headers = ["schema", "source_fields", "target_fields", "mapped_count",
               "coverage_pct", "high_confidence", "medium_confidence",
               "low_confidence", "required_satisfied",
               "missing_targets", "unmapped_source"]
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for r in results:
            row = [
                r["schema"], str(r["source_fields"]), str(r["target_fields"]),
                str(r["mapped_count"]), str(r["coverage_pct"]),
                str(r["high_confidence"]), str(r["medium_confidence"]),
                str(r["low_confidence"]), str(r["required_satisfied"]),
                ";".join(r["missing_targets"]),
                ";".join(r["unmapped_source"]),
            ]
            f.write(",".join(row) + "\n")
    print(f"\nCSV: {csv_path}")

    # Full JSON
    json_path = out_dir / "dr4_schema_mapping_eval.json"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
