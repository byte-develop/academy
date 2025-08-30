from services.category_service import get_all_categories

# Получить список всех категорий
async def get_category_list():
    categories = await get_all_categories()
    return [
        {
            "category_id": cat["category_id"],
            "name": cat["name"]
        }
        for cat in categories
    ]

# Получить список разделов для выбранной категории
async def get_sections_by_category(category_id: int):
    categories = await get_all_categories()
    for cat in categories:
        if cat["category_id"] == category_id:
            return cat.get("sections", [])
    return []
