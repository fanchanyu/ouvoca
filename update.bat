@echo off
REM ============================================================
REM  Ouvoca 更新（電腦小白版）/ Easy Updater
REM ============================================================
REM  雙擊即可從 GitHub 更新到最新版，全程：
REM    1. 自動備份你的資料（erp.db / .env / uploads）
REM    2. 下載新版程式碼（zip 或 git pull）
REM    3. 更新 Python 套件 + npm 套件
REM    4. 跑資料庫結構升級（alembic）
REM    5. 重啟服務
REM
REM  你的業務資料完全保留，不會清空。
REM  Your business data is fully preserved.
REM
REM  萬一壞了？備份在 backups\YYYYMMDD_HHMMSS\ 可手動還原
REM ============================================================

chcp 65001 > nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

cls
echo.
echo   ============================================================
echo.
echo     Ouvoca AI ERP - 自動更新 / Auto Updater
echo.
echo   ============================================================
echo.
echo     將會做這 5 件事 / Will do these 5 things:
echo.
echo     1. 停止 Ouvoca 服務 (port 8000 / 5173)
echo     2. 備份你的資料到 backups\YYYYMMDD_HHMMSS\
echo        - backend\erp.db (你的 ERP 資料)
echo        - backend\.env (JWT + LLM API Key)
echo        - backend\uploads\* (你上傳的檔案)
echo     3. 下載最新程式碼 (從 GitHub)
echo     4. 更新套件 (pip + npm，若有新依賴)
echo     5. 跑資料庫結構升級 (alembic)
echo     6. 重啟服務 → 自動開瀏覽器
echo.
echo     你的業務資料完全保留！/ Your business data is fully preserved!
echo.
echo   ============================================================
echo.
choice /M "現在更新嗎"
if errorlevel 2 (
    echo   已取消 / Cancelled
    pause & exit /b 0
)

REM ─── Sanity ───
where curl >nul 2>&1
if errorlevel 1 (
    echo   X curl 不存在 / curl not found
    echo   需要 Windows 10 ^(1803+^) / requires Windows 10 1803+
    pause & exit /b 1
)

REM ─── Prefer bundled tools (if install_easy.bat was used) ───
if exist "tools\python\python.exe" (
    set "PATH=%CD%\tools\python;%CD%\tools\python\Scripts;%PATH%"
)
if exist "tools\node\node.exe" (
    set "PATH=%CD%\tools\node;%PATH%"
)
if exist "backend\venv\Scripts\activate.bat" (
    set "PATH=%CD%\backend\venv\Scripts;%PATH%"
)

REM ============================================================
REM Step 1: 停止服務
REM ============================================================
echo.
echo [Step 1/6] 停止 Ouvoca 服務...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul
echo   OK 已停止

REM ============================================================
REM Step 2: 備份你的資料
REM ============================================================
echo.
echo [Step 2/6] 備份你的資料...

REM 產生時間戳記資料夾名稱 (YYYYMMDD_HHMMSS)
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "ts=%%a"
set "BACKUP_DIR=backups\!ts:~0,8!_!ts:~8,6!"

if not exist backups mkdir backups
mkdir "%BACKUP_DIR%"

REM 備份 ERP 資料庫
if exist backend\erp.db (
    copy /Y backend\erp.db "%BACKUP_DIR%\erp.db" >nul
    echo   OK erp.db -^> %BACKUP_DIR%\
)
REM 備份 .env (含 JWT_SECRET + API Key)
if exist backend\.env (
    copy /Y backend\.env "%BACKUP_DIR%\.env" >nul
    echo   OK .env -^> %BACKUP_DIR%\
)
REM 備份 uploads/
if exist backend\uploads (
    xcopy /E /I /Q /Y backend\uploads "%BACKUP_DIR%\uploads\" >nul 2>&1
    echo   OK uploads\ -^> %BACKUP_DIR%\
)
REM 寫一個簡單的 README 進備份資料夾
echo Ouvoca 備份 / Backup > "%BACKUP_DIR%\README.txt"
echo 建立時間: %date% %time% >> "%BACKUP_DIR%\README.txt"
echo. >> "%BACKUP_DIR%\README.txt"
echo 還原方法 / How to restore: >> "%BACKUP_DIR%\README.txt"
echo   1. 停止 Ouvoca ^(關閉視窗或跑 stop.sh^) >> "%BACKUP_DIR%\README.txt"
echo   2. 把這個資料夾的 erp.db / .env 複製回 backend\ >> "%BACKUP_DIR%\README.txt"
echo   3. 把 uploads\ 複製回 backend\uploads\ >> "%BACKUP_DIR%\README.txt"
echo   4. 重新啟動 start.bat >> "%BACKUP_DIR%\README.txt"

echo   OK 備份已存到 %BACKUP_DIR%\

REM ============================================================
REM Step 3: 下載新版程式碼
REM ============================================================
echo.
echo [Step 3/6] 下載最新版程式碼...

if exist .git (
    REM git 安裝路徑：使用 git pull
    where git >nul 2>&1
    if not errorlevel 1 (
        echo   偵測到 git，用 git pull 更新...
        git pull origin main 2>&1
        if errorlevel 1 (
            echo.
            echo   X git pull 失敗 — 可能你改過 code 有衝突
            echo   建議：開個新資料夾，重新跑 install_easy.bat，再從備份還原資料
            echo   備份位置: %BACKUP_DIR%\
            pause & exit /b 1
        )
        echo   OK 用 git pull 更新完成
    ) else (
        goto ZIP_UPDATE
    )
) else (
    :ZIP_UPDATE
    REM zip 安裝路徑：下載新 zip 解壓覆蓋
    echo   下載 main branch zip ^(~10 MB^)...
    if not exist tools\downloads mkdir tools\downloads
    curl -L --progress-bar -o tools\downloads\update.zip ^
        https://github.com/fanchanyu/ouvoca/archive/refs/heads/main.zip
    if errorlevel 1 (
        echo   X 下載失敗 — 檢查網路後重試
        pause & exit /b 1
    )

    echo   解壓縮到暫存資料夾...
    if exist tools\downloads\update_extract rmdir /s /q tools\downloads\update_extract
    mkdir tools\downloads\update_extract
    tar -xf tools\downloads\update.zip -C tools\downloads\update_extract
    if errorlevel 1 (
        echo   X 解壓失敗
        pause & exit /b 1
    )

    REM 找到 extract 出來的根資料夾（通常是 ouvoca-main）
    for /d %%d in (tools\downloads\update_extract\*) do set "EXTRACT_ROOT=%%d"

    echo   覆蓋新檔案 ^(保留你的資料 erp.db / .env / uploads / tools / venv / node_modules^)...
    REM 用 robocopy 排除使用者資料目錄
    robocopy "!EXTRACT_ROOT!" "%CD%" /E ^
        /XD "backend\uploads" "tools" "backend\venv" "frontend-desktop\node_modules" "backups" "backend\__pycache__" ".git" ^
        /XF "backend\erp.db" "backend\erp.db-journal" "backend\erp.db-wal" "backend\erp.db-shm" "backend\.env" "backend\.seeded" ^
        /NFL /NDL /NJH /NJS /NC /NS >nul

    REM 清暫存
    rmdir /s /q tools\downloads\update_extract
    del /q tools\downloads\update.zip
    echo   OK 程式碼已更新
)

REM ============================================================
REM Step 4: 更新 Python + Node 套件（若有新依賴）
REM ============================================================
echo.
echo [Step 4/6] 更新套件...

if exist backend\venv\Scripts\python.exe (
    echo   pip install -r requirements.txt ^(若有新套件^)...
    "backend\venv\Scripts\python.exe" -m pip install -r backend\requirements.txt --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo   WARN pip install 部分失敗，繼續嘗試
    )
    echo   OK Python 套件已更新
) else (
    echo   WARN backend\venv 不存在，跳過 pip — 建議跑 install_easy.bat
)

if exist frontend-desktop\node_modules (
    echo   npm install ^(若有新套件^)...
    pushd frontend-desktop
    call npm install --silent --no-audit --no-fund
    popd
    echo   OK Node 套件已更新
) else (
    echo   WARN frontend-desktop\node_modules 不存在，跳過 npm
)

REM ============================================================
REM Step 5: 資料庫結構升級 (alembic)
REM ============================================================
echo.
echo [Step 5/6] 資料庫結構升級...

if exist backend\alembic.ini (
    if exist backend\venv\Scripts\python.exe (
        pushd backend
        set PYTHONIOENCODING=utf-8
        "venv\Scripts\python.exe" -m alembic upgrade head 2>nul
        if errorlevel 1 (
            echo   WARN alembic upgrade 失敗或無需升級（SQLite 自動建表）
        ) else (
            echo   OK 資料庫結構已升級
        )
        popd
    )
)

REM ============================================================
REM Step 6: 重啟服務
REM ============================================================
echo.
echo [Step 6/6] 重啟服務...
echo.
echo   ============================================================
echo     更新完成！/ Update complete!
echo.
echo     備份位置 / Backup at:
echo       %BACKUP_DIR%\
echo.
echo     若新版有問題，可從備份還原：
echo       1. 關閉 Ouvoca
echo       2. 複製 %BACKUP_DIR%\erp.db 回 backend\
echo       3. 複製 %BACKUP_DIR%\.env 回 backend\
echo       4. 重新啟動 start.bat
echo   ============================================================
echo.
choice /M "現在啟動嗎"
if errorlevel 2 (
    echo   稍後雙擊 start.bat 即可啟動
    pause
    exit /b 0
)

call start.bat
endlocal
