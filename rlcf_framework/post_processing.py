
from sqlalchemy.orm import Session
from . import models
from .models import TaskType # Import TaskType

# --- Task-specific Consistency Functions ---

def _calculate_summarization_consistency(feedback: models.Feedback, aggregated_result: dict) -> float:
    # For summarization, consistency might mean if the user's revised_summary is close to the primary_answer
    # For simplicity, let's say 1.0 if the user's summary is the primary, 0.0 otherwise.
    if feedback.feedback_data and "revised_summary" in feedback.feedback_data:
        return 1.0 if feedback.feedback_data["revised_summary"] == aggregated_result.get("primary_answer") else 0.0
    return 0.0

def _calculate_classification_consistency(feedback: models.Feedback, aggregated_result: dict) -> float:
    # For classification, consistency means if the user's validated_labels match the primary_answer
    if feedback.feedback_data and "validated_labels" in feedback.feedback_data:
        return 1.0 if sorted(feedback.feedback_data["validated_labels"]) == sorted(aggregated_result.get("primary_answer")) else 0.0
    return 0.0

def _calculate_qa_consistency(feedback: models.Feedback, aggregated_result: dict) -> float:
    # For QA, consistency means if the user's validated_answer matches the primary_answer
    if feedback.feedback_data and "validated_answer" in feedback.feedback_data:
        return 1.0 if feedback.feedback_data["validated_answer"] == aggregated_result.get("primary_answer") else 0.0
    return 0.0

def _calculate_prediction_consistency(feedback: models.Feedback, aggregated_result: dict) -> float:
    # For prediction, consistency means if the user's chosen_outcome matches the primary_answer
    if feedback.feedback_data and "chosen_outcome" in feedback.feedback_data:
        return 1.0 if feedback.feedback_data["chosen_outcome"] == aggregated_result.get("primary_answer") else 0.0
    return 0.0

def _calculate_nli_consistency(feedback: models.Feedback, aggregated_result: dict) -> float:
    # For NLI, consistency means if the user's chosen_label matches the primary_answer
    if feedback.feedback_data and "chosen_label" in feedback.feedback_data:
        return 1.0 if feedback.feedback_data["chosen_label"] == aggregated_result.get("primary_answer") else 0.0
    return 0.0

def _calculate_ner_consistency(feedback: models.Feedback, aggregated_result: dict) -> float:
    # For NER, consistency means if the user's validated_tags match the primary_answer
    if feedback.feedback_data and "validated_tags" in feedback.feedback_data:
        return 1.0 if feedback.feedback_data["validated_tags"] == aggregated_result.get("primary_answer") else 0.0
    return 0.0

def _calculate_drafting_consistency(feedback: models.Feedback, aggregated_result: dict) -> float:
    # For drafting, consistency might mean if the user's revised_target is close to the primary_answer
    # For simplicity, let's say 1.0 if the user's revised_target is the primary, 0.0 otherwise.
    if feedback.feedback_data and "revised_target" in feedback.feedback_data:
        return 1.0 if feedback.feedback_data["revised_target"] == aggregated_result.get("primary_answer") else 0.0
    return 0.0

# --- Main Consistency Dispatcher ---

CONSISTENCY_DISPATCHER = {
    TaskType.SUMMARIZATION: _calculate_summarization_consistency,
    TaskType.CLASSIFICATION: _calculate_classification_consistency,
    TaskType.QA: _calculate_qa_consistency,
    TaskType.PREDICTION: _calculate_prediction_consistency,
    TaskType.NLI: _calculate_nli_consistency,
    TaskType.NER: _calculate_ner_consistency,
    TaskType.DRAFTING: _calculate_drafting_consistency,
}

def calculate_and_store_consistency(db: Session, task_id: int, aggregated_result: dict):
    """
    Calculates and stores the consistency score for each feedback on a given task.
    This should be called after the task's feedback has been aggregated.
    This function now acts as a dispatcher based on the task_type.
    """
    task = db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
    if not task:
        return

    feedbacks = db.query(models.Feedback).join(models.Response).filter(models.Response.task_id == task_id).all()

    consistency_func = CONSISTENCY_DISPATCHER.get(task.task_type)
    if not consistency_func:
        # Fallback or error if no specific consistency logic is defined for this task type
        return

    for feedback in feedbacks:
        score = consistency_func(feedback, aggregated_result)
        feedback.consistency_score = score
    
    db.commit()
