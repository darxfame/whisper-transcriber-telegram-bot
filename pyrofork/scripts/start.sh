#!/bin/bash
set -e

# Переходим в корень проекта
cd "$(dirname "$(readlink -f "$0")")/.."

echo "=========================================="
echo "🚀 VoiceBot Transcriber Startup"
echo "=========================================="
echo ""

# Проверка переменных окружения
echo "📋 Проверка переменных окружения..."

if [ -z "$API_ID" ]; then
    echo "❌ Ошибка: API_ID не установлена"
    exit 1
fi

if [ -z "$API_HASH" ]; then
    echo "❌ Ошибка: API_HASH не установлена"
    exit 1
fi

echo "✅ API_ID = ${API_ID:0:5}***"
echo "✅ API_HASH = ${API_HASH:0:5}***"
echo ""

# Проверка Redis
echo "🔍 Проверка Redis..."
redis_attempts=0
while [ $redis_attempts -lt 5 ]; do
    if redis-cli -h redis -p 6379 PING > /dev/null 2>&1; then
        echo "✅ Redis доступен на redis:6379"
        break
    else
        redis_attempts=$((redis_attempts + 1))
        if [ $redis_attempts -lt 5 ]; then
            echo "⚠️  Redis не доступен, попытка $redis_attempts/5..."
            sleep 2
        fi
    fi
done

if [ $redis_attempts -eq 5 ]; then
    echo "❌ Redis недоступен после 5 попыток"
    exit 1
fi

echo ""
echo "=========================================="
echo "🤖 Запуск бота с pyrogram..."
echo "=========================================="
echo ""

# Экспортирование переменных для Python
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

# Запуск Python приложения
exec python -u src/userbot.py
