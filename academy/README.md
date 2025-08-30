# academy Telegram Bot

## Быстрый запуск

1. Установите зависимости:
   ```
   pip install pyTelegramBotAPI
   ```

2. Укажите переменные окружения (например, через .env или в системе):
   ```
   BOT_TOKEN=your-telegram-bot-token
   CRYPTOBOT_TOKEN=your-cryptobot-token
   CHANNEL_ID=@your_channel
   CHAT_ID=@your_chat
   ADMIN_ID=123456789
   ```

3. Запустите бот:
   ```
   python academy/bot.py
   ```

## Особенности

- Одноразовые ссылки на канал и чат
- Проверка подписки пользователя
- Все настройки централизованы в config.py
- Не используется ngrok

## Важно

- Бот должен быть администратором в канале и чате для работы invite-link.
- Для production рекомендуется использовать webhook на реальном сервере.