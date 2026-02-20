#!/bin/bash
# deploy.sh — Сборка, запуск и автоочистка старых образов Docker
# Использование: bash scripts/deploy.sh
set -e
cd "$(dirname "$(readlink -f "$0")")/.."

# Включаем BuildKit явно — требуется для cache mounts
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# BUILD_DATE — передаём явно в окружение
BUILD_DATE=$(date -u +'%Y-%m-%d %H:%M:%S UTC')
export BUILD_DATE

echo "=========================================="
echo "🚀 DEPLOY: сборка и запуск (BuildKit: ON)"
echo "📅 Дата сборки: $BUILD_DATE"
echo "=========================================="

# docker-compose читает .env из текущей директории автоматически (v1 и v2)
# BUILD_DATE добавили в окружение через export выше
docker-compose up -d --build

echo ""
echo "=========================================="
echo "🧹 CLEANUP: удаление мусора"
echo "=========================================="

DANGLING=$(docker images -f "dangling=true" -q)
if [ -n "$DANGLING" ]; then
    echo "🗑️  Удаляю dangling образы..."
    docker image rm $DANGLING
else
    echo "✅ Dangling образов нет"
fi

STOPPED=$(docker ps -a -f "status=exited" -f "status=created" -q)
if [ -n "$STOPPED" ]; then
    echo "🗑️  Удаляю остановленные контейнеры..."
    docker container rm $STOPPED
else
    echo "✅ Остановленных контейнеров нет"
fi

docker network prune -f > /dev/null 2>&1
echo "✅ Неиспользуемые сети удалены"

echo ""
echo "=========================================="
echo "💾 Место на диске после очистки:"
docker system df
echo "=========================================="
echo ""
echo "📋 Логи: docker-compose logs -f userbot"
