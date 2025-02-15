import sys
import asyncio
from aiogram import Bot, Dispatcher
import os
from dotenv import load_dotenv
import logging
from handlers import router
from database import init_db

# Исправление для Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Загрузка переменных из .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

# Логирование
logging.basicConfig(level=logging.INFO)

# Создаем бота и диспетчер
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


async def main():
    logging.info('Starting bot...')
    try:
        # Инициализация базы данных
        await init_db()

        # Регистрация маршрутов
        dp.include_router(router)

        # Запуск бота
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")


if __name__ == '__main__':
    asyncio.run(main())
