from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings


async_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True
)


sync_engine = create_engine(
    settings.sync_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600
)


AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)


Base = declarative_base()


async def get_async_db() -> AsyncSession:
    """
    Dependency для получения асинхронной сессии базы данных.
    Используется в FastAPI endpoints через Depends().
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_db():
    """
    Dependency для получения синхронной сессии базы данных.
    Используется для миграций и создания тестовых данных.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """
    Инициализация базы данных (создание таблиц).
    Используется при первом запуске приложения.
    """
    async with async_engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)


def create_tables():
    """
    Синхронное создание всех таблиц в базе данных.
    Используется для инициализации БД в скриптах.
    """
    Base.metadata.create_all(bind=sync_engine)