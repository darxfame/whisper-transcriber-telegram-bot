"""
auth.py — Авторизация Pyrogram и создание session-файла.

Использование:
    pip install pyrogram tgcrypto
    python auth.py

Session-файл будет создан в корне проекта (../voice_transcriber.session).
"""

import os
import sys

# Переходим в корень проекта (на уровень выше scripts/)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT_DIR)

SESSION_NAME = "voice_transcriber"
SESSION_FILE = f"{SESSION_NAME}.session"

try:
    import tgcrypto  # noqa: F401

    print("✅ TgCrypto установлен")
except ImportError:
    print("⚠️  TgCrypto не установлен. Установите: pip install tgcrypto")
    print("   Бот будет работать, но медленнее.\n")

from pyrogram import Client  # noqa: E402

# ==================== КОНФИГУРАЦИЯ ====================
API_ID = 26607062
API_HASH = "8407ffeda812e8de2c1ed65f53f9b4c5"
# ======================================================

if not API_ID or not API_HASH:
    print("❌ Ошибка: заполни API_ID и API_HASH в этом файле!")
    sys.exit(1)


def main():
    """Основная функция авторизации."""
    print(f"📂 Рабочая директория: {os.getcwd()}")

    # Удаляем старый session-файл если он битый
    if os.path.exists(SESSION_FILE):
        print(f"⚠️  Найден существующий {SESSION_FILE}")
        answer = input("   Удалить и создать новый? (y/N): ").strip().lower()
        if answer == "y":
            os.remove(SESSION_FILE)
            print(f"   ✅ Удалён {SESSION_FILE}")
        else:
            print("   Используем существующий файл...")

    # Удаляем битый session из scripts/ если есть
    scripts_session = os.path.join(ROOT_DIR, "scripts", SESSION_FILE)
    if os.path.exists(scripts_session):
        print(f"⚠️  Найден лишний session в scripts/: {scripts_session}")
        os.remove(scripts_session)
        print("   ✅ Удалён (session должен быть в корне проекта)")

    print()
    print("🔐 Запускаю авторизацию Pyrogram...")
    print()
    print("📱 ВАЖНО: код авторизации придёт В ПРИЛОЖЕНИЕ Telegram!")
    print("   Откройте Telegram на телефоне/десктопе и найдите")
    print("   сообщение от «Telegram» с 5-значным кодом.")
    print()

    app = Client(
        name=SESSION_NAME,
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=False,
    )

    try:
        app.start()

        me = app.get_me()
        print()
        print("=" * 50)
        print("✅ АВТОРИЗАЦИЯ УСПЕШНА!")
        print("=" * 50)
        print(f"   Имя: {me.first_name} {me.last_name or ''}")
        print(f"   ID: {me.id}")
        print(f"   Username: @{me.username}" if me.username else "   Username: нет")
        print(f"   Файл: {os.path.abspath(SESSION_FILE)}")
        print()
        print("📋 Дальнейшие шаги:")
        print("   1. Скопируйте session в папку session/ для Docker:")
        print(f"      mkdir session")
        print(f"      copy {SESSION_FILE} session\\{SESSION_FILE}")
        print()
        print("   2. Запустите бота:")
        print("      docker-compose up -d --build")
        print()

        app.stop()
        print("✅ Сессия сохранена и закрыта.")

    except KeyboardInterrupt:
        print("\n\n❌ Прервано пользователем (Ctrl+C)")
        try:
            app.stop()
        except Exception:
            pass
    except Exception as e:
        print(f"\n❌ Ошибка авторизации: {e}")
        print()
        print("💡 Возможные решения:")
        print(f"   1. Удалите {SESSION_FILE} и попробуйте снова")
        print("   2. Убедитесь что API_ID и API_HASH верные")
        print("   3. Убедитесь что номер телефона верный")
        print("   4. Подождите 1-2 минуты (Telegram ограничивает частоту)")
        sys.exit(1)


if __name__ == "__main__":
    main()
