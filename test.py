import pytest
from unittest.mock import AsyncMock
from aiogram.types import Message, CallbackQuery, User, Chat
from aiogram.fsm.context import FSMContext
from datetime import datetime
from main import router, RequestForm, CandidateForm


@pytest.fixture
def mock_message():
    """Фикстура для создания мокированного объекта Message"""
    mock = AsyncMock(spec=Message)
    mock.message_id = 1
    mock.from_user = User(id=123456789, is_bot=False, first_name="TestUser")
    mock.chat = Chat(id=123456789, type="private")
    mock.text = "/start"
    mock.date = datetime.now()
    mock.answer = AsyncMock()
    return mock


@pytest.fixture
def mock_callback():
    """Фикстура для создания мокированного объекта CallbackQuery"""
    mock = AsyncMock(spec=CallbackQuery)
    mock.id = "12345"
    mock.from_user = User(id=123456789, is_bot=False, first_name="TestUser")
    mock.message = AsyncMock(spec=Message)
    mock.message.message_id = 1
    mock.message.chat = Chat(id=123456789, type="private")
    mock.message.text = "Test Callback"
    mock.message.date = datetime.now()
    mock.message.answer = AsyncMock()
    mock.data = "continue"
    return mock


@pytest.fixture
def mock_state():
    """Фикстура для FSMContext"""
    return AsyncMock(spec=FSMContext)


@pytest.mark.asyncio
async def test_start_command(mock_message):
    """Тест команды /start"""
    await router.message.handlers[0].callback(mock_message)
    mock_message.answer.assert_called_once_with(
        'Приветствуем в нашем проекте по поиску, обучению и тестированию новых сотрудников!',
        reply_markup=mock_message.reply_markup,
        parse_mode="Markdown"
    )


@pytest.mark.asyncio
async def test_continue_callback(mock_callback, mock_state):
    """Тест нажатия кнопки 'Продолжить' и перехода в FSM"""
    await router.callback_query.handlers[0].callback(mock_callback, mock_state)
    mock_callback.message.answer.assert_called_once_with(
        'Введите *название вашей компании* (имя клиента):',
        parse_mode="Markdown"
    )
    mock_state.set_state.assert_called_once_with(RequestForm.name)


@pytest.mark.asyncio
async def test_position_state(mock_message, mock_state):
    """Тест ввода позиции кандидата"""
    await router.message.handlers[1].callback(mock_message, mock_state)
    mock_state.update_data.assert_called_once_with(name=mock_message.text)
    mock_message.answer.assert_called_once_with(
        'Введите *позицию*, на которую ищете кандидата:',
        parse_mode="Markdown"
    )
    mock_state.set_state.assert_called_once_with(RequestForm.position)


@pytest.mark.asyncio
async def test_contact_number_state(mock_message, mock_state):
    """Тест ввода контактного номера"""
    await router.message.handlers[2].callback(mock_message, mock_state)
    mock_state.update_data.assert_called_once_with(position=mock_message.text)
    mock_message.answer.assert_called_once_with(
        "Введите *контактный номер* или нажмите 'Поделиться номером'.",
        parse_mode="Markdown",
        reply_markup=mock_message.reply_markup
    )
    mock_state.set_state.assert_called_once_with(RequestForm.contact_number)


@pytest.mark.asyncio
async def test_email_state_invalid(mock_message, mock_state):
    """Тест некорректного email"""
    mock_message.text = "invalid_email"
    await router.message.handlers[3].callback(mock_message, mock_state)
    mock_message.answer.assert_called_once_with(
        "Некорректный email. Пожалуйста, введите email в формате example@example.com."
    )


@pytest.mark.asyncio
async def test_email_state_valid(mock_message, mock_state):
    """Тест корректного email"""
    mock_message.text = "test@example.com"
    await router.message.handlers[3].callback(mock_message, mock_state)
    mock_state.update_data.assert_called_once_with(contact_email=mock_message.text)
    mock_message.answer.assert_called_once_with(
        "Введите *контактное лицо*:",
        parse_mode="Markdown"
    )
    mock_state.set_state.assert_called_once_with(RequestForm.quality)


@pytest.mark.asyncio
async def test_confirm_request(mock_message, mock_state):
    """Тест подтверждения заявки"""
    user_data = {
        'name': 'Компания X',
        'position': 'Разработчик',
        'contact_number': '+79998887766',
        'contact_email': 'test@example.com',
        'quality': 'Ответственность',
        'contact_person': 'Иван Иванов'
    }
    mock_state.get_data.return_value = user_data

    await router.message.handlers[6].callback(mock_message, mock_state)

    mock_message.answer.assert_called_once_with(
        f"✅ *Ваша заявка принята:*\n\n"
        f"📌 *Компания:* {user_data['name']}\n"
        f"📌 *Позиция искомого кандидата:* {user_data['position']}\n"
        f"📌 *Качества кандидата:* {user_data['quality']}\n"
        f"📌 *Контактный номер:* {user_data['contact_number']}\n"
        f"📌 *Почта:* {user_data['contact_email']}\n"
        f"📌 *Контактное лицо:* {user_data['contact_person']}\n\n"
        "Мы с вами свяжемся!",
        parse_mode="Markdown"
    )


@pytest.mark.asyncio
async def test_admin_command(mock_message, mock_state):
    """Тест команды /admin"""
    mock_message.from_user.id = 947159905  # Один из администраторов
    await router.message.handlers[7].callback(mock_message, mock_state)

    mock_message.answer.assert_called_once_with(
        "Давайте добавим нового кандидата.\n\n"
        "Введите специализацию кандидата:"
    )
    mock_state.set_state.assert_called_once_with(CandidateForm.specialist)


@pytest.mark.asyncio
async def test_process_specialist(mock_message, mock_state):
    """Тест ввода специализации кандидата"""
    await router.message.handlers[8].callback(mock_message, mock_state)
    mock_state.update_data.assert_called_once_with(specialist=mock_message.text)
    mock_message.answer.assert_called_once_with("Введите должность кандидата:")
    mock_state.set_state.assert_called_once_with(CandidateForm.position)


@pytest.mark.asyncio
async def test_process_position(mock_message, mock_state):
    """Тест ввода должности кандидата"""
    await router.message.handlers[9].callback(mock_message, mock_state)
    mock_state.update_data.assert_called_once_with(position=mock_message.text)
    mock_message.answer.assert_called_once_with("Введите навыки кандидата:")
    mock_state.set_state.assert_called_once_with(CandidateForm.skills)
