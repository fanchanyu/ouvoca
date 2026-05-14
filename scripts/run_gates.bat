@echo off
REM ===========================================================
REM  LLM-ERP - Self-Verification Gates (Windows)
REM  說「完成」前必須跑這個，看到 ALL GATES PASSED 才算完工
REM ===========================================================
setlocal enabledelayedexpansion
cd /d "%~dp0\.."

set FAIL=0
set PASS=0
set SKIP=0

echo.
echo ================================================================
echo   LLM-ERP Self-Verification Gates
echo ================================================================
echo.

REM ---- Gate 1 ------------------------------------------------
echo [Gate 1 - Compile]

call :run "backend pytest tests/smoke/"  cd backend ^&^& python -m pytest tests/smoke/ -q --tb=line
call :run "backend app import"           cd backend ^&^& python -c "from app.main import app; print(len(app.routes))"
if exist frontend-mobile\node_modules (
    call :run "mobile tsc --noEmit"      cd frontend-mobile ^&^& npx --no-install tsc --noEmit
) else (
    call :skip "mobile tsc" "node_modules missing"
)

echo.
echo [Gate 2 - Behavior]
call :run "persona test"                 cd backend ^&^& python -m pytest tests/personas/ -q --tb=line

if exist backend\tests\integration\test_mesh.py (
    call :run "MESH integration"          cd backend ^&^& python -m pytest tests/integration/ -q --tb=line
) else (
    call :skip "MESH integration" "Day 4 not done"
)

echo.
echo [Gate 3 - Docs]
if exist scripts\build-pdfs\node_modules (
    call :run "PDF builder"               cd scripts\build-pdfs ^&^& node build.mjs
) else (
    call :skip "PDF builder" "node_modules missing"
)

echo.
echo ================================================================
echo   Pass=%PASS%  Fail=%FAIL%  Skip=%SKIP%
echo ================================================================

if %FAIL% gtr 0 (
    echo [RED] GATES FAILED -- cannot say "done", cannot upload
    exit /b 1
)
echo [GREEN] ALL GATES PASSED -- ready to ship
exit /b 0

REM ----- Helpers -----
:run
set "_name=%~1"
shift
set "_cmd="
:run_loop
if "%~1"=="" goto run_exec
set "_cmd=%_cmd% %~1"
shift
goto run_loop
:run_exec
echo   ^>^> !_name!
%_cmd% >nul 2>&1
if errorlevel 1 (
    echo      [X] failed
    set /a FAIL+=1
) else (
    echo      [OK]
    set /a PASS+=1
)
exit /b 0

:skip
echo   -- %~1 ^(skip: %~2^)
set /a SKIP+=1
exit /b 0
