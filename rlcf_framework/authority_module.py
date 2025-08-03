import numpy
from sqlalchemy.orm import Session
from . import models
from .config import model_settings # Importa la nuova configurazione
from math import sqrt # Per usare nelle formule

def calculate_baseline_credentials(db: Session, user_id: int) -> float:
    """
    Calcola il punteggio delle credenziali di base (B_u) per un utente.
    Implementa la formula di somma ponderata descritta nella Sez. 2.2 del paper.
    Le regole, i pesi (w_i) e le funzioni di punteggio (c_i) sono caricate dinamicamente
    dal file model_config.yaml, rendendo il motore generico e configurabile.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return 0.0

    total_score = 0.0
    
    # Carica le regole dal file di configurazione
    rules = model_settings.baseline_credentials.types

    for cred in user.credentials:
        if cred.type not in rules:
            continue # Salta le credenziali non definite nelle regole

        rule = rules[cred.type]
        score = 0.0
        
        # Applica la scoring function definita nel YAML
        scoring_func = rule.scoring_function
        if scoring_func.type == "map":
            score = scoring_func.values.get(str(cred.value), scoring_func.default)
        
        elif scoring_func.type == "formula":
            try:
                # Ambiente sicuro per l'eval. Per produzione, usare 'asteval' o simili.
                safe_globals = {"__builtins__": {"sqrt": sqrt, "min": min, "max": max}}
                safe_locals = {'value': float(cred.value)}
                score = eval(scoring_func.expression, safe_globals, safe_locals)
            except (ValueError, SyntaxError, NameError):
                score = 0.0 # Default a 0 in caso di errore nella formula o nel valore
        
        # Applica il peso generale per questo tipo di credenziale (w_i)
        total_score += rule.weight * score

    user.baseline_credential_score = total_score
    db.commit()
    db.refresh(user)
    return total_score

# ... (il resto del file rimane simile ma deve usare 'model_settings')
def calculate_quality_score(db: Session, feedback: models.Feedback) -> float:
    """Calcola il punteggio di qualità aggregato (Q_u(t)) per un singolo feedback."""
    ratings = db.query(models.FeedbackRating).filter(models.FeedbackRating.feedback_id == feedback.id).all()
    q1 = numpy.mean([r.helpfulness_score for r in ratings]) / 5.0 if ratings else 0.5
    q2 = feedback.accuracy_score / 5.0
    q3 = feedback.consistency_score if feedback.consistency_score is not None else 0.5
    q4 = feedback.community_helpfulness_rating / 5.0 if feedback.community_helpfulness_rating else q1
    return (q1 + q2 + q3 + q4) / 4

def update_track_record(db: Session, user_id: int, quality_score: float) -> float:
    """Aggiorna lo storico delle performance (T_u) di un utente.""" 
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: return 0.0
    current_track_record = user.track_record_score
    update_factor = model_settings.track_record.get('update_factor', 0.05)
    new_track_record = ((1 - update_factor) * current_track_record + update_factor * quality_score)
    user.track_record_score = new_track_record
    db.commit()
    db.refresh(user)
    return new_track_record

def update_authority_score(db: Session, user_id: int, recent_performance: float) -> float:
    """Aggiorna il punteggio di autorità complessivo (A_u) di un utente."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: return 0.0
    weights = model_settings.authority_weights
    b_u = user.baseline_credential_score
    t_u = user.track_record_score
    new_authority_score = (weights.get('baseline_credentials', 0.3) * b_u +
                           weights.get('track_record', 0.5) * t_u +
                           weights.get('recent_performance', 0.2) * recent_performance)
    user.authority_score = new_authority_score
    db.commit()
    db.refresh(user)
    return new_authority_score