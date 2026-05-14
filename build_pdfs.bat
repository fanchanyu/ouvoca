@echo off
REM ============================================================
REM  LLM-ERP - One-click: convert all customer-facing
REM           manuals to PDFs (Windows)
REM ============================================================
REM  Requires: Node.js 18+ (https://nodejs.org/)
REM  Output  : docs\pdf\*.pdf (12 PDFs)
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ================================================================
echo   LLM-ERP PDF Manual Builder
echo ================================================================
echo.

REM 1. Check Node.js
where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js not installed
  echo Please install Node.js 20 LTS from https://nodejs.org/
  pause
  exit /b 1
)
for /f "tokens=*" %%v in ('node -v') do echo [OK] Node.js: %%v

REM 2. Install deps if needed
cd scripts\build-pdfs
if not exist node_modules (
  echo.
  echo [INFO] First run - installing dependencies...
  echo        This will download ~150MB ^(includes Chromium for Puppeteer^)
  echo        Please wait...
  call npm install --silent
  if errorlevel 1 (
    echo [ERROR] npm install failed
    pause
    exit /b 1
  )
)
echo [OK] Dependencies ready

REM 3. Run builder
echo.
call node build.mjs
if errorlevel 1 (
  echo.
  echo [WARN] Some PDFs failed - check log above
  cd ..\..
  pause
  exit /b 1
)

REM 4. Open output folder
cd ..\..
echo.
echo ================================================================
echo   Done! PDFs are in: %cd%\docs\pdf
echo ================================================================
echo.
start "" "%cd%\docs\pdf"
pause
