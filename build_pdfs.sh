#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────
# LLM-ERP · 一鍵把所有客戶面向手冊轉成 PDF
# One-click: convert all customer-facing manuals to PDFs
# ────────────────────────────────────────────────────────────────
# 需求 / Requires:
#   • Node.js 18+   (https://nodejs.org/)
#   • npm（隨 Node.js 安裝）
#
# 輸出 / Output: docs/pdf/*.pdf （12 個 PDF）
# ────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📚 LLM-ERP PDF 手冊產生器 / Manual Builder${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 1. Check Node.js
if ! command -v node &> /dev/null; then
  echo -e "${RED}❌ Node.js 未安裝 / Node.js not installed${NC}"
  echo "請先安裝 / Please install: https://nodejs.org/  (LTS, 18 or 20)"
  exit 1
fi
echo -e "${GREEN}✓${NC} Node.js: $(node -v)"

# 2. Install deps if needed
cd scripts/build-pdfs
if [ ! -d node_modules ]; then
  echo -e "${YELLOW}📦 首次執行，安裝依賴中... / Installing dependencies (first run)...${NC}"
  echo -e "${YELLOW}   會下載 ~150MB（含 Chromium for Puppeteer），請耐心${NC}"
  npm install --silent
fi
echo -e "${GREEN}✓${NC} Dependencies ready"

# 3. Run builder
echo ""
node build.mjs

# 4. Open output folder
cd ../..
OUT_DIR="$(pwd)/docs/pdf"
echo ""
echo -e "${GREEN}✅ 完成 / Done${NC}"
echo -e "📂 PDF 在 / PDFs at: ${OUT_DIR}"

# Try to open
if command -v xdg-open &> /dev/null; then
  xdg-open "$OUT_DIR" 2>/dev/null &
elif command -v open &> /dev/null; then
  open "$OUT_DIR"
fi
