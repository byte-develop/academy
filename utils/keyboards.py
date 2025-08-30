from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.sections import get_category_list, get_sections_by_category


# --- Главное меню для всех пользователей ---
def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📚 Категории"),
                KeyboardButton(text="⭐ Избранное")
            ],
            [
                KeyboardButton(text="👤 Профиль"),
                KeyboardButton(text="ℹ️ О нас")
            ]
        ],
        resize_keyboard=True
    )

# --- Инлайн клавиатура для выбора категории (Пользователь) ---
async def get_category_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    categories = await get_category_list()

    if not categories:
        # Если категорий нет — возвращаем кнопку-заглушку
        builder.button(text="❌ Нет категорий", callback_data="no_action")
        builder.adjust(1)  # По одной кнопке в строке
        return builder.as_markup()

    for category in categories:
        builder.button(
            text=category["name"],
            callback_data=f"select_category:{category['category_id']}"
        )

    # Устанавливаем по одной кнопке в строке для категорий (вертикальное расположение)
    builder.adjust(1)
    
    return builder.as_markup()

# --- Инлайн клавиатура для выбора раздела (Пользователь) ---
async def get_sections_inline_keyboard(category_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    sections = await get_sections_by_category(category_id)

    if not sections:
        # Если разделов нет — возвращаем кнопку-заглушку
        builder.button(text="❌ Нет разделов", callback_data="no_action")
        builder.adjust(1)
        # Добавляем кнопку назад к категориям в отдельном ряду
        builder.button(text="↩️ Назад к категориям", callback_data="back_to_categories")
        return builder.as_markup()

    for section in sections:
        builder.button(
            text=section["name"],
            callback_data=f"select_section:{category_id}:{section['section_id']}"
        )

    # Устанавливаем настройки расположения кнопок
    # Разделы могут быть в несколько столбцов (например, 2)
    builder.adjust(2)  
    
    # Добавляем кнопку назад к категориям отдельно, в последнем ряду
    builder.row(InlineKeyboardButton(text="↩️ Назад к категориям", callback_data="back_to_categories"))
    
    return builder.as_markup()

# --- Инлайн клавиатура для выбора категории (Админ) ---
def get_category_inline_keyboard_admin() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Категория 1 (пример)", callback_data="select_category_admin:0")],
            [InlineKeyboardButton(text="Категория 2 (пример)", callback_data="select_category_admin:1")]
        ]
    )
    return keyboard

# --- Инлайн клавиатура для выбора раздела (Админ) ---
def get_sections_inline_keyboard_admin(category_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Раздел 1 (пример)", callback_data=f"select_section_admin:{category_id}:0")],
            [InlineKeyboardButton(text="Раздел 2 (пример)", callback_data=f"select_section_admin:{category_id}:1")]
        ]
    )
    return keyboard

# --- Улучшенная клавиатура навигации по материалам ---
def get_material_navigation_keyboard(current_index: int, total: int, has_file: bool = False, is_favorites: bool = False) -> InlineKeyboardMarkup:
    keyboard = []
    
    # Информация о прогрессе
    progress_text = f"📄 {current_index + 1}/{total}"
    keyboard.append([InlineKeyboardButton(text=progress_text, callback_data="info")])
    
    # Кнопки навигации
    navigation_buttons = []
    if current_index > 0:
        navigation_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data="prev_material"))
    if current_index < total - 1:
        navigation_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data="next_material"))
    if navigation_buttons:
        keyboard.append(navigation_buttons)
    
    # Кнопка избранного (разная для обычного просмотра и избранного)
    if is_favorites:
        keyboard.append([InlineKeyboardButton(text="❌ Удалить из избранного", callback_data="remove_from_favorites")])
    else:
        keyboard.append([InlineKeyboardButton(text="⭐ Добавить в избранное", callback_data="add_to_favorites")])
    
    # Кнопка возврата (только для обычного просмотра материалов)
    if not is_favorites:
        keyboard.append([InlineKeyboardButton(text="↩️ Вернуться в раздел", callback_data="back_to_section")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- Клавиатура для админа ---
def get_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить материал")],
            [KeyboardButton(text="📖 Все материалы")],
            [KeyboardButton(text="📢 Изменить канал")],
            [KeyboardButton(text="💬 Изменить чат")]
        ],
        resize_keyboard=True
    )

def get_subscription_levels_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🪙 Расширенный — 10 USDT", callback_data="buy_sub:1")],
        [InlineKeyboardButton(text="💠 Премиум — 20 USDT", callback_data="buy_sub:2")],
        [InlineKeyboardButton(text="👑 Полный — 50 USDT", callback_data="buy_sub:3")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
