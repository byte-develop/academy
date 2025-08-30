import logging
from aiohttp import web
from pydantic import BaseModel
from typing import Dict, Any
from aiogram import Router
from payments.payment_service import register_payment, cryptopay
from database.settings import get_users_collection

logger = logging.getLogger(__name__)
cryptobot_webhook_router = Router()

class WebhookPayload(BaseModel):
    update_id: int
    update_type: str
    payload: Dict[str, Any]


def calculate_crystals(amount: float) -> int:
    if amount < 5:
        return int(amount * 50)
    elif amount < 10:
        return int(amount * 60)
    elif amount == 10:
        return int(amount * 65)
    else:
        return int(amount * 75)


async def handle_crypto_webhook(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        payload = data.get("payload", {})

        if payload.get("status") != "paid":
            logger.info(f"Пропущен платёж со статусом: {payload.get('status')}")
            return web.Response(text="Ignored")

        user_id = int(payload.get("payload"))  # ID пользователя закодирован в payload
        amount = float(payload.get("amount"))
        crystals = calculate_crystals(amount)

        users_collection = await get_users_collection()
        update_result = await users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"crystals": crystals}}
        )

        if update_result.modified_count > 0:
            logger.info(f"✅ Пользователю {user_id} начислено {crystals} кристаллов.")
        else:
            logger.warning(f"⚠️ Пользователь {user_id} не найден в базе данных.")

        return web.Response(text="OK")
    except Exception as e:
        logger.error(f"Ошибка при обработке платежа: {e}")
        return web.Response(text="Error", status=500)




async def handle_root_webhook(request: web.Request) -> web.Response:
    try:
        user_agent = request.headers.get('User-Agent', '')
        if 'Crypto Bot' in user_agent:
            logger.info("Перенаправление вебхука CryptoBot с корневого пути на /cryptobot-webhook")
            return await handle_crypto_webhook(request)
        else:
            logger.warning(f"Получен запрос на корневой путь с User-Agent: {user_agent}")
            return web.json_response({"error": "Not found"}, status=404)
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на корневой путь: {e}")
        return web.json_response({"error": str(e)}, status=500)


def setup_webhook_routes(app: web.Application):
    app.router.add_post('/cryptobot-webhook', handle_crypto_webhook)
    app.router.add_post('/', handle_root_webhook)
    logger.info("Зарегистрированы маршруты для вебхуков CryptoBot: /cryptobot-webhook и /")
