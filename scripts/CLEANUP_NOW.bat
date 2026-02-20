@echo off
chcp 65001 >nul
echo.
echo 🧹 ОЧИСТКА ПРОЕКТА ДЛЯ ПРОДАКШЕНА...
echo.

cd /d "%~dp0\.."

REM Удаляю старые версии кода
echo ❌ Удаляю старый код...
del /F /Q "userbot15.02.2026.py" 2>nul
del /F /Q "userbot_clean.py" 2>nul
del /F /Q "userbot_old.py" 2>nul

REM Удаляю session и логи
echo ❌ Удаляю session и логи...
del /F /Q "voice_transcriber.session" 2>nul
del /F /Q "voice_transcriber copy.session" 2>nul
del /F /Q "log.txt" 2>nul

REM Удаляю ВСЮ лишнюю документацию из корня
echo ❌ Удаляю лишнюю документацию...
del /F /Q "ANALYSIS.md" 2>nul
del /F /Q "CHANGELOG.md" 2>nul
del /F /Q "DOCUMENTATION_STRUCTURE.md" 2>nul
del /F /Q "ERRORS_EXPLAINED.md" 2>nul
del /F /Q "FINAL_STATUS.md" 2>nul
del /F /Q "FINAL_SUMMARY.md" 2>nul
del /F /Q "FIX_SUMMARY.md" 2>nul
del /F /Q "FULL_REPORT.md" 2>nul
del /F /Q "GETTING_STARTED.md" 2>nul
del /F /Q "ONE_PAGE_SUMMARY.md" 2>nul
del /F /Q "PRODUCTION_CLEANUP.md" 2>nul
del /F /Q "QUICK_FIX_CHECKLIST.md" 2>nul
del /F /Q "README_FIXES.md" 2>nul
del /F /Q "SOLUTION_DIAGRAM.md" 2>nul
del /F /Q "START_HERE.md" 2>nul
del /F /Q "SUMMARY_TABLE.md" 2>nul
del /F /Q "VERIFICATION.md" 2>nul
del /F /Q "STATUS.md" 2>nul
del /F /Q "FIXES.md" 2>nul
del /F /Q "BATNIKI.md" 2>nul
del /F /Q "CHANGES.md" 2>nul

REM Удаляю все скрипты очистки
echo ❌ Удаляю скрипты очистки...
del /F /Q "cleanup.sh" 2>nul
del /F /Q "cleanup.bat" 2>nul
del /F /Q "cleanup.ps1" 2>nul
del /F /Q "cleanup_production.sh" 2>nul
del /F /Q "cleanup_production.bat" 2>nul

REM Удаляю все батники из корня
echo ❌ Удаляю батники из корня...
del /F /Q "1_CLEANUP.bat" 2>nul
del /F /Q "2_RESTART.bat" 2>nul
del /F /Q "3_LOGS.bat" 2>nul
del /F /Q "4_CHECK_ERRORS.bat" 2>nul
del /F /Q "5_STATUS.bat" 2>nul
del /F /Q "6_STOP.bat" 2>nul
del /F /Q "7_START.bat" 2>nul
del /F /Q "8_CHECK_TYPES.bat" 2>nul

REM Очистка Python кэша
echo ❌ Очищаю __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul

REM Удаляю директорию old/
echo ❌ Удаляю директорию old/...
if exist "old\" rd /s /q "old\" 2>nul

echo.
echo ✅ ГОТОВО!
echo.
echo 📊 В корне осталось только необходимое:
echo   ✅ src/userbot.py
echo   ✅ requirements.txt
echo   ✅ docker-compose.yml
echo   ✅ Dockerfile
echo   ✅ README.md
echo   ✅ docs/
echo   ✅ scripts/
echo.
echo 🚀 ГОТОВО К ПРОДАКШЕНУ!
echo.
