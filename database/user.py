from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import asyncio

async def get_db():
    client = AsyncIOMotorClient(settings.MONGO_URI, io_loop=asyncio.get_event_loop())
    return client[settings.MONGO_DB_NAME]

async def get_user(user_id: int):
    db = await get_db()
    return await db.users.find_one({"user_id": user_id})

async def create_or_update_user(user_data: dict):
    db = await get_db()
    await db.users.update_one(
        {"user_id": user_data["user_id"]},
        {"$set": user_data},
        upsert=True
    )