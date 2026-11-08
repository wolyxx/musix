import asyncio
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BotCommand
import yt_dlp

BOT_TOKEN = os.getenv(9023302375:AAFiItEAqNNqgiNZbs6mdXAIzmL6cT7M0lk)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_languages = {}

MESSAGES = {
    "ru": {
        "welcome": "🌍 Выберите язык / Choose your language:",
        "ready": "🎵 Привет! Отправь мне ссылку на трек или видео и я скачаю для тебя MP3-файл.",
        "downloading": "⏳ Скачиваю и обрабатываю аудио, подождите...",
        "uploading": "📤 Отправляю файл...",
        "file_not_found": "❌ Не удалось найти итоговый аудиофайл.",
        "error": "❌ Произошла ошибка при обработке ссылки.",
    },
    "en": {
        "welcome": "🌍 Choose your language / Выберите язык:",
        "ready": "🎵 Hello! Send me a link to a track or video and I will download the MP3-file for you.",
        "downloading": "⏳ Downloading and processing audio, please wait...",
        "uploading": "📤 Uploading file...",
        "file_not_found": "❌ Could not find the audio file.",
        "error": "❌ An error occurred while processing the link.",
    }
}

def get_language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.button(text="🇬🇧 English", callback_data="lang_en")
    builder.adjust(2)
    return builder.as_markup()

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота / Start bot"),
        BotCommand(command="language", description="Сменить язык / Change language")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        MESSAGES["ru"]["welcome"],
        reply_markup=get_language_keyboard()
    )

@dp.message(Command("language"))
async def cmd_language(message: types.Message):
    await message.answer(
        "🌍 Выберите язык / Choose your language:",
        reply_markup=get_language_keyboard()
    )

@dp.callback_query(F.data.startswith("lang_"))
async def callbacks_lang(call: types.CallbackQuery):
    lang_code = call.data.split("_")[1]
    user_languages[call.from_user.id] = lang_code
    
    await call.answer()
    await call.message.edit_text(MESSAGES[lang_code]["ready"])

@dp.message(F.text.startswith("http"))
async def download_audio_handler(message: types.Message):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, "ru")
    
    url = message.text.strip()
    status_msg = await message.answer(MESSAGES[lang]["downloading"])

    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + ".mp3"

        if os.path.exists(mp3_filename):
            await status_msg.edit_text(MESSAGES[lang]["uploading"])
            audio_file = types.FSInputFile(mp3_filename)
            await message.answer_audio(audio=audio_file)
            
            os.remove(mp3_filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text(MESSAGES[lang]["file_not_found"])

    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text(MESSAGES[lang]["error"])

# --- Веб-сервер для Hugging Face (порт 7860) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")
    def log_message(self, format, *args):
        pass  # Отключаем лишний спам в логах

def run_web_server():
    server = HTTPServer(("0.0.0.0", 7860), HealthCheckHandler)
    server.serve_forever()
# ---------------------------------------------

async def main():
    # Запускаем веб-сервер в фоновом потоке, чтобы Hugging Face был доволен
    threading.Thread(target=run_web_server, daemon=True).start()
    
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())