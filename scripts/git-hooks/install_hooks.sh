#!/usr/bin/env bash
# ============================================================
#  erpilot · 安裝 git hooks（一鍵）
#  Mac / Linux / Git Bash on Windows 都能跑
# ============================================================
set -e

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
HOOKS_SRC="$REPO_ROOT/scripts/git-hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

if [ ! -d "$REPO_ROOT/.git" ]; then
    echo "❌ 找不到 .git 目錄。請先 git clone / git init"
    exit 1
fi

echo "📦 安裝 erpilot git hooks..."

for hook in pre-commit; do
    if [ -f "$HOOKS_SRC/$hook" ]; then
        cp "$HOOKS_SRC/$hook" "$HOOKS_DST/$hook"
        chmod +x "$HOOKS_DST/$hook"
        echo "  ✓ $hook"
    fi
done

echo "✅ 完成。從現在起每次 git commit 都會自動掃 secrets。"
echo "   跳過機制：git commit --no-verify（不建議）"
