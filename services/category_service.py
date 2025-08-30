from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

client = AsyncIOMotorClient(MONGO_URI)
db = client["sbot"]  # 👉 ЗАМЕНИ на своё название базы
collection = db["categories"]  # 👉 Или на нужное имя коллекции

async def add_category(category: dict):
    """Добавляет новую категорию в базу."""
    await collection.insert_one(category)

async def get_all_categories():
    """Возвращает список всех категорий."""
    categories = await collection.find().to_list(length=None)
    return categories


async def edit_category(category_id: str, new_name: str):
    """Обновляет название категории по category_id."""
    await collection.update_one(
        {"category_id": category_id},
        {"$set": {"name": new_name}}
    )


async def delete_category(category_id: str):
    """Удаляет категорию по category_id."""
    await collection.delete_one({"category_id": category_id})


async def add_section(category_id: str, section: dict):
    """Добавляет раздел в список sections внутри категории."""
    await collection.update_one(
        {"category_id": category_id},
        {"$push": {"sections": section}}
    )


async def edit_section(category_id: str, section_id: str, new_name: str):
    """Редактирует название раздела в категории."""
    await collection.update_one(
        {
            "category_id": category_id,
            "sections.section_id": section_id
        },
        {"$set": {"sections.$.name": new_name}}
    )


async def delete_section(category_id: str, section_id: str):
    """Удаляет раздел с указанным section_id из категории."""
    await collection.update_one(
        {"category_id": category_id},
        {"$pull": {"sections": {"section_id": section_id}}}
    )
