#!/usr/bin/env bash
# ============================================================
#  Ouvoca ERP — 完全重置腳本（含資料 / WITH DATA）
#  Full reset script — wipes all data and configuration
# ============================================================

set -e

cat <<'EOF'
╔════════════════════════════════════════════════╗
║  Ouvoca ERP — 完全重置（含資料 / WITH DATA）  ║
╚════════════════════════════════════════════════╝

此動作會：
  • 停止所有容器
  • 刪除所有資料庫資料（demo data）
  • 刪除 backend/.env 設定
  • 下次需重跑 ./install.sh

This will:
  • Stop all containers
  • Delete all database data (demo data)
  • Delete backend/.env configuration
  • You'll need to re-run ./install.sh

EOF

read -p "確定要重置？(輸入 YES 確認 / type YES to confirm): " CONFIRM
if [ "$CONFIRM" != "YES" ]; then
    echo "已取消 / Cancelled"
    exit 0
fi

docker compose down -v
rm -f backend/.seeded
rm -f backend/.env

echo
echo "✓ 已重置 / Reset complete"
echo "  執行 ./install.sh 重新安裝 / Run ./install.sh to reinstall"
