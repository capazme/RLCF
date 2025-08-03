from sqlalchemy.orm import Session
from . import models
from scipy.stats import entropy
from .config import model_settings
from .task_handlers import get_handler
from collections import Counter, defaultdict
import numpy as np

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

def extract_positions_from_feedback(feedbacks):
    """Estrae le posizioni distinte dai feedback con i loro sostenitori."""
    position_supporters = defaultdict(list)
    
    for fb in feedbacks:
        position_key = str(sorted(fb.feedback_data.items()))
        position_supporters[position_key].append({
            'user_id': fb.user_id,
            'username': fb.author.username,
            'authority': fb.author.authority_score,
            'reasoning': fb.feedback_data.get('reasoning', '')
        })
    
    return position_supporters

def identify_consensus_and_contention(feedbacks):
    """Identifica aree di consenso e punti di contesa."""
    all_keys = set()
    key_values = defaultdict(Counter)
    
    for fb in feedbacks:
        for key, value in fb.feedback_data.items():
            all_keys.add(key)
            key_values[key][str(value)] += fb.author.authority_score
    
    consensus_areas = []
    contention_points = []
    
    for key in all_keys:
        values = key_values[key]
        if len(values) == 1:
            consensus_areas.append(f"{key}: {list(values.keys())[0]}")
        else:
            total = sum(values.values())
            probs = [v/total for v in values.values()]
            disagreement = entropy(probs)
            if disagreement > 0.5:
                contention_points.append({
                    'aspect': key,
                    'positions': dict(values),
                    'disagreement_level': disagreement
                })
    
    return consensus_areas, contention_points

def extract_reasoning_patterns(feedbacks):
    """Estrae pattern di ragionamento dai feedback."""
    patterns = defaultdict(list)
    
    for fb in feedbacks:
        if 'reasoning' in fb.feedback_data:
            reasoning = fb.feedback_data['reasoning'].lower()
            if 'precedent' in reasoning or 'case law' in reasoning:
                patterns['precedent-based'].append(fb.user_id)
            elif 'principle' in reasoning or 'fundamental' in reasoning:
                patterns['principle-based'].append(fb.user_id)
            elif 'practical' in reasoning or 'consequence' in reasoning:
                patterns['pragmatic'].append(fb.user_id)
            else:
                patterns['other'].append(fb.user_id)
    
    return dict(patterns)

def aggregate_with_uncertainty(db: Session, task_id: int) -> dict:
    """
    Implementazione completa dell'Algoritmo 1 con preservazione dell'incertezza.
    """
    task = db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
    if not task:
        return {"error": "Task not found.", "type": "Error"}

    # Get all feedback for this task
    feedbacks = db.query(models.Feedback).join(models.Response).filter(
        models.Response.task_id == task_id
    ).all()
    
    if not feedbacks:
        return {"error": "No feedback found for this task.", "type": "NoFeedback"}
    
    # Calculate weighted positions
    handler = get_handler(db, task)
    aggregated_data = handler.aggregate_feedback()
    
    if "error" in aggregated_data:
        return aggregated_data
    
    # Extract positions and calculate disagreement
    position_supporters = extract_positions_from_feedback(feedbacks)
    
    # Calculate disagreement score
    weighted_positions = {}
    for pos, supporters in position_supporters.items():
        total_authority = sum(s['authority'] for s in supporters)
        weighted_positions[pos] = total_authority
    
    disagreement_score = calculate_disagreement(weighted_positions)
    
    # Identify consensus and contention
    consensus_areas, contention_points = identify_consensus_and_contention(feedbacks)
    
    # Extract reasoning patterns
    reasoning_patterns = extract_reasoning_patterns(feedbacks)
    
    # Build uncertainty-aware output
    if disagreement_score > model_settings.thresholds['disagreement']:
        # High disagreement - produce full uncertainty-preserving output
        
        # Find majority and minority positions
        sorted_positions = sorted(weighted_positions.items(), key=lambda x: x[1], reverse=True)
        primary_position = sorted_positions[0][0] if sorted_positions else None
        
        alternative_positions = []
        for pos, weight in sorted_positions[1:]:
            supporters = position_supporters[pos]
            alternative_positions.append({
                "position": pos,
                "support": f"{(weight / sum(weighted_positions.values()) * 100):.1f}%",
                "supporters": [s['username'] for s in supporters[:3]],
                "reasoning": supporters[0]['reasoning'] if supporters else ""
            })
        
        # Generate research suggestions based on contention points
        research_suggestions = []
        for point in contention_points[:3]:
            research_suggestions.append(
                f"Further investigate {point['aspect']} - "
                f"disagreement level: {point['disagreement_level']:.2f}"
            )
        
        return {
            "primary_answer": aggregated_data.get("consensus_answer"),
            "confidence_level": round(1 - disagreement_score, 2),
            "alternative_positions": alternative_positions,
            "expert_disagreement": {
                "consensus_areas": consensus_areas,
                "contention_points": contention_points,
                "reasoning_patterns": reasoning_patterns
            },
            "epistemic_metadata": {
                "uncertainty_sources": ["expert_disagreement", "multiple_valid_interpretations"],
                "suggested_research": research_suggestions
            },
            "transparency_metrics": {
                "evaluator_count": len(feedbacks),
                "total_authority_weight": sum(weighted_positions.values()),
                "disagreement_score": round(disagreement_score, 3)
            }
        }
    else:
        # Low disagreement - return consensus output
        return {
            "consensus_answer": aggregated_data.get("consensus_answer"),
            "confidence_level": round(1 - disagreement_score, 2),
            "transparency_metrics": {
                "evaluator_count": len(feedbacks),
                "consensus_strength": "high",
                "disagreement_score": round(disagreement_score, 3)
            }
        }
