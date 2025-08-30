from telebot import TeleBot

def is_user_subscribed(bot: TeleBot, user_id: int, chat_id: str) -> bool:
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        return status in ["member", "administrator", "creator"]
    except Exception:
        return False