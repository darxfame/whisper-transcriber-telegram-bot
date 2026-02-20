@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

echo.
echo ═══════════════════════════════════════════════════════
echo   🔍 ПРОВЕРКА ТИПОВ (Type Checking)
echo ═══════════════════════════════════════════════════════
echo.

echo Проверяю типы в src\userbot.py с помощью pyright...
echo.

REM Проверка что pyright установлен
where pyright >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ pyright не установлен!
    echo.
    echo Установите:
    echo   npm install -g pyright
    echo.
    echo Или используйте встроенную проверку в Zed/VSCode
    echo.
    pause
    exit /b 1
)

REM Запуск pyright
pyright src\userbot.py

echo.
echo ═══════════════════════════════════════════════════════

if %ERRORLEVEL% EQU 0 (
    echo   ✅ ВСЕ ТИПЫ КОРРЕКТНЫ!
) else (
    echo   ⚠️  НАЙДЕНЫ ПРОБЛЕМЫ С ТИПАМИ
)

echo ═══════════════════════════════════════════════════════
echo.
pause
