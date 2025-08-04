from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import models, aggregation_engine, post_processing, bias_analysis


async def orchestrate_task_aggregation(db: AsyncSession, task_id: int):
    """
    Orchestra il processo completo di aggregazione, post-processing e analisi bias per un task.

    This function is now atomic and resilient to failures. Each major operation
    (aggregation, consistency, bias) manages its own transaction to ensure
    partial failures don't prevent other operations from completing.

    Args:
        db: AsyncSession for database operations
        task_id: ID of the task to orchestrate aggregation for
    """
    # 1. Aggregate and save result - atomic operation
    await _aggregate_and_save_result(db, task_id)

    # 2. Calculate and store consistency - atomic operation
    await _calculate_and_store_consistency(db, task_id)

    # 3. Calculate and store bias - atomic operation
    await _calculate_and_store_bias(db, task_id)


async def _aggregate_and_save_result(db: AsyncSession, task_id: int) -> dict:
    """
    Atomic operation to calculate and save aggregation result.

    Args:
        db: AsyncSession for database operations
        task_id: ID of the task to aggregate

    Returns:
        dict: Aggregation result or error information
    """
    async with db.begin():
        try:
            result = await aggregation_engine.aggregate_with_uncertainty(db, task_id)
            if "error" not in result:
                # Store the aggregation result (implementation would depend on your needs)
                # For now, we just return the result
                pass
            return result
        except Exception as e:
            # Log error but don't re-raise to allow other operations to continue
            print(f"Error in aggregation for task {task_id}: {e}")
            return {"error": str(e)}


async def _calculate_and_store_consistency(db: AsyncSession, task_id: int):
    """
    Atomic operation to calculate and store consistency scores.

    Args:
        db: AsyncSession for database operations
        task_id: ID of the task to calculate consistency for
    """
    async with db.begin():
        try:
            # Get aggregation result first
            result = await aggregation_engine.aggregate_with_uncertainty(db, task_id)
            if "error" in result:
                return

            await post_processing.calculate_and_store_consistency(db, task_id, result)
            await post_processing.calculate_and_store_correctness(db, task_id)
        except Exception as e:
            print(f"Error in consistency calculation for task {task_id}: {e}")
            await db.rollback()


async def _calculate_and_store_bias(db: AsyncSession, task_id: int):
    """
    Atomic operation to calculate and store bias reports.

    Args:
        db: AsyncSession for database operations
        task_id: ID of the task to calculate bias for
    """
    async with db.begin():
        try:
            # Get participants for this task
            result = await db.execute(
                select(models.User)
                .join(models.Feedback)
                .join(models.Response)
                .filter(models.Response.task_id == task_id)
                .distinct()
            )
            participants = result.scalars().all()

            for user in participants:
                bias_score = await bias_analysis.calculate_professional_clustering_bias(
                    db, user.id, task_id
                )
                db_report = models.BiasReport(
                    task_id=task_id,
                    user_id=user.id,
                    bias_type="PROFESSIONAL_CLUSTERING",
                    bias_score=bias_score,
                )
                db.add(db_report)

            await db.commit()
        except Exception as e:
            print(f"Error in bias calculation for task {task_id}: {e}")
            await db.rollback()
