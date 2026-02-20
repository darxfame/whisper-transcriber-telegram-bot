"""
auth2.py — Умная авторизация для Pyrogram бота.

Возможности:
  - Обнаруживает существующие Telethon/Pyrogram session файлы
  - Предлагает конвертировать Telethon → Pyrogram без повторной авторизации
  - QR-авторизация через Telethon + автоконвертация в Pyrogram session
  - Поддержка 2FA (двухфакторная аутентификация)

Использование:
    pip install telethon pyrogram tgcrypto qrcode
    python auth2.py
"""

import asyncio
import glob
import os
import shutil
import sqlite3
import sys

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import SQLiteSession, StringSession

# ==================== КОНФИГУРАЦИЯ ====================
API_ID = 26607062
API_HASH = "8407ffeda812e8de2c1ed65f53f9b4c5"
# ======================================================

# Переходим в корень проекта
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT_DIR)

SESSION_NAME = "voice_transcriber"
PYROGRAM_SESSION = f"{SESSION_NAME}.session"
PROXY = ("socks5", "127.0.0.1", 2080)

MAX_RETRIES = 5


# ==================== Поиск session файлов ====================


def find_session_files():
    """Ищет все session файлы в проекте."""
    found = {}

    # Telethon StringSession (текстовый файл)
    for pattern in ["*.telethon_session", "**/*.telethon_session"]:
        for path in glob.glob(pattern, recursive=True):
            found[path] = "telethon_string"

    # Telethon SQLite session (.session файл с таблицей sessions/entities)
    # Pyrogram SQLite session (.session файл с таблицей sessions/peers)
    for pattern in ["*.session", "**/*.session"]:
        for path in glob.glob(pattern, recursive=True):
            if path in found:
                continue
            session_type = detect_session_type(path)
            if session_type:
                found[path] = session_type

    return found


def detect_session_type(path):
    """Определяет тип .session файла (pyrogram / telethon_sqlite / unknown)."""
    try:
        conn = sqlite3.connect(path)
        c = conn.cursor()

        # Получаем список таблиц
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in c.fetchall()}
        conn.close()

        if "peers" in tables and "sessions" in tables:
            return "pyrogram"
        if "entities" in tables and "sessions" in tables:
            return "telethon_sqlite"
        if "sessions" in tables:
            return "unknown_sqlite"

        return None
    except Exception:
        # Не SQLite — может быть текстовый файл
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            # Telethon StringSession — длинная base64 строка
            if len(content) > 100 and content.isascii() and " " not in content:
                return "telethon_string"
        except Exception:
            pass
        return None


def print_session_info(path, stype):
    """Печатает информацию о session файле."""
    size = os.path.getsize(path)
    labels = {
        "pyrogram": "✅ Pyrogram (готов для бота)",
        "telethon_sqlite": "🔄 Telethon SQLite (можно конвертировать)",
        "telethon_string": "🔄 Telethon StringSession (можно конвертировать)",
        "unknown_sqlite": "❓ SQLite session (неизвестный тип)",
    }
    label = labels.get(stype, "❓ Неизвестный тип")
    print(f"   {label}")
    print(f"   📁 {os.path.abspath(path)} ({size} байт)")


# ==================== Конвертация ====================


def convert_telethon_sqlite_to_pyrogram(telethon_path, output_path):
    """Конвертирует Telethon SQLite session в Pyrogram формат."""
    # Читаем данные из Telethon session
    conn_in = sqlite3.connect(telethon_path)
    c = conn_in.cursor()

    c.execute("SELECT dc_id, server_address, port, auth_key FROM sessions")
    row = c.fetchone()
    if not row:
        conn_in.close()
        print("   ❌ Telethon session пуст — нет данных сессии")
        return False

    dc_id, server_address, port, auth_key = row

    # Пытаемся получить user_id из entities
    user_id = 0
    try:
        c.execute("SELECT id FROM entities WHERE id > 0 LIMIT 1")
        entity_row = c.fetchone()
        if entity_row:
            user_id = entity_row[0]
    except Exception:
        pass

    conn_in.close()

    if not auth_key or len(auth_key) != 256:
        print(
            f"   ❌ Невалидный auth_key: {len(auth_key) if auth_key else 0} байт (нужно 256)"
        )
        return False

    # Создаём Pyrogram session
    return create_pyrogram_session(dc_id, auth_key, user_id, output_path)


def convert_telethon_string_to_pyrogram(string_path, output_path):
    """Конвертирует Telethon StringSession в Pyrogram формат."""
    with open(string_path, "r", encoding="utf-8") as f:
        session_string = f.read().strip()

    # Декодируем StringSession
    # Формат: 1 байт dc_id + 4 байта ip (или 16 для IPv6) + 2 байта port + 256 байт auth_key
    try:
        data = StringSession(session_string)
        dc_id = data.dc_id
        auth_key = data.auth_key.key if data.auth_key else None

        if not auth_key or len(auth_key) != 256:
            print(f"   ❌ Невалидный auth_key в StringSession")
            return False

        return create_pyrogram_session(dc_id, auth_key, 0, output_path)

    except Exception as e:
        print(f"   ❌ Ошибка разбора StringSession: {e}")
        return False


async def convert_telethon_string_with_connect(string_path, output_path):
    """Конвертирует Telethon StringSession → подключается → получает user_id → Pyrogram."""
    with open(string_path, "r", encoding="utf-8") as f:
        session_string = f.read().strip()

    print("   🔄 Подключаюсь к Telegram для проверки сессии...")
    client = TelegramClient(
        StringSession(session_string), API_ID, API_HASH, proxy=PROXY
    )

    try:
        await client.connect()

        if not await client.is_user_authorized():
            print("   ❌ Сессия невалидна или истекла")
            await client.disconnect()
            return False

        me = await client.get_me()
        print(f"   ✅ Авторизован: {me.first_name} (ID: {me.id})")

        convert_from_live_client(client, me.id, output_path)
        await client.disconnect()
        return True

    except Exception as e:
        print(f"   ❌ Ошибка подключения: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return False


def convert_from_live_client(telethon_client, user_id, output_path):
    """Конвертирует живой Telethon client в Pyrogram session."""
    session = telethon_client.session
    dc_id = session.dc_id
    auth_key = session.auth_key.key

    create_pyrogram_session(dc_id, auth_key, user_id, output_path)


def create_pyrogram_session(dc_id, auth_key, user_id, output_path):
    """Создаёт Pyrogram SQLite .session файл."""
    if os.path.exists(output_path):
        os.remove(output_path)

    conn = sqlite3.connect(output_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            dc_id     INTEGER PRIMARY KEY,
            api_id    INTEGER,
            test_mode INTEGER,
            auth_key  BLOB,
            date      INTEGER NOT NULL DEFAULT 0,
            user_id   INTEGER NOT NULL DEFAULT 0,
            is_bot    INTEGER NOT NULL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS peers (
            id             INTEGER PRIMARY KEY,
            access_hash    INTEGER,
            type           TEXT NOT NULL,
            username       TEXT,
            phone_number   TEXT,
            last_update_on INTEGER NOT NULL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS version (
            number INTEGER PRIMARY KEY
        )
    """)

    c.execute("INSERT OR REPLACE INTO version VALUES (?)", (3,))

    c.execute(
        "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
        (dc_id, API_ID, 0, auth_key, 0, user_id, 0),
    )

    conn.commit()
    conn.close()

    print(f"   ✅ Pyrogram session создан: {os.path.abspath(output_path)}")
    print(f"      DC: {dc_id}, User ID: {user_id}, Auth key: {len(auth_key)} bytes")
    return True


async def verify_pyrogram_session(session_path):
    """Верифицирует Pyrogram session — подключается и проверяет get_me()."""
    try:
        from pyrogram import Client as PyroClient

        session_name = session_path.replace(".session", "")
        test_client = PyroClient(
            session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            no_updates=True,
        )
        await test_client.start()
        me = await test_client.get_me()
        await test_client.stop()

        if me:
            print(f"   ✅ Верификация Pyrogram: {me.first_name} (ID: {me.id})")
            return True
        else:
            print("   ⚠️  Pyrogram открыл session, но get_me() вернул None")
            return True
    except ImportError:
        print("   ⚠️  Pyrogram не установлен локально — верификация пропущена")
        return True
    except Exception as e:
        print(f"   ⚠️  Верификация Pyrogram не прошла: {e}")
        print("      Session создан, но может быть несовместим.")
        print("      Попробуйте авторизацию через: python scripts/auth.py")
        return False


def copy_to_docker_session(source_path):
    """Копирует session файл в папку session/ для Docker."""
    session_dir = os.path.join(ROOT_DIR, "session")
    os.makedirs(session_dir, exist_ok=True)
    dst = os.path.join(session_dir, PYROGRAM_SESSION)
    shutil.copy2(source_path, dst)
    print(f"   ✅ Скопирован для Docker: {dst}")


# ==================== QR-авторизация ====================


def print_qr(url):
    """Генерирует и печатает QR-код в консоли."""
    os.system("cls" if os.name == "nt" else "clear")

    print("=" * 50)
    print("📱 ОТСКАНИРУЙТЕ QR-КОД ТЕЛЕФОНОМ")
    print("=" * 50)
    print("  1. Telegram → Настройки → Устройства")
    print("  2. «Подключить устройство»")
    print("  3. Наведите камеру на QR-код ниже")
    print("=" * 50)
    print()

    qr = qrcode.QRCode(border=2, box_size=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    print()
    print("⏳ Ожидаю сканирование...")
    print("   Нажмите Ctrl+C для отмены")
    print()


async def qr_auth():
    """Полная QR-авторизация через Telethon → конвертация в Pyrogram."""
    print("🔐 QR-авторизация через Telethon")
    print(f"🌐 Прокси: {PROXY[1]}:{PROXY[2]}")
    print()

    client = TelegramClient(StringSession(), API_ID, API_HASH, proxy=PROXY)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Уже авторизован: {me.first_name} (ID: {me.id})")
        convert_from_live_client(client, me.id, PYROGRAM_SESSION)
        copy_to_docker_session(PYROGRAM_SESSION)
        await verify_pyrogram_session(PYROGRAM_SESSION)
        await client.disconnect()
        return True

    try:
        qr_login = await client.qr_login()
        print_qr(qr_login.url)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                user = await qr_login.wait()
                if user:
                    break
            except SessionPasswordNeededError:
                print("\n✅ QR-код принят!")
                print("🔐 Двухфакторная аутентификация (2FA)")
                password = input("   Введите облачный пароль: ").strip()
                await client.sign_in(password=password)
                break
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    print(f"\n⏳ QR истёк. Обновляю... ({attempt + 1}/{MAX_RETRIES})")
                    await qr_login.recreate()
                    print_qr(qr_login.url)
                else:
                    print(f"\n❌ Не отсканирован после {MAX_RETRIES} попыток.")
                    await client.disconnect()
                    return False

        me = await client.get_me()
        if me is None:
            print("\n⚠️  Авторизация не завершена.")
            await client.disconnect()
            return False

        print()
        print("=" * 50)
        print("✅ АВТОРИЗАЦИЯ УСПЕШНА!")
        print("=" * 50)
        print(f"   👤 {me.first_name} {me.last_name or ''}")
        print(f"   🔢 ID: {me.id}")
        if me.username:
            print(f"   📛 @{me.username}")
        print()

        print("🔄 Конвертирую в Pyrogram session...")
        convert_from_live_client(client, me.id, PYROGRAM_SESSION)
        copy_to_docker_session(PYROGRAM_SESSION)
        await verify_pyrogram_session(PYROGRAM_SESSION)

        await client.disconnect()
        return True

    except KeyboardInterrupt:
        print("\n\n❌ Прервано (Ctrl+C)")
        await client.disconnect()
        return False
    except Exception as e:
        print(f"\n❌ Ошибка: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        await client.disconnect()
        return False


# ==================== Главное меню ====================


async def main():
    print("=" * 55)
    print("  🔐 Авторизация Telegram → Pyrogram session")
    print("=" * 55)
    print(f"  📂 Проект: {ROOT_DIR}")
    print()

    # Ищем существующие session файлы
    sessions = find_session_files()

    # Разделяем по типам
    pyrogram_sessions = {p: t for p, t in sessions.items() if t == "pyrogram"}
    telethon_sessions = {p: t for p, t in sessions.items() if t.startswith("telethon")}

    if not sessions:
        print("📭 Session файлы не найдены.")
        print()
        print("Запускаю QR-авторизацию...")
        print()
        success = await qr_auth()
        if success:
            print_final_instructions()
        return

    # Показываем найденные файлы
    print(f"📋 Найдено session файлов: {len(sessions)}")
    print()

    for i, (path, stype) in enumerate(sessions.items(), 1):
        print(f"  [{i}] {os.path.basename(path)}")
        print_session_info(path, stype)
        print()

    # Меню
    print("─" * 55)
    print("  Что вы хотите сделать?")
    print("─" * 55)

    options = []

    if telethon_sessions:
        options.append(("convert", "🔄 Конвертировать Telethon → Pyrogram"))

    if pyrogram_sessions:
        options.append(("use", "✅ Использовать существующий Pyrogram session"))

    options.append(("new", "🆕 Новая QR-авторизация (создать с нуля)"))
    options.append(("exit", "❌ Выход"))

    for i, (key, label) in enumerate(options, 1):
        print(f"  [{i}] {label}")

    print()
    choice = input("  Выберите (номер): ").strip()

    try:
        choice_idx = int(choice) - 1
        if choice_idx < 0 or choice_idx >= len(options):
            raise ValueError
        action = options[choice_idx][0]
    except ValueError:
        print("❌ Неверный выбор")
        return

    print()

    # === Конвертация ===
    if action == "convert":
        if len(telethon_sessions) == 1:
            path = list(telethon_sessions.keys())[0]
        else:
            print("  Какой файл конвертировать?")
            for i, (path, stype) in enumerate(telethon_sessions.items(), 1):
                print(f"    [{i}] {path}")
            sub = input("  Выберите (номер): ").strip()
            try:
                path = list(telethon_sessions.keys())[int(sub) - 1]
            except (ValueError, IndexError):
                print("❌ Неверный выбор")
                return

        stype = telethon_sessions[path]
        print(f"🔄 Конвертирую: {path}")
        print()

        if stype == "telethon_string":
            success = await convert_telethon_string_with_connect(path, PYROGRAM_SESSION)
        elif stype == "telethon_sqlite":
            success = convert_telethon_sqlite_to_pyrogram(path, PYROGRAM_SESSION)
        else:
            print("❌ Неподдерживаемый тип")
            return

        if success:
            copy_to_docker_session(PYROGRAM_SESSION)
            await verify_pyrogram_session(PYROGRAM_SESSION)
            print_final_instructions()

    # === Использовать существующий ===
    elif action == "use":
        if len(pyrogram_sessions) == 1:
            path = list(pyrogram_sessions.keys())[0]
        else:
            print("  Какой файл использовать?")
            for i, (path, stype) in enumerate(pyrogram_sessions.items(), 1):
                print(f"    [{i}] {path}")
            sub = input("  Выберите (номер): ").strip()
            try:
                path = list(pyrogram_sessions.keys())[int(sub) - 1]
            except (ValueError, IndexError):
                print("❌ Неверный выбор")
                return

        # Копируем в нужные места
        if os.path.abspath(path) != os.path.abspath(PYROGRAM_SESSION):
            shutil.copy2(path, PYROGRAM_SESSION)
            print(f"   ✅ Скопирован в корень: {PYROGRAM_SESSION}")

        copy_to_docker_session(PYROGRAM_SESSION)
        await verify_pyrogram_session(PYROGRAM_SESSION)
        print_final_instructions()

    # === Новая авторизация ===
    elif action == "new":
        success = await qr_auth()
        if success:
            print_final_instructions()

    # === Выход ===
    elif action == "exit":
        print("👋 До свидания!")


def print_final_instructions():
    """Печатает финальные инструкции."""
    print()
    print("=" * 55)
    print("  🚀 ГОТОВО! Session совместим с Pyrogram ботом.")
    print("=" * 55)
    print()
    print("  📋 Следующий шаг:")
    print("     docker-compose up -d --build")
    print()


if __name__ == "__main__":
    asyncio.run(main())
