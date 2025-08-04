from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import models
from .task_handlers import get_handler  # Import the handler factory


async def calculate_and_store_consistency(
    db: AsyncSession, task_id: int, aggregated_result: dict
):
    """
    Calculates and stores the consistency score for each feedback on a given task.
    This should be called after the task's feedback has been aggregated.
    This function now uses the Task Handler Pattern to delegate the consistency calculation.

    Args:
        db (AsyncSession): The async database session
        task_id (int): The ID of the task to calculate consistency for
        aggregated_result (dict): The aggregated result to compare feedback against

    Returns:
        None
    """
    result = await db.execute(
        select(models.LegalTask).filter(models.LegalTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return

    result = await db.execute(
        select(models.Feedback)
        .join(models.Response)
        .filter(models.Response.task_id == task_id)
    )
    feedbacks = result.scalars().all()

    handler = get_handler(db, task)

    for feedback in feedbacks:
        score = handler.calculate_consistency(feedback, aggregated_result)
        feedback.consistency_score = score

    await db.commit()


async def calculate_and_store_correctness(db: AsyncSession, task_id: int):
    """
    Calculates and stores the correctness score for each feedback on a given task
    by comparing it against the ground truth data.

    Args:
        db (AsyncSession): The async database session
        task_id (int): The ID of the task to calculate correctness for

    Returns:
        None
    """
    result = await db.execute(
        select(models.LegalTask).filter(models.LegalTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task or not task.ground_truth_data:
        return  # No task or no ground truth to compare against

    result = await db.execute(
        select(models.Feedback)
        .join(models.Response)
        .filter(models.Response.task_id == task_id)
    )
    feedbacks = result.scalars().all()

    handler = get_handler(db, task)

    for feedback in feedbacks:
        score = handler.calculate_correctness(feedback, task.ground_truth_data)
        feedback.correctness_score = score

    await db.commit()
