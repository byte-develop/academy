from database.settings import get_settings
from aiogram import Bot, exceptions
from config import settings as config
import logging

logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)

async def check_subscriptions(user_id: int) -> dict:
    """
    Проверяет, подписан ли пользователь на обязательные каналы и чаты.
    Возвращает:
      - subscribed: True/False
      - missing: список, что именно не пройдено (channel, chat)
    """
    try:
        settings_data = await get_settings()
        if not settings_data:
            logger.error("⚙️ Settings not found in database")
            return {"subscribed": False, "missing": ["channel", "chat"]}

        missing_subscriptions = []

        # --- Проверка канала ---
        if "channel_id" in settings_data:
            try:
                channel_member = await bot.get_chat_member(
                    chat_id=settings_data["channel_id"],
                    user_id=user_id
                )
                if channel_member.status in ["left", "kicked"]:
                    logger.info(f"❌ Пользователь {user_id} не подписан на канал.")
                    missing_subscriptions.append("channel")
                else:
                    logger.info(f"✅ Пользователь {user_id} подписан на канал.")
            except exceptions.TelegramForbiddenError:
                logger.error("🚫 Бот не имеет прав видеть участников канала.")
                missing_subscriptions.append("channel")
            except exceptions.TelegramBadRequest:
                logger.error("❗ Ошибка запроса к каналу (проверьте channel_id или права бота).")
                missing_subscriptions.append("channel")
            except Exception as e:
                logger.error(f"⚠️ Неожиданная ошибка проверки канала: {e}")
                missing_subscriptions.append("channel")

        # --- Проверка чата ---
        if "chat_id" in settings_data:
            try:
                chat_member = await bot.get_chat_member(
                    chat_id=settings_data["chat_id"],
                    user_id=user_id
                )
                if chat_member.status in ["left", "kicked"]:
                    logger.info(f"❌ Пользователь {user_id} не подписан на чат.")
                    missing_subscriptions.append("chat")
                else:
                    logger.info(f"✅ Пользователь {user_id} подписан на чат.")
            except exceptions.TelegramForbiddenError:
                logger.error("🚫 Бот не имеет прав видеть участников чата.")
                missing_subscriptions.append("chat")
            except exceptions.TelegramBadRequest:
                logger.error("❗ Ошибка запроса к чату (проверьте chat_id или права бота).")
                missing_subscriptions.append("chat")
            except Exception as e:
                logger.error(f"⚠️ Неожиданная ошибка проверки чата: {e}")
                missing_subscriptions.append("chat")

        return {
            "subscribed": len(missing_subscriptions) == 0,
            "missing": missing_subscriptions
        }

    except Exception as e:
        logger.error(f"🔥 Фатальная ошибка проверки подписки: {e}")
        return {"subscribed": False, "missing": ["channel", "chat"]}
