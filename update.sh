#!/usr/bin/env bash
# ============================================================
#  Ouvoca 更新 (Mac / Linux) / Easy Updater
# ============================================================
#  1. Auto-backup your data (erp.db / .env / uploads)
#  2. Download latest code (git pull or zip)
#  3. Update pip + npm packages
#  4. Run DB schema upgrade (alembic)
#  5. Restart services
#
#  Your business data is fully preserved.
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
err()  { echo -e "  ${RED}X${NC} $*" >&2; }

clear
echo ""
echo "  ============================================================"
echo "    Ouvoca AI ERP - 自動更新 / Auto Updater"
echo "  ============================================================"
echo ""
echo "  將會做 6 步 / Will do 6 steps:"
echo "    1. 停止服務 (8000 / 5173)"
echo "    2. 備份你的資料到 backups/YYYYMMDD_HHMMSS/"
echo "    3. 下載最新程式碼 (git pull 或 zip)"
echo "    4. 更新套件 (pip + npm)"
echo "    5. 跑 alembic 升級資料庫"
echo "    6. 重啟服務"
echo ""
echo "  你的資料完全保留 / Your data is preserved"
echo ""
read -p "現在更新嗎 / Update now? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "  已取消 / Cancelled"
    exit 0
fi

# Step 1: 停止服務
echo ""
echo "[Step 1/6] 停止服務..."
for port in 8000 5173; do
    PID=$(lsof -t -i:"$port" 2>/dev/null || true)
    [ -n "$PID" ] && kill -9 "$PID" 2>/dev/null || true
done
[ -f .backend.pid ] && rm -f .backend.pid
[ -f .frontend.pid ] && rm -f .frontend.pid
ok "服務已停止"

# Step 2: 備份
echo ""
echo "[Step 2/6] 備份你的資料..."
TS=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups/$TS"
mkdir -p "$BACKUP_DIR"

[ -f backend/erp.db ]  && cp backend/erp.db  "$BACKUP_DIR/" && ok "erp.db"
[ -f backend/.env ]    && cp backend/.env    "$BACKUP_DIR/" && ok ".env"
[ -d backend/uploads ] && cp -r backend/uploads "$BACKUP_DIR/" && ok "uploads/"

cat > "$BACKUP_DIR/README.txt" <<EOF
Ouvoca 備份 / Backup
建立時間: $(date)

還原方法 / How to restore:
  1. 停止 Ouvoca (bash stop.sh)
  2. cp $BACKUP_DIR/erp.db backend/
  3. cp $BACKUP_DIR/.env backend/
  4. cp -r $BACKUP_DIR/uploads backend/uploads
  5. bash start.sh
EOF

ok "備份已存到 $BACKUP_DIR/"

# Step 3: 下載新程式碼
echo ""
echo "[Step 3/6] 下載最新版程式碼..."

if [ -d .git ] && command -v git >/dev/null 2>&1; then
    echo "  使用 git pull..."
    if ! git pull origin main; then
        err "git pull 失敗 — 可能你改過 code"
        echo "  建議：開新資料夾重裝，從 $BACKUP_DIR/ 還原資料"
        exit 1
    fi
    ok "git pull 完成"
else
    echo "  下載 main branch zip (~10 MB)..."
    mkdir -p tools/downloads
    if ! curl -L --progress-bar -o tools/downloads/update.zip \
        https://github.com/fanchanyu/ouvoca/archive/refs/heads/main.zip; then
        err "下載失敗"
        exit 1
    fi

    rm -rf tools/downloads/update_extract
    mkdir -p tools/downloads/update_extract
    if ! tar -xf tools/downloads/update.zip -C tools/downloads/update_extract; then
        err "解壓失敗"
        exit 1
    fi

    EXTRACT_ROOT=$(find tools/downloads/update_extract -maxdepth 1 -mindepth 1 -type d | head -n 1)

    # rsync 覆蓋，排除使用者資料
    if command -v rsync >/dev/null 2>&1; then
        rsync -a \
          --exclude='backend/erp.db' \
          --exclude='backend/erp.db-*' \
          --exclude='backend/.env' \
          --exclude='backend/.seeded' \
          --exclude='backend/uploads/' \
          --exclude='backend/__pycache__/' \
          --exclude='backend/venv/' \
          --exclude='frontend-desktop/node_modules/' \
          --exclude='tools/' \
          --exclude='backups/' \
          --exclude='.git/' \
          "$EXTRACT_ROOT/" .
    else
        # rsync 不存在的 fallback (Mac 應該都有 rsync，Linux 也有)
        err "rsync 未安裝 — 請手動 cp 或安裝 rsync"
        exit 1
    fi

    rm -rf tools/downloads/update_extract tools/downloads/update.zip
    ok "程式碼已更新"
fi

# Step 4: 更新套件
echo ""
echo "[Step 4/6] 更新套件..."
if [ -d backend/venv ]; then
    # shellcheck disable=SC1091
    source backend/venv/bin/activate
    pip install -r backend/requirements.txt --quiet --disable-pip-version-check || warn "pip 部分失敗"
    ok "Python 套件已更新"
fi

if [ -d frontend-desktop/node_modules ]; then
    (cd frontend-desktop && npm install --silent --no-audit --no-fund)
    ok "Node 套件已更新"
fi

# Step 5: alembic
echo ""
echo "[Step 5/6] 資料庫結構升級..."
if [ -f backend/alembic.ini ] && [ -d backend/venv ]; then
    (cd backend && PYTHONIOENCODING=utf-8 venv/bin/python -m alembic upgrade head 2>/dev/null) \
      && ok "資料庫結構已升級" \
      || warn "alembic upgrade 失敗或無需升級"
fi

# Step 6: 重啟
echo ""
echo "[Step 6/6] 重啟服務..."
echo ""
echo "  ============================================================"
echo "    更新完成！/ Update complete!"
echo "    備份位置 / Backup: $BACKUP_DIR/"
echo ""
echo "    若新版有問題：see $BACKUP_DIR/README.txt 還原"
echo "  ============================================================"
echo ""
read -p "現在啟動嗎 / Launch now? (Y/n) " -n 1 -r
echo ""
[[ $REPLY =~ ^[Nn]$ ]] || bash start.sh
