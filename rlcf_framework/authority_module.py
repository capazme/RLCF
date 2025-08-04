import numpy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import models
from .config import model_settings  # Importa la nuova configurazione
from math import sqrt  # Per usare nelle formule
import asteval

# Create a single asteval interpreter instance for reuse
_evaluator = None


def _get_evaluator():
    """Get or create the asteval interpreter for safe formula evaluation."""
    global _evaluator
    if _evaluator is None:
        _evaluator = asteval.Interpreter()
        _evaluator.symtable.update({"sqrt": sqrt, "min": min, "max": max})
    return _evaluator


async def calculate_baseline_credentials(db: AsyncSession, user_id: int) -> float:
    """
    Calcola il punteggio delle credenziali di base (B_u) per un utente.
    Implementa la formula di somma ponderata descritta nella Sez. 2.2 del paper.
    Le regole, i pesi (w_i) e le funzioni di punteggio (c_i) sono caricate dinamicamente
    dal file model_config.yaml, rendendo il motore generico e configurabile.

    Args:
        db: AsyncSession for database operations
        user_id: ID of the user to calculate credentials for

    Returns:
        float: Calculated baseline credential score
    """
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return 0.0

    total_score = 0.0

    # Carica le regole dal file di configurazione
    rules = model_settings.baseline_credentials.types
    evaluator = _get_evaluator()

    for cred in user.credentials:
        if cred.type not in rules:
            continue  # Salta le credenziali non definite nelle regole

        rule = rules[cred.type]
        score = 0.0

        # Applica la scoring function definita nel YAML
        scoring_func = rule.scoring_function
        if scoring_func.type == "map":
            score = scoring_func.values.get(str(cred.value), scoring_func.default)

        elif scoring_func.type == "formula":
            try:
                # Use asteval for safe formula evaluation
                evaluator.symtable["value"] = float(cred.value)
                score = evaluator.eval(scoring_func.expression)
                if score is None:
                    score = 0.0
            except (ValueError, SyntaxError, NameError):
                score = 0.0  # Default a 0 in caso di errore nella formula o nel valore

        # Applica il peso generale per questo tipo di credenziale (w_i)
        total_score += rule.weight * score

    user.baseline_credential_score = total_score
    await db.commit()
    await db.refresh(user)
    return total_score


# ... (il resto del file rimane simile ma deve usare 'model_settings')
async def calculate_quality_score(db: AsyncSession, feedback: models.Feedback) -> float:
    """
    Calcola il punteggio di qualità aggregato (Q_u(t)) per un singolo feedback.

    Args:
        db: AsyncSession for database operations
        feedback: Feedback instance to calculate quality score for

    Returns:
        float: Calculated quality score
    """
    result = await db.execute(
        select(models.FeedbackRating).filter(
            models.FeedbackRating.feedback_id == feedback.id
        )
    )
    ratings = result.scalars().all()
    q1 = numpy.mean([r.helpfulness_score for r in ratings]) / 5.0 if ratings else 0.5
    q2 = feedback.accuracy_score / 5.0
    q3 = feedback.consistency_score if feedback.consistency_score is not None else 0.5
    q4 = (
        feedback.community_helpfulness_rating / 5.0
        if feedback.community_helpfulness_rating
        else q1
    )
    return (q1 + q2 + q3 + q4) / 4


async def update_track_record(
    db: AsyncSession, user_id: int, quality_score: float
) -> float:
    """
    Aggiorna lo storico delle performance (T_u) di un utente.

    Args:
        db: AsyncSession for database operations
        user_id: ID of the user to update
        quality_score: Quality score to incorporate into track record

    Returns:
        float: Updated track record score
    """
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return 0.0
    current_track_record = user.track_record_score
    update_factor = model_settings.track_record.get("update_factor", 0.05)
    new_track_record = (
        1 - update_factor
    ) * current_track_record + update_factor * quality_score
    user.track_record_score = new_track_record
    await db.commit()
    await db.refresh(user)
    return new_track_record


async def update_authority_score(
    db: AsyncSession, user_id: int, recent_performance: float
) -> float:
    """
    Aggiorna il punteggio di autorità complessivo (A_u) di un utente.

    Args:
        db: AsyncSession for database operations
        user_id: ID of the user to update
        recent_performance: Recent performance score

    Returns:
        float: Updated authority score
    """
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return 0.0
    weights = model_settings.authority_weights
    b_u = user.baseline_credential_score
    t_u = user.track_record_score
    new_authority_score = (
        weights.get("baseline_credentials", 0.3) * b_u
        + weights.get("track_record", 0.5) * t_u
        + weights.get("recent_performance", 0.2) * recent_performance
    )
    user.authority_score = new_authority_score
    await db.commit()
    await db.refresh(user)
    return new_authority_score
