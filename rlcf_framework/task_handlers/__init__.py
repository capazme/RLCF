from ..models import TaskType
from .classification_handler import ClassificationHandler
from .qa_handler import (
    QAHandler,
    SummarizationHandler,
    PredictionHandler,
    NLIHandler,
    NERHandler,
    DraftingHandler,
    RiskSpottingHandler,
    DoctrineApplicationHandler,
)

HANDLER_MAP = {
    TaskType.CLASSIFICATION: ClassificationHandler,
    TaskType.QA: QAHandler,
    TaskType.SUMMARIZATION: SummarizationHandler,
    TaskType.PREDICTION: PredictionHandler,
    TaskType.NLI: NLIHandler,
    TaskType.NER: NERHandler,
    TaskType.DRAFTING: DraftingHandler,
    TaskType.RISK_SPOTTING: RiskSpottingHandler,
    TaskType.DOCTRINE_APPLICATION: DoctrineApplicationHandler,
}


async def get_handler(db, task):
    """
    Get the appropriate task handler for the given task type.

    Args:
        db: AsyncSession for database operations
        task: LegalTask instance

    Returns:
        Task handler instance for the specific task type
    """
    handler_class = HANDLER_MAP.get(TaskType(task.task_type))
    if not handler_class:
        raise NotImplementedError(f"No handler for task type {task.task_type}")
    return handler_class(db, task)
