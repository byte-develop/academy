import os

BOT_TOKEN = os.getenv('BOT_TOKEN', 'your-telegram-bot-token')
CRYPTOBOT_TOKEN = os.getenv('CRYPTOBOT_TOKEN', 'your-cryptobot-token')
CHANNEL_ID = os.getenv('CHANNEL_ID', '@your_channel')
CHAT_ID = os.getenv('CHAT_ID', '@your_chat')
ADMIN_ID = int(os.getenv('ADMIN_ID', '123456789'))