from ..models import TaskType
from .classification_handler import ClassificationHandler
from .qa_handler import (
    QAHandler, SummarizationHandler, PredictionHandler, 
    NLIHandler, NERHandler, DraftingHandler
)

HANDLER_MAP = {
    TaskType.CLASSIFICATION: ClassificationHandler,
    TaskType.QA: QAHandler,
    TaskType.SUMMARIZATION: SummarizationHandler,
    TaskType.PREDICTION: PredictionHandler,
    TaskType.NLI: NLIHandler,
    TaskType.NER: NERHandler,
    TaskType.DRAFTING: DraftingHandler,
}

def get_handler(db, task):
    handler_class = HANDLER_MAP.get(TaskType(task.task_type))
    if not handler_class:
        raise NotImplementedError(f"No handler for task type {task.task_type}")
    return handler_class(db, task)