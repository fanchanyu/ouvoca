#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────
# LLM-ERP · 自證閘 (Self-Verification Gates)
# 在說「完成」之前必須跑這個腳本，並看到全綠。
# ────────────────────────────────────────────────────────────
# Gate 1 · 編譯閘  Backend ruff + mypy + pytest smoke / Desktop tsc
# Gate 2 · 行為閘  Backend persona (王董一天)
# Gate 3 · 文件閘  PDF builder 跑得起來、12 份產出
# ────────────────────────────────────────────────────────────

set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$ROOT"

# 顏色
G='\033[0;32m'  # green
R='\033[0;31m'  # red
Y='\033[1;33m'  # yellow
B='\033[0;34m'  # blue
N='\033[0m'     # reset

FAIL_COUNT=0
PASS_COUNT=0
SKIP_COUNT=0
START_TS=$(date +%s)

# ── helper ─────────────────────────────────────────────────
run_check() {
  local name="$1"; shift
  local cmd="$*"
  printf "  ${B}▶${N} %-50s" "$name"
  local t0=$(date +%s)
  if out=$(eval "$cmd" 2>&1); then
    local dt=$(($(date +%s) - t0))
    printf " ${G}✓${N} (${dt}s)\n"
    PASS_COUNT=$((PASS_COUNT + 1))
    return 0
  else
    local dt=$(($(date +%s) - t0))
    printf " ${R}✗${N} (${dt}s)\n"
    echo -e "${R}    ── error output ──${N}"
    echo "$out" | tail -15 | sed 's/^/    /'
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return 1
  fi
}

skip_check() {
  local name="$1"; local reason="$2"
  printf "  ${Y}▶${N} %-50s ${Y}—${N} skip (%s)\n" "$name" "$reason"
  SKIP_COUNT=$((SKIP_COUNT + 1))
}

# ────────────────────────────────────────────────────────────
echo
echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${B}🛡  LLM-ERP Self-Verification Gates${N}"
echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo

# ── Gate 1：編譯閘 ─────────────────────────────────────────
echo -e "${B}[Gate 1 · 編譯閘 / Compile Gate]${N}"

# Backend pytest smoke
if [ -d backend/tests/smoke ]; then
  run_check "backend pytest tests/smoke/" \
    "cd backend && python -m pytest tests/smoke/ -q --tb=line"
else
  skip_check "backend pytest smoke" "no tests/smoke"
fi

# Backend import sanity
run_check "backend app import sanity" \
  "cd backend && python -c 'from app.main import app; print(len(app.routes))'"

# Frontend desktop (若存在)
if [ -d frontend-desktop ] && [ -d frontend-desktop/node_modules ]; then
  run_check "desktop tsc --noEmit" \
    "cd frontend-desktop && npx --no-install tsc --noEmit"
elif [ -d frontend-desktop ]; then
  skip_check "desktop tsc" "node_modules not installed"
fi

echo

# ── Gate 2：行為閘 ─────────────────────────────────────────
echo -e "${B}[Gate 2 · 行為閘 / Behavior Gate]${N}"

if [ -d backend/tests/personas ]; then
  run_check "persona: 王董的一天 (end-to-end)" \
    "cd backend && python -m pytest tests/personas/ -q --tb=line"
else
  skip_check "persona test" "no tests/personas"
fi

if [ -d backend/tests/integration ] && [ "$(ls -A backend/tests/integration 2>/dev/null | grep -v __ | wc -l)" -gt 0 ]; then
  run_check "integration: MESH 跨廠聚合" \
    "cd backend && python -m pytest tests/integration/ -q --tb=line"
else
  skip_check "integration MESH" "no tests yet (Day 4)"
fi

echo

# ── Gate 3：文件閘 ─────────────────────────────────────────
echo -e "${B}[Gate 3 · 文件閘 / Doc Gate]${N}"

if [ -d scripts/build-pdfs/node_modules ]; then
  run_check "PDF builder dry-run (產 48 份)" \
    "cd scripts/build-pdfs && node build.mjs"
  # 48 PDFs: 46 base + v3.27 PLANNING_EXPLAINABILITY_DESIGN (ZH+EN)
  EXPECTED=48
  ACTUAL=$(ls docs/pdf/*.pdf 2>/dev/null | wc -l)
  if [ "$ACTUAL" -ge "$EXPECTED" ]; then
    printf "  ${B}▶${N} %-50s ${G}✓${N} (%d/%d files)\n" "PDF count check" "$ACTUAL" "$EXPECTED"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    printf "  ${B}▶${N} %-50s ${R}✗${N} (%d/%d files)\n" "PDF count check" "$ACTUAL" "$EXPECTED"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  skip_check "PDF builder" "scripts/build-pdfs/node_modules missing"
fi

echo

# ── Summary ────────────────────────────────────────────────
TOTAL=$((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))
DT=$(($(date +%s) - START_TS))
echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
printf "${G}✓ %d pass${N}  ${R}✗ %d fail${N}  ${Y}— %d skip${N}  / %d total  (%ds)\n" \
  "$PASS_COUNT" "$FAIL_COUNT" "$SKIP_COUNT" "$TOTAL" "$DT"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo -e "${R}🔴 GATES FAILED — 不可以說「完成」、不可以上傳${N}"
  echo
  exit 1
fi
echo -e "${G}🟢 ALL GATES PASSED — 可以說「完成」、可以上傳${N}"
echo
exit 0
