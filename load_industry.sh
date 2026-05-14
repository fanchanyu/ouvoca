#!/usr/bin/env bash
# 載入特定行業範例資料 / Load industry-specific demo data
# 用法 Usage:
#   ./load_industry.sh metal     # 金屬加工 / Metal machining
#   ./load_industry.sh plastic   # 塑膠射出 / Plastic injection
#   ./load_industry.sh pcb       # PCB 電子 / PCB assembly
#   ./load_industry.sh food      # 食品加工 / Food processing
#   ./load_industry.sh textile   # 紡織印染 / Textile dyeing
#   ./load_industry.sh all       # 全部 / All five

set -e

INDUSTRY="${1:-}"

if [ -z "$INDUSTRY" ]; then
  echo "用法 Usage: ./load_industry.sh <industry>"
  echo ""
  echo "可選 / Options:"
  echo "  metal    - 金屬加工 / Metal machining"
  echo "  plastic  - 塑膠射出 / Plastic injection"
  echo "  pcb      - PCB 電子 / PCB assembly"
  echo "  food     - 食品加工 / Food processing"
  echo "  textile  - 紡織印染 / Textile dyeing"
  echo "  all      - 全部 / All five"
  exit 1
fi

echo "📦 載入 / Loading: $INDUSTRY ..."
docker compose exec -T backend python -m scripts.seed_industries "$INDUSTRY"
echo "✅ 完成 / Done"
echo "🌐 進入 http://localhost:5173 查看 / Visit to view"
