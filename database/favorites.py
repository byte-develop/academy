from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import asyncio

async def get_db():
    client = AsyncIOMotorClient(settings.MONGO_URI, io_loop=asyncio.get_event_loop())
    return client[settings.MONGO_DB_NAME]

async def add_favorite_material(user_id: int, material_id):
    db = await get_db()
    await db.users.update_one(
        {"user_id": user_id},
        {"$addToSet": {"favorites": material_id}},
        upsert=True
    )

async def get_favorite_materials(user_id: int):
    db = await get_db()
    user = await db.users.find_one({"user_id": user_id})
    if not user or "favorites" not in user:
        return []
    
    material_ids = user["favorites"]
    materials = await db.materials.find({"_id": {"$in": material_ids}}).to_list(length=None)
    return materials
