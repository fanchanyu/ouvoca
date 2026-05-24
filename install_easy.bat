@echo off
REM ============================================================
REM  Ouvoca 簡易安裝（電腦小白版）/ Easy Installer for Non-Tech Users
REM ============================================================
REM  Zero prerequisites — no Docker, no Python, no Node needed.
REM  零前置 — 不需 Docker、不需事先裝 Python 或 Node。
REM
REM  Just double-click this file. Internet connection required.
REM  雙擊本檔即可。需要網路連線。
REM
REM  What this script does / 本腳本做的事：
REM    1. Downloads Python 3.11 silently to .\tools\python  (~26 MB)
REM    2. Downloads Node.js 20 to .\tools\node              (~30 MB)
REM    3. Creates backend\venv, installs backend deps      (~200 MB)
REM    4. Runs npm install for frontend                     (~250 MB)
REM    5. Seeds initial DB with admin user
REM    6. Asks if you want to launch right away
REM
REM  Total disk usage: ~750 MB (all inside this folder, easy to delete)
REM  All files stay local — uninstall = delete this folder.
REM ============================================================

chcp 65001 > nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

cls
echo.
echo   ============================================================
echo.
echo     Ouvoca AI ERP - Easy Installer
echo     Ouvoca AI ERP - 簡易安裝（電腦小白專用）
echo.
echo     - No Docker needed / 不需 Docker
echo     - No Python pre-install needed / 不需事先裝 Python
echo     - No Node pre-install needed / 不需事先裝 Node
echo.
echo     Total time: 10-20 minutes (mostly downloading)
echo     全程約 10-20 分鐘（大部分時間在下載）
echo.
echo   ============================================================
echo.

REM ─── 法律揭露：告知將從哪下載什麼 / Disclosure ───
echo   ============================================================
echo     即將下載 / About to download (~500 MB total):
echo   ============================================================
echo     - Python 3.11.9      (~26 MB)  from python.org   PSF License
echo     - Node.js 20.11.1    (~30 MB)  from nodejs.org   MIT License
echo     - PyPI packages      (~200 MB) from pypi.org     mostly MIT/Apache
echo     - npm packages       (~250 MB) from npmjs.org    mostly MIT/Apache
echo.
echo     Ouvoca 不重新散布上述軟體 — 您的電腦直接從原廠下載。
echo     Ouvoca does NOT redistribute these — your PC downloads from origins.
echo     詳見 / Details:  docs\THIRD_PARTY_DOWNLOADS_ZH.md
echo.
echo     不繼續請按 Ctrl+C / Press Ctrl+C to abort
echo   ============================================================
timeout /t 5 /nobreak >nul

REM ─── Sanity check: curl + tar (built into Windows 10 1803+) ───
where curl >nul 2>&1
if errorlevel 1 (
    echo   X 找不到 curl 命令 / curl not found
    echo   需要 Windows 10 ^(1803 build^) 以上
    echo   This script requires Windows 10 1803 or later.
    pause & exit /b 1
)
where tar >nul 2>&1
if errorlevel 1 (
    echo   X 找不到 tar 命令 / tar not found
    echo   需要 Windows 10 ^(1803 build^) 以上
    pause & exit /b 1
)

if not exist tools mkdir tools
if not exist tools\downloads mkdir tools\downloads

REM ============================================================
REM Step 1: Python
REM ============================================================
echo [Step 1/5] Python 3.11
echo --------------------------------------------------------------
if exist "tools\python\python.exe" (
    echo   OK Python already installed at tools\python
) else (
    echo   Downloading Python 3.11.9 ^(~26 MB^)...
    curl -L --progress-bar -o tools\downloads\python-installer.exe ^
        https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    if errorlevel 1 (
        echo   X 下載失敗 — 請檢查網路後重試
        echo   Download failed — check network and retry
        pause & exit /b 1
    )
    echo   Installing to tools\python ^(silent, no admin needed^)...
    tools\downloads\python-installer.exe /quiet ^
        InstallAllUsers=0 PrependPath=0 ^
        Include_pip=1 Include_test=0 Include_doc=0 ^
        Include_dev=0 Include_launcher=0 Include_tcltk=0 ^
        TargetDir="%CD%\tools\python"
    if errorlevel 1 (
        echo   X Python install failed
        echo   錯誤：可能是防毒軟體擋住，請暫時關閉後重試
        pause & exit /b 1
    )
    echo   OK Python 3.11.9 installed
)
set "PYEXE=%CD%\tools\python\python.exe"

REM ============================================================
REM Step 2: Node.js
REM ============================================================
echo.
echo [Step 2/5] Node.js 20
echo --------------------------------------------------------------
if exist "tools\node\node.exe" (
    echo   OK Node.js already installed at tools\node
) else (
    echo   Downloading Node.js 20.11.1 ^(~30 MB^)...
    curl -L --progress-bar -o tools\downloads\node.zip ^
        https://nodejs.org/dist/v20.11.1/node-v20.11.1-win-x64.zip
    if errorlevel 1 (
        echo   X Node download failed
        pause & exit /b 1
    )
    echo   Extracting...
    tar -xf tools\downloads\node.zip -C tools
    if exist "tools\node-v20.11.1-win-x64" (
        move /Y tools\node-v20.11.1-win-x64 tools\node >nul
    )
    echo   OK Node.js 20.11.1 installed
)
set "PATH=%CD%\tools\node;%PATH%"

REM ============================================================
REM Step 3: Backend (venv + pip)
REM ============================================================
echo.
echo [Step 3/5] 後端套件 / Backend dependencies
echo --------------------------------------------------------------

if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy backend\.env.example backend\.env >nul
        echo   Generating random JWT_SECRET...
        for /f "delims=" %%k in ('""%PYEXE%" -c "import secrets; print(secrets.token_hex(32))""') do set "NEWJWT=%%k"
        "%PYEXE%" -c "import pathlib; p=pathlib.Path('backend/.env'); s=p.read_text(encoding='utf-8'); s=s.replace('change-me-in-production-please-use-openssl-rand-hex-32', '%NEWJWT%'); p.write_text(s, encoding='utf-8')"
        echo   OK backend\.env created
    ) else (
        echo   X backend\.env.example missing
        pause & exit /b 1
    )
)

if not exist "backend\venv" (
    echo   Creating virtual environment...
    "%PYEXE%" -m venv backend\venv
    if errorlevel 1 (
        echo   X venv creation failed
        pause & exit /b 1
    )
)

echo   Installing backend packages ^(first time: 2-5 min^)...
call backend\venv\Scripts\activate.bat
"backend\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --disable-pip-version-check
"backend\venv\Scripts\python.exe" -m pip install -r backend\requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo   X pip install failed
    echo   Common cause: anti-virus blocking. Try whitelisting this folder.
    pause & exit /b 1
)
echo   OK Backend dependencies ready

REM ============================================================
REM Step 4: Frontend (npm install)
REM ============================================================
echo.
echo [Step 4/5] 前端套件 / Frontend dependencies
echo --------------------------------------------------------------
pushd frontend-desktop
if not exist "node_modules" (
    echo   Installing frontend packages ^(first time: 3-8 min^)...
    call npm install --silent --no-audit --no-fund
    if errorlevel 1 (
        echo   X npm install failed
        popd
        pause & exit /b 1
    )
)
echo   OK Frontend dependencies ready
popd

REM ============================================================
REM Step 5: Seed DB
REM ============================================================
echo.
echo [Step 5/5] 資料庫初始化 / Database seeding
echo --------------------------------------------------------------
if not exist "backend\.seeded" (
    pushd backend
    set PYTHONIOENCODING=utf-8
    "venv\Scripts\python.exe" -m scripts.seed
    if errorlevel 1 (
        echo   WARN seed failed - DB may already exist
    ) else (
        echo. > .seeded
        echo   OK Database seeded with admin user
    )
    popd
) else (
    echo   OK Database already seeded
)

REM ============================================================
REM Done!
REM ============================================================
echo.
echo   ============================================================
echo.
echo     安裝完成！Installation complete!
echo.
echo     登入帳密 / Login: admin / admin123
echo     ^(請首次登入後立即修改密碼 / change after first login^)
echo.
echo     下次啟動雙擊 start.bat 即可
echo     Next launch: double-click start.bat
echo.
echo     若要解除安裝，雙擊 uninstall_easy.bat（含註冊表清理）
echo     To uninstall: double-click uninstall_easy.bat (cleans registry too)
echo.
echo   ============================================================
echo.
choice /M "現在啟動嗎 / Launch now"
if errorlevel 2 (
    echo   稍後雙擊 start.bat 即可啟動
    pause
    exit /b 0
)

REM Export tools to PATH for start.bat
set "PATH=%CD%\tools\python;%CD%\tools\node;%CD%\backend\venv\Scripts;%PATH%"
call start.bat
endlocal
