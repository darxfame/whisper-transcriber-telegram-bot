@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

echo.
echo ═══════════════════════════════════════════════════════
echo   📊 СТАТУС БОТА
echo ═══════════════════════════════════════════════════════
echo.

echo [Статус контейнера]
docker-compose ps
echo.

echo ───────────────────────────────────────────────────────
echo [Использование ресурсов]
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | findstr userbot
echo.

echo ───────────────────────────────────────────────────────
echo [Последние 10 строк логов]
docker-compose logs --tail 10 userbot
echo.

echo ═══════════════════════════════════════════════════════
echo.
pause
