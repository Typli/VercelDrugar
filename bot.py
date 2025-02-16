import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode
from aiogram.utils.markdown import bold

# Загрузка конфигурации
def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            return json.load(f)
    return {}

# Инициализация бота
config = load_config()
if not config:
    print("Конфигурация Telegram не найдена. Запустите Flask-приложение для настройки.")
    exit()

bot = Bot(token=config['api_key'])
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer(
        f"Привет, {bold(message.from_user.full_name)}! Я бот для отправки слайд-шоу.",
        parse_mode=ParseMode.MARKDOWN
    )

# Отправка видео
async def send_video_to_user(video_path):
    try:
        video = FSInputFile(video_path)
        await bot.send_video(chat_id=config['user_id'], video=video)
        print("Видео успешно отправлено в Telegram.")
    except Exception as e:
        print(f"Ошибка при отправке видео в Telegram: {e}")

if __name__ == '__main__':
    dp.run_polling(bot)