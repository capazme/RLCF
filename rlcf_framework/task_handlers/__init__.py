from ..models import TaskType
from .classification_handler import ClassificationHandler

HANDLER_MAP = {
    TaskType.CLASSIFICATION: ClassificationHandler,
}

def get_handler(db, task):
    handler_class = HANDLER_MAP.get(TaskType(task.task_type))
    if not handler_class:
        raise NotImplementedError(f"No handler for task type {task.task_type}")
    return handler_class(db, task)