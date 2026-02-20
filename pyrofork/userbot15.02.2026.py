import os
import asyncio
import gc
import redis
import re
import json
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import PeerIdInvalid, UsernameInvalid, UserIdInvalid
from faster_whisper import WhisperModel
from concurrent.futures import ThreadPoolExecutor
from deepmultilingualpunctuation import PunctuationModel
import multiprocessing

# ==================== Конфиг ====================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
FRIEND_ID = int(os.getenv("FRIEND_USER_ID", 0))
MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")

# Лимиты Telegram
CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096

# ==================== Redis ====================
r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

if not r.exists('enabled'):  r.set('enabled', '1')
if not r.exists('my'):      r.set('my', '1')
if not r.exists('friend'):  r.set('friend', '1')
if not r.exists('model'):   r.set('model', MODEL_SIZE)

# Инициализация списка отслеживаемых пользователей
if not r.exists('tracked_users'):
    initial_users = [FRIEND_ID] if FRIEND_ID != 0 else []
    r.set('tracked_users', json.dumps(initial_users))

# ==================== Клиент ====================
app = Client("voice_transcriber", api_id=API_ID, api_hash=API_HASH)

# Глобальные переменные для моделей
model = None
punct_model = None

# ThreadPoolExecutor
CPU_CORES = multiprocessing.cpu_count()
executor = ThreadPoolExecutor(max_workers=CPU_CORES)

# Доступные модели
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

def get_tracked_users():
    """Получает список отслеживаемых пользователей из Redis"""
    try:
        users_json = r.get('tracked_users')
        return json.loads(users_json) if users_json else []
    except:
        return []

def add_tracked_user(user_id: int):
    """Добавляет пользователя в список отслеживания"""
    users = get_tracked_users()
    if user_id not in users:
        users.append(user_id)
        r.set('tracked_users', json.dumps(users))
        return True
    return False

def remove_tracked_user(user_id: int):
    """Удаляет пользователя из списка отслеживания"""
    users = get_tracked_users()
    if user_id in users:
        users.remove(user_id)
        r.set('tracked_users', json.dumps(users))
        return True
    return False

def load_model(model_size: str):
    """Загружает или перезагружает модель Whisper"""
    global model
    
    if model is not None:
        del model
        gc.collect()
    
    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        cpu_threads=CPU_CORES,
        num_workers=1
    )
    r.set('model', model_size)
    print(f"Модель {model_size} загружена с {CPU_CORES} CPU потоками")

def load_punctuation_model():
    """Загружает модель пунктуации"""
    global punct_model
    print("Загружаю модель пунктуации...")
    punct_model = PunctuationModel(model="kredor/punctuate-all")
    print("Модель пунктуации загружена")

# Загрузка моделей при старте
load_model(r.get('model') or MODEL_SIZE)
load_punctuation_model()

# ==================== Форматирование текста ====================
def format_text(text: str) -> str:
    """Улучшает форматирование текста"""
    if not text or text == "…":
        return text
    
    try:
        formatted = punct_model.restore_punctuation(text)
        sentences = re.split(r'(?<=[.!?])\s+', formatted)
        
        paragraphs = []
        current_paragraph = []
        
        for sentence in sentences:
            current_paragraph.append(sentence)
            if len(current_paragraph) >= 4:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
        
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        return '\n\n'.join(paragraphs)
    
    except Exception as e:
        print(f"Ошибка форматирования текста: {e}")
        return text

# ==================== Транскрипция ====================
def transcribe_file_sync(file_path: str) -> str:
    """Синхронная функция транскрипции"""
    try:
        segments, _ = model.transcribe(
            file_path,
            language="ru",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=400
            ),
            word_timestamps=True
        )
        
        text = " ".join(seg.text for seg in segments).strip()
        
        if text and text != "…":
            return format_text(text)
        
        return text if text else "…"
    
    except Exception as e:
        print(f"Ошибка транскрипции файла {file_path}: {e}")
        return f"Ошибка: {str(e)}"

async def transcribe(file_path: str) -> str:
    """Асинхронная обёртка для транскрипции"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, transcribe_file_sync, file_path)
    return result

def split_text(text: str, max_length: int = MESSAGE_LIMIT) -> list:
    """Разбивает текст на части"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        if len(current_chunk) + len(para) + 2 <= max_length:
            if current_chunk:
                current_chunk += '\n\n' + para
            else:
                current_chunk = para
        elif len(para) > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
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
    """Обработка своих голосовых"""
    file_path = None
    
    try:
        try:
            await message.edit_caption("⏳ Транскрипция в процессе...")
        except Exception as e:
            print(f"Не удалось добавить статус: {e}")
        
        file_path = await message.download(f"temp_{message.id}.ogg")
        text = await transcribe(file_path)
        
        if len(text) <= CAPTION_LIMIT:
            try:
                await message.edit_caption(text)
            except Exception as edit_error:
                print(f"Ошибка редактирования {message.id}: {edit_error}")
                try:
                    await message.edit_caption(f"❌ Ошибка: {str(edit_error)[:900]}")
                except:
                    pass
        else:
            try:
                first_sentence = text.split('\n\n')[0]
                if len(first_sentence) > CAPTION_LIMIT - 3:
                    first_sentence = text[:CAPTION_LIMIT-3]
                await message.edit_caption(first_sentence + "...")
            except:
                pass
            
            text_chunks = split_text(text, MESSAGE_LIMIT)
            
            for i, chunk in enumerate(text_chunks, 1):
                header = f"📝 **Часть {i}/{len(text_chunks)}**\n\n" if len(text_chunks) > 1 else ""
                await message.reply(header + chunk, quote=False)
                await asyncio.sleep(0.5)
    
    except Exception as e:
        error_message = f"❌ Ошибка обработки: {str(e)[:900]}"
        print(f"Критическая ошибка {message.id}: {e}")
        try:
            await message.edit_caption(error_message)
        except:
            try:
                await message.reply(error_message, quote=False)
            except:
                pass
    
    finally:
        if file_path:
            try:
                os.remove(file_path)
            except:
                pass

# ==================== Обработка голосовых от отслеживаемых пользователей ====================
async def process_tracked_voice(message: Message):
    """Обработка голосовых от отслеживаемых пользователей"""
    file_path = None
    status_message = None
    
    try:
        # Определяем префикс
        if message.chat.type in ["group", "supergroup"]:
            prefix = f"**[{message.from_user.first_name}]** (группа):\n\n"
        else:
            prefix = f"**[{message.from_user.first_name}]:**\n\n"
        
        try:
            status_message = await message.reply(
                "⏳ Транскрипция в процессе...",
                quote=True
            )
        except Exception as e:
            print(f"Не удалось отправить статус: {e}")
            return
        
        file_path = await message.download(f"temp_{message.id}.ogg")
        text = await transcribe(file_path)
        full_text = f"{prefix}{text}"
        
        if len(full_text) <= MESSAGE_LIMIT:
            try:
                await status_message.edit_text(full_text)
            except Exception as edit_error:
                print(f"Ошибка редактирования статуса: {edit_error}")
                try:
                    await status_message.edit_text(f"❌ Ошибка: {str(edit_error)[:900]}")
                except:
                    pass
        else:
            try:
                first_part = full_text[:MESSAGE_LIMIT-100]
                await status_message.edit_text(first_part + "...")
            except:
                pass
            
            text_chunks = split_text(full_text, MESSAGE_LIMIT)
            
            for i, chunk in enumerate(text_chunks[1:], 2):
                header = f"📝 **Часть {i}/{len(text_chunks)}**\n\n"
                await message.reply(header + chunk, quote=False)
                await asyncio.sleep(0.5)
    
    except Exception as e:
        error_message = f"❌ Ошибка обработки: {str(e)[:900]}"
        print(f"Критическая ошибка {message.id}: {e}")
        
        if status_message:
            try:
                await status_message.edit_text(error_message)
            except:
                try:
                    await message.reply(error_message, quote=True)
                except:
                    pass
        else:
            try:
                await message.reply(error_message, quote=True)
            except:
                pass
    
    finally:
        if file_path:
            try:
                os.remove(file_path)
            except:
                pass

# ==================== Обработчики ====================
@app.on_message(filters.voice & filters.me)
async def my_voice(client, message: Message):
    if r.get('enabled') != '1' or r.get('my') != '1':
        return
    asyncio.create_task(process_my_voice(message))

@app.on_message(filters.voice & ~filters.me)
async def tracked_voice(client, message: Message):
    if r.get('enabled') != '1' or r.get('friend') != '1':
        return
    
    # Проверяем, есть ли пользователь в списке отслеживаемых
    tracked_users = get_tracked_users()
    if message.from_user and message.from_user.id in tracked_users:
        asyncio.create_task(process_tracked_voice(message))

# ==================== Команды ====================
commands = {
    "voicebot_on":  lambda: (r.set('enabled', '1'), r.set('my', '1'), r.set('friend', '1'), "✅ Всё включено"),
    "voicebot_off": lambda: (r.set('enabled', '0'), None, None, "❌ Всё выключено"),
    "my_on":        lambda: (r.set('my', '1'), None, None, "✅ Твои голосовые → ВКЛ"),
    "my_off":       lambda: (r.set('my', '0'), None, None, "❌ Твои голосовые → ВЫКЛ"),
    "friend_on":    lambda: (r.set('friend', '1'), None, None, "✅ Голосовые друзей → ВКЛ"),
    "friend_off":   lambda: (r.set('friend', '0'), None, None, "❌ Голосовые друзей → ВЫКЛ"),
}

@app.on_message(filters.command(["addtovoicebot", "delfromvoicebot", "listvoicebot"]) & filters.me)
async def manage_tracked_users(client, message: Message):
    cmd = message.command[0].lower()
    
    if cmd == "addtovoicebot":
        user_id = None
        
        if message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id
            user_name = message.reply_to_message.from_user.first_name
        elif len(message.command) > 1:
            try:
                user_id = int(message.command[1])
                user_name = f"ID {user_id}"
            except:
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
            user_name = message.reply_to_message.from_user.first_name
        elif len(message.command) > 1:
            try:
                user_id = int(message.command[1])
                user_name = f"ID {user_id}"
            except:
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
        tracked_users = get_tracked_users()
        
        if not tracked_users:
            await message.reply("📋 Список отслеживаемых пуст\n\nИспользуй `/addtovoicebot` для добавления")
            return
        
        # Получаем информацию о пользователях с обработкой ошибок
        user_list = []
        for user_id in tracked_users:
            try:
                # Пытаемся получить информацию о пользователе
                user = await client.get_users(user_id)
                name = f"{user.first_name}"
                if user.last_name:
                    name += f" {user.last_name}"
                if user.username:
                    name += f" (@{user.username})"
                user_list.append(f"• **{name}**\n  ID: `{user_id}`")
            except (PeerIdInvalid, UsernameInvalid, UserIdInvalid, KeyError):
                # Если не удалось получить данные - показываем только ID
                user_list.append(f"• ID: `{user_id}` (данные недоступны)")
            except Exception as e:
                # Любая другая ошибка
                user_list.append(f"• ID: `{user_id}` (ошибка: {type(e).__name__})")
                print(f"Ошибка получения данных пользователя {user_id}: {e}")
        
        response = f"📋 **Отслеживаемые** ({len(tracked_users)}):\n\n"
        response += "\n\n".join(user_list)
        response += "\n\n💡 Данные обновятся после получения сообщений от пользователей"
        
        await message.reply(response)

@app.on_message(filters.private & filters.command(list(commands.keys()) + ["start", "status", "help", "model"]) & filters.me)
async def control_commands(client, message: Message):
    cmd = message.text.split()[0][1:].lower()
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if cmd == "start":
        await message.reply(
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
        await message.reply(help_text)
        return
    
    if cmd == "model":
        if not args:
            current_model = r.get('model')
            models_list = "\n".join([f"{'✅' if m == current_model else '⚪️'} {m}" for m in AVAILABLE_MODELS])
            
            await message.reply(
                f"🤖 **Текущая:** {current_model}\n\n"
                f"**Доступные:**\n{models_list}\n\n"
                f"Смена: `/model <имя>`"
            )
        else:
            new_model = args[0].lower()
            if new_model not in AVAILABLE_MODELS:
                await message.reply(
                    f"❌ Модель `{new_model}` не найдена\n\n"
                    f"Доступные: {', '.join(AVAILABLE_MODELS)}"
                )
            else:
                current = r.get('model')
                if new_model == current:
                    await message.reply(f"ℹ️ Модель `{new_model}` уже загружена")
                else:
                    status_msg = await message.reply(f"⏳ Загрузка `{new_model}`...")
                    
                    try:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, load_model, new_model)
                        
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
        
        await message.reply(
            f"📊 **Статус:**\n\n"
            f"Глобально: {e}\n"
            f"Свои: {m}\n"
            f"Чужие: {f}\n"
            f"Модель: `{current_model}`\n"
            f"CPU: {CPU_CORES} потоков\n"
            f"Отслеживается: {tracked_count} польз."
        )
        return
    
    if cmd in commands:
        commands[cmd]()
        await message.reply(commands[cmd]()[3])

# ==================== Запуск ====================
print("Запускаю голосового транскрибера (оптимизировано для E5620)…")
print(f"CPU потоков: {CPU_CORES}")
print(f"Отслеживаемых пользователей: {len(get_tracked_users())}")
app.start()
print(f"Работаю с моделью {r.get('model')}!")
print(f"Список отслеживаемых: {get_tracked_users()}")
idle()
