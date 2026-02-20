@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

echo.
echo ═══════════════════════════════════════════════════════
echo   📋 ЛОГИ БОТА (в реальном времени)
echo ═══════════════════════════════════════════════════════
echo.
echo Для выхода нажмите Ctrl+C
echo.

docker-compose logs -f userbot
