import asyncio
from aiogram import Bot, Dispatcher
import os
from dotenv import load_dotenv
import logging
from handlers import router
from database import init_db

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)


async def main():
    logging.info('Starting bot...')
    try:
        await init_db()
        dp.include_router(router)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(e)


if __name__ == '__main__':
    asyncio.run(main())
