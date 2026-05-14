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
if errorlevel 1 (
    echo [ERROR] copy 失敗
    exit /b 1
)
echo   [OK] pre-commit

echo.
echo [DONE] 完成。每次 git commit 都會自動掃 secrets。
echo        跳過：git commit --no-verify (不建議)
popd
