import random
import logging
from aiogram.fsm.state import default_state
from aiogram.types import Message


from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.user_service import is_admin
from services.subscription_service import check_subscriptions
from database.settings import get_settings, update_settings
from services.user_service import register_user
from aiogram.types import CallbackQuery
from database.materials import (
    get_materials_by_category_and_section,
    get_all_materials,
    add_material,
    delete_material
)
from services.category_service import get_all_categories
from bson import ObjectId

router = Router()
logger = logging.getLogger(__name__)

class AdminStates(StatesGroup):
    waiting_for_crystal_user_id = State()
    waiting_for_crystal_amount = State()
    waiting_for_new_channel_id = State()
    waiting_for_new_chat_id = State()
    waiting_for_new_channel_link = State()
    waiting_for_new_chat_link = State()
    waiting_for_material_name = State()
    waiting_for_material_description = State()
    waiting_for_material_price = State()
    waiting_for_material_file = State()
    waiting_for_category_name = State()  # <-- добавлено
    


@router.message(Command("admin"))
async def admin_panel(message: Message, user_id: int = None):
    uid = user_id if user_id is not None else message.from_user.id
    isadm = await is_admin(uid)

    await message.answer(f"🔐 Статус: {'✅ админ' if isadm else '❌ НЕ админ'}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))
    if not isadm:
        await message.answer("❌ У вас нет прав администратора.")
        return



    settings_data = await get_settings()
    channel_id = settings_data.get("channel_id", "❌ Не указан")
    chat_id = settings_data.get("chat_id", "❌ Не указан")
    channel_link = settings_data.get("channel_invite_link") or "https://t.me/"
    chat_link = settings_data.get("chat_invite_link") or "https://t.me/"

    text = (
        f"<b>📊 Панель администратора</b>\n\n"
        f"<b>📡 Канал:</b> <code>{channel_id}</code>\n"
        f"<a href='{channel_link}'>🔹 Перейти в канал</a>\n\n"
        f"<b>💬 Чат:</b> <code>{chat_id}</code>\n"
        f"<a href='{chat_link}'>🔸 Перейти в чат</a>\n\n"
        "Выберите действие:"
    )


    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [
            InlineKeyboardButton(text="✏️ Редактировать ID канала", callback_data="edit_channel_id"),
            InlineKeyboardButton(text="✏️ Редактировать ID чата", callback_data="edit_chat_id")
        ],
        [
            InlineKeyboardButton(text="🔗 Сгенерировать новую ссылку", callback_data="choose_link_type")
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить ссылку на канал", callback_data="edit_channel_link"),
            InlineKeyboardButton(text="✏️ Изменить ссылку на чат", callback_data="edit_chat_link")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить материал", callback_data="add_material"),
            InlineKeyboardButton(text="🗑 Удалить материал", callback_data="delete_material")
        ],
        [
        InlineKeyboardButton(text="💎 Добавить кристаллы", callback_data="add_crystals")
        ],
        [
            InlineKeyboardButton(text="🔧 Настройка каталога", callback_data="catalog_setup")
        ]
    ])


    await message.answer(text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True)

@router.callback_query(F.data == "choose_link_type")
async def choose_link_type(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 Сгенерировать ссылку на канал", callback_data="generate_channel_link")
        ],
        [
            InlineKeyboardButton(text="🔗 Сгенерировать ссылку на чат", callback_data="generate_chat_link")
        ]
    ])
    await callback.message.answer("Выберите, для чего сгенерировать ссылку:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "generate_channel_link")
async def generate_channel_invite_link(callback: types.CallbackQuery):
    settings_data = await get_settings()
    channel_id = settings_data.get("channel_id")

    if not channel_id:
        await callback.message.answer("❌ ID канала не найден в настройках.")
        await callback.answer()
        return

    try:
        new_link = await callback.bot.create_chat_invite_link(channel_id)
        await update_settings({"channel_invite_link": new_link.invite_link})
        await callback.message.answer(f"✅ Новая ссылка на канал:\n{new_link.invite_link}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))
    except Exception as e:
        logger.error(f"Ошибка при создании ссылки на канал: {e}")
        await callback.message.answer("❌ Не удалось создать ссылку на канал.")
    await callback.answer()

@router.callback_query(F.data == "generate_chat_link")
async def generate_chat_invite_link(callback: types.CallbackQuery):
    settings_data = await get_settings()
    chat_id = settings_data.get("chat_id")

    if not chat_id:
        await callback.message.answer("❌ ID чата не найден в настройках.")
        await callback.answer()
        return

    try:
        new_link = await callback.bot.create_chat_invite_link(chat_id)
        await update_settings({"chat_invite_link": new_link.invite_link})
        await callback.message.answer(f"✅ Новая ссылка на чат:\n{new_link.invite_link}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))
    except Exception as e:
        logger.error(f"Ошибка при создании ссылки на чат: {e}")
        await callback.message.answer("❌ Не удалось создать ссылку на чат.")
    await callback.answer()

@router.callback_query(F.data == "add_material")
async def start_add_material(callback: types.CallbackQuery, state: FSMContext):
    categories = await get_all_categories()

    keyboard = InlineKeyboardBuilder()
    for cat in categories:
        keyboard.button(text=cat.get("name", cat.get("category_id", "Без названия")), callback_data=f"catmat_{cat['category_id']}")
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")    
    keyboard.adjust(1)
    await callback.message.answer("Выберите категорию:", reply_markup=keyboard.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("catmat_"))
async def choose_category(callback: types.CallbackQuery, state: FSMContext):
    category_id = callback.data.replace("catmat_", "")
    categories = await get_all_categories()
    category = next((c for c in categories if c["category_id"] == category_id), None)

    if not category or not category.get("sections"):
        await callback.message.answer(
            "❌ В этой категории нет разделов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Назад", callback_data="delete_material")]
            ])
        )
        return

    await state.update_data(category_id=category_id, category_name=category["name"])

    sections = category["sections"]
    keyboard = InlineKeyboardBuilder()
    for sec in sections:
        keyboard.button(text=sec["name"], callback_data=f"sec_{sec['section_id']}")
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")    
    keyboard.adjust(1)
    await callback.message.answer("Выберите раздел:", reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("sec_"))
async def choose_section(callback: types.CallbackQuery, state: FSMContext):
    section_id = callback.data.replace("sec_", "")
    data = await state.get_data()
    category_id = data.get("category_id")

    categories = await get_all_categories()
    category = next((c for c in categories if c["category_id"] == category_id), None)
    if not category:
        await callback.message.answer("❌ Категория не найдена.")
        return

    section = next((s for s in category["sections"] if s["section_id"] == section_id), None)
    if not section:
        await callback.message.answer("❌ Раздел не найден.")
        return

    await state.update_data(section_id=section_id, section_name=section["name"])
    await state.set_state(AdminStates.waiting_for_material_name)
    await callback.message.answer("✏️ Введите название материала:")
    await callback.answer()


@router.message(AdminStates.waiting_for_material_name)
async def material_name_step(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.waiting_for_material_description)
    await message.answer("📝 Введите описание материала:")


@router.message(AdminStates.waiting_for_material_description)
async def material_description_step(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AdminStates.waiting_for_material_price)
    await message.answer("💎 Введите цену за просмотр материала (в кристаллах):")

@router.message(AdminStates.waiting_for_material_price)
async def material_price_step(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную цену (целое число ≥ 0):")
        return
    await state.update_data(price=price)
    await message.answer(
        "📎 Отправьте файл или нажмите кнопку 'Пропустить файл':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить файл", callback_data="skip_file")]
        ])
    )

    await state.set_state(AdminStates.waiting_for_material_file)

@router.message(AdminStates.waiting_for_material_file)
async def material_file_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.document.file_id if message.document else None
    await add_material(
        category_id=data["category_id"],
        section_id=data["section_id"],
        name=data["name"],
        description=data["description"],
        price=data['price'],
        file_id=file_id
    )
    await state.clear()    
    await message.answer(
        "✅ Материал успешно добавлен!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Назад", callback_data="add_material")]
    ])
)


@router.callback_query(F.data == "skip_file")
async def skip_file_step(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await add_material(
        category_id=data["category_id"],
        section_id=data["section_id"],
        name=data["name"],
        description=data["description"],
        price=data['price'],
        file_id=None
    )
    await state.clear()
    await callback.message.edit_text(
        "✅ Материал добавлен без файла!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="add_material")]
        ])
    )
    await callback.answer()



    await state.set_state(AdminStates.viewing_materials)
    await state.update_data(material_index=0)
    await show_material(callback.message, materials[0], 0, len(materials))
    await state.update_data(materials=materials)
    await callback.answer()

    if callback.data == "delete_material":
        material = materials[index]
        await delete_material(str(material["_id"]))
        materials.pop(index)
        if not materials:
            await callback.message.answer("🗑️ Материал удалён. Больше материалов нет.")
            await state.clear()
            await callback.answer()
            return
        index = max(0, index - 1)

    elif callback.data == "next_material":
        index = (index + 1) % len(materials)
    elif callback.data == "prev_material":
        index = (index - 1) % len(materials)

    await state.update_data(material_index=index, materials=materials)
    await show_material(callback.message, materials[index], index, len(materials))
    await callback.answer()

@router.callback_query(F.data == "add_category")
async def start_add_category(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✏️ Введите название новой категории:")
    await state.set_state(AdminStates.waiting_for_category_name)
    await callback.answer()





# === Меню "🔧 Настройка каталога" ===
SECTION_CATEGORY_MAP = {}
EDIT_SECTION_MAP = {}

@router.callback_query(F.data == "catalog_setup")
async def open_catalog_settings(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить категорию", callback_data="add_category"),
            InlineKeyboardButton(text="✏️ Редактировать категорию", callback_data="edit_category"),
            InlineKeyboardButton(text="🗑 Удалить категорию", callback_data="delete_category")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить раздел", callback_data="add_section"),
            InlineKeyboardButton(text="✏️ Редактировать раздел", callback_data="edit_section"),
            InlineKeyboardButton(text="🗑 Удалить раздел", callback_data="delete_section")
        ]
    ])
    await callback.message.answer("🔧 Настройка каталога:", reply_markup=keyboard)
    await callback.answer()


# === Редактирование категории ===
@router.callback_query(F.data == "edit_category")
async def edit_category_handler(callback: types.CallbackQuery, state: FSMContext):
    from services.category_service import get_all_categories
    categories = await get_all_categories()

    if not categories:
        await callback.message.answer("❌ Нет категорий.")
        return

    keyboard = InlineKeyboardBuilder()
    for cat in categories:
        keyboard.button(text=cat.get("name", cat.get("category_id", "Без названия")), callback_data=f"editcat_{cat['category_id']}")
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")    
    keyboard.adjust(1)
    await callback.message.answer("Выберите категорию для редактирования:", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("editcat_"))
async def prompt_new_category_name(callback: types.CallbackQuery, state: FSMContext):
    category_id = callback.data.replace("editcat_", "")
    await state.update_data(edit_category_id=category_id)
    await state.set_state(AdminStates.waiting_for_category_name)
    await callback.message.answer("✏️ Введите новое название категории:")

@router.message(AdminStates.waiting_for_category_name)
async def handle_category_name_input(message: types.Message, state: FSMContext):
    from services.category_service import add_category, edit_category
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым.")
        return

    data = await state.get_data()
    edit_id = data.get("edit_category_id")

    if edit_id:
        # Режим редактирования
        await edit_category(edit_id, name)
        await message.answer(
            f"✅ Категория переименована в: {name}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
            ])
        )
    else:
        # Режим добавления новой категории
        import random
        category_id = f"cat_{random.randint(1000, 9999)}"
        await add_category({"category_id": category_id, "name": name})
        await message.answer(
            "✅ Категория добавлена!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
            ])
        )

    await state.clear()



# === Удаление категории ===
@router.callback_query(F.data == "delete_category")
async def delete_category_handler(callback: types.CallbackQuery):
    from services.category_service import get_all_categories
    categories = await get_all_categories()

    if not categories:
        await callback.message.answer("❌ Нет категорий.")
        return

    keyboard = InlineKeyboardBuilder()
    for cat in categories:
        keyboard.button(text=cat.get("name", cat.get("category_id", "Без названия")), callback_data=f"delcat_{cat['category_id']}")
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")    
    keyboard.adjust(1)
    await callback.message.answer("Выберите категорию для удаления:", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("delcat_"))
async def confirm_delete_category(callback: types.CallbackQuery):
    from services.category_service import delete_category
    category_id = callback.data.replace("delcat_", "")
    await delete_category(category_id)
    await callback.message.answer("✅ Категория удалена.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))


# === Добавление и редактирование разделов ===

@router.callback_query(F.data == "add_section")
async def show_categories_for_section(callback: types.CallbackQuery):
    from services.category_service import get_all_categories
    categories = await get_all_categories()

    keyboard = InlineKeyboardBuilder()
    for cat in categories:
        keyboard.button(text=cat.get("name", cat.get("category_id", "Без названия")), callback_data=f"sectioncat_{cat['category_id']}")
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")    
    keyboard.adjust(1)
    await callback.message.answer("Выберите категорию для раздела:", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("sectioncat_"))
async def ask_section_name(callback: types.CallbackQuery):
    category_id = callback.data.replace("sectioncat_", "")
    SECTION_CATEGORY_MAP[callback.from_user.id] = category_id
    await callback.message.answer("Введите название нового раздела:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]]))

@router.callback_query(F.data == "edit_section")
async def choose_category_to_edit_section(callback: types.CallbackQuery):
    from services.category_service import get_all_categories
    categories = await get_all_categories()

    keyboard = InlineKeyboardBuilder()
    for cat in categories:
        keyboard.button(text=cat.get("name", cat.get("category_id", "Без названия")), callback_data=f"edit_sec_cat:{cat['category_id']}")
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")   
    keyboard.adjust(1)
    await callback.message.answer("Выберите категорию с разделами:", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("edit_sec_cat:"))
async def choose_section_to_rename(callback: types.CallbackQuery):
    from services.category_service import get_all_categories
    category_id = callback.data.split("edit_sec_cat:")[1]
    categories = await get_all_categories()
    category = next((c for c in categories if c["category_id"] == category_id), None)

    if not category or not category.get("sections"):
        await callback.message.answer("❌ В этой категории нет разделов.")
        return

    keyboard = InlineKeyboardBuilder()
    for sec in category["sections"]:
        keyboard.button(text=sec["name"], callback_data=f"edit_sec:{category_id}:{sec['section_id']}")
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")    
    keyboard.adjust(1)
    await callback.message.answer("Выберите раздел для редактирования:", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("edit_sec:"))
async def prompt_new_section_name(callback: types.CallbackQuery):
    try:
        _, category_id, section_id = callback.data.split(":")
    except ValueError:
        await callback.message.answer("Ошибка данных.")
        return

    EDIT_SECTION_MAP[callback.from_user.id] = (category_id, section_id)
    await callback.message.answer("✏️ Введите новое название раздела:")

@router.message(StateFilter(default_state))
async def handle_section_related_message(message: types.Message):
    from services.category_service import add_section, edit_section
    import uuid

    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in EDIT_SECTION_MAP:
        category_id, section_id = EDIT_SECTION_MAP.pop(user_id)
        await edit_section(category_id, section_id, text)
        await message.answer(f"✅ Раздел переименован в: {text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))
        return

    if user_id in SECTION_CATEGORY_MAP:
        category_id = SECTION_CATEGORY_MAP.pop(user_id)
        section = {"name": text, "section_id": str(uuid.uuid4())}
        await add_section(category_id, section)
        await message.answer(f"✅ Раздел '{text}' добавлен.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))




# === Удаление раздела ===
@router.callback_query(F.data == "delete_section")
async def choose_category_to_delete_section(callback: types.CallbackQuery):
    from services.category_service import get_all_categories
    categories = await get_all_categories()

    if not categories:
        await callback.message.answer("❌ Нет доступных категорий.")
        return

    keyboard = InlineKeyboardBuilder()
    for cat in categories:
        keyboard.button(text=cat.get("name", cat.get("category_id", "Без названия")), callback_data=f"del_sec_cat:{cat['category_id']}")
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")    
    keyboard.adjust(1)
    await callback.message.answer("Выберите категорию с разделами:", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("del_sec_cat:"))
async def choose_section_to_delete(callback: types.CallbackQuery):
    from services.category_service import get_all_categories
    category_id = callback.data.split("del_sec_cat:")[1]
    categories = await get_all_categories()
    category = next((c for c in categories if c["category_id"] == category_id), None)

    if not category or not category.get("sections"):
        await callback.message.answer("❌ В этой категории нет разделов.")
        return

    keyboard = InlineKeyboardBuilder()
    for sec in category["sections"]:
        keyboard.button(text=f"🗑 {sec['name']}", callback_data=f"del_sec:{category_id}:{sec['section_id']}")
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")    
    keyboard.adjust(1)
    await callback.message.answer("Выберите раздел для удаления:", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("del_sec:"))
async def delete_section_confirm(callback: types.CallbackQuery):
    from services.category_service import delete_section
    try:
        _, category_id, section_id = callback.data.split(":")
    except ValueError:
        await callback.message.answer("Ошибка при удалении.")
        return

    await delete_section(category_id, section_id)
    await callback.message.answer("✅ Раздел успешно удалён.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))



# === Обновление ID канала ===
@router.callback_query(F.data == "edit_channel_id")
async def prompt_new_channel_id(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_new_channel_id)
    await callback.message.answer("✏️ Введите новый ID канала:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]]))
    await callback.answer()

@router.message(AdminStates.waiting_for_new_channel_id)
async def save_new_channel_id(message: types.Message, state: FSMContext):
    await update_settings({"channel_id": message.text.strip()})
    await state.clear()
    await message.answer(f"✅ ID канала обновлён: <code>{message.text.strip()}</code>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))

# === Обновление ID чата ===
@router.callback_query(F.data == "edit_chat_id")
async def prompt_new_chat_id(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_new_chat_id)
    await callback.message.answer("✏️ Введите новый ID чата:")
    await callback.answer()

@router.message(AdminStates.waiting_for_new_chat_id)
async def save_new_chat_id(message: types.Message, state: FSMContext):
    await update_settings({"chat_id": message.text.strip()})
    await state.clear()
    await message.answer(f"✅ ID чата обновлён: <code>{message.text.strip()}</code>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))

# === Обновление ссылки на канал ===
@router.callback_query(F.data == "edit_channel_link")
async def prompt_new_channel_link(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_new_channel_link)
    await callback.message.answer("🔗 Введите новую ссылку на канал:")
    await callback.answer()

@router.message(AdminStates.waiting_for_new_channel_link)
async def save_new_channel_link(message: types.Message, state: FSMContext):
    await update_settings({"channel_invite_link": message.text.strip()})
    await state.clear()
    await message.answer("✅ Ссылка на канал обновлена.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))

# === Обновление ссылки на чат ===
@router.callback_query(F.data == "edit_chat_link")
async def prompt_new_chat_link(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_new_chat_link)
    await callback.message.answer("🔗 Введите новую ссылку на чат:")
    await callback.answer()

@router.message(AdminStates.waiting_for_new_chat_link)
async def save_new_chat_link(message: types.Message, state: FSMContext):
    await update_settings({"chat_invite_link": message.text.strip()})
    await state.clear()
    await message.answer("✅ Ссылка на чат обновлена.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_admin')]
    ]))



from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter

# FSM-хендлеры с отладкой

@router.callback_query(F.data == "edit_channel_id")
async def start_edit_channel_id(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_new_channel_id)
    await callback.message.answer("✏️ Введите новый ID канала:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]]))
    await callback.answer()

@router.message(AdminStates.waiting_for_new_channel_id)
async def receive_new_channel_id(message: Message, state: FSMContext):

    new_id = message.text.strip()
    await update_settings({"channel_id": new_id})
    await state.clear()
    await message.answer(
    f"✅ <b>ID канала обновлён:</b> <code>{message.text.strip()}</code>",
    parse_mode="HTML"
)



# Отладочный глобальный хендлер


@router.callback_query(F.data == "back_to_admin")
async def back_inline_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("↩️ Возврат в панель администратора")
    await admin_panel(callback.message, user_id=callback.from_user.id)

@router.callback_query(F.data == "back_to_admin")
async def back_inline_handler(callback: types.CallbackQuery):
    await callback.answer()
    await admin_panel_from_callback(callback)

async def admin_panel_from_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    isadm = await is_admin(uid)
    await callback.message.answer(f"🧩 Проверка ID: {uid}")
    status = "✅ админ" if isadm else "❌ НЕ админ"
    await callback.message.answer(f"🔐 Статус: {status}")
    if not isadm:
        return await callback.message.answer("❌ У вас нет прав администратора.")

    # Панель администратора
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Настройка каталога", callback_data="catalog_settings")],
        [InlineKeyboardButton(text="✏️ Изменить ID канала", callback_data="change_channel_id")],
    ])
    await callback.message.answer("🔧 Панель администратора", reply_markup=keyboard)

# === FSM и логика удаления материала ===

class DeleteMaterialFSM(StatesGroup):
    choosing_category = State()
    choosing_section = State()
    choosing_material = State()
    confirming_deletion = State()


@router.callback_query(F.data == "delete_material")
async def start_delete_material(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    categories = await get_all_categories()
    if not categories:
        return await callback.message.answer("❌ Нет доступных категорий.", reply_markup=back_to_admin_btn())

    keyboard = InlineKeyboardBuilder()
    for cat in categories:
        keyboard.button(text=cat["name"], callback_data=f'del_cat_{cat["category_id"]}')
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")
    keyboard.adjust(1)
    await callback.message.answer("📁 Выберите категорию для удаления материала:", reply_markup=keyboard.as_markup())
    await state.set_state(DeleteMaterialFSM.choosing_category)









@router.callback_query(F.data.startswith("del_mat_"), DeleteMaterialFSM.choosing_material)
async def confirm_delete_material(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    mat_id = callback.data.split("_")[-1]
    await state.update_data(material_id=mat_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="confirm_delete_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="confirm_delete_no")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_admin")]
    ])
    await callback.message.answer("⚠️ Точно удалить материал?", reply_markup=keyboard)
    await state.set_state(DeleteMaterialFSM.confirming_deletion)


@router.callback_query(F.data == "confirm_delete_yes", DeleteMaterialFSM.confirming_deletion)
async def do_delete_material(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    from database.materials import delete_material
    data = await state.get_data()
    mat_id = data.get("material_id")
    if mat_id:
        await delete_material(mat_id)
        await callback.message.answer("✅ Материал удалён.", reply_markup=back_to_admin_btn())
    else:
        await callback.message.answer("❌ Материал не найден.", reply_markup=back_to_admin_btn())
    await state.clear()


@router.callback_query(F.data == "confirm_delete_no", DeleteMaterialFSM.confirming_deletion)
async def cancel_delete_material(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    section_id = data.get("section_id")
    category_id = data.get("category_id")
    from database.materials import get_materials_by_category_and_section
    materials = await get_materials_by_category_and_section(category_id, section_id)
    keyboard = InlineKeyboardBuilder()
    for mat in materials:
        keyboard.button(text=mat["name"], callback_data=f'del_mat_{str(mat["_id"])}')
    keyboard.button(text="↩️ Назад", callback_data="back_to_admin")
    await callback.message.answer("🗂 Выберите материал для удаления:", reply_markup=keyboard.as_markup())
    await state.set_state(DeleteMaterialFSM.choosing_material)


def back_to_admin_btn():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_admin")]])

@router.callback_query(F.data.startswith("del_cat_"), DeleteMaterialFSM.choosing_category)
async def choose_section_for_deletion(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    category_id = callback.data.replace("del_cat_", "")
    categories = await get_all_categories()
    category = next((c for c in categories if c["category_id"] == category_id), None)

    if not category or not category.get("sections"):
        return await callback.message.answer("❌ В этой категории нет разделов.", reply_markup=back_to_admin_btn())

    await state.update_data(
        category_id=category_id,
        category_name=category["name"]
    )

    keyboard = InlineKeyboardBuilder()
    for sec in category["sections"]:
        keyboard.button(text=sec["name"], callback_data=f'del_sec_{sec["section_id"]}')
    keyboard.button(text="↩️ Назад", callback_data="delete_material")
    keyboard.adjust(1)
    await callback.message.answer("📚 Выберите раздел:", reply_markup=keyboard.as_markup())
    await state.set_state(DeleteMaterialFSM.choosing_section)


@router.callback_query(DeleteMaterialFSM.choosing_section, F.data.startswith("del_sec_"))
async def choose_material_to_delete(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    section_id = callback.data.replace("del_sec_", "")
    data = await state.get_data()

    categories = await get_all_categories()
    category = next((c for c in categories if c["category_id"] == data["category_id"]), None)
    section = next((s for s in category["sections"] if s["section_id"] == section_id), None)

    if not section:
        return await callback.message.answer("❌ Раздел не найден.")

    section_name = section["name"]
    await state.update_data(section_id=section_id, section_name=section_name)
    data = await state.get_data()

    materials = await get_materials_by_category_and_section(data["category_name"], data["section_name"])


    if not materials:
        return await callback.message.answer("❌ В этом разделе нет материалов.")

    keyboard = InlineKeyboardBuilder()
    for mat in materials:
        keyboard.button(text=mat["name"], callback_data=f"del_mat_{str(mat['_id'])}")
    keyboard.button(text="↩️ Назад", callback_data=f"del_cat_{data['category_id']}")
    keyboard.adjust(1)

    await callback.message.answer("🗂 Выберите материал для удаления:", reply_markup=keyboard.as_markup())
    await state.set_state(DeleteMaterialFSM.choosing_material)

@router.callback_query(F.data == "add_crystals")
async def start_add_crystals(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID пользователя, которому хотите добавить кристаллы:")
    await state.set_state(AdminStates.waiting_for_crystal_user_id)
    await callback.answer()

@router.message(AdminStates.waiting_for_crystal_user_id)
async def get_user_id_for_crystals(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await state.update_data(target_user_id=user_id)
        await state.set_state(AdminStates.waiting_for_crystal_amount)
        await message.answer("Введите количество кристаллов для добавления:")
    except ValueError:
        await message.answer("❌ Введите корректный числовой ID пользователя.")

@router.message(AdminStates.waiting_for_crystal_amount)
async def get_crystal_amount(message: Message, state: FSMContext):
    from database.settings import get_users_collection
    data = await state.get_data()
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное целое число.")
        return

    user_id = data["target_user_id"]
    users = await get_users_collection()
    result = await users.update_one({"user_id": user_id}, {"$inc": {"crystals": amount}})

    if result.modified_count:
        await message.answer(f"✅ {amount} кристаллов добавлены пользователю с ID {user_id}.")
    else:
        await message.answer("❌ Пользователь не найден в базе.")
    await state.clear()
