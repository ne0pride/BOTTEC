import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import router
from logger import logger
from database import Database

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    db = Database()
    await db.connect()
    try:
        await dp.start_polling(bot)
        logger.info("✅ Бот запущен!")  # Лог при старте
    except Exception as e:
        logger.error(f"❌ Ошибка в работе бота: {e}")
    finally:
        await db.close()
if __name__ == "__main__":
    asyncio.run(main())