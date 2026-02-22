# auth_only.py — только авторизация, никаких зависимостей кроме Pyrogram

from pyrogram import Client
import os

# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
# ВСТАВЬ СЮДА СВОИ ДАННЫЕ:
API_ID=
API_HASH=''
# →→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→

if not API_ID or not API_HASH:
    print("Ошибка: заполни API_ID и API_HASH в этом файле!")
    exit()

app = Client(
    name="voice_transcriber",
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=False,      # сохранит .session файл на диск
)

print("Запускаю авторизацию…")
app.start()

print("\nУСПЕШНО! Авторизация прошла!")
print("Создан файл: voice_transcriber.session")
print("Скопируй его в папку session/ для Docker:")
print("   mkdir -p session && cp voice_transcriber.session session/")

app.idle()  # держит сессию живой, пока не нажмёшь Ctrl+C
