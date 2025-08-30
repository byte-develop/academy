from telebot import TeleBot

def generate_chat_invite_link(bot: TeleBot, chat_id: str) -> str:
    # Бот должен быть администратором в группе/канале
    try:
        invite_link = bot.create_chat_invite_link(chat_id, member_limit=1)
        return invite_link.invite_link
    except Exception as e:
        print(f"Ошибка генерации ссылки: {e}")
        return f"https://t.me/{chat_id.lstrip('@')}"