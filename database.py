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


async def get_all_users(db_session: AsyncSession):
    stmt = select(User.name, User.position, User.status)
    result = await db_session.execute(stmt)
    return result.fetchall()