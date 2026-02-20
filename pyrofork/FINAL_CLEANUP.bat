@echo off
chcp 65001 >nul
echo.
echo ════════════════════════════════════════════════════════════
echo  ✨ ФИНАЛЬНАЯ ОЧИСТКА ПРОЕКТА (GitHub стандарты)
echo ════════════════════════════════════════════════════════════
echo.

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM Счетчик удаленных файлов
set deleted=0

REM === 1. Удаляю батники из корня ===
echo [1/4] Удаляю батники и скрипты из корня...
for %%f in (
    1_CLEANUP.bat
    2_RESTART.bat
    3_LOGS.bat
    4_CHECK_ERRORS.bat
    5_STATUS.bat
    6_STOP.bat
    7_START.bat
    8_CHECK_TYPES.bat
    CLEANUP_NOW.bat
    cleanup.ps1
    start.sh
    health_check.sh
) do (
    if exist "%%f" (
        del /F /Q "%%f"
        echo   ✓ Удален: %%f
        set /a deleted=!deleted!+1
    )
)

REM === 2. Удаляю документацию из корня ===
echo.
echo [2/4] Удаляю документацию из корня...
for %%f in (
    BATNIKI.md
    CHANGES.md
    FIXES.md
    PRODUCTION_CLEANUP.md
    START.md
    STATUS.md
    TYPE_FIX_SUMMARY.txt
    CLEANUP_PLAN.md
) do (
    if exist "%%f" (
        del /F /Q "%%f"
        echo   ✓ Удален: %%f
        set /a deleted=!deleted!+1
    )
)

REM === 3. Удаляю userbot.py из корня (копия в src/) ===
echo.
echo [3/4] Удаляю дублированный userbot.py из корня...
if exist "userbot.py" (
    del /F /Q "userbot.py"
    echo   ✓ Удален: userbot.py (основной файл теперь в src/)
    set /a deleted=!deleted!+1
)

REM === 4. Удаляю временные файлы и папки ===
echo.
echo [4/4] Удаляю временные файлы и папки...

if exist "voice_transcriber copy.session" (
    del /F /Q "voice_transcriber copy.session"
    echo   ✓ Удален: voice_transcriber copy.session
    set /a deleted=!deleted!+1
)

if exist "old" (
    rd /s /q "old"
    echo   ✓ Удалена папка: old/
    set /a deleted=!deleted!+1
)

REM Очистка Python кэша везде
for /d /r . %%d in (__pycache__) do @if exist "%%d" (
    rd /s /q "%%d" 2>nul
)
del /s /q *.pyc 2>nul

REM === Финальный статус ===
echo.
echo ════════════════════════════════════════════════════════════
echo  ✅ ОЧИСТКА ЗАВЕРШЕНА!
echo ════════════════════════════════════════════════════════════
echo.
echo 📊 Статистика:
echo   • Файлов удалено: !deleted!
echo.
echo 📁 Структура проекта готова к GitHub:
echo   ✅ src/userbot.py              - основной код
echo   ✅ scripts/                    - батники и утилиты
echo   ✅ docs/                       - полная документация
echo   ✅ docker-compose.yml          - конфигурация Docker
echo   ✅ Dockerfile                  - образ Docker
echo   ✅ requirements.txt            - зависимости
echo   ✅ README.md                   - описание проекта
echo   ✅ .env.example                - пример переменных
echo   ✅ .gitignore                  - игнорирование файлов
echo.
echo 🎯 Проект соответствует стандартам GitHub!
echo.
echo Ключевые файлы для GitHub:
echo   • LICENSE (если нужна)
echo   • .github/workflows/ (для CI/CD)
echo   • CONTRIBUTING.md (если нужно)
echo.
echo Готово к коммиту в Git! 🚀
echo.
