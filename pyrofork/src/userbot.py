import asyncio
import gc
import json
import logging
import multiprocessing
import os
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor

import redis
from deepmultilingualpunctuation import PunctuationModel
from faster_whisper import WhisperModel
from pyrogram import Client, filters, idle
from pyrogram.errors import PeerIdInvalid, UserIdInvalid, UsernameInvalid
from pyrogram.types import Message

# ==================== Логирование ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Глушим MTProto-спам, оставляем только важное
logging.getLogger("pyrogram").setLevel(logging.WARNING)
# НО оставляем session на INFO — покажет NetworkTask/PingTask/HandlerTasks
logging.getLogger("pyrogram.session.session").setLevel(logging.INFO)
logging.getLogger("pyrogram.connection.connection").setLevel(logging.INFO)

# ==================== Версия и дата сборки ====================
VERSION = "2.2.1"
BUILD_DATE = os.getenv("BUILD_DATE", "unknown")

# ==================== Конфиг ====================
API_ID = int(os.getenv("API_ID") or "0")
API_HASH = os.getenv("API_HASH") or ""
FRIEND_ID = int(os.getenv("FRIEND_USER_ID") or "0")
MODEL_SIZE = os.getenv("WHISPER_MODEL") or "small"

if API_ID == 0 or not API_HASH:
    raise ValueError(
        "❌ API_ID и API_HASH обязательны! Проверьте .env / docker-compose.yml"
    )

CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096

# ==================== Redis ====================
r = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

if not r.exists("enabled"):
    r.set("enabled", "1")
if not r.exists("my"):
    r.set("my", "1")
if not r.exists("friend"):
    r.set("friend", "1")
if not r.exists("model"):
    r.set("model", MODEL_SIZE)

if not r.exists("tracked_users"):
    initial_users = [FRIEND_ID] if FRIEND_ID != 0 else []
    r.set("tracked_users", json.dumps(initial_users))

logger.info(
    f"Redis: enabled={r.get('enabled')}, my={r.get('my')}, "
    f"friend={r.get('friend')}, model={r.get('model')}"
)

# ==================== Session ====================
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"
SESSION_NAME = "voice_transcriber"
SESSION_WORKDIR = "session" if RUNNING_IN_DOCKER else "."
SESSION_FILE = os.path.join(os.path.abspath(SESSION_WORKDIR), SESSION_NAME + ".session")

logger.info(f"Session: {SESSION_FILE}")
if not os.path.exists(SESSION_FILE):
    logger.critical(
        f"❌ Session файл не найден: {SESSION_FILE}\n"
        "   Создайте: docker-compose run --rm userbot python scripts/auth_docker.py"
    )
    sys.exit(1)

try:
    _c = sqlite3.connect(SESSION_FILE)
    _c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    _c.close()
    logger.info(f"Session валиден ({os.path.getsize(SESSION_FILE)} байт)")
except Exception as _e:
    logger.critical(f"❌ Session повреждён: {_e}")
    sys.exit(1)

# ==================== Клиент ====================
# Синхронный паттерн как в старом рабочем боте + workdir для Docker
app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    workdir=SESSION_WORKDIR,
)

# ==================== Модели ====================
model = None
punct_model = None
CPU_CORES = multiprocessing.cpu_count()
executor = ThreadPoolExecutor(max_workers=CPU_CORES)
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

# Хранилище фоновых задач — предотвращает GC asyncio tasks (Python docs)
_background_tasks: set = set()


def get_tracked_users():
    try:
        users_json = r.get("tracked_users")
        return json.loads(users_json) if users_json else []
    except Exception:
        return []


def add_tracked_user(user_id: int):
    users = get_tracked_users()
    if user_id not in users:
        users.append(user_id)
        r.set("tracked_users", json.dumps(users))
        return True
    return False


def remove_tracked_user(user_id: int):
    users = get_tracked_users()
    if user_id in users:
        users.remove(user_id)
        r.set("tracked_users", json.dumps(users))
        return True
    return False


def load_model(model_size: str):
    global model
    if model is not None:
        del model
        gc.collect()
    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        cpu_threads=CPU_CORES,
        num_workers=1,
    )
    r.set("model", model_size)
    logger.info(f"Модель {model_size} загружена ({CPU_CORES} потоков)")


def load_punctuation_model():
    global punct_model
    logger.info("Загружаю модель пунктуации...")
    punct_model = PunctuationModel(model="kredor/punctuate-all")
    logger.info("Модель пунктуации загружена")


load_model(r.get("model") or MODEL_SIZE)
load_punctuation_model()


# ==================== Форматирование ====================
def format_text(text: str) -> str:
    if not text or text == "…" or punct_model is None:
        return text
    try:
        formatted = punct_model.restore_punctuation(text)
        sentences = re.split(r"(?<=[.!?])\s+", formatted)
        paragraphs, current = [], []
        for sentence in sentences:
            current.append(sentence)
            if len(current) >= 4:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))
        return "\n\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Ошибка форматирования: {e}")
        return text


# ==================== Транскрипция ====================
def transcribe_file_sync(file_path: str) -> str:
    if model is None:
        return "Ошибка: модель не загружена"
    try:
        segments, _ = model.transcribe(
            file_path,
            language="ru",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=400),
            word_timestamps=True,
        )
        text = " ".join(seg.text for seg in segments).strip()
        return format_text(text) if text and text != "…" else (text or "…")
    except Exception as e:
        logger.error(f"Ошибка транскрипции: {e}", exc_info=True)
        return f"Ошибка: {e}"


async def transcribe(file_path: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, transcribe_file_sync, file_path)


def split_text(text: str, max_length: int = MESSAGE_LIMIT) -> list:
    if len(text) <= max_length:
        return [text]
    chunks, current_chunk = [], ""
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 <= max_length:
            current_chunk = (current_chunk + "\n\n" + para) if current_chunk else para
        elif len(para) > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            for sentence in re.split(r"(?<=[.!?])\s+", para):
                if len(current_chunk) + len(sentence) + 1 <= max_length:
                    current_chunk += (" " if current_chunk else "") + sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


# ==================== Обработка своих голосовых ====================
async def process_my_voice(message: Message):
    file_path = None
    logger.info(f"[MY_VOICE] обработка msg={message.id}")
    try:
        try:
            await message.edit_caption("⏳ Транскрипция в процессе...")
        except Exception:
            pass

        os.makedirs("temp", exist_ok=True)
        file_path = await message.download(os.path.join("temp", f"{message.id}.ogg"))
        text = await transcribe(file_path)
        logger.info(f"[MY_VOICE] готово: {len(text)} символов")

        if len(text) <= CAPTION_LIMIT:
            try:
                await message.edit_caption(text)
            except Exception as e:
                await message.reply(text, quote=False)
        else:
            first = text.split("\n\n")[0]
            if len(first) > CAPTION_LIMIT - 3:
                first = text[: CAPTION_LIMIT - 3]
            try:
                await message.edit_caption(first + "…")
            except Exception:
                pass
            chunks = split_text(text)  # вычисляем ОДИН раз
            for i, chunk in enumerate(chunks, 1):
                header = (
                    f"📝 **Часть {i}/{len(chunks)}**\n\n" if len(chunks) > 1 else ""
                )
                await message.reply(header + chunk, quote=False)
                await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"[MY_VOICE] ошибка msg={message.id}: {e}", exc_info=True)
        err = f"❌ Ошибка: {str(e)[:900]}"
        try:
            await message.edit_caption(err)
        except Exception:
            try:
                await message.reply(err, quote=False)
            except Exception:
                pass
    finally:
        if file_path:
            try:
                os.remove(file_path)
            except OSError:
                pass


# ==================== Обработка чужих голосовых ====================
async def process_tracked_voice(message: Message):
    file_path = None
    status_msg = None
    try:
        user_name = (
            message.from_user.first_name if message.from_user else "Пользователь"
        )
        chat_type = str(message.chat.type)
        prefix = (
            f"**[{user_name}]** (группа):\n\n"
            if "group" in chat_type
            else f"**[{user_name}]:**\n\n"
        )

        try:
            status_msg = await message.reply(
                "⏳ Транскрипция в процессе...", quote=True
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить статус: {e}")
            return

        os.makedirs("temp", exist_ok=True)
        file_path = await message.download(os.path.join("temp", f"{message.id}.ogg"))
        text = await transcribe(file_path)
        full_text = f"{prefix}{text}"

        if len(full_text) <= MESSAGE_LIMIT:
            await status_msg.edit_text(full_text)
        else:
            await status_msg.edit_text(full_text[: MESSAGE_LIMIT - 100] + "…")
            chunks = split_text(full_text, MESSAGE_LIMIT)
            for i, chunk in enumerate(chunks[1:], 2):
                await message.reply(
                    f"📝 **Часть {i}/{len(chunks)}**\n\n{chunk}", quote=False
                )
                await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"[TRACKED_VOICE] ошибка: {e}", exc_info=True)
        err = f"❌ Ошибка: {str(e)[:900]}"
        if status_msg:
            try:
                await status_msg.edit_text(err)
            except Exception:
                pass
        else:
            try:
                await message.reply(err, quote=True)
            except Exception:
                pass
    finally:
        if file_path:
            try:
                os.remove(file_path)
            except OSError:
                pass


# ==================== Хендлеры ====================


# ДИАГНОСТИКА: ловит ВСЕ сообщения (низкий приоритет) — убедиться что апдейты доходят вообще
@app.on_message(group=100)
async def debug_all_messages(client, message: Message):
    """Логирует ВСЕ входящие сообщения для отладки."""
    msg_type = (
        "text"
        if message.text
        else ("voice" if message.voice else f"{message.media.__class__.__name__}")
    )
    sender = (
        f"@{message.from_user.username}"
        if (message.from_user and message.from_user.username)
        else f"ID:{message.from_user.id if message.from_user else 'unknown'}"
    )
    logger.info(
        f"[DEBUG_ALL] {sender} → {msg_type} | chat={message.chat.id} | from_me={message.outgoing}"
    )
    message.continue_propagation()


# Голосовые — СВОИ (filters.me как в оригинальном рабочем скрипте)
@app.on_message(filters.voice & filters.me)
async def my_voice(client, message: Message):
    logger.info(f"[VOICE_ME] msg={message.id} chat={message.chat.id}")
    if r.get("enabled") != "1" or r.get("my") != "1":
        return
    task = asyncio.create_task(process_my_voice(message))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# Голосовые — ЧУЖИЕ
@app.on_message(filters.voice & ~filters.me)
async def tracked_voice(client, message: Message):
    if r.get("enabled") != "1" or r.get("friend") != "1":
        return
    tracked = get_tracked_users()
    if message.from_user and message.from_user.id in tracked:
        logger.info(f"[VOICE_FRIEND] msg={message.id} user={message.from_user.id}")
        task = asyncio.create_task(process_tracked_voice(message))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)


# ==================== Команды (только в Saved Messages = filters.private & filters.me) ====================
commands = {
    "voicebot_on": (
        "✅ Всё включено",
        lambda: (r.set("enabled", "1"), r.set("my", "1"), r.set("friend", "1")),
    ),
    "voicebot_off": ("❌ Всё выключено", lambda: r.set("enabled", "0")),
    "my_on": ("✅ Твои голосовые → ВКЛ", lambda: r.set("my", "1")),
    "my_off": ("❌ Твои голосовые → ВЫКЛ", lambda: r.set("my", "0")),
    "friend_on": ("✅ Голосовые друзей → ВКЛ", lambda: r.set("friend", "1")),
    "friend_off": ("❌ Голосовые друзей → ВЫКЛ", lambda: r.set("friend", "0")),
}


@app.on_message(
    filters.command(["addtovoicebot", "delfromvoicebot", "listvoicebot"]) & filters.me
)
async def manage_tracked_users(client, message: Message):
    cmd = message.command[0].lower()

    if cmd == "addtovoicebot":
        user_id = None
        if message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id
            user_name = message.reply_to_message.from_user.first_name or "Пользователь"
        elif len(message.command) > 1:
            try:
                user_id = int(message.command[1])
                user_name = f"ID {user_id}"
            except ValueError:
                await message.reply("❌ Неверный формат ID")
                return
        else:
            await message.reply(
                "ℹ️ **Использование:**\n"
                "• Ответь на сообщение: `/addtovoicebot`\n"
                "• Или укажи ID: `/addtovoicebot 123456789`"
            )
            return
        if add_tracked_user(user_id):
            await message.reply(f"✅ **{user_name}** добавлен\nID: `{user_id}`")
        else:
            await message.reply(f"ℹ️ **{user_name}** уже в списке\nID: `{user_id}`")

    elif cmd == "delfromvoicebot":
        user_id = None
        if message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id
            user_name = message.reply_to_message.from_user.first_name or "Пользователь"
        elif len(message.command) > 1:
            try:
                user_id = int(message.command[1])
                user_name = f"ID {user_id}"
            except ValueError:
                await message.reply("❌ Неверный формат ID")
                return
        else:
            await message.reply(
                "ℹ️ **Использование:**\n"
                "• Ответь на сообщение: `/delfromvoicebot`\n"
                "• Или укажи ID: `/delfromvoicebot 123456789`"
            )
            return
        if remove_tracked_user(user_id):
            await message.reply(f"✅ **{user_name}** удалён\nID: `{user_id}`")
        else:
            await message.reply(f"ℹ️ **{user_name}** не найден\nID: `{user_id}`")

    elif cmd == "listvoicebot":
        tracked = get_tracked_users()
        if not tracked:
            await message.reply("📋 Список пуст. Используй `/addtovoicebot`")
            return
        user_list = []
        for uid in tracked:
            try:
                user = await client.get_users(uid)
                name = user.first_name or "Пользователь"
                if user.last_name:
                    name += f" {user.last_name}"
                if user.username:
                    name += f" (@{user.username})"
                user_list.append(f"• **{name}**\n  ID: `{uid}`")
            except (PeerIdInvalid, UsernameInvalid, UserIdInvalid, KeyError):
                user_list.append(f"• ID: `{uid}` (недоступен)")
            except Exception as e:
                user_list.append(f"• ID: `{uid}` (ошибка: {type(e).__name__})")
        response = f"📋 **Отслеживаемые** ({len(tracked)}):\n\n" + "\n\n".join(
            user_list
        )
        await message.reply(response)


@app.on_message(
    filters.command(list(commands.keys()) + ["start", "status", "help", "model"])
    & filters.private
    & filters.me
)
async def control_commands(client, message: Message):
    cmd = message.command[0].lower()
    args = message.command[1:] if len(message.command) > 1 else []
    logger.info(f"[CMD] /{cmd} chat={message.chat.id}")

    if cmd == "start":
        await message.reply(
            "👋 **Голосовой транскрибер**\n\n"
            "Распознаёт голосовые сообщения автоматически.\n\n"
            "✨ **Возможности:**\n"
            "• Авто-пунктуация и абзацы\n"
            "• Многопоточная обработка\n"
            "• Управление списком пользователей\n"
            "• Голосовые — в любых чатах\n\n"
            "Команды работают только в **Избранном**.\n"
            "Используй `/help` для списка команд."
        )
        return

    if cmd == "help":
        models_list = ", ".join(AVAILABLE_MODELS)
        await message.reply(
            "📋 **Команды** (пиши в Избранном):\n\n"
            "**Управление:**\n"
            "`/voicebot_on` — Включить всё\n"
            "`/voicebot_off` — Выключить всё\n"
            "`/my_on` / `/my_off` — Свои голосовые\n"
            "`/friend_on` / `/friend_off` — Чужие голосовые\n\n"
            "**Пользователи:**\n"
            "`/addtovoicebot` — Добавить (в ответ на сообщение)\n"
            "`/delfromvoicebot` — Удалить\n"
            "`/listvoicebot` — Список\n\n"
            "**Модель Whisper:**\n"
            f"`/model` — Текущая\n"
            f"`/model <имя>` — Сменить ({models_list})\n\n"
            "**Инфо:**\n"
            "`/status` — Статус бота\n"
            "💡 Голосовые работают в **любых** чатах"
        )
        return

    if cmd == "status":
        await message.reply(
            f"📊 **Статус:**\n\n"
            f"Глобально: {'✅' if r.get('enabled') == '1' else '❌'}\n"
            f"Свои: {'✅' if r.get('my') == '1' else '❌'}\n"
            f"Чужие: {'✅' if r.get('friend') == '1' else '❌'}\n"
            f"Модель: `{r.get('model') or MODEL_SIZE}`\n"
            f"CPU: {CPU_CORES} потоков\n"
            f"Отслеживается: {len(get_tracked_users())} польз."
        )
        return

    if cmd == "model":
        if not args:
            current = r.get("model") or MODEL_SIZE
            models_list = "\n".join(
                f"{'✅' if m == current else '⚪️'} {m}" for m in AVAILABLE_MODELS
            )
            await message.reply(
                f"🤖 **Текущая:** {current}\n\n**Доступные:**\n{models_list}\n\nСмена: `/model <имя>`"
            )
        else:
            new_model = args[0].lower()
            if new_model not in AVAILABLE_MODELS:
                await message.reply(f"❌ Модель `{new_model}` не найдена")
            elif new_model == (r.get("model") or MODEL_SIZE):
                await message.reply(f"ℹ️ Модель `{new_model}` уже загружена")
            else:
                status_msg = await message.reply(f"⏳ Загружаю `{new_model}`...")
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, load_model, new_model)
                    await status_msg.edit_text(
                        f"✅ Модель сменена → **{new_model}**\n\n"
                        f"**Скорость на E5620:**\n"
                        f"tiny ~0.5x⚡ base ~0.7x small ~1.5x⭐ medium ~3x large ~5x🐌"
                    )
                except Exception as e:
                    await status_msg.edit_text(f"❌ Ошибка загрузки: {e}")
        return

    if cmd in commands:
        reply_text, action = commands[cmd]
        action()
        await message.reply(reply_text)


# ==================== Запуск ====================
def main():
    """
    Синхронный паттерн — точная копия старого рабочего бота:
    app.start() запускает диспетчер и событийный loop Pyrofork
    idle() блокирует до Ctrl+C
    Это работает на 100% в Pyrofork 2.3.x
    """
    logger.info("=" * 60)
    logger.info(f"🚀 Голосовой транскрибер | v{VERSION}")
    logger.info(f"📅 Дата сборки: {BUILD_DATE}")
    logger.info("=" * 60)
    logger.info(f"CPU: {CPU_CORES}, отслеживаемых: {len(get_tracked_users())}")

    try:
        app.start()
        logger.info("✅ Клиент запущен")

        me = app.get_me()
        logger.info(f"✅ Авторизован: {me.first_name} (ID: {me.id})")
        logger.info(f"Модель: {r.get('model') or MODEL_SIZE}")
        logger.info(f"Список отслеживаемых: {get_tracked_users()}")

        try:
            app.send_message(
                me.id, "🔧 Голосовой транскрибер запущен. Пиши /help в Избранном."
            )
            logger.info("Тест-сообщение отправлено")
        except Exception as e:
            logger.warning(f"Тест-сообщение: {e}")

        logger.info("✅ Бот готов! Жду голосовые и команды...")
        idle()
    except KeyboardInterrupt:
        logger.info("Остановлен по Ctrl+C")
    finally:
        try:
            app.stop()
        except (ConnectionError, Exception):
            pass
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    main()
