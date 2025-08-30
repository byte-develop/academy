from pydantic_settings import BaseSettings
from typing import Dict, ClassVar


class Settings(BaseSettings):
    BOT_TOKEN: str
    MONGO_URI: str
    MONGO_DB_NAME: str = "sbot"
    DEFAULT_ADMIN_ID: int = 5989023142
    
    # Настройки CryptoBot
    CRYPTOBOT_TOKEN: str = "105772:AAynYu5wytrQwBtKU98iLf84DLJ7bfvUVhn"  # API токен от @CryptoBot
    
    # Настройки вебхуков
    USE_WEBHOOKS: bool = False  # Флаг использования вебхуков (False для long polling)
    WEBHOOK_HOST: str = "0.0.0.0"  # Хост для запуска вебхук-сервера
    WEBHOOK_PORT: int = 8443  # Порт для запуска вебхук-сервера
    
    # Названия уровней подписки
    SUBSCRIPTION_LEVELS_NAMES: ClassVar[Dict[int, str]] = {
        0: "Бесплатный (1 запрос/день)",
        1: "Расширенный (10 запросов/день)",
        2: "Премиум (30 запросов/день)",
        3: "Полный (безлимит)"
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Для обратной совместимости с существующим кодом
MONGO_URI = settings.MONGO_URI
MONGO_DB_NAME = settings.MONGO_DB_NAME
DEFAULT_ADMIN_ID = settings.DEFAULT_ADMIN_ID