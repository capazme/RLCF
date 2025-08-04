from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base

from .config import app_settings

# Convert SQLite URL to async version
SQLALCHEMY_DATABASE_URL = app_settings.DATABASE_URL.replace(
    "sqlite:///", "sqlite+aiosqlite:///"
)

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()
