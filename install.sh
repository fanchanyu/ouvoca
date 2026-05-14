#!/usr/bin/env bash
# ============================================================
#  LLM-ERP 一鍵安裝腳本（Mac / Linux）
#  LLM-ERP One-Click Installer (Mac / Linux)
# ============================================================
#  用法 Usage:
#    chmod +x install.sh && ./install.sh
#
#  這個腳本會：This script will:
#    1. 檢查 Docker 是否安裝 / Check Docker
#    2. 自動產生 JWT_SECRET / Auto-generate JWT_SECRET
#    3. 啟動所有服務 / Start all services
#    4. 載入示範資料 / Seed demo data
#    5. 自動開啟瀏覽器 / Open browser
# ============================================================

set -e

# 顏色 / Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 檢測語言 / Detect language
case "$LANG" in
  zh*) LANGCODE="zh" ;;
  *)   LANGCODE="en" ;;
esac

msg() {
  if [ "$LANGCODE" = "zh" ]; then echo -e "$1"; else echo -e "$2"; fi
}

clear
echo -e "${CYAN}"
cat <<'EOF'
  ╔══════════════════════════════════════════════════════════╗
  ║                                                          ║
  ║   LLM-ERP · AI-Native ERP for Small Manufacturers       ║
  ║                                                          ║
  ║              一鍵安裝 / One-Click Installer              ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ============================================================
# Step 1: 檢查 Docker
# ============================================================
msg "${BLUE}🔍 步驟 1/5：檢查 Docker...${NC}" "${BLUE}🔍 Step 1/5: Checking Docker...${NC}"

if ! command -v docker &> /dev/null; then
  msg "${RED}❌ 找不到 Docker！${NC}" "${RED}❌ Docker not found!${NC}"
  msg "請先安裝 Docker：https://docs.docker.com/get-docker/" \
      "Please install Docker first: https://docs.docker.com/get-docker/"
  msg "${YELLOW}安裝完 Docker 後，重新執行 ./install.sh${NC}" \
      "${YELLOW}After installing Docker, re-run ./install.sh${NC}"
  exit 1
fi

if ! docker ps &> /dev/null; then
  msg "${RED}❌ Docker 安裝了但沒在運行${NC}" "${RED}❌ Docker installed but not running${NC}"
  msg "請啟動 Docker Desktop 或 systemctl start docker" \
      "Please start Docker Desktop or run: systemctl start docker"
  exit 1
fi

msg "${GREEN}✅ Docker 已安裝且運行中${NC}" "${GREEN}✅ Docker is installed and running${NC}"

# ============================================================
# Step 2: 設定 .env（含自動產生 JWT_SECRET）
# ============================================================
echo
msg "${BLUE}🔐 步驟 2/5：設定環境變數...${NC}" "${BLUE}🔐 Step 2/5: Configuring environment...${NC}"

ENV_FILE="backend/.env"
if [ ! -f "$ENV_FILE" ]; then
  cp backend/.env.example "$ENV_FILE"
  msg "  ✓ 已建立 .env" "  ✓ Created .env"

  # 自動產生 JWT_SECRET
  if command -v openssl &> /dev/null; then
    SECRET=$(openssl rand -hex 32)
  else
    SECRET=$(head -c 32 /dev/urandom | xxd -p -c 32)
  fi

  # macOS / Linux sed 差異
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|change-me-in-production-please-use-openssl-rand-hex-32|$SECRET|" "$ENV_FILE"
  else
    sed -i "s|change-me-in-production-please-use-openssl-rand-hex-32|$SECRET|" "$ENV_FILE"
  fi

  msg "  ✓ JWT_SECRET 已自動產生（64 字元）" "  ✓ JWT_SECRET auto-generated (64 chars)"
else
  msg "  ℹ️  .env 已存在，跳過" "  ℹ️  .env already exists, skipping"
fi

# ============================================================
# Step 3: 啟動 Docker Compose
# ============================================================
echo
msg "${BLUE}🐳 步驟 3/5：啟動服務（首次可能要 2-5 分鐘下載映像檔）...${NC}" \
    "${BLUE}🐳 Step 3/5: Starting services (first run takes 2-5 min to pull images)...${NC}"
docker compose up -d --build

# ============================================================
# Step 4: 等 backend 啟動
# ============================================================
echo
msg "${BLUE}⏳ 步驟 4/5：等待後端就緒...${NC}" "${BLUE}⏳ Step 4/5: Waiting for backend...${NC}"
for i in $(seq 1 60); do
  if curl -fsS http://localhost:8000/api/health > /dev/null 2>&1; then
    msg "  ✅ 後端啟動完成（耗時 ${i} 秒）" "  ✅ Backend ready (took ${i}s)"
    break
  fi
  sleep 1
  if [ $((i % 10)) -eq 0 ]; then
    msg "  ⏳ 仍在等待... ($i 秒)" "  ⏳ Still waiting... ($i s)"
  fi
done

# ============================================================
# Step 5: 首次 seed
# ============================================================
echo
msg "${BLUE}🌱 步驟 5/5：載入示範資料...${NC}" "${BLUE}🌱 Step 5/5: Loading demo data...${NC}"

if [ ! -f "backend/.seeded" ]; then
  docker compose exec -T backend python -m scripts.seed
  touch backend/.seeded
  msg "  ✅ 示範資料載入完成" "  ✅ Demo data loaded"
else
  msg "  ℹ️  已 seed 過，跳過" "  ℹ️  Already seeded, skipping"
fi

# ============================================================
# 完成！
# ============================================================
echo
echo -e "${GREEN}"
cat <<'EOF'
  ╔══════════════════════════════════════════════════════════╗
  ║                                                          ║
  ║              🎉  安裝完成 / Installation Done           ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

msg "請打開瀏覽器訪問：" "Open your browser:"
echo
echo -e "  ${CYAN}🖥️  Desktop UI:   ${YELLOW}http://localhost:5173${NC}"
echo -e "  ${CYAN}📡 War Room:     ${YELLOW}http://localhost:8080${NC}"
echo -e "  ${CYAN}📚 API Docs:     ${YELLOW}http://localhost:8000/docs${NC}"
echo

msg "登入 / Login:" "Login:"
echo -e "  ${CYAN}帳號 / Username:${NC}  ${GREEN}admin${NC}"
echo -e "  ${CYAN}密碼 / Password:${NC}  ${GREEN}admin123${NC}"
echo

msg "${YELLOW}💡 提示 / Tip：${NC}" "${YELLOW}💡 Tip:${NC}"
msg "  - 設定 LLM API Key：編輯 backend/.env，填入 LLM_API_KEY" \
    "  - Set LLM API Key: edit backend/.env, fill LLM_API_KEY"
msg "  - 載入行業範例：./load_industry.sh metal" \
    "  - Load industry data: ./load_industry.sh metal"
msg "  - 停止服務：docker compose down" \
    "  - Stop services: docker compose down"
echo

# 嘗試自動開瀏覽器
if [[ "$OSTYPE" == "darwin"* ]]; then
  open http://localhost:5173 2>/dev/null && msg "  🌐 已自動開啟瀏覽器" "  🌐 Browser opened"
elif command -v xdg-open &> /dev/null; then
  xdg-open http://localhost:5173 2>/dev/null && msg "  🌐 已自動開啟瀏覽器" "  🌐 Browser opened"
fi
