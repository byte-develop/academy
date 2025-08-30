from motor.motor_asyncio import AsyncIOMotorClient
from config import settings as config
import asyncio

# ✅ создаём клиент один раз, переиспользуем
_client = AsyncIOMotorClient(config.MONGO_URI)
_db = _client[config.MONGO_DB_NAME]

async def get_db():
    return _db

async def get_settings():
    db = await get_db()
    return await db.settings.find_one({"name": "main"})

async def update_settings_field(field: str, value):
    db = await get_db()
    await db.settings.update_one(
        {"name": "main"},
        {"$set": {field: value}},
        upsert=True
    )

async def get_users_collection():
    db = await get_db()
    return db.users

async def get_materials_collection():
    db = await get_db()
    return db.materials

async def get_settings_collection():
    db = await get_db()
    return db.settings

async def get_categories_collection():
    db = await get_db()
    return db["categories"]

async def update_settings(new_data: dict):
    settings_collection = await get_settings_collection()
    await settings_collection.update_one(
        {"name": "main"},
        {"$set": new_data},
        upsert=True
    )