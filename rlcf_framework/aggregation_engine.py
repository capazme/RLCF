from sqlalchemy.orm import Session
from . import models
from .models import TaskType # Import TaskType
import numpy
from scipy.stats import entropy
from .config import model_settings
from collections import Counter

def calculate_disagreement(weighted_feedback: dict) -> float:
    """
    Quantifica il livello di disaccordo (delta) usando l'entropia di Shannon normalizzata.
    Implementa l'Eq. 4 del paper (Sez. 3.2).
    L'input è un dizionario di posizioni ponderate per l'autorità degli utenti che le supportano.
    """
    if not weighted_feedback or len(weighted_feedback) <= 1:
        return 0.0

    total_authority_weight = sum(weighted_feedback.values())
    if total_authority_weight == 0:
        return 0.0

    probabilities = [weight / total_authority_weight for weight in weighted_feedback.values()]
    
    num_positions = len(probabilities)
    if num_positions <= 1:
        return 0.0

    return entropy(probabilities, base=num_positions)

# --- Task-specific Aggregation Functions ---

def _aggregate_summarization(feedbacks: list[models.Feedback], task: models.LegalTask) -> dict:
    # For summarization, we might aggregate based on 'revised_summary' and 'rating'
    # For simplicity, let's just pick the highest rated summary by authority
    weighted_summaries = Counter()
    for fb in feedbacks:
        if fb.feedback_data and "revised_summary" in fb.feedback_data and "rating" in fb.feedback_data:
            summary = fb.feedback_data["revised_summary"]
            rating = fb.feedback_data["rating"]
            authority = fb.author.authority_score
            
            # Simple weighting: good=1.0, bad=0.5 (example)
            rating_weight = 1.0 if rating == "good" else 0.5
            weighted_summaries[summary] += authority * rating_weight
    
    if not weighted_summaries:
        return {"error": "No valid summarization feedback.", "type": "No Consensus"}

    primary_summary = weighted_summaries.most_common(1)[0][0]
    # Disagreement calculation for summarization is more complex, might involve semantic similarity
    # For now, we'll use a placeholder or simplify.
    # Let's use the general disagreement for now, based on the primary summary vs others
    
    # Simplified disagreement for summarization: how many unique summaries are there?
    unique_summaries = len(weighted_summaries)
    # This is a very basic proxy for disagreement. A real implementation would use NLP metrics.
    disagreement_proxy = 0.0 if unique_summaries <= 1 else 0.5 # Placeholder

    return {
        "primary_answer": primary_summary,
        "confidence_level": 1 - disagreement_proxy,
        "type": "Consensus" if disagreement_proxy <= model_settings.thresholds['disagreement'] else "Disagreement",
        "details": weighted_summaries # For debugging
    }

def _aggregate_classification(feedbacks: list[models.Feedback], task: models.LegalTask) -> dict:
    # For classification, aggregate based on 'validated_labels'
    # We need to find the most authoritative set of labels
    weighted_label_sets = Counter()
    for fb in feedbacks:
        if fb.feedback_data and "validated_labels" in fb.feedback_data:
            labels_tuple = tuple(sorted(fb.feedback_data["validated_labels"]))
            authority = fb.author.authority_score
            weighted_label_sets[labels_tuple] += authority
    
    if not weighted_label_sets:
        return {"error": "No valid classification feedback.", "type": "No Consensus"}

    primary_labels = list(weighted_label_sets.most_common(1)[0][0])
    
    # Calculate disagreement based on label sets
    total_weight = sum(weighted_label_sets.values())
    if total_weight == 0: # Avoid division by zero
        return {"error": "No authoritative classification feedback.", "type": "No Consensus"}

    # Convert weighted label sets to a format suitable for calculate_disagreement
    # This is a simplification: treating each unique label set as a 'position'
    disagreement_input = {str(k): v for k, v in weighted_label_sets.items()}
    disagreement_score = calculate_disagreement(disagreement_input)

    if disagreement_score > model_settings.thresholds['disagreement']:
        alternative_label_sets = []
        for labels, weight in weighted_label_sets.items():
            if list(labels) != primary_labels:
                alternative_label_sets.append({
                    "labels": list(labels),
                    "support_percentage": weight / total_weight
                })
        return {
            "type": "Disagreement",
            "primary_answer": primary_labels,
            "confidence_level": 1 - disagreement_score,
            "alternative_positions": alternative_label_sets
        }
    else:
        return {
            "type": "Consensus",
            "consensus_answer": primary_labels,
            "confidence_level": 1 - disagreement_score,
        }

def _aggregate_qa(feedbacks: list[models.Feedback], task: models.LegalTask) -> dict:
    # For QA, aggregate based on 'validated_answer' and 'position' (correct/incorrect)
    weighted_answers = Counter()
    for fb in feedbacks:
        if fb.feedback_data and "validated_answer" in fb.feedback_data and "position" in fb.feedback_data:
            answer = fb.feedback_data["validated_answer"]
            position = fb.feedback_data["position"]
            authority = fb.author.authority_score
            
            # Weight by correctness and authority
            answer_weight = authority * (1.0 if position == "correct" else 0.1) # Penalize incorrect answers
            weighted_answers[answer] += answer_weight
    
    if not weighted_answers:
        return {"error": "No valid QA feedback.", "type": "No Consensus"}

    primary_answer = weighted_answers.most_common(1)[0][0]
    
    # Disagreement for QA: how much authority supports 'incorrect' or different answers
    total_weight = sum(weighted_answers.values())
    if total_weight == 0: # Avoid division by zero
        return {"error": "No authoritative QA feedback.", "type": "No Consensus"}

    disagreement_input = {str(k): v for k, v in weighted_answers.items()}
    disagreement_score = calculate_disagreement(disagreement_input)

    if disagreement_score > model_settings.thresholds['disagreement']:
        alternative_answers = []
        for ans, weight in weighted_answers.items():
            if ans != primary_answer:
                alternative_answers.append({
                    "answer": ans,
                    "support_percentage": weight / total_weight
                })
        return {
            "type": "Disagreement",
            "primary_answer": primary_answer,
            "confidence_level": 1 - disagreement_score,
            "alternative_positions": alternative_answers
        }
    else:
        return {
            "type": "Consensus",
            "consensus_answer": primary_answer,
            "confidence_level": 1 - disagreement_score,
        }

def _aggregate_prediction(feedbacks: list[models.Feedback], task: models.LegalTask) -> dict:
    # For prediction, aggregate based on 'chosen_outcome'
    weighted_outcomes = Counter()
    for fb in feedbacks:
        if fb.feedback_data and "chosen_outcome" in fb.feedback_data:
            outcome = fb.feedback_data["chosen_outcome"]
            authority = fb.author.authority_score
            weighted_outcomes[outcome] += authority
    
    if not weighted_outcomes:
        return {"error": "No valid prediction feedback.", "type": "No Consensus"}

    primary_outcome = weighted_outcomes.most_common(1)[0][0]
    
    total_weight = sum(weighted_outcomes.values())
    if total_weight == 0: # Avoid division by zero
        return {"error": "No authoritative prediction feedback.", "type": "No Consensus"}

    disagreement_input = {str(k): v for k, v in weighted_outcomes.items()}
    disagreement_score = calculate_disagreement(disagreement_input)

    if disagreement_score > model_settings.thresholds['disagreement']:
        alternative_outcomes = []
        for outcome, weight in weighted_outcomes.items():
            if outcome != primary_outcome:
                alternative_outcomes.append({
                    "outcome": outcome,
                    "support_percentage": weight / total_weight
                })
        return {
            "type": "Disagreement",
            "primary_answer": primary_outcome,
            "confidence_level": 1 - disagreement_score,
            "alternative_positions": alternative_outcomes
        }
    else:
        return {
            "type": "Consensus",
            "consensus_answer": primary_outcome,
            "confidence_level": 1 - disagreement_score,
        }

def _aggregate_nli(feedbacks: list[models.Feedback], task: models.LegalTask) -> dict:
    # For NLI, aggregate based on 'chosen_label'
    weighted_labels = Counter()
    for fb in feedbacks:
        if fb.feedback_data and "chosen_label" in fb.feedback_data:
            label = fb.feedback_data["chosen_label"]
            authority = fb.author.authority_score
            weighted_labels[label] += authority
    
    if not weighted_labels:
        return {"error": "No valid NLI feedback.", "type": "No Consensus"}

    primary_label = weighted_labels.most_common(1)[0][0]
    
    total_weight = sum(weighted_labels.values())
    if total_weight == 0: # Avoid division by zero
        return {"error": "No authoritative NLI feedback.", "type": "No Consensus"}

    disagreement_input = {str(k): v for k, v in weighted_labels.items()}
    disagreement_score = calculate_disagreement(disagreement_input)

    if disagreement_score > model_settings.thresholds['disagreement']:
        alternative_labels = []
        for label, weight in weighted_labels.items():
            if label != primary_label:
                alternative_labels.append({
                    "label": label,
                    "support_percentage": weight / total_weight
                })
        return {
            "type": "Disagreement",
            "primary_answer": primary_label,
            "confidence_level": 1 - disagreement_score,
            "alternative_positions": alternative_labels
        }
    else:
        return {
            "type": "Consensus",
            "consensus_answer": primary_label,
            "confidence_level": 1 - disagreement_score,
        }

def _aggregate_ner(feedbacks: list[models.Feedback], task: models.LegalTask) -> dict:
    # For NER, aggregate based on 'validated_tags'
    # This is complex as it involves sequence labeling. For simplicity, we'll aggregate based on exact tag sequence match.
    weighted_tag_sequences = Counter()
    for fb in feedbacks:
        if fb.feedback_data and "validated_tags" in fb.feedback_data:
            tags_tuple = tuple(fb.feedback_data["validated_tags"])
            authority = fb.author.authority_score
            weighted_tag_sequences[tags_tuple] += authority
    
    if not weighted_tag_sequences:
        return {"error": "No valid NER feedback.", "type": "No Consensus"}

    primary_tags = list(weighted_tag_sequences.most_common(1)[0][0])
    
    total_weight = sum(weighted_tag_sequences.values())
    if total_weight == 0: # Avoid division by zero
        return {"error": "No authoritative NER feedback.", "type": "No Consensus"}

    disagreement_input = {str(k): v for k, v in weighted_tag_sequences.items()}
    disagreement_score = calculate_disagreement(disagreement_input)

    if disagreement_score > model_settings.thresholds['disagreement']:
        alternative_tag_sequences = []
        for tags, weight in weighted_tag_sequences.items():
            if list(tags) != primary_tags:
                alternative_tag_sequences.append({
                    "tags": list(tags),
                    "support_percentage": weight / total_weight
                })
        return {
            "type": "Disagreement",
            "primary_answer": primary_tags,
            "confidence_level": 1 - disagreement_score,
            "alternative_positions": alternative_tag_sequences
        }
    else:
        return {
            "type": "Consensus",
            "consensus_answer": primary_tags,
            "confidence_level": 1 - disagreement_score,
        }

def _aggregate_drafting(feedbacks: list[models.Feedback], task: models.LegalTask) -> dict:
    # For drafting, aggregate based on 'revised_target' and 'rating' (better/worse)
    weighted_drafts = Counter()
    for fb in feedbacks:
        if fb.feedback_data and "revised_target" in fb.feedback_data and "rating" in fb.feedback_data:
            draft = fb.feedback_data["revised_target"]
            rating = fb.feedback_data["rating"]
            authority = fb.author.authority_score
            
            # Simple weighting: better=1.0, worse=0.5 (example)
            rating_weight = 1.0 if rating == "better" else 0.5
            weighted_drafts[draft] += authority * rating_weight
    
    if not weighted_drafts:
        return {"error": "No valid drafting feedback.", "type": "No Consensus"}

    primary_draft = weighted_drafts.most_common(1)[0][0]
    
    total_weight = sum(weighted_drafts.values())
    if total_weight == 0: # Avoid division by zero
        return {"error": "No authoritative drafting feedback.", "type": "No Consensus"}

    disagreement_input = {str(k): v for k, v in weighted_drafts.items()}
    disagreement_score = calculate_disagreement(disagreement_input)

    if disagreement_score > model_settings.thresholds['disagreement']:
        alternative_drafts = []
        for draft, weight in weighted_drafts.items():
            if draft != primary_draft:
                alternative_drafts.append({
                    "draft": draft,
                    "support_percentage": weight / total_weight
                })
        return {
            "type": "Disagreement",
            "primary_answer": primary_draft,
            "confidence_level": 1 - disagreement_score,
            "alternative_positions": alternative_drafts
        }
    else:
        return {
            "type": "Consensus",
            "consensus_answer": primary_draft,
            "confidence_level": 1 - disagreement_score,
        }

# --- Main Aggregation Dispatcher ---

AGGREGATION_DISPATCHER = {
    TaskType.SUMMARIZATION: _aggregate_summarization,
    TaskType.CLASSIFICATION: _aggregate_classification,
    TaskType.QA: _aggregate_qa,
    TaskType.PREDICTION: _aggregate_prediction,
    TaskType.NLI: _aggregate_nli,
    TaskType.NER: _aggregate_ner,
    TaskType.DRAFTING: _aggregate_drafting,
}

def aggregate_with_uncertainty(db: Session, task_id: int) -> dict:
    """
    Implementa l'Algoritmo 1 (AGGREGATE_WITH_UNCERTAINTY) descritto nella Sez. 3.1 del paper.
    Il processo aggrega il feedback ponderato per autorità, calcola il disaccordo e produce
    un output che preserva l'incertezza se il disaccordo supera una soglia (tau).
    La soglia è definita in `model_settings.thresholds['disagreement']`.
    Questa funzione ora agisce come un dispatcher basato sul task_type.
    """
    task = db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
    if not task:
        return {"error": "Task not found.", "type": "Error"}

    task_feedbacks = db.query(models.Feedback).join(models.Response).filter(models.Response.task_id == task_id).all()

    if not task_feedbacks:
        return {"error": "No feedback found for this task.", "type": "No Consensus"}

    # Dispatch to the appropriate aggregation function
    agg_func = AGGREGATION_DISPATCHER.get(task.task_type)
    if not agg_func:
        return {"error": f"No aggregation logic for task type {task.task_type}.", "type": "Error"}

    return agg_func(task_feedbacks, task)
