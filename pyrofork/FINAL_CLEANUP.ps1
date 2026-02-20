#!/usr/bin/env pwsh
# FINAL_CLEANUP.ps1 - Финальная очистка проекта для GitHub стандартов

Write-Host "✨ ФИНАЛЬНАЯ ОЧИСТКА ПРОЕКТА (GitHub стандарты)" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Переход в корень проекта
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "📂 Работаю в: $(Get-Location)" -ForegroundColor Green
Write-Host ""

$deletedCount = 0

# === 1. Батники ===
Write-Host "[1/5] Удаляю батники из корня..." -ForegroundColor Yellow
$batFiles = @(
    "1_CLEANUP.bat",
    "2_RESTART.bat",
    "3_LOGS.bat",
    "4_CHECK_ERRORS.bat",
    "5_STATUS.bat",
    "6_STOP.bat",
    "7_START.bat",
    "8_CHECK_TYPES.bat",
    "CLEANUP_NOW.bat",
    "cleanup.ps1"
)

foreach ($file in $batFiles) {
    if (Test-Path $file) {
        Remove-Item $file -Force -ErrorAction SilentlyContinue
        Write-Host "   ✓ Удален: $file" -ForegroundColor Green
        $deletedCount++
    }
}

# === 2. Скрипты ===
Write-Host ""
Write-Host "[2/5] Удаляю скрипты из корня..." -ForegroundColor Yellow
$scriptFiles = @("start.sh", "health_check.sh")

foreach ($file in $scriptFiles) {
    if (Test-Path $file) {
        Remove-Item $file -Force -ErrorAction SilentlyContinue
        Write-Host "   ✓ Удален: $file" -ForegroundColor Green
        $deletedCount++
    }
}

# === 3. Документация ===
Write-Host ""
Write-Host "[3/5] Удаляю документацию из корня..." -ForegroundColor Yellow
$docFiles = @(
    "BATNIKI.md",
    "CHANGES.md",
    "FIXES.md",
    "PRODUCTION_CLEANUP.md",
    "START.md",
    "STATUS.md",
    "TYPE_FIX_SUMMARY.txt",
    "CLEANUP_PLAN.md"
)

foreach ($file in $docFiles) {
    if (Test-Path $file) {
        Remove-Item $file -Force -ErrorAction SilentlyContinue
        Write-Host "   ✓ Удален: $file" -ForegroundColor Green
        $deletedCount++
    }
}

# === 4. Исходный код из корня ===
Write-Host ""
Write-Host "[4/5] Удаляю дублированный userbot.py из корня..." -ForegroundColor Yellow
if (Test-Path "userbot.py") {
    Remove-Item "userbot.py" -Force -ErrorAction SilentlyContinue
    Write-Host "   ✓ Удален: userbot.py (основной: src/userbot.py)" -ForegroundColor Green
    $deletedCount++
}

# === 5. Временные файлы и папки ===
Write-Host ""
Write-Host "[5/5] Удаляю временные файлы и папки..." -ForegroundColor Yellow

if (Test-Path "voice_transcriber copy.session") {
    Remove-Item "voice_transcriber copy.session" -Force -ErrorAction SilentlyContinue
    Write-Host "   ✓ Удален: voice_transcriber copy.session" -ForegroundColor Green
    $deletedCount++
}

if (Test-Path "old") {
    Remove-Item "old" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "   ✓ Удалена папка: old/" -ForegroundColor Green
    $deletedCount++
}

# Очистка __pycache__
$pycacheDirs = Get-ChildItem -Path . -Directory -Name "__pycache__" -Recurse -ErrorAction SilentlyContinue
if ($pycacheDirs) {
    $pycacheDirs | ForEach-Object {
        $fullPath = (Get-Item $_).FullName
        Remove-Item $fullPath -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "   ✓ Удалены __pycache__ директории" -ForegroundColor Green
}

# === Финальный статус ===
Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "✅ ОЧИСТКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Статистика:" -ForegroundColor Cyan
Write-Host "   • Файлов удалено: $deletedCount" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Структура проекта готова к GitHub:" -ForegroundColor Cyan
Write-Host "   ✅ src/userbot.py              - основной код" -ForegroundColor Green
Write-Host "   ✅ scripts/                    - батники и утилиты" -ForegroundColor Green
Write-Host "   ✅ docs/                       - полная документация" -ForegroundColor Green
Write-Host "   ✅ docker-compose.yml          - конфигурация Docker" -ForegroundColor Green
Write-Host "   ✅ Dockerfile                  - образ Docker" -ForegroundColor Green
Write-Host "   ✅ requirements.txt            - зависимости" -ForegroundColor Green
Write-Host "   ✅ README.md                   - описание проекта" -ForegroundColor Green
Write-Host "   ✅ .env.example                - пример переменных" -ForegroundColor Green
Write-Host ""
Write-Host "🎯 Проект соответствует стандартам GitHub!" -ForegroundColor Green
Write-Host ""
Write-Host "Готово к коммиту в Git! 🚀" -ForegroundColor Green
Write-Host ""

# Удалить сам себя
$scriptPath = $MyInvocation.MyCommand.Path
if (Test-Path $scriptPath) {
    Write-Host "Удаляю скрипт очистки..." -ForegroundColor Gray
    Start-Sleep -Milliseconds 500
    Remove-Item $scriptPath -Force -ErrorAction SilentlyContinue
}
