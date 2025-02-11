from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard():
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='Продолжить', callback_data='continue')]])
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