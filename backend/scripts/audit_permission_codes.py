"""M1-0 權限碼對齊審計工具 — audit_permission_codes.

目的：
  找出「程式碼引用的權限碼」與「DB 已 seed 的 PermissionDef.code」之間的不一致。
  在 CI 當 gate（存在 MISSING 即 exit 1），防止：
    - require_permission("...") 引用未定義碼 → 所有人 fail-closed（403）
    - LLM tool 的 required_permission 引用未定義碼 → agents_exec 對一般使用者永遠 403

掃描範圍：
  1. backend/app/**/*.py 中 require_permission("<code>") 字面量
  2. backend/app/**/*.py 中 @register_tool(... required_permission="<code>") 字面量

對照資料：
  3. DB 中 PermissionDef.code（需先跑過 scripts.seed_permissions）
  4. backend/data/permission_alias.json 同義組（組內任一碼被引用 → 整組都必須存在，
     用於 tax.* ↔ accounting.einvoice.* 等 canonical/legacy 並存）

使用：
  python -m scripts.audit_permission_codes            # 全量審計（MISSING → exit 1）
  python -m scripts.audit_permission_codes --json      # CI 機器可讀（stdout JSON）
"""
from __future__ import annotations

import ast
import asyncio
import json
import sys
from pathlib import Path

# Windows console（cp950）無法輸出 emoji/方框符號 → 強制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
ALIAS_FILE = BACKEND_ROOT / "data" / "permission_alias.json"

# 靜態掃描參照用（避免 import app 造成啟動副作用）
_SCAN_DIRS = [APP_ROOT]
# ORPHAN 判斷時，seed_permissions.py 內的 wildcard pattern（如 "sales.*"）也算引用
_SEED_ROLES_FILE = BACKEND_ROOT / "scripts" / "seed_permissions.py"


def _collect_file_refs(py: Path, refs: dict[str, list[tuple[str, int]]]) -> None:
    """以 ast 收集單一 .py 檔內的權限碼字面量引用。"""
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return
    rel = str(py.relative_to(BACKEND_ROOT))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # require_permission("code") — func 為 Name
        if isinstance(node.func, ast.Name) and node.func.id == "require_permission":
            if node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                refs.setdefault(node.args[0].value, []).append((rel, node.lineno))
        # 任何 Call 的 required_permission="code" keyword（register_tool 等）
        for kw in node.keywords:
            if kw.arg == "required_permission" and isinstance(kw.value, ast.Constant) \
                    and isinstance(kw.value.value, str):
                refs.setdefault(kw.value.value, []).append((rel, node.lineno))


def scan_referenced_codes() -> dict[str, list[tuple[str, int]]]:
    """掃描全部 target 目錄，回 {code: [(file, line), ...]}。"""
    refs: dict[str, list[tuple[str, int]]] = {}
    for scan_dir in _SCAN_DIRS:
        for py in sorted(scan_dir.rglob("*.py")):
            _collect_file_refs(py, refs)
    return refs


def load_alias_groups() -> dict[str, list[str]]:
    """讀同義權限碼組（group_name -> codes）。檔案不存在回空 dict。"""
    if not ALIAS_FILE.exists():
        return {}
    return json.loads(ALIAS_FILE.read_text(encoding="utf-8"))


def _code_to_group(alias_groups: dict[str, list[str]]) -> dict[str, str]:
    """code -> group_name 反查表（重複宣告時取第一個）。"""
    out: dict[str, str] = {}
    for group, codes in alias_groups.items():
        for c in codes:
            out.setdefault(c, group)
    return out


async def load_db_codes() -> set[str]:
    """連 DB 讀全部 PermissionDef.code（需先 seed）。"""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal, init_db
    from app.models.permission import PermissionDef

    await init_db()
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(PermissionDef.code))).scalars().all()
        return set(rows)


def _seed_file_text() -> str:
    try:
        return _SEED_ROLES_FILE.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def audit(db_codes: set[str]) -> dict:
    """執行審計，回結構化結果。"""
    refs = scan_referenced_codes()
    alias_groups = load_alias_groups()
    code_to_group = _code_to_group(alias_groups)
    seed_text = _seed_file_text()

    missing: list[dict] = []     # 引用但 DB 不存在（硬 gate）
    orphan: list[str] = []       # DB 存在但無任何引用（警告）
    ok_aliased: list[str] = []   # 引用且由 alias 組補足

    for code, locations in sorted(refs.items()):
        if code in db_codes:
            continue
        group = code_to_group.get(code)
        if group is not None:
            members = alias_groups[group]
            absent = sorted(m for m in members if m not in db_codes)
            if absent:
                missing.append({
                    "code": code, "group": group, "absent_members": absent,
                    "locations": locations,
                })
            else:
                ok_aliased.append(code)
        else:
            missing.append({"code": code, "group": None, "absent_members": [], "locations": locations})

    for code in sorted(db_codes):
        if code in refs:
            continue
        if code in code_to_group:
            continue
        if code in seed_text:  # seed_permissions.py 內 ROLES wildcard / 明細引用
            continue
        orphan.append(code)

    return {
        "referenced_total": len(refs),
        "seeded_total": len(db_codes),
        "ok_aliased": ok_aliased,
        "missing": missing,
        "orphan": orphan,
    }


def _print_human(result: dict) -> int:
    print("權限碼審計 / Permission code audit")
    print(f"  引用數 referenced : {result['referenced_total']}")
    print(f"  DB 數 seeded      : {result['seeded_total']}")
    print(f"  alias 補足        : {len(result['ok_aliased'])}")

    missing = result["missing"]
    if missing:
        print("\n❌ MISSING（引用但未 seed，必須修復）:")
        for m in missing:
            group_note = f" [alias 組: {m['group']} 缺 {', '.join(m['absent_members'])}]" if m["absent_members"] else ""
            locs = ", ".join(f"{f}:{l}" for f, l in m["locations"][:3])
            print(f"  - {m['code']}{group_note}   @ {locs}")
    else:
        print("\n✅ 無 MISSING")

    if result["orphan"]:
        print(f"\n⚠️  ORPHAN（seed 但無引用，僅警告）: {len(result['orphan'])}")
        print("  " + ", ".join(result["orphan"]))
    return 1 if missing else 0


def _print_json(result: dict) -> int:
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 1 if result["missing"] else 0


async def main_async() -> int:
    db_codes = await load_db_codes()
    if not db_codes:
        print("⚠️  DB 沒有任何 PermissionDef — 請先執行 python -m scripts.seed_permissions",
              file=sys.stderr)
        return 2
    result = audit(db_codes)
    use_json = "--json" in sys.argv
    return _print_json(result) if use_json else _print_human(result)


def main() -> None:
    sys.exit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
