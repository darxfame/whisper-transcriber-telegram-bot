#!/bin/bash
# health_check.sh - проверка здоровья приложения

# Переходим в корень проекта
cd "$(dirname "$(readlink -f "$0")")/.."

echo "🏥 Health Check VoiceBot"
echo "========================"
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_count=0
pass_count=0

# Функция для проверки
check() {
    local name=$1
    local cmd=$2
    check_count=$((check_count + 1))

    echo -n "[$check_count] $name... "

    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
}

# === DOCKER CHECKS ===
echo -e "${YELLOW}🐳 Docker Checks${NC}"

check "Docker installed" "command -v docker"
check "Docker running" "docker ps > /dev/null"
check "Docker compose" "command -v docker-compose"

echo ""

# === CONTAINERS ===
echo -e "${YELLOW}🔧 Containers${NC}"

check "Redis container exists" "docker ps -a | grep -q voicebot-redis"
check "Userbot container exists" "docker ps -a | grep -q voicebot-userbot"
check "Redis running" "docker ps | grep -q voicebot-redis"
check "Userbot running" "docker ps | grep -q voicebot-userbot"

echo ""

# === REDIS ===
echo -e "${YELLOW}💾 Redis${NC}"

check "Redis ping" "docker exec voicebot-redis redis-cli PING > /dev/null"
check "Redis data" "docker exec voicebot-redis redis-cli GET enabled > /dev/null"

echo ""

# === NETWORK ===
echo -e "${YELLOW}🌐 Network${NC}"

check "Internet connection" "docker exec voicebot-userbot ping -c 1 8.8.8.8 > /dev/null"
check "Telegram API DNS" "docker exec voicebot-userbot ping -c 1 api.telegram.org > /dev/null"

echo ""

# === FILES ===
echo -e "${YELLOW}📁 Files${NC}"

check "src/userbot.py exists" "[ -f ./src/userbot.py ]"
check ".env exists" "[ -f ./.env ]"
check "voice_transcriber.session" "[ -f ./voice_transcriber.session ]"

echo ""

# === LOGS ===
echo -e "${YELLOW}📋 Logs${NC}"

echo "Last 20 log lines:"
echo "===================="
docker-compose logs --tail=20 userbot 2>/dev/null | tail -20

echo ""
echo "===================="
echo "Summary: $pass_count/$check_count checks passed"
echo ""

if [ $pass_count -eq $check_count ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed${NC}"
    exit 1
fi
