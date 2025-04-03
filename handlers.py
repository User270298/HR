import re
from datetime import datetime
from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from keyboard import start_keyboard, admin_keyboard, approved_keyboard, candidate_keyboard, admin_help_keyboard
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from database import add_user, get_db, get_position_by_telegram_id, update_user_status, get_user, addon, add_candidate, \
    get_all_candidates, get_pending_requests, update_candidate_status
import logging
from sqlalchemy import select
from database import Candidate

router = Router()
ADMIN_ID = [ 947159905, 5584822662]  # 947159905,



@router.callback_query(F.data=='admin')
async def admin_panel(callback: CallbackQuery):
    logging.info(f"Команда /admin вызвана пользователем {callback.from_user.id}")
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_ID:
        logging.info(f"Пользователь {callback.from_user.id} не является администратором")
        await callback.message.answer("У вас нет доступа к этой команде.")
        return
    
    # Получаем все неподтвержденные заявки
    async for db_session in get_db():
        pending_requests = await get_pending_requests(db_session)
    
    logging.info(f"Найдено {len(pending_requests) if pending_requests else 0} неподтвержденных заявок")
    
    if not pending_requests:
        await callback.message.answer("Неподтвержденных заявок нет.")
        return
    
    # Отправляем сообщение с информацией о каждой заявке
    await callback.message.answer("📋 *Список неподтвержденных заявок:*", parse_mode="Markdown")
    
    for request in pending_requests:
        logging.info(f"Отправка информации о заявке от пользователя {request.telegram_id}")
        request_info = (
            f"👤 *Заявка от пользователя с ID:* {request.telegram_id}\n\n"
            f"📌 *Компания:* {request.name}\n"
            f"📌 *Позиция искомого кандидата:* {request.position}\n"
            f"📌 *Контактный номер:* {request.contact_number}\n"
            f"📌 *Почта:* {request.contact_email}\n"
            f"📌 *Контактное лицо:* {request.contact_person}\n"
        )
        
        # Отправляем информацию о заявке с кнопками для подтверждения/отклонения
        await callback.message.answer(text=request_info, parse_mode="Markdown", 
                            reply_markup=admin_keyboard(request.telegram_id))

@router.message(Command(commands=['start']))
async def hello(message: Message):
    await message.answer(
        'Приветствуем в нашем проекте по поиску, обучению и тестированию новых сотрудников!',
        reply_markup=start_keyboard(),
        parse_mode="Markdown")


@router.callback_query(F.data == 'ankets')
async def show_candidates(callback: CallbackQuery):
    # Получаем всех кандидатов из базы асинхронно
    async for db_session in get_db():
        candidates = await get_all_candidates(db_session)
    if candidates==[]:
        await callback.message.answer('Нет доступных анкет!')
        return
    # Формируем сообщения для каждого кандидата
    for candidate in candidates:
        message = (
            f'🚀 Анкета кандидата 🚀\n'
            f'🔹*Специалист по*: {candidate.specialist}\n'
            f'🔹 *Должность*: {candidate.position}\n'
            f'🔹 *Что умеет лучше всего*: {candidate.skills}\n'
            f'🔹 *Достижения*: {candidate.experience}\n'
            f'🔹 *Образование*: {candidate.education}\n'
            f'🔹 *Дополнительно*: {candidate.addon}\n'
            f'🔹 *Сервис*: {candidate.service}\n'
            f'📩 Хотите узнать больше? Свяжитесь с нашим HR: +7(928)907-53-00'
        )
        # Отправляем сообщение для каждого кандидата
        await callback.message.answer(message, parse_mode="Markdown")

class RequestForm(StatesGroup):
    name = State()
    position = State()
    contact_number = State()
    contact_email = State()
    quality = State()
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

    if not re.match(r'^([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$|(^\+?[0-9]{1,3}[- ]?[0-9]{3}[- ]?[0-9]{3}[- ]?[0-9]{4}$)', contact_number):
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
    await state.set_state(RequestForm.quality)

@router.message(StateFilter(RequestForm.quality))
async def quality(message: Message, state: FSMContext):
    await state.update_data(contact_person=message.text)
    await message.answer("Введите *необходимые качества кандидата*:", parse_mode="Markdown")
    await state.set_state(RequestForm.contact_person)


@router.message(StateFilter(RequestForm.contact_person))
async def confirm_request(message: Message, state: FSMContext, bot):
    await state.update_data(quality=message.text)
    user_data = await state.get_data()

    async for db_session in get_db():
        await add_user(db_session, {
            'telegram_id': message.from_user.id,
            'name': user_data['name'],
            'position': user_data['position'],
            'contact_number': user_data['contact_number'],
            'contact_email': user_data['contact_email'],
            'quality': user_data['quality'],
            'contact_person': user_data['contact_person'],
            'status': "pending"
        })

    await message.answer(
        f"✅ *Ваша заявка принята:*\n\n"
        f"📌 *Компания:* {user_data['name']}\n"
        f"📌 *Позиция искомого кандидата:* {user_data['position']}\n"
        f"📌 *Качества кандидата:* {user_data['quality']}\n"
        f"📌 *Контактный номер:* {user_data['contact_number']}\n"
        f"📌 *Почта:* {user_data['contact_email']}\n"
        f"📌 *Контактное лицо:* {user_data['contact_person']}\n\n"
        "Мы с вами свяжемся!", parse_mode="Markdown")
    for admin in ADMIN_ID:
        await message.bot.send_message(chat_id=admin, text=
        f"✅ *Поступила заявка от {message.from_user.full_name}:*\n\n"
        f"📌 *Компания:* {user_data['name']}\n"
        f"📌 *Позиция искомого кандидата:* {user_data['position']}\n"
        f"📌 *Качества кандидата:* {user_data['quality']}\n"
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
    await callback.message.answer("Введите *приблизительное время оказания услуг* (в формате ДД.ММ.ГГГГ):", parse_mode="Markdown")
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
            f"📌 Сообщаем, что кандидат будет найден и обучен приблизительно в срок до *{service_date}*.\n"
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
                 f"- Приблизительный срок оказания услуг до {user_info.service_date}.\n"
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
                 f"- Приблизительный срок оказания услуг до {user_info.service_date}.\n"
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


class CandidateForm(StatesGroup):
    specialist = State()
    position = State()
    skills = State()
    experience = State()
    education = State()
    addon = State()
    service = State()


@router.callback_query(F.data=='add')
async def admin(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    if telegram_id not in ADMIN_ID:
        await callback.answer('Вы не являетесь админом')
        return

    # Очистка состояния перед началом нового процесса
    await state.clear()

    print(f"DEBUG: {callback.from_user.id} нажал /admin, текущее состояние: {await state.get_state()}")  # Лог

    await callback.message.answer(
        "Давайте добавим нового кандидата.\n\n"
        "Введите специализацию кандидата:"
    )
    await state.set_state(CandidateForm.specialist)  # Устанавливаем первое состояние


@router.message(StateFilter(CandidateForm.specialist))
async def process_specialist(message: Message, state: FSMContext):
    await state.update_data(specialist=message.text)  # Сохраняем специализацию
    await message.answer("Введите должность кандидата:")
    await state.set_state(CandidateForm.position)  # Переходим к следующему состоянию


@router.message(StateFilter(CandidateForm.position))
async def process_position(message: Message, state: FSMContext):
    await state.update_data(position=message.text)  # Сохраняем должность
    await message.answer("Введите навыки кандидата:")
    await state.set_state(CandidateForm.skills)  # Переходим к следующему состоянию


@router.message(StateFilter(CandidateForm.skills))
async def process_skills(message: Message, state: FSMContext):
    await state.update_data(skills=message.text)  # Сохраняем навыки
    await message.answer("Введите опыт кандидата:")
    await state.set_state(CandidateForm.experience)  # Переходим к следующему состоянию


@router.message(StateFilter(CandidateForm.experience))
async def process_experience(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)  # Сохраняем опыт
    await message.answer("Введите образование кандидата:")
    await state.set_state(CandidateForm.education)  # Переходим к следующему состоянию


@router.message(StateFilter(CandidateForm.education))
async def process_education(message: Message, state: FSMContext):
    await state.update_data(education=message.text)  # Сохраняем образование
    await message.answer("Введите дополнительную информацию о кандидате:")
    await state.set_state(CandidateForm.addon)  # Переходим к следующему состоянию

@router.message(StateFilter(CandidateForm.addon))
async def process_addon(message: Message, state: FSMContext):
    await state.update_data(addon=message.text)  # Сохраняем дополнительную информацию
    await message.answer("Введите сервис, сопровождающий кандидата:")
    await state.set_state(CandidateForm.service)  # Переходим к следующему состоянию


@router.message(StateFilter(CandidateForm.service))
async def process_service(message: Message, state: FSMContext):
    await state.update_data(service=message.text)  # Сохраняем дополнительную информацию
    data = await state.get_data()
    await state.update_data(status="active")
    async for db_session in get_db():
        await add_candidate(db_session, data)

    # Завершаем состояние, чтобы избежать путаницы в будущем
    await state.clear()

    await message.answer("Кандидат успешно добавлен в базу данных!")


@router.callback_query(F.data=='close')
async def show_candidates_for_close(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    if telegram_id not in ADMIN_ID:
        await callback.answer('Вы не являетесь админом')
        return
    # Получаем всех кандидатов из базы асинхронно
    async for db_session in get_db():
        candidates = await get_all_candidates(db_session)
    if candidates==[]:
        await callback.message.answer('Нет доступных анкет!')
        return
    # Формируем сообщения для каждого кандидата
    for candidate in candidates:
        message_text = (
            f'🚀 Анкета кандидата 🚀\n'
            f'🔹*Специалист по*: {candidate.specialist}\n'
            f'🔹 *Должность*: {candidate.position}\n'
            f'🔹 *Что умеет лучше всего*: {candidate.skills}\n'
            f'🔹 *Достижения*: {candidate.experience}\n'
            f'🔹 *Образование*: {candidate.education}\n'
            f'🔹 *Дополнительно*: {candidate.addon}\n'
            f'🔹 *Сервис*: {candidate.service}'
        )
        # Отправляем сообщение для каждого кандидата
        await callback.message.answer(message_text, parse_mode="Markdown",
                           reply_markup=candidate_keyboard(candidate.id))

@router.callback_query(F.data.startswith('close_candidate_'))
async def close_candidate(callback: CallbackQuery):
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_ID:
        await callback.answer("У вас нет доступа к этой функции.")
        return
        
    candidate_id = int(callback.data.split('_')[-1])
    
    # Получаем информацию о кандидате
    async for db_session in get_db():
        result = await db_session.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        
        if candidate:
            # Обновляем статус кандидата на "closed"
            await update_candidate_status(db_session, candidate_id, "closed")
            
            # Отправляем уведомление админу
            await callback.message.answer(
                f"✅ Анкета кандидата на должность {candidate.position} успешно закрыта."
            )
        else:
            await callback.answer("Кандидат не найден.")



@router.message(Command(commands=['help']))
async def help_command(message: Message):
    if message.from_user.id in ADMIN_ID:
        # Помощь для админов
        help_text = (
            "👨‍💼 *Панель администратора*\n\n"
            "Доступные команды:\n"
        )
        await message.answer(help_text, parse_mode="Markdown", reply_markup=admin_help_keyboard())
    else:
        # Помощь для обычных пользователей
        help_text = (
            "👋 *Добро пожаловать в HR-бот АГРОКОР!*\n\n"
            "🤖 *Что умеет бот:*\n"
            "• Создание заявки на поиск сотрудника\n"
            "• Просмотр доступных анкет кандидатов\n\n"
            "📝 *Как использовать:*\n"
            "1. Нажмите кнопку «Оставить заявку на поиск сотрудника»\n"
            "2. Заполните все необходимые поля\n"
            "3. После отправки заявки мы свяжемся с вами для обсуждения деталей\n\n"
            "📋 *Просмотр анкет:*\n"
            "• Нажмите кнопку «Посмотреть анкеты кандидатов»\n"
            "• Выберите подходящего кандидата\n"
            "• Свяжитесь с HR для получения дополнительной информации\n\n"
            "❓ *Нужна помощь?*\n"
            "Свяжитесь с нашим HR: +7(928)907-53-00"
        )
        await message.answer(help_text, parse_mode="Markdown")
