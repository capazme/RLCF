from sqlalchemy.orm import Session
from . import models
from collections import Counter

def calculate_professional_clustering_bias(db: Session, user_id: int, task_id: int) -> float:
    """
    Calcola il bias di un utente come la sua deviazione dal consenso del suo gruppo professionale.
    Restituisce 1.0 se l'utente è in disaccordo con il suo gruppo, 0.0 altrimenti.
    """
    # 1. Trova il gruppo professionale dell'utente (es. 'Diritto Civile')
    user_credential = db.query(models.Credential).filter_by(user_id=user_id, type="PROFESSIONAL_FIELD").first()
    if not user_credential:
        return 0.0 # L'utente non ha un gruppo professionale definito, non si può calcolare il bias
    
    professional_group = user_credential.value

    # 2. Trova tutti i feedback per quel task dati da utenti dello stesso gruppo
    group_feedbacks = db.query(models.Feedback).join(models.User).join(models.Credential).filter(
            models.Credential.type == "PROFESSIONAL_FIELD",
            models.Credential.value == professional_group,
            models.Feedback.response.has(task_id=task_id) # Assicura che il feedback sia per il task corretto
        ).all()

    if not group_feedbacks or len(group_feedbacks) < 2: # Se non c'è un gruppo o l'utente è l'unico
            return 0.0

    # 3. Calcola la posizione di consenso del gruppo
    position_counts = Counter(f.position for f in group_feedbacks)
    group_consensus_position = position_counts.most_common(1)[0][0]

    # 4. Trova la posizione dell'utente specifico
    user_feedback = next((f for f in group_feedbacks if f.user_id == user_id), None)
    if not user_feedback:
        return 0.0

    # 5. Calcola il bias
    bias_score = 0.0 if user_feedback.position == group_consensus_position else 1.0
    return bias_score
