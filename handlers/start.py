import random
import logging
from aiogram import Router, types, F
from aiocryptopay import AioCryptoPay, Networks






cryptopay = AioCryptoPay(
    token="105772:AAynYu5wytrQwBtKU98iLf84DLJ7bfvUVhn",  # ← сюда вставь реальный API Token (не обязательно)
    network=Networks.MAIN_NET
)

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import CallbackQuery

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from typing import Union


class FSMFillForm(StatesGroup):
    topup_amount = State()

from aiogram.filters import StateFilter
from database.settings import get_users_collection
from services.subscription_service import check_subscriptions
from database.settings import get_settings
from services.user_service import register_user, get_user
from services.user_service import decrease_limit  # Добавь, если ещё нет
from database.materials import (
    get_materials_by_category_and_section,
    add_to_favorites,
    get_favorites,
    remove_from_favorites  # Добавлен новый импорт
)
from utils.keyboards import (
    get_main_menu_keyboard,
    get_category_inline_keyboard,
    get_sections_inline_keyboard,
    get_material_navigation_keyboard,
    get_subscription_levels_keyboard
)
from utils.sections import get_category_list, get_sections_by_category  # исправленный импорт

router = Router()

def format_material_name(name: str, price: int, max_len: int = 35) -> str:
    cropped = name if len(name) <= max_len else name[:max_len - 3] + "..."
    return f"{cropped} \U0001F48E {price}"

def build_materials_list_keyboard(materials: list) -> InlineKeyboardMarkup:
    keyboard = []
    for material in materials:
        button_text = format_material_name(material.get("name", "Без названия"), material.get("price", 0))
        callback_data = f"open_material:{str(material['_id'])}"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    # Добавляем кнопку "Назад к разделам"
    keyboard.append([InlineKeyboardButton(text="↩️ Назад к разделам", callback_data="back_to_section")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)



logger = logging.getLogger(__name__)

# --- Состояния FSM пользователя ---
class UserStates(StatesGroup):
    waiting_for_captcha = State()
    waiting_for_category = State()
    waiting_for_section = State()

class ViewMaterial(StatesGroup):
    viewing = State()
    viewing_favorites = State()

# Генерация клавиатуры подписки
async def generate_subscription_keyboard(settings_data, missing_subs):
    builder = InlineKeyboardBuilder()
    
    if "channel" in missing_subs and settings_data.get("channel_invite_link"):
        builder.button(text="📢 Наш канал", url=settings_data["channel_invite_link"])
    
    if "chat" in missing_subs and settings_data.get("chat_invite_link"):
        builder.button(text="💬 Наш чат", url=settings_data["chat_invite_link"])
    
    builder.button(text="✅ Проверить подписку", callback_data="check_subscriptions")
    
    builder.adjust(2, 1)
    return builder.as_markup()

# /start
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    try:
        await state.clear()

        user = await get_user(message.from_user.id)

        if user:
            await message.answer(
                f"👋 Привет снова, {message.from_user.first_name}!",
                reply_markup=get_main_menu_keyboard()
            )
            return

        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        correct_answer = num1 + num2

        await state.update_data(captcha_answer=str(correct_answer))

        options = [correct_answer, random.randint(2, 20), random.randint(2, 20)]
        random.shuffle(options)

        keyboard = InlineKeyboardBuilder()
        for option in options:
            keyboard.button(text=str(option), callback_data=f"captcha:{option}")
        keyboard.adjust(3)

        await message.answer(
            f"🛡 Для входа реши пример:\n\n<b>{num1} + {num2} = ?</b>",
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(UserStates.waiting_for_captcha)

    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await message.answer("⚠️ Ошибка при запуске.")

# Обработка капчи
@router.callback_query(UserStates.waiting_for_captcha, F.data.startswith("captcha:"))
async def captcha_check(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("captcha_answer")
    user_answer = callback.data.split(":")[1]

    if user_answer == correct_answer:
        await state.clear()

        settings_data = await get_settings()
        subscription_status = await check_subscriptions(callback.from_user.id)

        if subscription_status["subscribed"]:
            await register_user(callback.from_user)

            await callback.message.answer(
                "✅ Добро пожаловать!",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.message.delete()
        else:
            keyboard = await generate_subscription_keyboard(settings_data, subscription_status["missing"])
            await callback.message.edit_text(
                "📢 Для доступа к боту подпишитесь на канал и чат:",
                reply_markup=keyboard
            )
        await callback.answer()
    else:
        await callback.answer("❌ Неправильный ответ! Попробуй ещё раз.", show_alert=True)

# Проверка подписки кнопкой
@router.callback_query(F.data == "check_subscriptions")
async def check_subs_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        settings_data = await get_settings()
        subscription_status = await check_subscriptions(callback.from_user.id)

        if subscription_status["subscribed"]:
            users_collection = await get_users_collection()
            user = await users_collection.find_one({"user_id": callback.from_user.id})

            if not user:
                # Если пользователь ещё не зарегистрирован — регистрируем
                await register_user(callback.from_user)
                users_collection = await get_users_collection()
                user = await users_collection.find_one({"user_id": callback.from_user.id})

            # Проверка: получал ли пользователь тестовые кристаллы
            if not user.get("got_test_crystals"):
                await users_collection.update_one(
                    {"user_id": callback.from_user.id},
                    {
                        "$set": {"got_test_crystals": True},
                        "$inc": {"crystals": 50}
                    }
                )

            await callback.message.answer(
                "✅ Подписка проверена!\nВам начислено 50 тестовых кристаллов 💎",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.message.delete()

        else:
            keyboard = await generate_subscription_keyboard(settings_data, subscription_status["missing"])
            await callback.answer("❌ Вы ещё не подписались!", show_alert=True)
            await callback.message.edit_reply_markup(reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in check subscription: {e}")
        await callback.answer("⚠️ Ошибка проверки подписки", show_alert=True)


# --- Пользователь нажал "📚 Категории" ---
@router.message(F.text == "📚 Категории")
async def categories_handler(message: types.Message, state: FSMContext):
    subscription_status = await check_subscriptions(message.from_user.id)

    if not subscription_status["subscribed"]:
        settings_data = await get_settings()
        keyboard = await generate_subscription_keyboard(settings_data, subscription_status["missing"])
        await message.answer(
            "📢 Для доступа к категориям подпишитесь на:\n\n"
            "• Наш канал и чат!",
            reply_markup=keyboard
        )
        return

    keyboard = await get_category_inline_keyboard()
    await message.answer(
        "📚 Выберите категорию:",
        reply_markup=keyboard
    )
    await state.set_state(UserStates.waiting_for_category)

# --- Пользователь выбрал категорию ---
@router.callback_query(F.data.startswith("select_category:"))
async def user_category_chosen(callback: types.CallbackQuery, state: FSMContext):
    category_id = callback.data.split(":")[1]
    await state.update_data(category_id=category_id)
    keyboard = await get_sections_inline_keyboard(category_id)
    await callback.message.edit_text(
        "📂 Теперь выберите раздел:",
        reply_markup=keyboard
    )
    await state.set_state(UserStates.waiting_for_section)
    await callback.answer()

# --- Пользователь выбрал раздел ---
@router.callback_query(F.data.startswith("select_section:"))
async def user_section_chosen(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    category_id = parts[1]
    section_id = parts[2]

    categories = await get_category_list()
    category = next((c["name"] for c in categories if c["category_id"] == category_id), None)

    sections = await get_sections_by_category(category_id)
    section = next((s["name"] for s in sections if s["section_id"] == section_id), None)

    if not category or not section:
        await callback.message.edit_text("❌ Ошибка выбора категории или раздела.")
        await state.clear()
        return

    materials = await get_materials_by_category_and_section(category, section)

    if not materials:
        await callback.message.edit_text("❌ В этом разделе пока нет материалов.")
        await state.clear()
        return

    keyboard = build_materials_list_keyboard(materials)
    await state.update_data(category_id=category_id, section_id=section_id)
    await callback.message.edit_text("📚 Выберите материал:", reply_markup=keyboard)
    await callback.answer()



# --- Отправка материала пользователю ---
async def send_current_material(message, materials, index, state: FSMContext, user_id: int):
    from services.user_service import get_user, decrease_limit

    material = materials[index]
    current_state = await state.get_state()
    is_favorites = current_state == ViewMaterial.viewing_favorites.state

    if not is_favorites:
        user = await get_user(user_id)
        if not user:
            await message.answer("⚠️ Не удалось получить данные пользователя.")
            return

        price = material.get("price", 0)
        if user.get("crystals", 0) < price:
            await message.answer(
    f"❌ Недостаточно кристаллов. У вас: {user.get('crystals', 0)}, нужно: {price}",
    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить", callback_data="open_profile")]
    ])

)
            return

        await decrease_limit(user_id, price)

    await state.update_data(prev_state=current_state)
    await state.set_state(ViewMaterial.viewing_favorites if is_favorites else ViewMaterial.viewing)

    text = f"📚 <b>{material['name']}</b>\n\n📝 {material['description']}"
    keyboard = get_material_navigation_keyboard(
        current_index=index,
        total=len(materials),
        has_file=bool(material.get("file_id")),
        is_favorites=is_favorites
    )

    if material.get("file_id"):
        await message.answer_document(
            material['file_id'],
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard,
            protect_content=True
        )
    else:
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
            protect_content=True
        )



# --- Обработка навигации по материалам (для обоих состояний) ---
@router.callback_query(F.data.in_(["next_material", "prev_material", "add_to_favorites"]))
async def navigate_materials(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    # Получаем текущее состояние
    current_state = await state.get_state()
    
    # Проверяем, что мы в одном из допустимых состояний просмотра
    if current_state not in [ViewMaterial.viewing.state, ViewMaterial.viewing_favorites.state]:
        await callback.answer("❌ Ошибка: некорректное состояние")
        return
    
    # Проверка лимита только для обычного просмотра (не для избранного)
    
    materials = data.get("materials", [])
    current_index = data.get("current_index", 0)
    new_index = current_index
    if callback.data == "next_material" and current_index < len(materials) - 1:
        new_index += 1
    elif callback.data == "prev_material" and current_index > 0:
        new_index -= 1
    price = materials[new_index].get("price", 0)
    
    # Получаем данные из состояния
    data = await state.get_data()
    
    # Обрабатываем различные действия
    if callback.data == "next_material" and current_index < len(materials) - 1:
        current_index += 1
    elif callback.data == "prev_material" and current_index > 0:
        current_index -= 1
    elif callback.data == "add_to_favorites":
        # Добавляем в избранное (только если не находимся в избранном)
        if current_state != ViewMaterial.viewing_favorites.state:
            await add_to_favorites(callback.from_user.id, materials[current_index])
            await callback.answer("⭐ Материал добавлен в избранное")
            return
        else:
            await callback.answer("⚠️ Этот материал уже в избранном")
            return
    
    # Обновляем индекс в состоянии
    await state.update_data(current_index=current_index)
    
    # Отправляем текущий материал
    await send_current_material(callback.message, materials, current_index, state, user_id=callback.from_user.id)
    await callback.answer()

# --- Просмотр Избранного ---
@router.message(F.text == "⭐ Избранное")
async def show_favorites(message: types.Message, state: FSMContext):
    # Получаем избранные материалы пользователя
    favorites = await get_favorites(message.from_user.id)

    if not favorites:
        await message.answer("⭐ У вас пока нет избранных материалов.")
        return

    # ВАЖНО: явно устанавливаем состояние просмотра избранного
    await state.set_state(ViewMaterial.viewing_favorites)
    
    # Сохраняем список материалов и начальный индекс
    await state.update_data(materials=favorites, current_index=0)
    
    # Отправляем первый материал
    await send_current_material(message, favorites, 0, state, user_id=message.from_user.id)


    
@router.callback_query(F.data.startswith("buy_sub:"))
async def buy_subscription_handler(callback: types.CallbackQuery):
    """
    Обработчик кнопки покупки подписки через CryptoBot
    """
    try:
        user_id = callback.from_user.id
        level = int(callback.data.split(":")[1])
        
        # Проверяем, что уровень подписки корректный
        if level not in [1, 2, 3]:
            await callback.answer("❌ Неверный уровень подписки", show_alert=True)
            return
        
        # Создаем счет для оплаты через CryptoBot
        from payments.payment_service import create_payment_invoice
        invoice_data = await create_payment_invoice(user_id, level)
        
        # Получаем названия уровней подписки из настроек
        from config import settings
        level_name = settings.SUBSCRIPTION_LEVELS_NAMES.get(level, f"Уровень {level}")
        
        # Создаем клавиатуру с кнопкой оплаты
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить через CryptoBot", url=invoice_data["payment_url"])],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_subscription")]
        ])
        
        # Отправляем сообщение с информацией о подписке
        await callback.message.answer(
            f"🔐 <b>Подписка '{level_name}'</b>\n\n"
            f"💰 Сумма: {invoice_data['amount']} USD\n\n"
            f"• После оплаты подписка активируется автоматически\n"
            f"• Подписка действует 30 дней\n",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при создании счета: {e}")
        await callback.message.answer("❌ Ошибка при создании счета. Попробуйте позже.")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

# Обработчик для возврата к меню подписки
@router.callback_query(F.data == "back_to_subscription")
async def back_to_subscription_handler(callback: types.CallbackQuery):
    """
    Обработчик кнопки возврата к меню подписки
    """
    await show_subscription_status(callback.message)
    await callback.answer()
    

async def create_invoice(user_id: int, amount: float, level: int) -> str:
    invoice = await cryptopay.create_invoice(
        asset="USDT",
        amount=amount,
        description=f"Подписка {level} уровня для {user_id}",
        hidden_message=f"{user_id}:{level}"
    )
    return invoice.bot_invoice_url  # ← ВАЖНО: используем публичный URL



@router.callback_query(F.data.startswith("buy_sub:"))
async def buy_subscription_handler(callback: types.CallbackQuery):
    """
    Обработчик кнопки покупки подписки через CryptoBot
    """
    try:
        user_id = callback.from_user.id
        level = int(callback.data.split(":")[1])
        
        # Проверяем, что уровень подписки корректный
        if level not in [1, 2, 3]:
            await callback.answer("❌ Неверный уровень подписки", show_alert=True)
            return
        
        # Получаем URL для вебхука из payment_service
        from payments.payment_service import cryptobot_webhook_url, create_payment_invoice
        
        # Создаем счет, передавая URL для вебхука
        invoice_data = await create_payment_invoice(
            user_id=user_id, 
            level=level,
            callback_url=cryptobot_webhook_url  # Передаем URL для вебхука
        )
        
        # Получаем названия уровней подписки из настроек
        from config import settings
        level_name = settings.SUBSCRIPTION_LEVELS_NAMES.get(level, f"Уровень {level}")
        
        # Создаем клавиатуру с кнопкой оплаты
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить через CryptoBot", url=invoice_data["payment_url"])],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_payment:{invoice_data['invoice_id']}")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_subscription")]
        ])
        
        # Отправляем сообщение с информацией о подписке
        await callback.message.answer(
            f"🔐 <b>Подписка '{level_name}'</b>\n\n"
            f"💰 Сумма: {invoice_data['amount']} USDT\n\n"
            f"• После оплаты подписка активируется автоматически\n"
            f"• Если этого не произошло, нажмите кнопку 'Проверить оплату'\n"
            f"• Подписка действует бессрочно\n",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при создании счета: {e}")
        await callback.message.answer("❌ Ошибка при создании счета. Попробуйте позже.")
        await callback.answer("❌ Произошла ошибка", show_alert=True)




@router.callback_query(F.data == "back_to_section")
async def back_to_section(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category_id = data.get("category_id")
    section_id = data.get("section_id")

    if not category_id or not section_id:
        await callback.message.answer("❌ Не удалось восстановить раздел.")
        await state.clear()
        return

    categories = await get_category_list()
    category = next((c["name"] for c in categories if c["category_id"] == category_id), None)

    sections = await get_sections_by_category(category_id)
    section = next((s["name"] for s in sections if s["section_id"] == section_id), None)

    if not category or not section:
        await callback.message.answer("❌ Раздел не найден.")
        await state.clear()
        return

    materials = await get_materials_by_category_and_section(category, section)
    if not materials:
        await callback.message.answer("❌ В этом разделе пока нет материалов.")
        await state.clear()
        return
    
    # Возвращаемся к выбору разделов в текущей категории
    keyboard = await get_sections_inline_keyboard(category_id)
    await callback.message.edit_text(
        f"📂 Раздел: {section} (категория: {category})",
        reply_markup=keyboard
    )
    await state.set_state(UserStates.waiting_for_section)
    await callback.answer("↩️ Вернулись к разделу")


@router.callback_query(F.data.startswith("back_to_category:"))
async def back_to_category_user(callback: types.CallbackQuery, state: FSMContext):
    category_id = callback.data.split(":")[1]
    await state.update_data(category_id=category_id)

    keyboard = await get_sections_inline_keyboard(category_id)
    await callback.message.edit_text(
        "📂 Теперь выберите раздел:",
        reply_markup=keyboard
    )
    await state.set_state(UserStates.waiting_for_section)
    await callback.answer()



@router.callback_query(F.data == "go_back")
async def go_back(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_state = data.get("prev_state")

    if prev_state:
        await state.set_state(prev_state)
        await callback.message.answer("↩️ Вы вернулись назад.")
    else:
        await callback.message.answer("🚫 Некуда возвращаться.")

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик для возврата из разделов к списку категорий"""
    # Получаем клавиатуру со списком категорий
    keyboard = await get_category_inline_keyboard()
    
    # Изменяем текущее сообщение, показывая список категорий
    await callback.message.edit_text(
        "📚 Выберите категорию:",
        reply_markup=keyboard
    )
    
    # Устанавливаем состояние ожидания выбора категории
    await state.set_state(UserStates.waiting_for_category)
    
    # Показываем всплывающее уведомление
    await callback.answer("↩️ Вернулись к категориям")
    
# --- Обработчик удаления из избранного ---
@router.callback_query(F.data == "remove_from_favorites")
async def remove_from_favorites_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик для удаления материала из избранного"""
    data = await state.get_data()
    materials = data.get("materials", [])
    current_index = data.get("current_index", 0)
    
    if not materials or current_index >= len(materials):
        await callback.answer("❌ Ошибка: материал не найден")
        return
    
    # Получаем текущий материал
    material = materials[current_index]
    
    # Удаляем из базы данных
    # Важно: material должен иметь поле _id или id для идентификации в БД
    material_id = str(material.get("_id", material.get("id", "")))
    if not material_id:
        await callback.answer("❌ Ошибка: не удалось определить ID материала")
        return
        
    success = await remove_from_favorites(callback.from_user.id, material_id)
    
    if not success:
        await callback.answer("❌ Ошибка при удалении из избранного")
        return
    
    # Удаляем материал из локального списка
    materials.pop(current_index)
    
    # Обновляем индекс, если нужно
    if not materials:
        # Если больше нет материалов, возвращаемся в главное меню
        await callback.message.answer(
            "⭐ В избранном больше нет материалов",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        await callback.answer("✅ Материал удален из избранного")
        return
    
    # Корректируем индекс, если удалили последний элемент
    if current_index >= len(materials):
        current_index = len(materials) - 1
        
    # Обновляем данные состояния
    await state.update_data(materials=materials, current_index=current_index)
    
    # Отправляем следующий материал
    await send_current_material(callback.message, materials, current_index, state, user_id=callback.from_user.id)
    await callback.answer("✅ Материал удален из избранного")
    

# Обработчик для возврата к меню подписки
@router.callback_query(F.data == "back_to_subscription")
async def back_to_subscription_handler(callback: types.CallbackQuery):
    """
    Обработчик кнопки возврата к меню подписки
    """
    await show_subscription_status(callback.message)
    await callback.answer()


# --- Состояние ожидания суммы пополнения ---
class ProfileStates(StatesGroup):
    waiting_for_topup_amount = State()

# Обработчик кнопки "👤 Профиль"
@router.message(F.text == "👤 Профиль")
@router.callback_query(F.data == "open_profile")
async def show_profile(message_or_callback: Union[Message, CallbackQuery], state: FSMContext):
    user_id = message_or_callback.from_user.id
    user = await get_user(user_id)
    crystals = user.get("crystals", 0)

    text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"💎 Баланс: <b>{crystals}</b> кристаллов\n\n"
        "💰 <b>Прайс на пополнение:</b>\n"
        "▪️ 1 $ → 50 💎\n"
        "▪️ 5 $ → 300 💎\n"
        "▪️ 10 $ → 650 💎\n"
        "▪️ >10 $ → 75 💎 за $ (бонус 15%)"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="topup_crystals")]
    ])

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_callback.message.answer(text, reply_markup=kb, parse_mode="HTML")



# Кнопка "Пополнить баланс"
@router.callback_query(F.data == "topup_crystals")
async def prompt_topup(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_topup_amount)
    await callback.message.answer("Введите сумму пополнения в $ (например, 5):")
    await callback.answer()


@router.message(StateFilter(FSMFillForm.topup_amount))
async def process_topup_amount(message: Message, state: FSMContext):
    try:
        usd_amount = float(message.text.strip().replace(",", "."))
        if usd_amount < 1:
            await message.answer("Минимальная сумма пополнения — $1. Введите сумму ещё раз:")
            return

        invoice = await create_crystal_invoice(user_id=message.from_user.id, usd_amount=usd_amount)

        await message.answer(
            text=f"💳 Счёт на сумму ${usd_amount:.2f} создан!\n\nОплатите по ссылке: {invoice.pay_url}",
            reply_markup=menu_reply)
        await state.clear()

    except ValueError:
        await message.answer("Введите корректную сумму в долларах. Например: 5")
    except Exception as e:
        logging.exception("Ошибка при создании счёта")
        await message.answer("Произошла ошибка при создании счёта. Попробуйте позже.")


# Приём суммы пополнения
@router.message(ProfileStates.waiting_for_topup_amount)
async def process_topup_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError

        # Получаем user_id
        user_id = message.from_user.id

        # Создаём инвойс
        invoice = await cryptopay.create_invoice(
            asset="USDT",  # или "TON", "BTC", если используете другую валюту
            amount=amount,
            description=f"Пополнение баланса пользователем {user_id}",
            hidden_message="Спасибо за оплату! Кристаллы будут зачислены автоматически.",
            payload=str(user_id)  # можно использовать как идентификатор при webhook-обработке
        )

        await message.answer(
            f"✅ Счёт создан на сумму {amount} USDT\n"
            f"💳 Оплатите по ссылке:\n{invoice.bot_invoice_url}"
        )

        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректную сумму в числовом формате.")


@router.callback_query(F.data.startswith("open_material:"))
async def open_material_by_id(callback: CallbackQuery, state: FSMContext):
    from database.materials import get_materials_by_category_and_section

    material_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    category_id = data.get("category_id")
    section_id = data.get("section_id")

    # получаем имена
    categories = await get_category_list()
    sections = await get_sections_by_category(category_id)
    category = next((c["name"] for c in categories if c["category_id"] == category_id), None)
    section = next((s["name"] for s in sections if s["section_id"] == section_id), None)

    if not category or not section:
        await callback.message.answer("⚠️ Ошибка: раздел не найден.")
        return

    materials = await get_materials_by_category_and_section(category, section)

    for i, mat in enumerate(materials):
        if str(mat['_id']) == material_id:
            await state.update_data(materials=materials, current_index=i)
            await send_current_material(callback.message, materials, i, state, user_id=callback.from_user.id)
            return

    await callback.message.answer("❌ Материал не найден.")


@router.callback_query(F.data == "open_profile")
async def open_profile_handler(callback: CallbackQuery, state: FSMContext):
    await show_profile(callback, state)
    await callback.answer()
