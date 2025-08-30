from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from bson import ObjectId
from utils.sections import get_category_list, get_sections_by_category

# Подключение к MongoDB
async def get_db():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]

# Добавление материала через ID категории и раздела с поддержкой цены
async def add_material(category_id: int, section_id: int, name: str, description: str, price: int = 0, file_id: str = None):
    db = await get_db()

    categories = await get_category_list()
    category = next((c for c in categories if c["category_id"] == category_id), None)

    sections = await get_sections_by_category(category_id)
    section = next((s for s in sections if s["section_id"] == section_id), None)

    if not category or not section:
        raise ValueError("Категория или раздел не найдены")

    material = {
        "category": category.get("category_name") or category.get("name", "Неизвестно"),
        "section": section.get("section_name") or section.get("name", "Без названия"),
        "name": name,
        "description": description,
        "price": price
    }
    if file_id:
        material["file_id"] = file_id

    await db.materials.insert_one(material)

# Получение материалов по категории и разделу
async def get_materials_by_category_and_section(category: str, section: str) -> list:
    db = await get_db()
    cursor = db.materials.find({"category": category, "section": section})
    materials = await cursor.to_list(length=None)
    return materials

# Добавление материала в избранное
async def add_to_favorites(user_id: int, material: dict):
    db = await get_db()
    favorite = {
        "user_id": user_id,
        "category": material["category"],
        "section": material["section"],
        "name": material["name"],
        "description": material["description"],
        "file_id": material.get("file_id")
    }
    await db.favorites.insert_one(favorite)

# Получение всех избранных материалов пользователя
async def get_favorites(user_id: int) -> list:
    db = await get_db()
    cursor = db.favorites.find({"user_id": user_id})
    favorites = await cursor.to_list(length=None)
    return favorites

# Удаление материала из избранного
async def remove_from_favorites(user_id: int, material_id: str):
    db = await get_db()
    try:
        obj_id = ObjectId(material_id) if ObjectId.is_valid(material_id) else material_id
        result = await db.favorites.delete_one({
            "user_id": user_id,
            "_id": obj_id
        })
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error in remove_from_favorites: {e}")
        return False

# Получение всех материалов для админов
async def get_all_materials() -> list:
    db = await get_db()
    cursor = db.materials.find()
    materials = await cursor.to_list(length=None)
    return materials

# Удалить материал по его ObjectId
async def delete_material(material_id: str):
    db = await get_db()
    await db.materials.delete_one({"_id": ObjectId(material_id)})
