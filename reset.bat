@echo off
chcp 65001 > nul
echo ╔════════════════════════════════════════════════╗
echo ║  Ouvoca ERP — 完全重置（含資料 / WITH DATA）  ║
echo ╚════════════════════════════════════════════════╝
echo.
echo 此動作會：
echo   • 停止所有容器
echo   • 刪除所有資料庫資料（demo data）
echo   • 刪除 backend\.env 設定
echo   • 下次需重跑 install.bat
echo.
set /p CONFIRM="確定要重置？(輸入 YES 確認): "
if /i not "%CONFIRM%"=="YES" (
    echo 已取消 / Cancelled
    pause
    exit /b 0
)
docker compose down -v
del /q backend\.seeded 2>nul
del /q backend\.env 2>nul
echo.
echo ✓ 已重置 / Reset complete
echo   執行 install.bat 重新安裝
pause
