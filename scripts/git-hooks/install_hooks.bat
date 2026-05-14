@echo off
REM ============================================================
REM  erpilot - 安裝 git hooks (Windows)
REM ============================================================
setlocal
set "REPO_ROOT=%~dp0..\.."
pushd "%REPO_ROOT%"

if not exist ".git" (
    echo [ERROR] 找不到 .git 目錄。請先 git clone / git init
    exit /b 1
)

echo [INFO] 安裝 erpilot git hooks...

copy /Y "scripts\git-hooks\pre-commit" ".git\hooks\pre-commit" >nul
if errorlevel 1 ( echo [ERROR] copy pre-commit fail & exit /b 1 )
echo   [OK] pre-commit

copy /Y "scripts\git-hooks\pre-push" ".git\hooks\pre-push" >nul
if errorlevel 1 ( echo [ERROR] copy pre-push fail & exit /b 1 )
echo   [OK] pre-push

echo.
echo [DONE]
echo   git commit  -^> auto-scan secrets / .env / hardcoded password
echo   git push    -^> auto-run 8 gates before pushing main/develop
echo                  (markdown-only changes skipped)
echo.
echo   Bypass: git commit --no-verify ^| git push --no-verify (not recommended)
popd
