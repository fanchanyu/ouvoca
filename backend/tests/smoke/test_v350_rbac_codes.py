"""v3.50 RBAC 防漏網測試：每個 require_permission("X") 用到的權限碼都必須在 seed 定義。

緣由
----
audit 發現約 15 個權限碼被 endpoint require_permission(...) 引用，
但 seed_permissions.py 的 PERMISSIONS 清單沒定義 → 非 super_admin 角色拿 403。

這個測試一旦掛掉，就是「又有新 endpoint 引了沒定義的權限」——
請去 backend/scripts/seed_permissions.py 補進去 PERMISSIONS / EXTRA_PERMISSIONS。
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
API_DIR = BACKEND / "app" / "api"
CORE_DIR = BACKEND / "app" / "core"
MIDDLEWARE_DIR = BACKEND / "app" / "middleware"

# 讓 import scripts.seed_permissions 找得到
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


_PERM_RE = re.compile(r"""require_permission\(\s*["']([^"']+)["']""")


def _collect_used_codes() -> set[str]:
    used: set[str] = set()
    for folder in (API_DIR, CORE_DIR, MIDDLEWARE_DIR):
        if not folder.exists():
            continue
        for py in folder.rglob("*.py"):
            src = py.read_text(encoding="utf-8", errors="ignore")
            for m in _PERM_RE.finditer(src):
                used.add(m.group(1))
    return used


def _collect_defined_codes() -> set[str]:
    # 動態 import，避免在 test collection 階段就 fail
    from scripts.seed_permissions import PERMISSIONS, EXTRA_PERMISSIONS

    defined: set[str] = set()
    for perm in PERMISSIONS:
        # tuple 格式：(module, resource, action, name_zh, sensitive, risk)
        if len(perm) >= 3:
            defined.add(f"{perm[0]}.{perm[1]}.{perm[2]}")
    for perm in EXTRA_PERMISSIONS:
        code = perm.get("code") if isinstance(perm, dict) else None
        if code:
            defined.add(code)
    return defined


def test_all_required_permissions_defined_in_seed():
    """每個 require_permission("X") 的 X 都必須在 seed 定義。

    若 fail：把缺漏的 code 加進 backend/scripts/seed_permissions.py
    （3 段格式進 PERMISSIONS、2 段別名進 EXTRA_PERMISSIONS）。
    """
    used = _collect_used_codes()
    defined = _collect_defined_codes()

    missing = sorted(used - defined)

    assert not missing, (
        "以下權限碼被 require_permission() 使用但未在 "
        "seed_permissions.PERMISSIONS / EXTRA_PERMISSIONS 定義：\n"
        f"  {missing}\n"
        "請補進 backend/scripts/seed_permissions.py 並指派給適當 role。"
    )


def test_seed_permissions_have_no_duplicate_codes():
    """同一個 code 不能重複定義（會造成 INSERT unique-constraint 衝突）。"""
    from scripts.seed_permissions import PERMISSIONS, EXTRA_PERMISSIONS

    codes: list[str] = []
    for perm in PERMISSIONS:
        codes.append(f"{perm[0]}.{perm[1]}.{perm[2]}")
    for perm in EXTRA_PERMISSIONS:
        if isinstance(perm, dict) and perm.get("code"):
            codes.append(perm["code"])

    dupes = sorted({c for c in codes if codes.count(c) > 1})
    assert not dupes, f"seed 內出現重複的 permission code：{dupes}"


def test_used_codes_nonempty_sanity():
    """sanity：至少應該抓到一些 require_permission() 呼叫——
    若拿到 0 個，代表 regex 或路徑斷了，而不是真的沒人用。
    """
    used = _collect_used_codes()
    assert len(used) > 10, (
        f"只抓到 {len(used)} 個 require_permission() 呼叫——"
        "regex 或 API_DIR 路徑可能斷了，請檢查測試本身。"
    )
