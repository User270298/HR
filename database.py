import asyncio

import aiosqlite
from sqlalchemy import create_engine, Column, Integer, String, update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

DATABASE_URL = "sqlite+aiosqlite:///hr.db"  # Путь к базе данных

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    telegram_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    position = Column(String)
    contact_number = Column(String)
    contact_email = Column(String)
    contact_person = Column(String)
    status = Column(String, default="pending")
    service_date = Column(String)
    service_price = Column(String)


class Candidate(Base):
    __tablename__ = 'candidate'

    id = Column(Integer, primary_key=True, autoincrement=True)  # Добавляем первичный ключ
    specialist = Column(String, index=True)
    position = Column(String)
    skills = Column(String)
    experience = Column(String)
    education = Column(String)
    addon = Column(String)


# Создаем движок и сессию для SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# Создание базы данных
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as db_session:
        yield db_session


from sqlalchemy.exc import IntegrityError

async def add_candidate(db_session: AsyncSession, user_data: dict):
    """
    Добавляет нового кандидата в базу данных.

    :param db_session: Асинхронная сессия SQLAlchemy.
    :param user_data: Словарь с данными кандидата.
    :return: Объект Candidate, если успешно добавлен.
    """
    # Создаем объект Candidate из переданных данных
    new_candidate = Candidate(
        specialist=user_data.get("specialist"),
        position=user_data.get("position"),
        skills=user_data.get("skills"),
        experience=user_data.get("experience"),
        education=user_data.get("education"),
        addon=user_data.get("addon")
    )

    # Добавляем объект в сессию
    db_session.add(new_candidate)

    # Фиксируем изменения в базе данных
    await db_session.commit()

    # Обновляем объект, чтобы получить его ID (если нужно)
    await db_session.refresh(new_candidate)





async def add_user(db_session, user_data):
    # Проверяем, существует ли пользователь с данным telegram_id
    existing_user = await db_session.execute(
        select(User).filter(User.telegram_id == user_data['telegram_id'])
    )
    user = existing_user.scalars().first()

    if user:
        # Если пользователь существует, можно обновить его данные
        user.name = user_data['name']
        user.position = user_data['position']
        user.contact_number = user_data['contact_number']
        user.contact_email = user_data['contact_email']
        user.contact_person = user_data['contact_person']
        user.status = user_data['status']
        user.service_date = user_data['service_date']
        user.service_price = user_data['service_price']
    else:
        # Если пользователя нет, создаем новую запись
        user = User(**user_data)
        db_session.add(user)

    try:
        await db_session.commit()
    except IntegrityError as e:
        # Обрабатываем ошибку уникальности, если возникла
        await db_session.rollback()
        print(f"Ошибка при добавлении пользователя: {e}")


# Получение позиции по Telegram ID
async def get_position_by_telegram_id(db_session: AsyncSession, telegram_id: int):
    stmt = select(User.position).where(User.telegram_id == telegram_id)
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


# Получение статуса по Telegram ID
async def get_status_by_telegram_id(db_session: AsyncSession, telegram_id: int):
    stmt = select(User.status).where(User.telegram_id == telegram_id)
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


# Обновление статуса пользователя
async def update_user_status(db_session: AsyncSession, telegram_id: int, new_status: str):
    try:
        # Выполняем обновление статуса пользователя
        stmt = update(User).where(User.telegram_id == telegram_id).values(status=new_status)
        await db_session.execute(stmt)
        await db_session.commit()
    except Exception as e:
        # Обрабатываем ошибки транзакции
        print(f"Ошибка при обновлении статуса: {e}")
        await db_session.rollback()


async def addon(db_session: AsyncSession, telegram_id: int, service_date: str, service_price: str):
    try:
        stmt = update(User).where(User.telegram_id == telegram_id).values(service_date=service_date,
                                                                          service_price=service_price)
        await db_session.execute(stmt)
        await db_session.commit()
    except Exception as e:
        # Обрабатываем ошибки транзакции
        print(f"Ошибка при обновлении статуса: {e}")
        await db_session.rollback()


async def get_user(db_session: AsyncSession, telegram_id: int):
    try:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()
    except Exception as e:
        await db_session.rollback()


async def get_all_candidates(db_session: AsyncSession):
    # Запрос для получения всех кандидатов
    result = await db_session.execute(select(Candidate))

    # Получаем все кандидаты из результата
    candidates = result.scalars().all()

    return candidates