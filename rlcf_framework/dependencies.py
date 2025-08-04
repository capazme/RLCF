"""
Centralized dependency injection for the RLCF framework.

This module provides all dependencies needed across the application,
improving testability and configuration management.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from .database import SessionLocal
from .config import model_settings, task_settings, ModelConfig, TaskConfig


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency that provides database session.

    Yields:
        AsyncSession: SQLAlchemy async database session
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_model_settings() -> ModelConfig:
    """
    Dependency that provides model configuration settings.

    Returns:
        ModelConfig: Current model configuration
    """
    return model_settings


def get_task_settings() -> TaskConfig:
    """
    Dependency that provides task configuration settings.

    Returns:
        TaskConfig: Current task configuration
    """
    return task_settings
