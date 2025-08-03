
from sqlalchemy.orm import Session
from . import models
from .task_handlers import get_handler # Import the handler factory

def calculate_and_store_consistency(db: Session, task_id: int, aggregated_result: dict):
    """
    Calculates and stores the consistency score for each feedback on a given task.
    This should be called after the task's feedback has been aggregated.
    This function now uses the Task Handler Pattern to delegate the consistency calculation.
    """
    task = db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
    if not task:
        return

    feedbacks = db.query(models.Feedback).join(models.Response).filter(models.Response.task_id == task_id).all()

    handler = get_handler(db, task)

    for feedback in feedbacks:
        score = handler.calculate_consistency(feedback, aggregated_result)
        feedback.consistency_score = score
    
    db.commit()

def calculate_and_store_correctness(db: Session, task_id: int):
    """
    Calculates and stores the correctness score for each feedback on a given task
    by comparing it against the ground truth data.
    """
    task = db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
    if not task or not task.ground_truth_data:
        return # No task or no ground truth to compare against

    feedbacks = db.query(models.Feedback).join(models.Response).filter(models.Response.task_id == task_id).all()

    handler = get_handler(db, task)

    for feedback in feedbacks:
        score = handler.calculate_correctness(feedback, task.ground_truth_data)
        feedback.correctness_score = score
    
    db.commit()
