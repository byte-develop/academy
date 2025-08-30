from aiogram.fsm.state import StatesGroup, State

class AdminStates(StatesGroup):
    # Категории
    waiting_for_new_category_name = State()
    waiting_for_renamed_category_name = State()
    waiting_for_category_to_delete = State()

    # Разделы
    waiting_for_new_section_name = State()
    waiting_for_renamed_section_name = State()
    waiting_for_section_to_delete = State()

    # Материалы
    choosing_category = State()
    choosing_section = State()
    waiting_for_material_name = State()
    waiting_for_material_description = State()
    waiting_for_material_file = State()

    # Настройки канала / чата
    waiting_for_channel_id = State()
    waiting_for_chat_id = State()
    waiting_for_new_link = State()


class UserStates(StatesGroup):
    waiting_for_section = State()
    viewing_material = State()