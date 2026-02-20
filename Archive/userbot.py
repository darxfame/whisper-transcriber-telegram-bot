import os
import asyncio
import gc
import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import redis
from pyrofork import Client, filters, idle
from pyrofork.errors import (
    FloodWait,
    RPCError,
    Timeout,
    PeerIdInvalid,
    UsernameInvalid,
    UserIdInvalid
)
from pyrofork.handlers import MessageHandler
from pyrofork.types import Message
from deepmultilingualpunctuation import PunctuationModel
from faster_whisper import WhisperModel
import multiprocessing

# ────────────────────────────────────────────────
# Логирование
# ────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("VoiceTranscriber")

# ────────────────────────────────────────────────
# Конфигурация
# ────────────────────────────────────────────────

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")                     # если используется userbot — можно убрать или закомментировать
FRIEND_ID = int(os.getenv("FRIEND_USER_ID", 0))
MODEL_SIZE = os.getenv("WHISPER_MODEL", "small").lower()

CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096

AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

# ────────────────────────────────────────────────
# Redis
# ────────────────────────────────────────────────

r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def init_redis():
    defaults = {
        'enabled': '1',
        'my': '1',
        'friend': '1',
        'model': MODEL_SIZE,
    }
    for k, v in defaults.items():
        if not r.exists(k):
            r.set(k, v)

    if not r.exists('tracked_users'):
        initial = [FRIEND_ID] if FRIEND_ID != 0 else []
        r.set('tracked_users', json.dumps(initial))

init_redis()

# ────────────────────────────────────────────────
# Глобальные объекты
# ────────────────────────────────────────────────

app = Client(
    "voice_transcriber",
    api_id=API_ID,
    api_hash=API_HASH,
    # bot_token=BOT_TOKEN,   # раскомментировать, если нужен Bot API вместо Userbot
)

model: Optional[WhisperModel] = None
punct_model: Optional[PunctuationModel] = None

CPU_CORES = multiprocessing.cpu_count()
executor = ThreadPoolExecutor(max_workers=CPU_CORES * 2)


def load_model(model_size: str):
    global model
    if model is not None:
        del model
        gc.collect()

    logger.info(f"Загружаю модель Whisper: {model_size}")
    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        cpu_threads=CPU_CORES,
        num_workers=1
    )
    r.set('model', model_size)
    logger.info(f"Модель {model_size} загружена ({CPU_CORES} потоков)")


def load_punctuation_model():
    global punct_model
    logger.info("Загружаю модель пунктуации...")
    punct_model = PunctuationModel(model="kredor/punctuate-all")
    logger.info("Модель пунктуации загружена")


# ────────────────────────────────────────────────
# Утилиты
# ────────────────────────────────────────────────

def get_tracked_users() -> list[int]:
    try:
        data = r.get('tracked_users')
        return json.loads(data) if data else []
    except Exception:
        return []


def add_tracked_user(user_id: int) -> bool:
    users = get_tracked_users()
    if user_id not in users:
        users.append(user_id)
        r.set('tracked_users', json.dumps(users))
        return True
    return False


def remove_tracked_user(user_id: int) -> bool:
    users = get_tracked_users()
    if user_id in users:
        users.remove(user_id)
        r.set('tracked_users', json.dumps(users))
        return True
    return False


def format_text(text: str) -> str:
    if not text or text.strip() in ("…", ""):
        return text

    try:
        formatted = punct_model.restore_punctuation(text.strip())
        sentences = re.split(r'(?<=[.!?])\s+', formatted)

        paragraphs = []
        chunk = []

        for s in sentences:
            chunk.append(s)
            if len(chunk) >= 4:
                paragraphs.append(" ".join(chunk))
                chunk = []

        if chunk:
            paragraphs.append(" ".join(chunk))

        return "\n\n".join(paragraphs).strip()
    except Exception as e:
        logger.warning(f"Ошибка пунктуации: {e}")
        return text


async def transcribe_file(file_path: str) -> str:
    try:
        segments, info = await asyncio.to_thread(
            model.transcribe,
            file_path,
            language="ru",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=400),
            word_timestamps=True
        )

        text = " ".join(s.text for s in segments).strip()

        if text and text != "…":
            return format_text(text)
        return text or "…"
    except Exception as e:
        logger.error(f"Ошибка транскрипции {file_path}: {e}", exc_info=True)
        return f"Ошибка транскрипции: {str(e)[:200]}"


def split_text(text: str, max_len: int = MESSAGE_LIMIT) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_len:
            current += ("\n\n" if current else "") + para
        elif len(para) > max_len:
            if current:
                chunks.append(current)
                current = ""
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                if len(current) + len(sent) + 1 <= max_len:
                    current += (" " if current else "") + sent
                else:
                    if current:
                        chunks.append(current)
                    current = sent
        else:
            if current:
                chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    return chunks


# ────────────────────────────────────────────────
# Обработка голосовых сообщений
# ────────────────────────────────────────────────

async def process_voice(message: Message, is_self: bool = False):
    file_path = None
    status_msg = None

    try:
        prefix = ""
        if not is_self:
            if message.chat.type in {"group", "supergroup"}:
                prefix = f"**[{message.from_user.first_name or 'Пользователь'}]** (группа):\n\n"
            else:
                prefix = f"**[{message.from_user.first_name or 'Пользователь'}]:**\n\n"

        try:
            if is_self:
                await message.edit_caption("⏳ Обработка…")
            else:
                status_msg = await message.reply("⏳ Транскрипция…", quote=True)
        except Exception:
            pass

        for attempt in range(1, 4):
            try:
                file_path = await message.download(f"voice_{message.id}_{int(time.time())}.ogg")
                break
            except Timeout:
                if attempt == 3:
                    raise
                await asyncio.sleep(2 ** attempt)

        text = await transcribe_file(file_path)

        full_text = prefix + text if prefix else text

        if is_self:
            if len(full_text) <= CAPTION_LIMIT:
                await message.edit_caption(full_text or "…")
            else:
                first = full_text[:CAPTION_LIMIT - 3] + "…"
                await message.edit_caption(first)
                chunks = split_text(full_text)
                for i, chunk in enumerate(chunks, 1):
                    header = f"📝 **Часть {i}/{len(chunks)}**\n\n" if len(chunks) > 1 else ""
                    await message.reply(header + chunk, quote=False)
                    await asyncio.sleep(0.5)
        else:
            if len(full_text) <= MESSAGE_LIMIT:
                await status_msg.edit_text(full_text or "…")
            else:
                first = full_text[:MESSAGE_LIMIT - 100] + "…"
                await status_msg.edit_text(first)
                chunks = split_text(full_text)
                for i, chunk in enumerate(chunks[1:], 2):
                    header = f"📝 **Часть {i}/{len(chunks)}**\n\n"
                    await message.reply(header + chunk, quote=False)
                    await asyncio.sleep(0.5)

    except FloodWait as e:
        logger.warning(f"FloodWait {e.value} сек")
        await asyncio.sleep(e.value + 2)

    except Exception as e:
        logger.error(f"Ошибка обработки голосового {message.id}: {e}", exc_info=True)
        err_text = f"❌ Ошибка: {str(e)[:400]}"
        try:
            if is_self:
                await message.edit_caption(err_text)
            elif status_msg:
                await status_msg.edit_text(err_text)
            else:
                await message.reply(err_text, quote=True)
        except Exception:
            pass

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass


# ────────────────────────────────────────────────
# Обработчики голосовых
# ────────────────────────────────────────────────

@app.on_message(filters.voice & filters.me)
async def on_my_voice(_, msg: Message):
    if r.get('enabled') != '1' or r.get('my') != '1':
        return
    asyncio.create_task(process_voice(msg, is_self=True))


@app.on_message(filters.voice & ~filters.me)
async def on_foreign_voice(_, msg: Message):
    if r.get('enabled') != '1' or r.get('friend') != '1':
        return

    tracked = get_tracked_users()
    if msg.from_user and msg.from_user.id in tracked:
        asyncio.create_task(process_voice(msg, is_self=False))


# ────────────────────────────────────────────────
# Команды управления состоянием
# ────────────────────────────────────────────────

async def cmd_voicebot_on(_, msg: Message):
    r.set('enabled', '1')
    r.set('my', '1')
    r.set('friend', '1')
    await msg.reply("✅ Всё включено")


async def cmd_voicebot_off(_, msg: Message):
    r.set('enabled', '0')
    await msg.reply("❌ Всё выключено")


async def cmd_my_on(_, msg: Message):
    r.set('my', '1')
    await msg.reply("✅ Свои голосовые → ВКЛ")


async def cmd_my_off(_, msg: Message):
    r.set('my', '0')
    await msg.reply("❌ Свои голосовые → ВЫКЛ")


async def cmd_friend_on(_, msg: Message):
    r.set('friend', '1')
    await msg.reply("✅ Голосовые друзей → ВКЛ")


async def cmd_friend_off(_, msg: Message):
    r.set('friend', '0')
    await msg.reply("❌ Голосовые друзей → ВЫКЛ")


# ────────────────────────────────────────────────
# Управление списком пользователей
# ────────────────────────────────────────────────

async def manage_tracked_users(client: Client, msg: Message):
    cmd = msg.command[0].lower()
    
    if cmd == "addtovoicebot":
        user_id = None
        user_name = None
        
        if msg.reply_to_message and msg.reply_to_message.from_user:
            user_id = msg.reply_to_message.from_user.id
            user_name = msg.reply_to_message.from_user.first_name
        elif len(msg.command) > 1:
            try:
                user_id = int(msg.command[1])
                user_name = f"ID {user_id}"
            except ValueError:
                await msg.reply("❌ Неверный формат ID")
                return
        else:
            await msg.reply(
                "ℹ️ **Использование:**\n"
                "• Ответь на сообщение: `/addtovoicebot`\n"
                "• Или укажи ID: `/addtovoicebot 123456789`"
            )
            return
        
        if add_tracked_user(user_id):
            await msg.reply(f"✅ **{user_name}** добавлен\nID: `{user_id}`")
        else:
            await msg.reply(f"ℹ️ **{user_name}** уже в списке\nID: `{user_id}`")
    
    elif cmd == "delfromvoicebot":
        user_id = None
        user_name = None
        
        if msg.reply_to_message and msg.reply_to_message.from_user:
            user_id = msg.reply_to_message.from_user.id
            user_name = msg.reply_to_message.from_user.first_name
        elif len(msg.command) > 1:
            try:
                user_id = int(msg.command[1])
                user_name = f"ID {user_id}"
            except ValueError:
                await msg.reply("❌ Неверный формат ID")
                return
        else:
            await msg.reply(
                "ℹ️ **Использование:**\n"
                "• Ответь на сообщение: `/delfromvoicebot`\n"
                "• Или укажи ID: `/delfromvoicebot 123456789`"
            )
            return
        
        if remove_tracked_user(user_id):
            await msg.reply(f"✅ **{user_name}** удалён\nID: `{user_id}`")
        else:
            await msg.reply(f"ℹ️ **{user_name}** не найден\nID: `{user_id}`")
    
    elif cmd == "listvoicebot":
        tracked_users = get_tracked_users()
        
        if not tracked_users:
            await msg.reply("📋 Список отслеживаемых пуст\n\nИспользуй `/addtovoicebot` для добавления")
            return
        
        user_list = []
        for user_id in tracked_users:
            try:
                user = await client.get_users(user_id)
                name = f"{user.first_name}"
                if user.last_name:
                    name += f" {user.last_name}"
                if user.username:
                    name += f" (@{user.username})"
                user_list.append(f"• **{name}**\n  ID: `{user_id}`")
            except (PeerIdInvalid, UsernameInvalid, UserIdInvalid):
                user_list.append(f"• ID: `{user_id}` (данные недоступны)")
            except Exception as e:
                user_list.append(f"• ID: `{user_id}` (ошибка: {type(e).__name__})")
                logger.warning(f"Ошибка получения пользователя {user_id}: {e}")
        
        response = f"📋 **Отслеживаемые** ({len(tracked_users)}):\n\n"
        response += "\n\n".join(user_list)
        response += "\n\n💡 Данные обновятся после получения сообщений от пользователей"
        
        await msg.reply(response)


# ────────────────────────────────────────────────
# Команды контроля и информации
# ────────────────────────────────────────────────

async def control_commands(client: Client, msg: Message):
    cmd = msg.command[0].lower()
    args = msg.command[1:] if len(msg.command) > 1 else []
    
    if cmd == "start":
        await msg.reply(
            "👋 **Голосовой транскрибер**\n\n"
            "Автоматическое распознавание голосовых сообщений с форматированием текста.\n\n"
            "✨ **Возможности:**\n"
            "• Автоматическая пунктуация\n"
            "• Разбиение на абзацы\n"
            "• Многопоточная обработка\n"
            "• Управление списком пользователей\n"
            "• Работает везде\n\n"
            "Используй `/help` для списка команд"
        )
        return
    
    if cmd == "help":
        models_list = ", ".join(AVAILABLE_MODELS)
        help_text = (
            "📋 **Команды:**\n\n"
            "**Управление:**\n"
            "`/voicebot_on` — Включить всё\n"
            "`/voicebot_off` — Выключить всё\n"
            "`/my_on` / `/my_off` — Свои голосовые\n"
            "`/friend_on` / `/friend_off` — Чужие\n\n"
            "**Пользователи:**\n"
            "`/addtovoicebot` — Добавить\n"
            "`/delfromvoicebot` — Удалить\n"
            "`/listvoicebot` — Список\n\n"
            "**Модель:**\n"
            "`/model` — Текущая модель\n"
            f"`/model <имя>` — Сменить\n"
            f"Доступно: {models_list}\n\n"
            "**Другое:**\n"
            "`/status` — Статус бота\n"
            "`/help` — Эта справка"
        )
        await msg.reply(help_text)
        return
    
    if cmd == "model":
        if not args:
            current_model = r.get('model')
            models_list = "\n".join([f"{'✅' if m == current_model else '⚪️'} {m}" for m in AVAILABLE_MODELS])
            
            await msg.reply(
                f"🤖 **Текущая:** {current_model}\n\n"
                f"**Доступные:**\n{models_list}\n\n"
                f"Смена: `/model <имя>`"
            )
        else:
            new_model = args[0].lower()
            if new_model not in AVAILABLE_MODELS:
                await msg.reply(
                    f"❌ Модель `{new_model}` не найдена\n\n"
                    f"Доступные: {', '.join(AVAILABLE_MODELS)}"
                )
            else:
                current = r.get('model')
                if new_model == current:
                    await msg.reply(f"ℹ️ Модель `{new_model}` уже загружена")
                else:
                    status_msg = await msg.reply(f"⏳ Загрузка `{new_model}`...")
                    
                    try:
                        await asyncio.to_thread(load_model, new_model)
                        
                        await status_msg.edit_text(
                            f"✅ **{current}** → **{new_model}**\n\n"
                            f"**Скорость на E5620:**\n"
                            f"• tiny: ~0.5x RT ⚡\n"
                            f"• base: ~0.7x RT\n"
                            f"• small: ~1.5x RT ⭐\n"
                            f"• medium: ~3x RT\n"
                            f"• large: ~5x RT 🐌\n\n"
                            f"RT = Real Time (время аудио)"
                        )
                    except Exception as e:
                        await status_msg.edit_text(f"❌ Ошибка: {e}")
        return
    
    if cmd == "status":
        e = "✅" if r.get('enabled') == '1' else "❌"
        m = "✅" if r.get('my') == '1' else "❌"
        f = "✅" if r.get('friend') == '1' else "❌"
        current_model = r.get('model')
        tracked_count = len(get_tracked_users())
        
        await msg.reply(
            f"📊 **Статус:**\n\n"
            f"Глобально: {e}\n"
            f"Свои: {m}\n"
            f"Чужие: {f}\n"
            f"Модель: `{current_model}`\n"
            f"CPU: {CPU_CORES} потоков\n"
            f"Отслеживается: {tracked_count} польз."
        )
        return


# ────────────────────────────────────────────────
# Главный цикл с переподключением
# ────────────────────────────────────────────────

async def main():
    load_model(r.get('model') or MODEL_SIZE)
    load_punctuation_model()

    logger.info(f"Запуск бота • модель: {r.get('model')} • tracked: {len(get_tracked_users())}")

    retry_delay = 5
    max_delay = 300

    while True:
        try:
            await app.start()
            logger.info("Соединение с Telegram установлено")

            # Регистрация обработчиков
            app.add_handler(MessageHandler(cmd_voicebot_on, filters.command("voicebot_on") & filters.me))
            app.add_handler(MessageHandler(cmd_voicebot_off, filters.command("voicebot_off") & filters.me))
            app.add_handler(MessageHandler(cmd_my_on, filters.command("my_on") & filters.me))
            app.add_handler(MessageHandler(cmd_my_off, filters.command("my_off") & filters.me))
            app.add_handler(MessageHandler(cmd_friend_on, filters.command("friend_on") & filters.me))
            app.add_handler(MessageHandler(cmd_friend_off, filters.command("friend_off") & filters.me))
            app.add_handler(MessageHandler(manage_tracked_users, filters.command(["addtovoicebot", "delfromvoicebot", "listvoicebot"]) & filters.me))
            app.add_handler(MessageHandler(control_commands, filters.private & filters.command(["start", "status", "help", "model"]) & filters.me))

            await idle()
            logger.warning("idle() завершился — перезапуск")

        except (Timeout, OSError, ConnectionResetError, RPCError) as e:
            logger.error(f"Ошибка соединения: {e}", exc_info=True)
            logger.info(f"Переподключение через {retry_delay} сек…")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)

        except KeyboardInterrupt:
            logger.info("Получен Ctrl+C → выход")
            break

        except Exception as e:
            logger.critical(f"Критическая ошибка, завершение: {e}", exc_info=True)
            break

    await app.stop()
    logger.info("Клиент остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Завершение по Ctrl+C")
    except Exception as e:
        logger.critical("Необработанная ошибка на верхнем уровне", exc_info=True)
        sys.exit(1)