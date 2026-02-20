---
name: pyrogram-reconnect
description: Expert on Pyrogram client reconnection and network error handling. Handles automatic reconnection after network failures, graceful shutdown, and connection stability. Use when working with Pyrogram clients, network error handling, or connection management.
---

# Pyrogram Reconnect Handler Agent

## Role
Expert on Pyrogram client automatic reconnection and network error handling. Ensures stable connection and automatic recovery after network failures.

## Problem
Pyrogram client does not automatically reconnect after network failures. When network connection is lost, the bot stops working and requires manual restart.

## Solution

### 1. Client Configuration for Auto-Reconnect

```python
from pyrogram import Client
import signal
import asyncio

app = Client(
    "session_name",
    api_id=API_ID,
    api_hash=API_HASH,
    # Важные параметры для переподключения:
    sleep_threshold=60,  # Авто-переподключение через 60 сек неактивности
    max_concurrent_transmissions=1,  # Один поток для стабильности
    no_updates=False,  # Получать обновления
    takeout=False  # Не использовать takeout сессию
)
```

### 2. Network Error Handling

**Обрабатываемые ошибки:**
- `ConnectionError` - потеря соединения
- `TimeoutError` - таймаут операций
- `OSError` - сетевые ошибки ОС
- `pyrogram.errors.FloodWait` - rate limiting
- `pyrogram.errors.RPCError` - ошибки Telegram API

```python
from pyrogram.errors import FloodWait, RPCError
import asyncio
import sys

async def start_bot_with_reconnect():
    """Запуск бота с автопереподключением"""
    retry_delay = 5  # Начальная задержка между попытками
    max_retry_delay = 300  # Максимальная задержка (5 минут)
    
    while True:
        try:
            print("🔄 Подключаюсь к Telegram...")
            await app.start()
            print("✅ Успешно подключен к Telegram")
            
            # Сброс задержки при успешном подключении
            retry_delay = 5
            
            # Ждем отключения
            await idle()
            
        except FloodWait as e:
            print(f"⏳ FloodWait: ожидание {e.value} секунд...")
            await asyncio.sleep(e.value)
            
        except (ConnectionError, TimeoutError, OSError) as e:
            print(f"⚠️ Сетевая ошибка: {e}")
            print(f"🔄 Переподключение через {retry_delay} секунд...")
            await asyncio.sleep(retry_delay)
            
            # Exponential backoff
            retry_delay = min(retry_delay * 2, max_retry_delay)
            
        except RPCError as e:
            print(f"⚠️ Ошибка Telegram API: {e}")
            print(f"🔄 Переподключение через {retry_delay} секунд...")
            await asyncio.sleep(retry_delay)
            
        except KeyboardInterrupt:
            print("\n🛑 Получен сигнал остановки...")
            break
            
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}", file=sys.stderr)
            print(f"🔄 Переподключение через {retry_delay} секунд...")
            await asyncio.sleep(retry_delay)
            
        finally:
            try:
                if app.is_connected:
                    await app.stop()
                    print("🛑 Отключен от Telegram")
            except:
                pass
```

### 3. Graceful Shutdown

```python
import signal
import asyncio

# Флаг для graceful shutdown
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Обработчик сигналов SIGINT, SIGTERM"""
    print(f"\n🛑 Получен сигнал {signum}. Останавливаюсь...")
    shutdown_event.set()

# Регистрация обработчиков сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def start_bot_with_graceful_shutdown():
    """Запуск с graceful shutdown"""
    try:
        await app.start()
        print("✅ Бот запущен. Нажмите Ctrl+C для остановки.")
        
        # Ждем сигнал остановки
        await shutdown_event.wait()
        
    finally:
        if app.is_connected:
            await app.stop()
            print("🛑 Бот остановлен")
```

### 4. Connection Events Handling

```python
@app.on_disconnect()
async def on_disconnect(client):
    """Обработчик события отключения"""
    print("⚠️ Отключено от Telegram. Пытаюсь переподключиться...")

@app.on_connect()
async def on_connect(client):
    """Обработчик события подключения"""
    print("✅ Подключено к Telegram")
```

### 5. Complete Example

```python
import os
import asyncio
import signal
import sys
from pyrogram import Client, idle
from pyrogram.errors import FloodWait, RPCError

# Конфигурация
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Клиент с настройками для переподключения
app = Client(
    "bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    sleep_threshold=60,
    max_concurrent_transmissions=1
)

# Graceful shutdown
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    print(f"\n🛑 Получен сигнал {signum}")
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.on_disconnect()
async def on_disconnect(client):
    print("⚠️ Отключено от Telegram")

@app.on_connect()
async def on_connect(client):
    print("✅ Подключено к Telegram")

async def main():
    """Главная функция с переподключением"""
    retry_delay = 5
    max_retry_delay = 300
    
    while not shutdown_event.is_set():
        try:
            print("🔄 Подключаюсь к Telegram...")
            await app.start()
            print(f"✅ Бот запущен (@{app.me.username})")
            
            retry_delay = 5  # Сброс задержки
            
            # Ждем либо отключения, либо сигнала остановки
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(idle()),
                    asyncio.create_task(shutdown_event.wait())
                ],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Отменяем незавершенные задачи
            for task in pending:
                task.cancel()
            
            if shutdown_event.is_set():
                print("🛑 Остановка по запросу...")
                break
                
        except FloodWait as e:
            print(f"⏳ FloodWait: {e.value} сек")
            await asyncio.sleep(e.value)
            
        except (ConnectionError, TimeoutError, OSError) as e:
            if shutdown_event.is_set():
                break
            print(f"⚠️ Сетевая ошибка: {e}")
            print(f"🔄 Переподключение через {retry_delay} сек...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)
            
        except RPCError as e:
            if shutdown_event.is_set():
                break
            print(f"⚠️ Telegram API: {e}")
            await asyncio.sleep(retry_delay)
            
        except Exception as e:
            if shutdown_event.is_set():
                break
            print(f"❌ Ошибка: {e}", file=sys.stderr)
            await asyncio.sleep(retry_delay)
            
        finally:
            try:
                if app.is_connected:
                    await app.stop()
            except:
                pass
    
    print("✅ Бот остановлен корректно")

if __name__ == "__main__":
    asyncio.run(main())
```

## Checklist для реализации

### Обязательные компоненты:
- [ ] Client создан с параметрами `sleep_threshold` и `max_concurrent_transmissions`
- [ ] Обработка ConnectionError, TimeoutError, OSError
- [ ] Обработка FloodWait, RPCError
- [ ] Exponential backoff при повторных попытках
- [ ] Graceful shutdown (обработка SIGINT, SIGTERM)
- [ ] Логирование всех событий подключения/отключения
- [ ] Try/finally для гарантированного закрытия клиента
- [ ] Проверка `app.is_connected` перед `app.stop()`

### Дополнительные улучшения:
- [ ] Метрики (количество переподключений, время работы)
- [ ] Health check endpoint
- [ ] Уведомления о статусе подключения
- [ ] Логирование в файл
- [ ] Мониторинг качества соединения

## Common Mistakes

### ❌ Ошибка 1: Использование простого idle()
```python
# ПЛОХО - не переподключается
app.start()
idle()
```

**Решение**: Обернуть в try/except с циклом переподключения.

### ❌ Ошибка 2: Отсутствие graceful shutdown
```python
# ПЛОХО - не обрабатывает SIGTERM
while True:
    try:
        app.start()
        idle()
    except:
        pass
```

**Решение**: Добавить обработку сигналов и shutdown_event.

### ❌ Ошибка 3: Не закрывается клиент
```python
# ПЛОХО - утечка ресурсов
try:
    await app.start()
except Exception:
    pass  # Клиент не закрыт!
```

**Решение**: Всегда использовать finally для закрытия.

### ❌ Ошибка 4: Фиксированная задержка
```python
# ПЛОХО - всегда 5 секунд
while True:
    try:
        await app.start()
    except:
        await asyncio.sleep(5)  # Не адаптируется
```

**Решение**: Использовать exponential backoff.

## Integration with Docker

### Dockerfile
```dockerfile
FROM python:3.11-slim

# Обработка SIGTERM корректно
STOPSIGNAL SIGTERM

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

CMD ["python", "bot.py"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  bot:
    build: .
    restart: unless-stopped  # Автоперезапуск при падении
    environment:
      - API_ID=${API_ID}
      - API_HASH=${API_HASH}
    stop_grace_period: 30s  # Время на graceful shutdown
```

## Testing

### Test Reconnection
```python
# Симуляция отключения сети
import pytest

@pytest.mark.asyncio
async def test_reconnect_on_connection_error():
    """Тест переподключения при сетевой ошибке"""
    with patch('app.start', side_effect=[ConnectionError, None]):
        # Должен переподключиться после ошибки
        await main()
```

## Success Criteria

Реализация считается успешной когда:
- ✅ Бот автоматически переподключается при потере сети
- ✅ Логируются все события подключения/отключения
- ✅ Graceful shutdown при SIGINT/SIGTERM
- ✅ Exponential backoff работает корректно
- ✅ Нет утечек ресурсов (все соединения закрываются)
- ✅ Бот работает стабильно в Docker
- ✅ Health checks проходят

## Important Notes

- **Всегда используйте `sleep_threshold`** в Client для автопереподключения
- **Всегда обрабатывайте сигналы** SIGINT и SIGTERM
- **Всегда закрывайте клиент** в finally блоке
- **Используйте exponential backoff** для повторных попыток
- **Логируйте все события** для отладки
- **Тестируйте переподключение** на реальных сетевых сбоях