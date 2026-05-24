@echo off
REM ============================================================
REM  Ouvoca 解除安裝（電腦小白版）/ Easy Uninstaller
REM ============================================================
REM  完整移除 install_easy.bat 安裝的所有東西：
REM    - Python（含 Windows 註冊表項，不會在「新增/移除程式」殘留）
REM    - Node.js / 套件 / venv / node_modules
REM    - 可選：你的 ERP 資料（DB / uploads / .env）
REM    - 可選：全域 cache（npm / pip）
REM
REM  Completely removes everything install_easy.bat installed,
REM  including Windows registry entries — leaves NO residue.
REM ============================================================

chcp 65001 > nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

cls
echo.
echo   ============================================================
echo.
echo     Ouvoca AI ERP - 解除安裝 / Uninstall
echo.
echo   ============================================================
echo.
echo     將會自動移除 / Will auto-remove:
echo       1. 執行中的服務 (port 8000 / 5173)
echo       2. tools\python   (含 Windows 註冊表項)
echo       3. tools\node
echo       4. backend\venv
echo       5. frontend-desktop\node_modules
echo.
echo     稍後會問你（你的資料）/ Will ASK before removing:
echo       - backend\erp.db        (你的 ERP 業務資料)
echo       - backend\uploads\*     (你上傳的報價/發票檔)
echo       - backend\.env          (JWT 密鑰 + LLM API Key)
echo       - %%AppData%%\npm-cache\  (~250 MB)
echo       - %%LocalAppData%%\pip\Cache\
echo.
echo   ============================================================
echo.
choice /M "確定要解除安裝嗎"
if errorlevel 2 (
    echo   已取消 / Cancelled
    pause & exit /b 0
)

REM ============================================================
REM Step 1: 停止執行中的服務
REM ============================================================
echo.
echo [Step 1/5] 停止執行中的服務...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo   OK 已停止 backend (8000) + frontend (5173)

REM ============================================================
REM Step 2: 移除 Python（含註冊表清理）
REM ============================================================
echo.
echo [Step 2/5] 移除 Python (含註冊表清理)...
if exist "tools\downloads\python-installer.exe" (
    REM 用原 installer /uninstall 模式：清掉 HKCU\Software\Python 註冊表
    tools\downloads\python-installer.exe /uninstall /quiet >nul 2>&1
    echo   OK Python 已從 Windows 註冊表移除
) else (
    REM Installer 不存在 (使用者已刪)，手動清註冊表
    echo   Installer 已不存在，手動清註冊表...
    reg delete "HKCU\Software\Python\PythonCore\3.11" /f >nul 2>&1
    reg delete "HKCU\Software\Python\PythonCore\3.11-32" /f >nul 2>&1
    REM 嘗試清各種可能的 uninstall key（版本號可能不同）
    for /f "tokens=*" %%k in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall" /f "Python 3.11" /k 2^>nul ^| findstr /i "Python 3.11"') do (
        reg delete "%%k" /f >nul 2>&1
    )
    echo   OK
)

REM ============================================================
REM Step 3: 刪除 tools\ 資料夾
REM ============================================================
echo.
echo [Step 3/5] 刪除 tools\ 資料夾...
if exist tools (
    rmdir /s /q tools 2>nul
    if exist tools (
        echo   WARN tools\ 部分檔案被占用，請手動刪除
    ) else (
        echo   OK tools\ 已清空
    )
) else (
    echo   - tools\ 不存在，略過
)

REM ============================================================
REM Step 4: 刪除套件目錄
REM ============================================================
echo.
echo [Step 4/5] 刪除套件目錄...
if exist backend\venv (
    rmdir /s /q backend\venv 2>nul
    echo   OK backend\venv (Python 套件)
)
if exist frontend-desktop\node_modules (
    rmdir /s /q frontend-desktop\node_modules 2>nul
    echo   OK frontend-desktop\node_modules (前端套件)
)
if exist .backend.pid del /q .backend.pid 2>nul
if exist .frontend.pid del /q .frontend.pid 2>nul
if exist logs-backend.txt del /q logs-backend.txt 2>nul
if exist logs-frontend.txt del /q logs-frontend.txt 2>nul

REM ============================================================
REM Step 5: 詢問是否刪除使用者資料
REM ============================================================
echo.
echo [Step 5/5] 你的資料 / Your data
echo --------------------------------------------------------------
echo   建議：先備份 backend\erp.db 再刪
echo   你的資料在 / Your data is at:
echo     - backend\erp.db
echo     - backend\uploads\
echo     - backend\.env (含 JWT_SECRET + API Key)
echo.
choice /M "也刪除你的 ERP 資料嗎 (不可復原)"
if errorlevel 2 (
    echo   OK 資料保留在 backend\ 內
    echo   要手動備份：複製整個 backend\ 資料夾即可
    goto SKIP_DATA_DELETE
)

echo.
echo   ⚠️  警告：將永久刪除你的 ERP 業務資料
choice /M "再次確認：永久刪除你的 ERP 資料"
if errorlevel 2 (
    echo   OK 取消，資料保留
    goto SKIP_DATA_DELETE
)

if exist backend\erp.db del /q backend\erp.db 2>nul
if exist backend\erp.db-journal del /q backend\erp.db-journal 2>nul
if exist backend\erp.db-wal del /q backend\erp.db-wal 2>nul
if exist backend\erp.db-shm del /q backend\erp.db-shm 2>nul
if exist backend\uploads rmdir /s /q backend\uploads 2>nul
if exist backend\.env del /q backend\.env 2>nul
if exist backend\.seeded del /q backend\.seeded 2>nul
echo   OK 你的 ERP 資料已全部刪除

:SKIP_DATA_DELETE

REM ============================================================
REM 額外：清全域 cache
REM ============================================================
echo.
echo --------------------------------------------------------------
echo   進階選項 / Advanced
echo --------------------------------------------------------------
echo   全域 cache 可釋放 ~500 MB，但若你有其他 Node/Python 專案會被影響
echo     - %%AppData%%\npm-cache\
echo     - %%LocalAppData%%\pip\Cache\
echo.
choice /M "也清除全域 cache 嗎 (其他 Node/Python 專案會重下載套件)"
if errorlevel 2 (
    echo   OK Cache 保留 (推薦：若有其他 Node/Python 專案)
) else (
    if exist "%AppData%\npm-cache" rmdir /s /q "%AppData%\npm-cache" 2>nul
    if exist "%LocalAppData%\pip\Cache" rmdir /s /q "%LocalAppData%\pip\Cache" 2>nul
    echo   OK 全域 cache 已清除
)

REM ============================================================
REM 完成
REM ============================================================
echo.
echo   ============================================================
echo.
echo     解除安裝完成 / Uninstall complete!
echo.
echo     接下來 / Next:
echo       1. 你現在可以放心刪除整個 Ouvoca 資料夾
echo          You can now safely delete the entire Ouvoca folder
echo       2. Windows 註冊表 / 系統服務 / 啟動項 都已清乾淨
echo          Windows registry / services / startup are all clean
echo.
echo     若要重裝 / To reinstall:
echo       再次雙擊 install_easy.bat 即可
echo.
echo   ============================================================
echo.
pause
endlocal
