"""
auth_docker.py — Авторизация Pyrogram ВНУТРИ Docker контейнера.

Запуск:
    docker-compose run --rm userbot python scripts/auth_docker.py
"""

import asyncio
import os
import sys

SESSION_DIR = "session"
SESSION_NAME = "voice_transcriber"
SESSION_FILE = os.path.join(SESSION_DIR, SESSION_NAME + ".session")

API_ID = int(os.getenv("API_ID") or "0")
API_HASH = os.getenv("API_HASH") or ""

if API_ID == 0 or not API_HASH:
    print("❌ API_ID и API_HASH не заданы!")
    print("   Они берутся из .env / docker-compose.yml environment")
    sys.exit(1)

os.makedirs(SESSION_DIR, exist_ok=True)

# Удаляем битый session если есть
if os.path.exists(SESSION_FILE):
    try:
        import sqlite3

        conn = sqlite3.connect(SESSION_FILE)
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        conn.close()
        print(f"ℹ️  Существующий session валиден ({os.path.getsize(SESSION_FILE)} байт)")
        answer = input("   Удалить и создать новый? (y/N): ").strip().lower()
        if answer == "y":
            os.remove(SESSION_FILE)
            print("   ✅ Удалён")
        else:
            print("   Используем существующий")
    except Exception:
        print(f"⚠️  Существующий session повреждён — удаляю")
        os.remove(SESSION_FILE)

print()
print("=" * 50)
print("  🔐 Авторизация Pyrogram (pyrofork)")
print("=" * 50)
print(f"  API_ID:  {API_ID}")
print(f"  Session: {os.path.abspath(SESSION_FILE)}")
print()
print("  📱 Код придёт В ПРИЛОЖЕНИЕ Telegram!")
print("     Откройте Telegram → чат «Telegram»")
print("=" * 50)
print()

from pyrogram import Client


async def main():
    app = Client(
        SESSION_NAME,
        api_id=API_ID,
        api_hash=API_HASH,
        workdir=SESSION_DIR,
    )

    try:
        await app.start()

        me = await app.get_me()
        print()
        print("=" * 50)
        print("  ✅ АВТОРИЗАЦИЯ УСПЕШНА!")
        print("=" * 50)
        print(f"  👤 {me.first_name} {me.last_name or ''}")
        print(f"  🔢 ID: {me.id}")
        if me.username:
            print(f"  📛 @{me.username}")
        print(f"  📁 {os.path.abspath(SESSION_FILE)}")
        print()
        print("  📋 Теперь запускайте бота:")
        print("     docker-compose up -d")
        print()

        await app.stop()

    except KeyboardInterrupt:
        print("\n❌ Прервано")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
