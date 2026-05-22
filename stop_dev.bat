@echo off
REM ============================================================
REM  Ouvoca - Stop dev environment (Windows)
REM ============================================================
REM  Kills processes listening on :8000 (backend) and :5173 (frontend)
REM  Targets by port - won't kill unrelated Python/Node processes.
REM ============================================================
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo   Stopping Ouvoca dev environment
echo ================================================================
echo.

set KILLED=0

REM ---- Kill backend on :8000 ----
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo   [INFO] Stopping backend (PID %%a on :8000)
    taskkill /F /PID %%a >nul 2>nul
    if not errorlevel 1 set /a KILLED+=1
)

REM ---- Kill frontend on :5173 ----
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do (
    echo   [INFO] Stopping frontend (PID %%a on :5173)
    taskkill /F /PID %%a >nul 2>nul
    if not errorlevel 1 set /a KILLED+=1
)

REM ---- Close console windows we labelled ----
taskkill /F /FI "WINDOWTITLE eq ouvoca-backend*"  >nul 2>nul
taskkill /F /FI "WINDOWTITLE eq ouvoca-frontend*" >nul 2>nul

echo.
if !KILLED! gtr 0 (
    echo   [DONE] %KILLED% process(es) stopped.
) else (
    echo   [INFO] No Ouvoca dev process found running.
)
echo.
endlocal
