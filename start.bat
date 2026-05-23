@echo off
REM ============================================================
REM  Ouvoca 啟動器 / One-Click Launcher
REM ============================================================
REM  Uses bundled Python/Node if present (set up by install_easy.bat),
REM  otherwise falls back to system Python/Node.
REM
REM  If you haven't installed yet, run install_easy.bat first.
REM  尚未安裝請先執行 install_easy.bat
REM ============================================================
chcp 65001 > nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM ─── Prefer bundled tools (from install_easy.bat) ───
if exist "tools\python\python.exe" (
    set "PATH=%CD%\tools\python;%CD%\tools\python\Scripts;%PATH%"
)
if exist "tools\node\node.exe" (
    set "PATH=%CD%\tools\node;%PATH%"
)
if exist "backend\venv\Scripts\activate.bat" (
    set "PATH=%CD%\backend\venv\Scripts;%PATH%"
)

REM ─── Sanity check ───
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo   X Python not found / 找不到 Python
    echo   Please run install_easy.bat first / 請先執行 install_easy.bat
    echo.
    pause & exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
    echo.
    echo   X Node.js not found / 找不到 Node.js
    echo   Please run install_easy.bat first / 請先執行 install_easy.bat
    echo.
    pause & exit /b 1
)

if not exist "backend\.env" (
    echo   X backend\.env missing / 找不到 backend\.env
    echo   Please run install_easy.bat first / 請先執行 install_easy.bat
    pause & exit /b 1
)

echo.
echo   ============================================================
echo     Ouvoca AI ERP - Starting / 啟動中
echo   ============================================================
echo.

REM ─── Kill stale instances on :8000 / :5173 ───
echo [1/3] Cleaning up old instances / 清除舊執行緒...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM ─── Start backend ───
echo [2/3] Starting backend on port 8000...
start "ouvoca-backend" /MIN cmd /k "cd /d %CD%\backend && set PYTHONIOENCODING=utf-8 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info"

REM Wait for backend healthy
set RETRIES=30
:WAIT_BACKEND
set /a RETRIES-=1
if !RETRIES! lss 0 (
    echo   X Backend failed to start in 30s
    echo   Check the ouvoca-backend window for errors
    pause & exit /b 1
)
curl -s -m 2 http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT_BACKEND
)
echo   OK Backend healthy

REM ─── Start frontend ───
echo [3/3] Starting frontend on port 5173...
start "ouvoca-frontend" /MIN cmd /k "cd /d %CD%\frontend-desktop && npm run dev"

REM Wait for frontend ready
set RETRIES=30
:WAIT_FRONTEND
set /a RETRIES-=1
if !RETRIES! lss 0 (
    echo   WARN Frontend slow to start - opening browser anyway
    goto OPEN
)
curl -s -m 2 -o nul http://localhost:5173 2>nul
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT_FRONTEND
)
echo   OK Frontend ready

:OPEN
echo.
echo   ============================================================
echo     Ouvoca is running! / Ouvoca 運行中！
echo.
echo     開瀏覽器 / Open browser:  http://localhost:5173
echo     後端 API / Backend API:    http://localhost:8000
echo     API 文件 / API docs:       http://localhost:8000/docs
echo.
echo     登入 / Login: admin / admin123
echo.
echo     關閉所有服務 / Stop all:  stop_dev.bat
echo   ============================================================
echo.

start "" http://localhost:5173

endlocal
