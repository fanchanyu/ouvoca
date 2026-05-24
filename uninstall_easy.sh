#!/usr/bin/env bash
# ============================================================
#  Ouvoca 解除安裝 (Mac / Linux) / Easy Uninstaller
# ============================================================
#  Removes everything install_easy.sh installed in this folder.
#  Python/Node themselves are NOT removed (they're system-managed
#  via brew/apt; you didn't install them via this script).
# ============================================================
set -uo pipefail
cd "$(dirname "$0")"

if [ -t 1 ]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
else
    GREEN=''; RED=''; YELLOW=''; NC=''
fi
ok()   { echo -e "  ${GREEN}OK${NC} $*"; }
warn() { echo -e "  ${YELLOW}WARN${NC} $*"; }

clear
echo ""
echo "  ============================================================"
echo "    Ouvoca AI ERP - 解除安裝 / Uninstall"
echo "  ============================================================"
echo ""
echo "  將會自動移除 / Will auto-remove:"
echo "    - 執行中的服務 (port 8000 / 5173)"
echo "    - backend/venv"
echo "    - frontend-desktop/node_modules"
echo ""
echo "  稍後會問你（你的資料）/ Will ASK before:"
echo "    - backend/erp.db        (你的 ERP 資料)"
echo "    - backend/uploads/*"
echo "    - backend/.env          (JWT + LLM API Key)"
echo ""
echo "  注意：Python/Node 是你系統裝的（brew/apt），不會動到"
echo "  Note: Python/Node are system-installed (brew/apt), not touched"
echo ""
read -p "確定要解除安裝嗎 / Confirm uninstall? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "  已取消 / Cancelled"
    exit 0
fi

# Step 1: 停止服務
echo ""
echo "[Step 1/3] 停止執行中的服務..."
for port in 8000 5173; do
    PID=$(lsof -t -i:"$port" 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill -9 "$PID" 2>/dev/null || true
    fi
done
[ -f .backend.pid ] && rm -f .backend.pid
[ -f .frontend.pid ] && rm -f .frontend.pid
[ -f logs-backend.txt ] && rm -f logs-backend.txt
[ -f logs-frontend.txt ] && rm -f logs-frontend.txt
ok "服務已停止"

# Step 2: 套件目錄
echo ""
echo "[Step 2/3] 刪除套件目錄..."
[ -d backend/venv ] && rm -rf backend/venv && ok "backend/venv"
[ -d frontend-desktop/node_modules ] && rm -rf frontend-desktop/node_modules && ok "frontend-desktop/node_modules"

# Step 3: 詢問是否刪資料
echo ""
echo "[Step 3/3] 你的資料 / Your data"
echo "--------------------------------------------------------------"
echo "  建議：先備份 backend/erp.db 再刪"
echo "  你的資料在 / Your data is at:"
echo "    - backend/erp.db"
echo "    - backend/uploads/"
echo "    - backend/.env"
echo ""
read -p "也刪除你的 ERP 資料嗎 (不可復原)? (y/N) " -n 1 -r
echo ""
DELETE_DATA=false
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "再次確認：永久刪除你的 ERP 資料? (y/N) " -n 1 -r
    echo ""
    [[ $REPLY =~ ^[Yy]$ ]] && DELETE_DATA=true
fi

if [ "$DELETE_DATA" = true ]; then
    [ -f backend/erp.db ] && rm -f backend/erp.db
    [ -f backend/erp.db-journal ] && rm -f backend/erp.db-journal
    [ -f backend/erp.db-wal ] && rm -f backend/erp.db-wal
    [ -f backend/erp.db-shm ] && rm -f backend/erp.db-shm
    [ -d backend/uploads ] && rm -rf backend/uploads
    [ -f backend/.env ] && rm -f backend/.env
    [ -f backend/.seeded ] && rm -f backend/.seeded
    ok "你的 ERP 資料已全部刪除"
else
    warn "資料保留在 backend/ 內，要手動備份請複製整個 backend/ 資料夾"
fi

# 可選：清 pip/npm cache
echo ""
echo "--------------------------------------------------------------"
echo "  進階：清全域 cache (可釋放 ~500MB)"
echo "    - npm cache:  ~/.npm/"
echo "    - pip cache:  ~/.cache/pip/"
echo ""
read -p "也清這些 cache 嗎? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    npm cache clean --force 2>/dev/null || true
    [ -d "$HOME/.cache/pip" ] && rm -rf "$HOME/.cache/pip"
    ok "Cache 已清除"
else
    ok "Cache 保留"
fi

echo ""
echo "  ============================================================"
echo "    解除安裝完成 / Uninstall complete!"
echo ""
echo "    接下來 / Next:"
echo "      1. 你可以放心刪除整個 Ouvoca 資料夾"
echo "      2. Python/Node 本身在你系統 (brew/apt) — 沒動到"
echo ""
echo "    若要重裝 / To reinstall:"
echo "      bash install_easy.sh"
echo "  ============================================================"
echo ""
