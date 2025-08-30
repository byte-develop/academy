
from database.settings import get_users_collection
from datetime import datetime
from config import settings


# Регистрация нового пользователя
async def register_user(user: dict):
    users = await get_users_collection()
    existing = await users.find_one({"user_id": user.id})
    if existing:
        return

    new_user = {
        "user_id": user.id,
        "role": "user",
        "last_reset_date": datetime.utcnow().date().isoformat(),
        "crystals": 0,
        "bonus_given": False
    }
    await users.insert_one(new_user)


# Получение пользователя по user_id
async def get_user(user_id: int):
    users = await get_users_collection()
    return await users.find_one({"user_id": user_id})

# Проверка, является ли пользователь админом
async def is_admin(user_id: int) -> bool:
    users = await get_users_collection()
    user = await users.find_one({"user_id": user_id})
    if not user:
        return False
    return user.get("role") == "admin"


# Списать запрос у пользователя
async def decrease_limit(user_id: int, amount: int) -> bool:
    users = await get_users_collection()
    user = await users.find_one({"user_id": user_id})
    if not user:
        return False

    crystals = user.get("crystals", 0)
    if crystals >= amount:
        await users.update_one({"user_id": user_id}, {"$inc": {"crystals": -amount}})
        return True
    return False

    crystals = user.get("crystals", 0)
    if crystals >= 15:
        await users.update_one({"user_id": user_id}, {"$inc": {"crystals": -15}})
        return True
    return False

    limit = user.get("daily_limit_left", 0)
    level = user.get("subscription_level", 0)

    if level == 3:
        return True  # Полный доступ

    if limit > 0:
        await users.update_one(
            {"user_id": user_id},
            {"$inc": {"daily_limit_left": -1}}
        )
        return True
    else:
        return False


