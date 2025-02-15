import re
from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from keyboard import start_keyboard, admin_keyboard, approved_keyboard, admin_menu_keyboard
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from database import add_user, get_db, get_position_by_telegram_id, update_user_status, get_all_users

router = Router()
ADMIN_ID = [947159905, 5584822662]


@router.message(Command(commands=['start']))
async def start_command(message: Message):
    if message.from_user.id in ADMIN_ID:
        await message.answer("Добро пожаловать, администратор!", reply_markup=admin_menu_keyboard())
    else:
        await message.answer(
            'Приветствуем в нашем проекте по поиску, обучению и тестированию новых сотрудников!\n\n'
            'Для составления заявки нажмите *«Продолжить»*',
            reply_markup=start_keyboard(),
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "admin_keyboard")
async def list_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_ID:
        return

    # Получаем сессию базы данных
    async for db_session in get_db():
        users = await get_all_users(db_session)  # Передаем сессию в функцию `get_all_users`

        # Если пользователей нет
        if not users:
            await callback.message.answer("Нет зарегистрированных пользователей.")
            return

        # Формируем список пользователей
        user_list = "\n".join(
            [f"📌 *ФИО:* {user[0]}, *Позиция:* {user[1]}, *Статус:* {user[2]}" for user in users]
        )

        # Отправляем список
        await callback.message.answer(f"📋 Список зарегистрированных пользователей:\n\n{user_list}", parse_mode="Markdown")


class RequestForm(StatesGroup):
    name = State()
    position = State()
    contact_number = State()
    contact_email = State()
    contact_person = State()


@router.callback_query(F.data == 'continue')
async def start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer('Введите *название вашей компании* (имя клиента):', parse_mode="Markdown")
    await state.set_state(RequestForm.name)


@router.message(StateFilter(RequestForm.name))
async def position(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('Введите *позицию*, на которую ищете кандидата:', parse_mode="Markdown")
    await state.set_state(RequestForm.position)


@router.message(StateFilter(RequestForm.position))
async def contact_number(message: Message, state: FSMContext):
    await state.update_data(position=message.text)
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Поделиться номером", request_contact=True)]],
                                   resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Введите *контактный номер* или нажмите 'Поделиться номером'.", reply_markup=keyboard,
                         parse_mode="Markdown")
    await state.set_state(RequestForm.contact_number)


@router.message(StateFilter(RequestForm.contact_number))
async def contact_email(message: Message, state: FSMContext):
    if message.contact:
        contact_number = message.contact.phone_number
    else:
        contact_number = message.text

    if not re.match(r'^(\+7|8)\d{10}$', contact_number):
        await message.answer(
            "Некорректный номер телефона. Пожалуйста, введите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX.")
        return

    await state.update_data(contact_number=contact_number)
    await message.answer("Введите *контактную почту*:", parse_mode="Markdown")
    await state.set_state(RequestForm.contact_email)


@router.message(StateFilter(RequestForm.contact_email))
async def contact_person(message: Message, state: FSMContext):
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', message.text):
        await message.answer("Некорректный email. Пожалуйста, введите email в формате example@example.com.")
        return
    await state.update_data(contact_email=message.text)

    await message.answer("Введите *контактное лицо*:", parse_mode="Markdown")
    await state.set_state(RequestForm.contact_person)


@router.message(StateFilter(RequestForm.contact_person))
async def confirm_request(message: Message, state: FSMContext, bot):
    await state.update_data(contact_person=message.text)
    user_data = await state.get_data()

    async for db_session in get_db():
        await add_user(db_session, {
            'telegram_id': message.from_user.id,
            'name': user_data['name'],
            'position': user_data['position'],
            'contact_number': user_data['contact_number'],
            'contact_email': user_data['contact_email'],
            'contact_person': user_data['contact_person'],
            'status': "pending"
        })

    await message.answer(
        f"✅ *Ваша заявка принята:*\n\n"
        f"📌 *Компания:* {user_data['name']}\n"
        f"📌 *Позиция искомого кандидата:* {user_data['position']}\n"
        f"📌 *Контактный номер:* {user_data['contact_number']}\n"
        f"📌 *Почта:* {user_data['contact_email']}\n"
        f"📌 *Контактное лицо:* {user_data['contact_person']}\n\n"
        "Мы с вами свяжемся!", parse_mode="Markdown")
    for admin in ADMIN_ID:
        await message.bot.send_message(chat_id=admin, text=
        f"✅ *Поступила заявка от {message.from_user.full_name}:*\n\n"
        f"📌 *Компания:* {user_data['name']}\n"
        f"📌 *Позиция искомого кандидата:* {user_data['position']}\n"
        f"📌 *Контактный номер:* {user_data['contact_number']}\n"
        f"📌 *Почта:* {user_data['contact_email']}\n"
        f"📌 *Контактное лицо:* {user_data['contact_person']}\n\n"
                                       , parse_mode="Markdown",
                                       reply_markup=admin_keyboard(message.from_user.id))


class ApprovedRequestForm(StatesGroup):
    date = State()
    price = State()


@router.callback_query(F.data.startswith('approved_'))
async def approved(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.data.split('_')[1]
    await state.update_data(telegram_id=telegram_id)
    await callback.message.answer("Введите *срок оказания услуг*:", parse_mode="Markdown")
    await state.set_state(ApprovedRequestForm.date)


@router.message(StateFilter(ApprovedRequestForm.date))
async def service_cost(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await message.answer("Введите *стоимость оказываемых услуг*:", parse_mode="Markdown")
    await state.set_state(ApprovedRequestForm.price)


@router.message(StateFilter(ApprovedRequestForm.price))
async def send_confirmation(message: Message, state: FSMContext):
    user_data = await state.get_data()

    telegram_id = user_data['telegram_id']
    async for db_session in get_db():
        position = await get_position_by_telegram_id(db_session, telegram_id)
        await update_user_status(db_session, telegram_id, 'approved_admin')
    service_date = user_data['date']
    service_price = message.text

    confirmation_message = (
        f"Уважаемые коллеги! Благодарим за обращение в ООО АГРОКОР за поиском и обучением кандидата на должность "
        f"*{position}*.\n\n"
        f"📌 Сообщаем, что кандидат будет найден и обучен в срок до *{service_date}*.\n"
        f"📌 Стоимость оказываемой услуги составит *{service_price}* рублей.\n\n"
        "Для подтверждения, нажмите *«Подтвердить»*."
    )

    await message.bot.send_message(chat_id=telegram_id, text=confirmation_message, parse_mode="Markdown",
                                   reply_markup=approved_keyboard(telegram_id))


@router.callback_query(F.data.startswith('conf_'))
async def confirm_user(callback: CallbackQuery, state: FSMContext):
    telegram_id = int(callback.data.split('_')[1])
    async for db_session in get_db():
        await update_user_status(db_session, telegram_id, 'approved_user')
    await callback.bot.send_message(chat_id=telegram_id,
                                    text='Заявка подтверждена. На предоставленную электронную почту будет направлен Договор оказания услуг. Мы начнем поиск кандидата после предоставления Вами подписанного договора')
    await callback.bot.send_message(
        chat_id=telegram_id,
        text='Приветствуем в нашем проекте по поиску, обучению и тестированию новых сотрудников!\n\n'
             'Для составления заявки нажмите *«Продолжить»*',
        reply_markup=start_keyboard(),
        parse_mode="Markdown")


@router.callback_query(F.data.startswith('canc_'))
async def cancel_user(callback: CallbackQuery, state: FSMContext):
    telegram_id = int(callback.data.split('_')[1])
    async for db_session in get_db():
        await update_user_status(db_session, telegram_id, 'cancel_user')
    await callback.bot.send_message(chat_id=telegram_id, text='Заявка отменена.')
    await callback.bot.send_message(
        chat_id=telegram_id,
        text='Приветствуем в нашем проекте по поиску, обучению и тестированию новых сотрудников!\n\n'
             'Для составления заявки нажмите *«Продолжить»*',
        reply_markup=start_keyboard(),
        parse_mode="Markdown")


class CancelRequestForm(StatesGroup):
    answer_admin = State()


@router.callback_query(F.data.startswith('cancel_'))
async def cancel_admin(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.data.split('_')[1]  # Получаем telegram_id из данных кнопки
    await state.update_data(telegram_id=telegram_id)  # Сохраняем telegram_id в состоянии
    await callback.message.answer('Введите *причину* отказа:', parse_mode="Markdown")
    await state.set_state(CancelRequestForm.answer_admin)


@router.message(StateFilter(CancelRequestForm.answer_admin))
async def description(message: Message, state: FSMContext):
    # Получаем данные из состояния
    user_data = await state.get_data()
    answer_admin = message.text  # Текст с причиной отказа
    telegram_id = user_data['telegram_id']  # Получаем telegram_id пользователя, чья заявка отклонена

    # Отправляем сообщение пользователю с отказом
    await message.bot.send_message(
        chat_id=telegram_id,
        text=f'Ваша заявка отклонена по следующей причине:\n\n{answer_admin}'
    )
    async for db_session in get_db():
        await update_user_status(db_session, telegram_id, 'cancel_admin')
    # Дополнительно, можно уведомить администратора о том, что отказ был отправлен
    await message.bot.send_message(
        chat_id=message.from_user.id,
        text=f"Заявка пользователя {telegram_id} отклонена. Причина отказа: {answer_admin}"
    )
    await message.bot.send_message(
        chat_id=telegram_id,
        text='Приветствуем в нашем проекте по поиску, обучению и тестированию новых сотрудников!\n\n'
             'Для составления заявки нажмите *«Продолжить»*',
        reply_markup=start_keyboard(),
        parse_mode="Markdown")
