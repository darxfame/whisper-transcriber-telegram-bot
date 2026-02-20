@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

echo.
echo ═══════════════════════════════════════════════════════
echo   🧹 ОЧИСТКА ПРОЕКТА ПЕРЕД ПРОДАКШЕНОМ
echo ═══════════════════════════════════════════════════════
echo.

echo [1/6] Удаляю старые версии кода...
if exist "userbot15.02.2026.py" del /F /Q "userbot15.02.2026.py" && echo   ✓ userbot15.02.2026.py
if exist "userbot_clean.py" del /F /Q "userbot_clean.py" && echo   ✓ userbot_clean.py
if exist "userbot_old.py" del /F /Q "userbot_old.py" && echo   ✓ userbot_old.py

echo.
echo [2/6] Удаляю файлы сессий...
if exist "voice_transcriber.session" del /F /Q "voice_transcriber.session" && echo   ✓ voice_transcriber.session
if exist "voice_transcriber copy.session" del /F /Q "voice_transcriber copy.session" && echo   ✓ voice_transcriber copy.session

echo.
echo [3/6] Удаляю тестовые логи...
if exist "log.txt" del /F /Q "log.txt" && echo   ✓ log.txt

echo.
echo [4/6] Удаляю лишнюю документацию из корня...
for %%f in (
    FIXES.md
    STATUS.md
    START.md
    PRODUCTION_CLEANUP.md
    TYPE_FIX_SUMMARY.txt
    ANALYSIS.md
    CHANGELOG.md
    DOCUMENTATION_STRUCTURE.md
    ERRORS_EXPLAINED.md
    FINAL_STATUS.md
    FINAL_SUMMARY.md
    FIX_SUMMARY.md
    FULL_REPORT.md
    GETTING_STARTED.md
    ONE_PAGE_SUMMARY.md
    QUICK_FIX_CHECKLIST.md
    README_FIXES.md
    SOLUTION_DIAGRAM.md
    START_HERE.md
    SUMMARY_TABLE.md
    VERIFICATION.md
    BATNIKI.md
    CHANGES.md
    CLEANUP_PLAN.md
) do (
    if exist "%%f" del /F /Q "%%f" && echo   ✓ %%f
)

echo.
echo [5/6] Удаляю лишние батники и скрипты из корня...
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
    cleanup.sh
    cleanup_production.sh
    cleanup_production.bat
) do (
    if exist "%%f" del /F /Q "%%f" && echo   ✓ %%f
)

echo.
echo [6/6] Очищаю кэш Python...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul
echo   ✓ __pycache__ и *.pyc удалены

echo.
echo ═══════════════════════════════════════════════════════
echo   ✅ ОЧИСТКА ЗАВЕРШЕНА!
echo ═══════════════════════════════════════════════════════
echo.
echo 📊 В корне осталось только необходимое:
echo   ✅ src/userbot.py (исправленный код)
echo   ✅ requirements.txt
echo   ✅ docker-compose.yml
echo   ✅ Dockerfile
echo   ✅ README.md
echo   ✅ docs/ (вся документация)
echo   ✅ scripts/ (батники и утилиты)
echo.
echo 🚀 ПРОЕКТ ГОТОВ К ПРОДАКШЕНУ!
echo.
echo Нажмите любую клавишу для выхода...
pause >nul
