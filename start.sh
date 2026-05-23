#!/usr/bin/env bash
# ============================================================
#  Ouvoca 啟動器 / One-Click Launcher (Mac / Linux)
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

if [ -t 1 ]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
else
    GREEN=''; RED=''; NC=''
fi
ok()  { echo -e "  ${GREEN}OK${NC} $*"; }
err() { echo -e "  ${RED}X${NC} $*" >&2; }

if [ ! -d backend/venv ] || [ ! -d frontend-desktop/node_modules ]; then
    err "Setup not complete — run: bash install_easy.sh"
    exit 1
fi
if [ ! -f backend/.env ]; then
    err "backend/.env missing — run: bash install_easy.sh"
    exit 1
fi

echo ""
echo "  ============================================================"
echo "    Ouvoca AI ERP - Starting"
echo "  ============================================================"
echo ""

# ─── Kill stale instances ───
echo "[1/3] Cleaning up old instances..."
for port in 8000 5173; do
    PID=$(lsof -t -i:"$port" 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill -9 "$PID" 2>/dev/null || true
    fi
done

# ─── Start backend ───
echo "[2/3] Starting backend on :8000..."
(
    cd backend
    # shellcheck disable=SC1091
    source venv/bin/activate
    PYTHONIOENCODING=utf-8 nohup python -m uvicorn app.main:app \
        --host 0.0.0.0 --port 8000 --log-level info \
        > ../logs-backend.txt 2>&1 &
    echo $! > ../.backend.pid
) || { err "Backend failed to start"; exit 1; }

# Wait for backend healthy
RETRIES=30
while [ $RETRIES -gt 0 ]; do
    if curl -s -m 2 http://localhost:8000/api/health >/dev/null 2>&1; then
        ok "Backend healthy"
        break
    fi
    sleep 1
    RETRIES=$((RETRIES - 1))
done
if [ $RETRIES -eq 0 ]; then
    err "Backend not healthy after 30s — check logs-backend.txt"
    exit 1
fi

# ─── Start frontend ───
echo "[3/3] Starting frontend on :5173..."
(
    cd frontend-desktop
    nohup npm run dev > ../logs-frontend.txt 2>&1 &
    echo $! > ../.frontend.pid
)

# Wait for frontend ready
RETRIES=30
while [ $RETRIES -gt 0 ]; do
    if curl -s -m 2 -o /dev/null http://localhost:5173 2>/dev/null; then
        ok "Frontend ready"
        break
    fi
    sleep 1
    RETRIES=$((RETRIES - 1))
done

echo ""
echo "  ============================================================"
echo "    Ouvoca is running!"
echo ""
echo "    開瀏覽器 / Open browser:  http://localhost:5173"
echo "    後端 API / Backend API:    http://localhost:8000"
echo "    登入 / Login: admin / admin123"
echo ""
echo "    停止服務 / Stop services:  bash stop.sh"
echo "    後端 log:                  logs-backend.txt"
echo "    前端 log:                  logs-frontend.txt"
echo "  ============================================================"
echo ""

# Open browser (cross-platform)
if command -v open >/dev/null 2>&1; then
    open http://localhost:5173
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open http://localhost:5173 >/dev/null 2>&1 &
fi
