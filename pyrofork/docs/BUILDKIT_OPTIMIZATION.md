# 🚀 BuildKit - максимальная оптимизация Docker кэша

## Проблема

Даже с multi-stage build, при каждой пересборке Docker может не использовать кэш оптимально.

## Решение: Docker BuildKit

BuildKit - это современный builder для Docker с улучшенным кэшем.

### Как включить BuildKit

#### На хосте

```bash
# Способ 1: переменная окружения
export DOCKER_BUILDKIT=1
docker-compose up -d --build

# Способ 2: в docker-compose.yml
services:
  userbot:
    build:
      context: .
      dockerfile: Dockerfile
      cache_from:
        - type=local,src=.buildcache
      cache_to:
        - type=local,dest=.buildcache
```

#### На Proxmox LXC (рекомендуется)

```bash
# Включить BuildKit в daemon
echo '{"features": {"buildkit": true}}' | tee /etc/docker/daemon.json
systemctl restart docker

# Теперь BuildKit используется по умолчанию
docker-compose up -d --build
```

### Команды с BuildKit

```bash
# С BuildKit (автоматически, если включен)
docker-compose up -d --build

# Явно с BuildKit
DOCKER_BUILDKIT=1 docker-compose up -d --build

# Без кэша (если что-то сломалось)
DOCKER_BUILDKIT=1 docker-compose build --no-cache

# Проверить, что BuildKit работает
docker buildx ls
```

## Результат с BuildKit

```bash
# Первая сборка
DOCKER_BUILDKIT=1 docker-compose up -d --build    # 5-10 мин

# Вторая пересборка (с BuildKit!)
DOCKER_BUILDKIT=1 docker-compose up -d --build    # 5-10 секунд! ⚡⚡

# Только изменили код
docker-compose up -d --build                       # 3-5 секунд ⚡⚡⚡
```

## Почему BuildKit лучше?

| Функция | Обычный Docker | BuildKit |
|---------|:---:|:---:|
| Кэш слоев | ✅ | ✅✅ Умнее |
| Параллельная сборка | ❌ | ✅ Быстрее |
| Локальный кэш | ❌ | ✅ Сохраняет между сборками |
| Выгрузка кэша | ❌ | ✅ На диск |

## Дополнительные оптимизации

### 1. Сохранение кэша на диск

```bash
# Создать папку для кэша
mkdir -p .buildcache

# Команда с сохранением кэша
docker buildx build \
  --cache-from=type=local,src=.buildcache \
  --cache-to=type=local,dest=.buildcache \
  -t voicebot-userbot:latest .
```

### 2. В docker-compose.yml

```yaml
services:
  userbot:
    build:
      context: .
      dockerfile: Dockerfile
      # BuildKit автоматически кэширует
      # Дополнительный контроль (опционально):
      cache_from:
        - type=local,src=.buildcache
      cache_to:
        - type=local,dest=.buildcache
```

### 3. Пересборка БЕЗ кэша (если нужно)

```bash
# Полная пересборка без кэша
docker-compose build --no-cache
DOCKER_BUILDKIT=1 docker-compose build --no-cache
```

## Проверка работы

```bash
# Посмотреть, какой builder используется
docker buildx ls

# Должно быть похоже на:
# NAME/NODE    DRIVER/ENDPOINT             STATUS   PLATFORMS
# default      docker                      -        linux/amd64, ...
# desktop      docker (default)            running  linux/amd64, ...
```

## На Proxmox LXC - пошагово

### Шаг 1: Включить BuildKit

```bash
# SSH в LXC контейнер или хост Proxmox
ssh root@proxmox-host

# Отредактировать Docker конфиг
nano /etc/docker/daemon.json

# Добавить или убедиться, что есть:
{
  "features": {
    "buildkit": true
  }
}

# Перезагрузить Docker
systemctl restart docker
```

### Шаг 2: Проверить

```bash
docker buildx ls
# Должна быть поддержка BuildKit
```

### Шаг 3: Использовать

```bash
cd /path/to/pyrofork

# Первая сборка - медленнее, но нормально
docker-compose up -d --build    # 5-10 мин

# Вторая - ОЧЕНЬ быстро!
docker-compose up -d --build    # 5-10 сек ⚡

# Только код изменился?
docker-compose up -d --build    # 2-3 сек ⚡⚡
```

## Итого: комбо многоэтапная сборка + BuildKit

```
Первая сборка:           5-10 минут
Вторая (код изменился):  3-5 секунд
Третья (только код):     2-3 секунды

Все NVIDIA пакеты:
- Первый раз: скачиваются и кэшируются
- Потом: из кэша BuildKit (мгновенно)
```

## .gitignore для кэша

```bash
# Добавить в .gitignore
.buildcache/
```

---

**Когда это помогает больше всего:**
- Много кода меняется, зависимости редко
- CI/CD пайплайны с частыми деплоями
- Локальная разработка с редеплоями

**Рекомендация:**
Включите BuildKit на Proxmox - это значительно ускорит пересборки!

---

**Версия:** 2.0  
**Дата:** 2026-02-18

