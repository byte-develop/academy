import asyncio
import logging
import subprocess
import time
import requests
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config import settings
from handlers import start, admin
from payments.webhook_handler import cryptobot_webhook_router, setup_webhook_routes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем бота и диспетчер
bot = Bot(token=settings.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Включаем все необходимые роутеры
dp.include_router(start.router)
dp.include_router(admin.router)
dp.include_router(cryptobot_webhook_router)

# Функция для запуска через поллинг (для локальной разработки)
async def main_polling():
    await dp.start_polling(bot)

# Функция для запуска Ngrok и получения URL
def start_ngrok():
    ngrok_path = r"C:\ngrok\ngrok.exe"  # Измените на путь к вашему ngrok.exe
    port = settings.WEBHOOK_PORT
    
    try:
        # Запускаем Ngrok в фоновом режиме
        subprocess.Popen([ngrok_path, "http", str(port)])
        
        # Ждем запуска Ngrok
        time.sleep(3)
        
        # Получаем URL из локального API Ngrok
        for _ in range(5):  # Пробуем несколько раз
            try:
                response = requests.get("http://localhost:4040/api/tunnels")
                if response.status_code == 200:
                    data = response.json()
                    for tunnel in data["tunnels"]:
                        if tunnel["proto"] == "https":
                            logger.info(f"Ngrok запущен с URL: {tunnel['public_url']}")
                            return tunnel["public_url"]
            except:
                pass
            
            time.sleep(1)
        
        raise Exception("Не удалось получить URL Ngrok")
        
    except Exception as e:
        logger.error(f"Ошибка при запуске Ngrok: {e}")
        raise

# Функция для настройки вебхуков при запуске
async def on_startup(bot: Bot, webhook_url: str):
    # Устанавливаем вебхук для Telegram бота
    tg_webhook_url = f"{webhook_url}/webhook"
    await bot.set_webhook(tg_webhook_url)
    logger.info(f"Установлен вебхук для Telegram: {tg_webhook_url}")
    
    # Настраиваем вебхук для CryptoBot
    from payments.payment_service import setup_cryptobot_webhook
    
    cryptobot_webhook_url = f"{webhook_url}/cryptobot-webhook"
    success = await setup_cryptobot_webhook(cryptobot_webhook_url)
    
    if success:
        logger.info(f"Установлен вебхук для CryptoBot: {cryptobot_webhook_url}")
    else:
        logger.error(f"Не удалось установить вебхук для CryptoBot: {cryptobot_webhook_url}")

# Функция для отмены вебхуков при выключении
async def on_shutdown(bot: Bot):
    # Отключаем вебхук для Telegram бота
    await bot.delete_webhook()
    logger.info("Вебхук для Telegram отключен")
    
    # Отключаем вебхук для CryptoBot
    from payments.payment_service import remove_cryptobot_webhook
    
    success = await remove_cryptobot_webhook()
    
    if success:
        logger.info("Вебхук для CryptoBot отключен")
    else:
        logger.error("Не удалось отключить вебхук для CryptoBot")

# Запуск через вебхуки
def main_webhook():
    try:
        # Запускаем Ngrok и получаем URL
        webhook_url = start_ngrok()
        
        # Создаем приложение aiohttp
        app = web.Application()
        
        # Настраиваем обработчик вебхуков для Telegram
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        
        # Сохраняем бота в контексте приложения (для доступа в обработчиках)
        app["bot"] = bot
        
        # Настраиваем пути для вебхуков
        webhook_handler.register(app, path="/webhook")
        
        # Регистрируем маршрут для вебхуков CryptoBot
        setup_webhook_routes(app)
        
        # Регистрируем startup/shutdown обработчики
        app.on_startup.append(lambda app: on_startup(bot, webhook_url))
        app.on_shutdown.append(lambda app: on_shutdown(bot))
        
        # Запускаем приложение
        host = settings.WEBHOOK_HOST
        port = settings.WEBHOOK_PORT
        
        logger.info(f"Запуск вебхук-сервера на {host}:{port}")
        logger.info(f"Telegram webhook URL: {webhook_url}/webhook")
        logger.info(f"CryptoBot webhook URL: {webhook_url}/cryptobot-webhook")
        
        web.run_app(app, host=host, port=port)
        
    except Exception as e:
        logger.error(f"Ошибка при настройке вебхуков: {e}")
        logger.info("Запуск в режиме long polling в качестве запасного варианта...")
        asyncio.run(main_polling())

if __name__ == "__main__":
    # Проверяем, нужно ли использовать вебхуки или поллинг
    if settings.USE_WEBHOOKS:
        logger.info("Запуск бота с использованием вебхуков")
        main_webhook()
    else:
        logger.info("Запуск бота с использованием long polling")
        asyncio.run(main_polling())