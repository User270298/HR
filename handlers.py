from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from keyboard import start_keyboard, admin_keyboard, approved_keyboard
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from database import add_user, get_db, get_position_by_telegram_id

router = Router()
ADMIN_ID = [947159905]


@router.message(Command(commands=['start']))
async def hello(message: Message):
    await message.answer(
        'Приветствуем в нашем проекте по поиску, обучению и тестированию новых сотрудников!\n\n'
        'Для составления заявки нажмите *«Продолжить»*',
        reply_markup=start_keyboard(),
        parse_mode="Markdown")


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
    await state.update_data(contact_number=contact_number)
    await message.answer("Введите *контактную почту*:", parse_mode="Markdown")
    await state.set_state(RequestForm.contact_email)


@router.message(StateFilter(RequestForm.contact_email))
async def contact_person(message: Message, state: FSMContext):
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
        f"✅ *Ваша заявка принята от {message.from_user.full_name}:*\n\n"
        f"📌 *Компания:* {user_data['name']}\n"
        f"📌 *Позиция искомого кандидата:* {user_data['position']}\n"
        f"📌 *Контактный номер:* {user_data['contact_number']}\n"
        f"📌 *Почта:* {user_data['contact_email']}\n"
        f"📌 *Контактное лицо:* {user_data['contact_person']}\n\n"
        "Мы с вами свяжемся!", parse_mode="Markdown",
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


@router.message(F.data.startswith('conf_'))
async def confirm_request(message: Message, state: FSMContext):
    pass


@router.callback_query(F.data.startswith('cancel_'))
async def approved(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.data.split('_')[1]
    await state.update_data(telegram_id=telegram_id)
    await callback.bot.send_message(chat_id=telegram_id, text='Вашу заявку отклонили!')
