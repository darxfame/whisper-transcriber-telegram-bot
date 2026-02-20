# 🔧 TROUBLESHOOTING Guide

## 🚨 Частые проблемы и решения

### 1. ❌ "Peer id invalid" - Повреждена сессия

**Ошибка:**
```
ValueError('Peer id invalid')
```

**Причина:** Кэш pyrogram повреждён после разрыва соединения

**Решение:**
```bash
# Удалить кэш сессии
docker exec voicebot-userbot rm -rf .pyro-sessions/
docker exec voicebot-userbot rm -rf .pyro-*

# Перезапустить бот
docker-compose restart userbot

# Проверить логи
docker-compose logs -f userbot
```

---

### 2. ❌ "Connection lost" / Socket error

**Ошибка:**
```
socket.send() raised exception.
ConnectionResetError: [Errno 104] Connection reset by peer
```

**Причина:** Сеть упала или соединение прервалось

**Решение:** Это нормально! Бот должен автоматически переподключиться
```bash
# Проверить, переподключается ли бот
docker-compose logs --tail=50 userbot | grep "Reconnect\|подключен\|Соединение"

# Если не переподключается после 5 попыток - перезапустить
docker-compose restart userbot
```

**Ожидаемое поведение:**
```
⏳ Переподключение через 5s...
[1/5] Подключение к Telegram...
⏳ Переподключение через 10s...
[2/5] Подключение к Telegram...
✅ Соединение с Telegram установлено
```

---

### 3. ❌ Redis not available

**Ошибка:**
```
❌ Не удалось подключиться к Redis после 5 попыток
```

**Решение:**

```bash
# Проверить статус Redis
docker-compose ps redis

# Если не запущен
docker-compose up -d redis

# Если запущен но не отвечает
docker-compose logs redis

# Если Redis в плохом состоянии - пересоздать
docker-compose down
docker volume rm pyrofork_redis_data
docker-compose up -d redis
```

---

### 4. ❌ API_ID/API_HASH not found

**Ошибка:**
```
❌ Критические переменные окружения не установлены!
   Проверьте API_ID и API_HASH в .env файле
```

**Решение:**
```bash
# Проверить .env
cat .env

# Убедиться, что есть значения
API_ID=26607062
API_HASH=8407ffeda812e8de2c1ed65f53f9b4c5

# Если .env пуст
cp .env.example .env
# Отредактировать с реальными значениями

# Перезапустить бот
docker-compose down
docker-compose up -d
```

---

### 5. ❌ Docker compose command not found

**Ошибка:**
```
command not found: docker-compose
```

**Решение:**

На новых версиях Docker используется `docker compose` (без дефиса)

```bash
# Проверить версию Docker
docker --version

# Если версия < 20.10, установить docker-compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Или использовать встроенный плагин
docker compose ps  # вместо docker-compose ps
```

---

### 6. ❌ Out of memory

**Ошибка:**
```
Killed
OOMKilled
Memory error
```

**Причина:** На системе недостаточно памяти для модели Whisper

**Решение:**

Уменьшить модель в docker-compose.yml:
```yaml
environment:
  - WHISPER_MODEL=tiny    # вместо small или medium
```

Или увеличить память для LXC контейнера в Proxmox:
```bash
# В Proxmox WebUI
Контейнер → Ресурсы → Память: увеличить до 16-32GB
```

---

### 7. ❌ ffmpeg not found

**Ошибка:**
```
ffmpeg: not found
whisper error: ffmpeg not available
```

**Решение:**

Этот файл уже включён в Dockerfile. Если ошибка появляется:

```bash
# Пересобрать образ
docker-compose build --no-cache

# Переиндексировать контейнеры
docker-compose down
docker-compose up -d
```

---

### 8. ❌ Бот не обрабатывает голосовые

**Проблема:** Голосовые приходят, но не транскрибируются

**Решение:**

```bash
# 1. Проверить, включен ли бот
docker-compose exec userbot python -c "import redis; r=redis.Redis(host='redis'); print('enabled:', r.get('enabled')); print('my:', r.get('my')); print('friend:', r.get('friend'))"

# Вывод должен быть:
# enabled: 1
# my: 1
# friend: 1

# 2. Если выключено, включить через команду
# /voicebot_on

# 3. Если включено - проверить модель
docker-compose exec userbot python -c "import redis; r=redis.Redis(host='redis'); print('model:', r.get('model'))"

# 4. Проверить логи при отправке голосового
docker-compose logs -f userbot
```

---

### 9. ❌ Модель очень медленно транскрибирует

**Проблема:** Транскрипция длится минуты для короткого аудио

**Решение:**

Переключиться на более быструю модель:
```bash
# Отправить боту команду
/model tiny       # самая быстрая, худшее качество
/model base       # быстрая, среднее качество  
/model small      # баланс скорость/качество (рекомендуется)
```

Или отредактировать docker-compose.yml:
```yaml
environment:
  - WHISPER_MODEL=tiny
```

**Скорости на CPU:**
- tiny: ~0.5x RT (в 2 раза быстрее реального времени)
- base: ~0.7x RT
- small: ~1.5x RT (рекомендуется)
- medium: ~3x RT
- large: ~5-10x RT (очень медленно на CPU)

---

### 10. ❌ "Connection refused" для redis://redis:6379

**Ошибка:**
```
redis.exceptions.ConnectionError: Error 111 connecting to redis:6379.
Connection refused.
```

**Причина:** Redis контейнер не доступен из userbot контейнера

**Решение:**

```bash
# Проверить, что контейнеры в одной сети
docker-compose ps

# Проверить сеть
docker network ls
docker network inspect pyrofork_voicebot_net

# Если сеть не создана, пересоздать
docker-compose down
docker-compose up -d --build
```

---

### 11. ❌ Port already in use

**Ошибка:**
```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:6379 -> 0.0.0.0:6379
```

**Решение:**

```bash
# Найти процесс на порту 6379
lsof -i :6379
# или на Windows
netstat -ano | findstr :6379

# Убить процесс
kill -9 <PID>

# Или изменить порт в docker-compose.yml
ports:
  - "6380:6379"  # вместо 6379:6379
```

---

### 12. ❌ File permissions denied

**Ошибка:**
```
Permission denied: './voice_transcriber.session'
```

**Решение:**

```bash
# На Linux/MacOS
chmod 666 voice_transcriber.session
chmod 755 start.sh
chmod 755 health_check.sh

# На Windows (в Git Bash)
git update-index --chmod=+x start.sh
```

---

## 🔍 Диагностика

### Полная проверка системы

```bash
#!/bin/bash
echo "=== System Check ==="
docker --version
docker-compose version
free -h
df -h
ps aux | grep docker

echo ""
echo "=== Container Status ==="
docker-compose ps

echo ""
echo "=== Redis Status ==="
docker-compose logs --tail=10 redis

echo ""
echo "=== Bot Status ==="
docker-compose logs --tail=50 userbot

echo ""
echo "=== Connectivity Test ==="
docker exec voicebot-userbot ping -c 1 8.8.8.8
docker exec voicebot-redis redis-cli PING
```

### Просмотр логов в реальном времени

```bash
# Все контейнеры
docker-compose logs -f

# Только userbot
docker-compose logs -f userbot

# Только redis
docker-compose logs -f redis

# Последние 200 строк
docker-compose logs --tail=200 userbot

# За последний час
docker-compose logs --since=1h userbot
```

### Интерактивная оболочка контейнера

```bash
# Войти в контейнер userbot
docker-compose exec userbot bash

# Внутри контейнера
python --version
redis-cli -h redis PING
ls -la /app/
```

---

## 🆘 Если ничего не помогает

### 1. Полная переустановка

```bash
# Остановить всё
docker-compose down -v

# Удалить образы
docker rmi pyrofork-userbot
docker rmi redis:7-alpine

# Удалить сессию (внимание - потребуется новая авторизация)
rm -f voice_transcriber.session

# Пересобрать и запустить
docker-compose up -d --build
```

### 2. Проверить логи Docker daemon

```bash
# На Linux
journalctl -u docker -n 100

# На MacOS
log stream --level debug --process docker

# На Windows
Get-EventLog -LogName Application -Source Docker -Newest 50
```

### 3. Проверить конфигурацию

```bash
# Валидировать docker-compose.yml
docker-compose config

# Проверить синтаксис
docker-compose up --validate
```

### 4. Контактировать с поддержкой

Если ничего не помогает, соберите информацию:

```bash
# Сохранить диагностику
{
  docker --version
  docker-compose version
  docker-compose config
  docker-compose logs --tail=200 > logs.txt
  uname -a
  free -h
  df -h
} > diagnostics.txt

# Отправить файл logs.txt и diagnostics.txt разработчику
```

---

## ✅ Нормальные сообщения логирования

Это НЕ ошибки, не паникуйте:

```
⏳ Переподключение через 5s...        # Нормальное переподключение
[1/5] Подключение к Telegram...      # Повторная попытка подключения
⚠️  Попытка 1 не удалась              # Redis может быть медленнее
❌ Ошибка редактирования сообщения     # Может быть, если сообщение старое
FloodWait 5 сек                       # Telegram просит подождать
```

---

**Последнее обновление:** 2026-02-18  
**Версия:** 2.0

