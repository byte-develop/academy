import telebot
from config import BOT_TOKEN, CHANNEL_ID, CHAT_ID
from utils.invite_links import generate_chat_invite_link
from utils.subscription import is_user_subscribed

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    channel_link = generate_chat_invite_link(bot, CHANNEL_ID)
    chat_link = generate_chat_invite_link(bot, CHAT_ID)
    bot.send_message(
        user_id,
        f"Ваша одноразовая ссылка на канал: {channel_link}\nВаша одноразовая ссылка на чат: {chat_link}"
    )
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Проверить")
    bot.send_message(user_id, "Нажмите 'Проверить' после подписки.", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "Проверить")
def handle_check(message):
    user_id = message.from_user.id
    if is_user_subscribed(bot, user_id, CHANNEL_ID) and is_user_subscribed(bot, user_id, CHAT_ID):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Меню")
        bot.send_message(user_id, "Вы успешно подписались! Главное меню:", reply_markup=markup)
    else:
        bot.send_message(user_id, "Вы ещё не подписались на канал или чат!")

if __name__ == "__main__":
    bot.polling(none_stop=True)