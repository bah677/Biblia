from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict

def create_more_keyboard(buttons: List[Dict]) -> InlineKeyboardMarkup:
    """
    Создает INLINE клавиатуру для команды /more на основе данных из базы
    """
    builder = InlineKeyboardBuilder()
    
    for button in buttons:
        # 🔥 ИСПРАВЛЕНИЕ: Используем ID кнопки вместо команды
        button_id = button.get('id')
        builder.add(InlineKeyboardButton(
            text=button['button_text'],
            callback_data=f"more_button_{button_id}"  # <-- ИСПРАВЛЕНО
        ))
    
    # Делаем клавиатуру адаптивной (2 кнопки в ряду)
    builder.adjust(2)
    
    return builder.as_markup()

def create_support_topics_keyboard(topics: List[Dict]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с темами поддержки
    """
    builder = InlineKeyboardBuilder()
    
    for topic in topics:
        builder.add(InlineKeyboardButton(
            text=f"{topic['emoji']} {topic['button_text']}",
            callback_data=f"support_topic_{topic['id']}"
        ))
    
    builder.adjust(1)  # По одной кнопке в ряду
    
    return builder.as_markup()

def create_my_tickets_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для команды /mytickets
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Создать новое обращение", callback_data="support_new")],
        [InlineKeyboardButton(text="🔄 Обновить список", callback_data="mytickets_refresh")]
    ])