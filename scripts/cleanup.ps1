# PowerShell скрипт для полной очистки проекта перед продакшеном

Write-Host "🧹 Полная очистка проекта для продакшена..." -ForegroundColor Cyan
Write-Host ""

# Перейти в родительскую директорию
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

# Функция для безопасного удаления файла
function Remove-FileIfExists {
    param(
        [string]$FilePath,
        [string]$Description
    )

    if (Test-Path $FilePath) {
        try {
            Remove-Item $FilePath -Force -ErrorAction Stop
            Write-Host "  ✅ Удален: $Description" -ForegroundColor Green
        }
        catch {
            Write-Host "  ⚠️  Ошибка удаления $Description`: $_" -ForegroundColor Yellow
        }
    }
}

Write-Host "1️⃣  Удаляю старые версии кода..." -ForegroundColor Yellow
Remove-FileIfExists "userbot15.02.2026.py" "userbot15.02.2026.py"
Remove-FileIfExists "userbot_clean.py" "userbot_clean.py"
Remove-FileIfExists "userbot_old.py" "userbot_old.py"

Write-Host ""
Write-Host "2️⃣  Удаляю файлы сессии и логи..." -ForegroundColor Yellow
Remove-FileIfExists "voice_transcriber.session" "voice_transcriber.session"
Remove-FileIfExists "voice_transcriber copy.session" "voice_transcriber copy.session"
Remove-FileIfExists "log.txt" "log.txt"

Write-Host ""
Write-Host "3️⃣  Удаляю лишнюю документацию..." -ForegroundColor Yellow

$docFiles = @(
    "ANALYSIS.md",
    "DOCUMENTATION_STRUCTURE.md",
    "ERRORS_EXPLAINED.md",
    "FINAL_SUMMARY.md",
    "FIX_SUMMARY.md",
    "FULL_REPORT.md",
    "GETTING_STARTED.md",
    "ONE_PAGE_SUMMARY.md",
    "QUICK_FIX_CHECKLIST.md",
    "README_FIXES.md",
    "SOLUTION_DIAGRAM.md",
    "START_HERE.md",
    "SUMMARY_TABLE.md",
    "VERIFICATION.md",
    "FINAL_STATUS.md",
    "CHANGELOG.md",
    "PRODUCTION_CLEANUP.md",
    "START.md",
    "STATUS.md",
    "FIXES.md",
    "BATNIKI.md",
    "CHANGES.md"
)

foreach ($file in $docFiles) {
    Remove-FileIfExists $file $file
}

Write-Host ""
Write-Host "4️⃣  Удаляю батники и скрипты из корня..." -ForegroundColor Yellow

$scriptFiles = @(
    "1_CLEANUP.bat",
    "2_RESTART.bat",
    "3_LOGS.bat",
    "4_CHECK_ERRORS.bat",
    "5_STATUS.bat",
    "6_STOP.bat",
    "7_START.bat",
    "8_CHECK_TYPES.bat",
    "CLEANUP_NOW.bat",
    "cleanup.sh",
    "cleanup.bat",
    "cleanup_production.sh",
    "cleanup_production.bat"
)

foreach ($file in $scriptFiles) {
    Remove-FileIfExists $file $file
}

Write-Host ""
Write-Host "5️⃣  Очищаю кэш Python..." -ForegroundColor Yellow

$pycacheDirs = Get-ChildItem -Path . -Directory -Name "__pycache__" -Recurse -ErrorAction SilentlyContinue
if ($pycacheDirs) {
    foreach ($dir in $pycacheDirs) {
        $fullPath = (Get-Item $_).FullName
        Remove-Item $fullPath -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  ✅ Удалены __pycache__ директории" -ForegroundColor Green
}

$pycFiles = Get-ChildItem -Path . -Filter "*.pyc" -Recurse -ErrorAction SilentlyContinue
if ($pycFiles) {
    $pycFiles | Remove-Item -Force -ErrorAction SilentlyContinue
    Write-Host "  ✅ Удалены *.pyc файлы" -ForegroundColor Green
}

Write-Host ""
Write-Host "6️⃣  Удаляю директорию old/..." -ForegroundColor Yellow
if (Test-Path "old") {
    Remove-Item "old" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  ✅ Удалена директория old/" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" * 60
Write-Host "✅ ОЧИСТКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "=" * 60
Write-Host ""
Write-Host "📊 Структура проекта готова для продакшена:" -ForegroundColor Cyan
Write-Host "  ✅ src/userbot.py - основной файл бота"
Write-Host "  ✅ requirements.txt"
Write-Host "  ✅ docker-compose.yml"
Write-Host "  ✅ Dockerfile"
Write-Host "  ✅ README.md"
Write-Host "  ✅ docs/ - вся документация здесь"
Write-Host "  ✅ scripts/ - батники и утилиты"
Write-Host ""
Write-Host "🚀 ГОТОВО К ПРОДАКШЕНУ!" -ForegroundColor Green
Write-Host ""

# Удалить сам себя
$scriptPath = $MyInvocation.MyCommand.Path
if (Test-Path $scriptPath) {
    Start-Sleep -Milliseconds 500
    Remove-Item $scriptPath -Force -ErrorAction SilentlyContinue
}
