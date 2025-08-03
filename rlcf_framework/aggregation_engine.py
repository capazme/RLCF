from sqlalchemy.orm import Session
from . import models
from scipy.stats import entropy
from .config import model_settings
from .task_handlers import get_handler # Import the handler factory

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

def aggregate_with_uncertainty(db: Session, task_id: int) -> dict:
    """
    Implementa l'Algoritmo 1 (AGGREGATE_WITH_UNCERTAINTY) descritto nella Sez. 3.1 del paper.
    Il processo aggrega il feedback ponderato per autorità, calcola il disaccordo e produce
    un output che preserva l'incertezza se il disaccordo supera una soglia (tau).
    La soglia è definita in `model_settings.thresholds['disagreement']`.
    Questa function ora utilizza il Task Handler Pattern per delegare l'aggregazione.
    """
    task = db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
    if not task:
        return {"error": "Task not found.", "type": "Error"}

    handler = get_handler(db, task)
    aggregated_data = handler.aggregate_feedback()

    if "error" in aggregated_data:
        return aggregated_data # Return error from handler if no valid feedback

    # Calculate disagreement based on the aggregated data from the handler
    # This part assumes aggregated_data contains information suitable for disagreement calculation
    # For classification, aggregated_data["details"] (weighted_labels) can be used.
    # For other types, the handler should return a structure that allows for this.
    # For now, we'll use a simplified approach for disagreement calculation,
    # assuming 'details' key holds the weighted positions.
    disagreement_input = {str(k): v for k, v in aggregated_data.get("details", {}).items()}
    disagreement_score = calculate_disagreement(disagreement_input)

    # Apply uncertainty-preserving output structure based on disagreement_score
    if disagreement_score > model_settings.thresholds['disagreement']:
        # This part needs to be generalized based on the handler's output structure
        # For now, it's a placeholder, assuming primary_answer and alternative_positions
        return {
            "primary_answer": aggregated_data.get("consensus_answer"),
            "confidence_level": 1 - disagreement_score,
            "alternative_positions": [], # This needs to be populated by handler or generalized
            "expert_disagreement": {
                "consensus_areas": [],
                "contention_points": [],
                "reasoning_patterns": []
            },
            "epistemic_metadata": {
                "uncertainty_sources": [],
                "suggested_research": []
            }
        }
    else:
        return {
            "consensus_answer": aggregated_data.get("consensus_answer"),
            "confidence_level": 1 - disagreement_score,
        }
