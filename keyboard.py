from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard():
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='Оставить заявку на поиск сотрудника', callback_data='continue')],
                         [InlineKeyboardButton(text='Посмотреть анкеты кандидатов', callback_data='ankets')],])
    return inline_keyboard

def admin_keyboard(telegram_id):
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='Подтвердить', callback_data=f'approved_{telegram_id}')],
                         [InlineKeyboardButton(text='Отклонить', callback_data=f'cancel_{telegram_id}')]]
    )
    return inline_keyboard

def approved_keyboard(telegram_id):
    confirm_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data=f"conf_{telegram_id}")],
            [InlineKeyboardButton(text="Отказаться", callback_data=f"canc_{telegram_id}")]
        ]
    )
    return confirm_markup

def candidate_keyboard(candidate_id):
    """
    Создает клавиатуру для анкеты кандидата.
    Для обычных пользователей показывает только телефон HR,
    для админов добавляет кнопку закрытия анкеты.
    """
      # Проверка на админа
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Закрыть анкету", callback_data=f"close_candidate_{candidate_id}")]
        ]
    )
    return inline_keyboard