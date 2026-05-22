@echo off
REM ============================================================
REM  LLM-ERP 一鍵安裝（Windows）/ One-Click Installer (Windows)
REM ============================================================
REM  用法 Usage:
REM    雙擊本檔案 / Double-click this file
REM    或在 cmd 執行 / Or in cmd: install.bat
REM ============================================================

chcp 65001 > nul
setlocal EnableDelayedExpansion

cls
echo.
echo   ============================================================
echo
echo     LLM-ERP - AI-Native ERP for Small Manufacturers
echo
echo                 一鍵安裝 / One-Click Installer
echo
echo   ============================================================
echo.

REM ============================================================
REM Step 1: 檢查 Docker / Check Docker
REM ============================================================
echo [Step 1/5] 檢查 Docker / Checking Docker...

where docker > nul 2>&1
if errorlevel 1 (
    echo.
    echo   X 找不到 Docker！/ Docker not found!
    echo.
    echo   請先安裝 Docker Desktop：
    echo   Please install Docker Desktop first:
    echo   https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

docker ps > nul 2>&1
if errorlevel 1 (
    echo.
    echo   X Docker 沒啟動 / Docker not running
    echo   請啟動 Docker Desktop 後再執行
    echo   Please start Docker Desktop and retry
    echo.
    pause
    exit /b 1
)

echo   OK Docker installed and running
echo.

REM ============================================================
REM Step 2: 設定 .env
REM ============================================================
echo [Step 2/5] 設定環境變數 / Configuring environment...

if not exist "backend\.env" (
    copy backend\.env.example backend\.env > nul

    REM 用 PowerShell 產生 JWT_SECRET
    for /f %%i in ('powershell -Command "[Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(48)).Replace('+','').Replace('/','').Replace('=','').Substring(0,64)"') do set "SECRET=%%i"

    REM 替換預設 JWT_SECRET
    powershell -Command "(Get-Content 'backend\.env') -replace 'change-me-in-production-please-use-openssl-rand-hex-32', '%SECRET%' | Set-Content 'backend\.env'"

    echo   OK .env 已建立，JWT_SECRET 已自動產生
    echo   OK .env created, JWT_SECRET auto-generated
) else (
    echo   i .env 已存在，跳過 / .env exists, skipping
)
echo.

REM ============================================================
REM Step 2.5: Port 預檢（v3.43 P0-1：避免 docker 噴英文錯誤）
REM ============================================================
echo [Step 2.5] 檢查 port 衝突 / Checking port conflicts...
set portbusy=0
for %%p in (8000 5173 8080) do (
    netstat -ano -p tcp | findstr ":%%p " | findstr "LISTENING" > nul
    if not errorlevel 1 (
        echo   X Port %%p 已被佔用 / Port %%p in use
        set portbusy=1
    )
)
if !portbusy! equ 1 (
    echo.
    echo   錯誤 / Error: 部分 port 已被佔用 / Some ports already used.
    echo   請關閉佔用程式或修改 docker-compose.yml 內 port 映射
    echo   Please close occupying programs OR edit docker-compose.yml port mapping
    echo.
    echo   小提示：常見佔用者
    echo     - Skype 可能佔 80/443
    echo     - 其他 dev server 占 5173 / 8080
    echo     - 之前的 Ouvoca 沒關乾淨 → 跑 'docker compose down' 先
    echo.
    pause
    exit /b 1
)
echo   OK 所有 port 都可用 / All ports available
echo.

REM ============================================================
REM Step 3: Docker Compose
REM ============================================================
echo [Step 3/5] 啟動服務 (首次需 2-5 分鐘) / Starting services (first run 2-5min)...
docker compose up -d --build
if errorlevel 1 (
    echo X Docker compose 失敗 / Failed
    pause
    exit /b 1
)
echo.

REM ============================================================
REM Step 4: 等 backend 就緒
REM ============================================================
echo [Step 4/5] 等待後端就緒 / Waiting for backend...
set count=0
:waitloop
set /a count+=1
curl -fsS http://localhost:8000/api/health > nul 2>&1
if errorlevel 1 (
    if !count! geq 60 (
        echo   X 後端超時 / Backend timeout
        pause
        exit /b 1
    )
    timeout /t 1 /nobreak > nul
    if !count! gtr 0 (
        set /a mod=count %% 10
        if !mod! equ 0 echo   等待中... ^(!count!s^)
    )
    goto waitloop
)
echo   OK 後端就緒 ^(!count! 秒^) / Backend ready
echo.

REM ============================================================
REM Step 4.5: 雙重 endpoint 驗證 (Windows Docker Desktop quirk)
REM ============================================================
echo [Step 4.5] 驗證 localhost + 127.0.0.1 雙路徑 / Verifying dual endpoints...

set lh_ok=0
set ip_ok=0
curl -fsS http://localhost:8000/api/health > nul 2>&1
if not errorlevel 1 set lh_ok=1
curl -fsS http://127.0.0.1:8000/api/health > nul 2>&1
if not errorlevel 1 set ip_ok=1

if !lh_ok! equ 1 if !ip_ok! equ 1 (
    echo   OK localhost + 127.0.0.1 都通 / Both endpoints work
) else (
    if !lh_ok! equ 0 echo   X localhost:8000 不通 / localhost:8000 unreachable
    if !ip_ok! equ 0 echo   X 127.0.0.1:8000 不通 / 127.0.0.1:8000 unreachable
    echo.
    echo   提示：Windows Docker Desktop 若 0.0.0.0 bind 不穩，
    echo   docker-compose.yml 已預設綁 127.0.0.1。
    echo   若仍有問題，請改用 http://127.0.0.1:5173 訪問前端。
)
echo.

REM ============================================================
REM Step 5: Seed
REM ============================================================
echo [Step 5/5] 載入示範資料 / Loading demo data...

if not exist "backend\.seeded" (
    docker compose exec -T backend python -m scripts.seed
    echo. > backend\.seeded
    echo   OK 示範資料已載入 / Demo data loaded
) else (
    echo   i 已 seed 過 / Already seeded
)
echo.

REM ============================================================
REM 完成
REM ============================================================
echo.
echo   ============================================================
echo
echo                安裝完成 / Installation Done
echo
echo   ============================================================
echo.
echo   請打開瀏覽器訪問 / Open your browser:
echo.
echo     Desktop UI:   http://localhost:5173
echo     War Room:     http://localhost:8080
echo     API Docs:     http://localhost:8000/docs
echo.
echo   登入 / Login:
echo     帳號 / Username:  admin
echo     密碼 / Password:  admin123
echo.
echo   *** 重要 IMPORTANT (v3.37) ***
echo     登入後請立即在 Chat 講「改密碼」更換預設密碼
echo     After login, immediately say "change password" in Chat
echo.
echo   *** Windows 開機自啟（v3.39 K8）/ Auto-start on boot ***
echo     Ouvoca 由 Docker 跑；Docker Desktop 需要先啟動。
echo     開啟 Docker 設定 ^> General ^> 勾「Start Docker Desktop when you log in」
echo     Open Docker Settings ^> General ^> check "Start Docker Desktop when you log in"
echo     Ouvoca 容器設了 restart: unless-stopped 會自動隨 Docker 啟動。
echo.
echo   提示 / Tip:
echo     - 編輯 backend\.env 填入 LLM_API_KEY 啟用 AI 助手
echo     - Edit backend\.env to set LLM_API_KEY for AI assistant
echo     - 停止服務 / Stop: docker compose down
echo     - 設公司資料：在 Chat 講「公司叫 XX 公司 統編 12345678」
echo.

REM 自動開瀏覽器
start http://localhost:5173

pause
