import re
from datetime import datetime
from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from keyboard import start_keyboard, admin_keyboard, approved_keyboard
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from database import add_user, get_db, get_position_by_telegram_id, update_user_status, get_user, addon

router = Router()
ADMIN_ID = [5584822662]  # 947159905,


@router.message(Command(commands=['start']))
async def hello(message: Message):
    await message.answer(
        'Приветствуем в нашем проекте по поиску, обучению и тестированию новых сотрудников!',
        reply_markup=start_keyboard(),
        parse_mode="Markdown")


@router.callback_query(F.data == 'ankets')
async def callback_query(callback: CallbackQuery):
    await callback.message.answer(f'🚀 Анкета кандидата 🚀\n'
                                  f'🔹 Специалист по: ...\n'
                                  f'🔹 Должность: ...\n'
                                  f'🔹 Что умею лучше всего?\n'
                                  f'🔹 Мои достижения: ...\n'
                                  f'🔹 Образование: ...\n'
                                  f'🔹 Дополнительно:...\n\n'
                                  f'📩 Хотите узнать больше? Свяжитесь с нашим HR: ...')


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

    if not re.match(r'((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}', contact_number):
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
    await callback.message.answer("Введите *срок оказания услуг* (в формате ДД.ММ.ГГГГ):", parse_mode="Markdown")
    await state.set_state(ApprovedRequestForm.date)


@router.message(StateFilter(ApprovedRequestForm.date))
async def service_cost(message: Message, state: FSMContext):
    try:
        # Пытаемся преобразовать введенный текст в дату
        date = datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(date=date.strftime("%d.%m.%Y"))
        await message.answer("Введите *стоимость оказываемых услуг* (только число):", parse_mode="Markdown")
        await state.set_state(ApprovedRequestForm.price)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ:")


@router.message(StateFilter(ApprovedRequestForm.price))
async def send_confirmation(message: Message, state: FSMContext):
    try:
        await message.answer('Пользователю отправлено уведомление о поиске кандидата.')
        # Пытаемся преобразовать введенный текст в число
        service_price = float(message.text.replace(',', '.'))  # Поддержка как точки, так и запятой
        await state.update_data(service_price=service_price)
        user_data = await state.get_data()
        service_date = user_data['date']
        telegram_id = user_data['telegram_id']
        async for db_session in get_db():
            position = await get_position_by_telegram_id(db_session, telegram_id)
            await update_user_status(db_session, telegram_id, 'approved_admin')
            await addon(db_session, telegram_id, str(service_date), str(service_price))

        confirmation_message = (
            f"Уважаемые коллеги! Благодарим за обращение в ООО АГРОКОР за поиском и обучением кандидата на должность "
            f"*{position}*.\n\n"
            f"📌 Сообщаем, что кандидат будет найден и обучен в срок до *{service_date}*.\n"
            f"📌 Стоимость оказываемой услуги составит *{service_price:.2f}* рублей.\n\n"
            "Для подтверждения, нажмите *«Подтвердить»*."
        )

        await message.bot.send_message(chat_id=telegram_id, text=confirmation_message, parse_mode="Markdown",
                                       reply_markup=approved_keyboard(telegram_id))
    except ValueError:
        await message.answer("❌ Неверный формат числа. Пожалуйста, введите стоимость услуг в виде числа:")


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
    async for db_session in get_db():
        user_info = await get_user(db_session, telegram_id)
    for admin in ADMIN_ID:
        await callback.bot.send_message(
            chat_id=admin,
            text=f"✅ Компания {user_info.name} подтвердила заявку по поиску {user_info.position}.\n"
                 f"- Срок оказания услуг до {user_info.service_date}.\n"
                 f"- Стоимость услуг {user_info.service_price} рублей.\n"
                 f"- Контактный номер {user_info.contact_number}.\n"
                 f"- Контактная электронная почта {user_info.contact_email}.\n")


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
    async for db_session in get_db():
        user_info = await get_user(db_session, telegram_id)
    for admin in ADMIN_ID:
        await callback.bot.send_message(
            chat_id=admin,
            text=f"❌ Компания {user_info.name} подтвердила заявку по поиску {user_info.position}.\n"
                 f"- Срок оказания услуг до {user_info.service_date}.\n"
                 f"- Стоимость услуг {user_info.service_price} рублей.\n"
                 f"- Контактный номер {user_info.contact_number}.\n"
                 f"- Контактная электронная почта {user_info.contact_email}.\n")


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



    