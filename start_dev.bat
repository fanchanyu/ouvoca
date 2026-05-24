@echo off
REM ============================================================
REM  Ouvoca - One-click dev environment startup (Windows)
REM ============================================================
REM  Launches:
REM    1. Backend  (uvicorn :8000)  in a new console window
REM    2. Frontend (vite :5173)     in a new console window
REM    3. Opens http://localhost:5173 in default browser
REM
REM  To stop everything, run stop_dev.bat
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM --- Prefer bundled tools (from install_easy.bat) ---
if exist "tools\python\python.exe" (
    set "PATH=%CD%\tools\python;%CD%\tools\python\Scripts;%PATH%"
)
if exist "tools\node\node.exe" (
    set "PATH=%CD%\tools\node;%PATH%"
)
if exist "backend\venv\Scripts\activate.bat" (
    set "PATH=%CD%\backend\venv\Scripts;%PATH%"
)

echo.
echo ================================================================
echo   Ouvoca dev environment - one-click startup
echo ================================================================
echo.

REM ---- Step 1: Sanity checks ----
echo [1/5] Sanity checks...

where python >nul 2>nul
if errorlevel 1 (
    echo   [ERROR] Python not on PATH.
    echo           Recommended: double-click install_easy.bat to auto-install Python 3.11
    echo           推薦 / Recommended: 雙擊 install_easy.bat 自動安裝 Python 3.11
    echo           或自己裝 / Or install manually: Python 3.11 ^(not 3.12+^)
    pause
    exit /b 1
)
echo   [OK] Python found

where node >nul 2>nul
if errorlevel 1 (
    echo   [ERROR] Node.js not on PATH.
    echo           Recommended: double-click install_easy.bat to auto-install Node 20
    echo           推薦 / Recommended: 雙擊 install_easy.bat 自動安裝 Node 20
    echo           或自己裝 / Or install manually: Node 20 LTS
    pause
    exit /b 1
)
echo   [OK] Node found

if not exist backend\.env (
    if exist backend\.env.example (
        echo   [WARN] backend\.env missing - copying from .env.example
        copy backend\.env.example backend\.env >nul
        echo   [TIP] You should set a real JWT_SECRET in backend\.env later:
        echo           python -c "import secrets; print(secrets.token_hex(32))"
    ) else (
        echo   [ERROR] backend\.env.example missing - this is not a valid Ouvoca repo
        pause
        exit /b 1
    )
) else (
    echo   [OK] backend\.env present
)

if not exist backend\erp.db (
    echo   [WARN] backend\erp.db missing - seeding fresh DB...
    pushd backend
    set PYTHONIOENCODING=utf-8
    python -m scripts.seed
    if errorlevel 1 (
        echo   [ERROR] Seed failed
        popd
        pause
        exit /b 1
    )
    popd
    echo   [OK] DB seeded ^(admin/admin123^)
) else (
    echo   [OK] backend\erp.db present
)

if not exist frontend-desktop\node_modules (
    echo   [WARN] frontend-desktop\node_modules missing - running npm install...
    pushd frontend-desktop
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        echo   [ERROR] npm install failed
        popd
        pause
        exit /b 1
    )
    popd
    echo   [OK] frontend deps installed
) else (
    echo   [OK] frontend\node_modules present
)

REM ---- Step 2: Kill any leftover instances on :8000 / :5173 ----
echo.
echo [2/5] Cleaning up old instances...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo   [INFO] Killing stale backend PID %%a
    taskkill /F /PID %%a >nul 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do (
    echo   [INFO] Killing stale frontend PID %%a
    taskkill /F /PID %%a >nul 2>nul
)

REM ---- Step 3: Start backend ----
echo.
echo [3/5] Starting backend (uvicorn :8000)...
start "ouvoca-backend" /MIN cmd /k "cd /d %CD%\backend && set PYTHONIOENCODING=utf-8 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info"
echo   [OK] Window opened: ouvoca-backend

REM ---- Step 4: Wait for backend healthy then start frontend ----
echo.
echo [4/5] Waiting for backend to be healthy...
set RETRIES=30
:WAIT
set /a RETRIES-=1
if !RETRIES! lss 0 (
    echo   [ERROR] Backend did not become healthy in 30s
    echo           Check the ouvoca-backend window for errors.
    pause
    exit /b 1
)
curl -s -m 2 http://localhost:8000/api/health >nul 2>nul
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT
)
echo   [OK] Backend healthy
start "ouvoca-frontend" /MIN cmd /k "cd /d %CD%\frontend-desktop && npm run dev"
echo   [OK] Window opened: ouvoca-frontend

REM ---- Step 5: Wait for frontend and open browser ----
echo.
echo [5/5] Waiting for frontend...
set RETRIES=30
:WAIT2
set /a RETRIES-=1
if !RETRIES! lss 0 (
    echo   [WARN] Frontend slow to start - opening browser anyway
    goto OPEN
)
curl -s -m 2 -o nul http://localhost:5173 2>nul
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT2
)
echo   [OK] Frontend ready

:OPEN
echo.
echo ================================================================
echo   Ouvoca is running!
echo.
echo     Desktop UI:  http://localhost:5173
echo     Backend API: http://localhost:8000
echo     API Docs:    http://localhost:8000/docs
echo.
echo     Login:  admin  /  admin123
echo.
echo   To stop:  stop_dev.bat
echo ================================================================
echo.
start "" http://localhost:5173
endlocal
