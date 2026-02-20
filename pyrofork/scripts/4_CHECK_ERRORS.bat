@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

echo.
echo ═══════════════════════════════════════════════════════
echo   🔍 ПРОВЕРКА ОШИБОК
echo ═══════════════════════════════════════════════════════
echo.

echo Ищу ошибки в логах...
echo.

docker-compose logs userbot | findstr /i "ERROR ValueError exception" > temp_errors.txt

if %ERRORLEVEL% EQU 0 (
    echo ❌ НАЙДЕНЫ ОШИБКИ:
    echo ───────────────────────────────────────────────────────
    type temp_errors.txt
    echo ───────────────────────────────────────────────────────
    del temp_errors.txt
) else (
    echo ✅ ОШИБОК НЕ НАЙДЕНО!
    echo.
    echo Бот работает стабильно.
    del temp_errors.txt 2>nul
)

echo.
echo ═══════════════════════════════════════════════════════
echo.
pause
