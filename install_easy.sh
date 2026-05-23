#!/usr/bin/env bash
# ============================================================
#  Ouvoca 簡易安裝 (Mac / Linux) / Easy Installer
# ============================================================
#  Detects Python 3.11+ and Node 18+ ; suggests install commands
#  if missing. No Docker required.
#
#  Run with: bash install_easy.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

# ANSI colors (degrade gracefully if not a TTY)
if [ -t 1 ]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
else
    GREEN=''; RED=''; YELLOW=''; NC=''
fi
ok()   { echo -e "  ${GREEN}OK${NC} $*"; }
warn() { echo -e "  ${YELLOW}WARN${NC} $*"; }
err()  { echo -e "  ${RED}X${NC} $*" >&2; }

echo ""
echo "  ============================================================"
echo "    Ouvoca AI ERP - Easy Installer (Mac / Linux)"
echo "  ============================================================"
echo ""

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Darwin*) PLATFORM=mac ;;
    Linux*)  PLATFORM=linux ;;
    *) err "Unsupported OS: $OS"; exit 1 ;;
esac

# ─── Step 1: Python ──────────────────────────────────────────
echo "[Step 1/5] Python 3.11+"
echo "--------------------------------------------------------------"
PY_BIN=""
for cand in python3.12 python3.11 python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        ver=$("$cand" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
        major=${ver%%.*}; minor=${ver##*.}
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PY_BIN="$cand"
            ok "Python $ver found: $(command -v "$cand")"
            break
        fi
    fi
done

if [ -z "$PY_BIN" ]; then
    err "Python 3.11+ not found"
    echo ""
    if [ "$PLATFORM" = "mac" ]; then
        echo "  Install with Homebrew:"
        echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "    brew install python@3.11"
    else
        echo "  Ubuntu / Debian:  sudo apt install -y python3.11 python3.11-venv python3-pip"
        echo "  Fedora / RHEL:    sudo dnf install -y python3.11 python3-pip"
        echo "  Arch:             sudo pacman -S python python-pip"
    fi
    echo ""
    exit 1
fi

# ─── Step 2: Node.js ─────────────────────────────────────────
echo ""
echo "[Step 2/5] Node.js 18+"
echo "--------------------------------------------------------------"
if command -v node >/dev/null 2>&1; then
    NODE_VER=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VER" -ge 18 ]; then
        ok "Node.js v$NODE_VER found"
    else
        err "Node.js v$NODE_VER too old (need 18+)"
        if [ "$PLATFORM" = "mac" ]; then
            echo "  Upgrade with: brew install node@20 && brew link --force --overwrite node@20"
        else
            echo "  Use NodeSource: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs"
        fi
        exit 1
    fi
else
    err "Node.js not found"
    echo ""
    if [ "$PLATFORM" = "mac" ]; then
        echo "  Install with Homebrew:  brew install node@20"
    else
        echo "  Ubuntu / Debian:"
        echo "    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
        echo "    sudo apt install -y nodejs"
        echo "  Fedora:  sudo dnf install -y nodejs"
        echo "  Arch:    sudo pacman -S nodejs npm"
    fi
    echo ""
    exit 1
fi

# ─── Step 3: Backend ─────────────────────────────────────────
echo ""
echo "[Step 3/5] 後端套件 / Backend dependencies"
echo "--------------------------------------------------------------"
if [ ! -f backend/.env ]; then
    if [ -f backend/.env.example ]; then
        cp backend/.env.example backend/.env
        NEW_JWT=$("$PY_BIN" -c 'import secrets; print(secrets.token_hex(32))')
        if [ "$PLATFORM" = "mac" ]; then
            sed -i '' "s|change-me-in-production-please-use-openssl-rand-hex-32|$NEW_JWT|g" backend/.env
        else
            sed -i "s|change-me-in-production-please-use-openssl-rand-hex-32|$NEW_JWT|g" backend/.env
        fi
        ok "backend/.env created with random JWT_SECRET"
    else
        err "backend/.env.example missing"
        exit 1
    fi
fi

if [ ! -d backend/venv ]; then
    echo "  Creating virtual environment..."
    "$PY_BIN" -m venv backend/venv
fi

# shellcheck disable=SC1091
source backend/venv/bin/activate
echo "  Installing backend packages (first time: 2-5 min)..."
python -m pip install --upgrade pip --quiet --disable-pip-version-check
pip install -r backend/requirements.txt --quiet --disable-pip-version-check
ok "Backend dependencies ready"

# ─── Step 4: Frontend ────────────────────────────────────────
echo ""
echo "[Step 4/5] 前端套件 / Frontend dependencies"
echo "--------------------------------------------------------------"
pushd frontend-desktop >/dev/null
if [ ! -d node_modules ]; then
    echo "  Installing frontend packages (first time: 3-8 min)..."
    npm install --silent --no-audit --no-fund
fi
ok "Frontend dependencies ready"
popd >/dev/null

# ─── Step 5: Seed DB ─────────────────────────────────────────
echo ""
echo "[Step 5/5] 資料庫初始化 / Database seeding"
echo "--------------------------------------------------------------"
if [ ! -f backend/.seeded ]; then
    pushd backend >/dev/null
    PYTHONIOENCODING=utf-8 python -m scripts.seed && touch .seeded && ok "Database seeded" || warn "Seed failed - DB may already exist"
    popd >/dev/null
else
    ok "Database already seeded"
fi

echo ""
echo "  ============================================================"
echo "    安裝完成！Installation complete!"
echo ""
echo "    登入帳密 / Login: admin / admin123"
echo "    (請首次登入後立即修改密碼 / change after first login)"
echo ""
echo "    下次啟動 / Next launch:  bash start.sh"
echo "  ============================================================"
echo ""

read -p "現在啟動嗎 / Launch now? (Y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    bash start.sh
fi
