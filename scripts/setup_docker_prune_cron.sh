#!/bin/bash
# setup_docker_prune_cron.sh — Устанавливает еженедельную автоочистку Docker
# Запусти ОДИН РАЗ на сервере: bash scripts/setup_docker_prune_cron.sh
set -e

CRON_JOB="0 3 * * 0 docker system prune -f --filter 'until=168h' >> /var/log/docker-prune.log 2>&1"

echo "📋 Добавляю cron задачу автоочистки Docker..."

(crontab -l 2>/dev/null | grep -v "docker system prune"; echo "$CRON_JOB") | crontab -

echo "✅ Cron задача добавлена:"
echo "   Каждое воскресенье в 3:00 — удаление образов старше 7 дней"
echo ""
echo "📋 Текущий crontab:"
crontab -l
