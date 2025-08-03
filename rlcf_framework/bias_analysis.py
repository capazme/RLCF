from sqlalchemy.orm import Session
from . import models
from collections import Counter, defaultdict
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import entropy

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

def calculate_demographic_bias(db: Session, task_id: int) -> float:
    """
    Calcola il bias demografico analizzando la correlazione tra
    caratteristiche demografiche e posizioni prese.
    """
    feedbacks = db.query(models.Feedback).join(models.Response).filter(
        models.Response.task_id == task_id
    ).all()
    
    # Raggruppa per caratteristiche demografiche (es. esperienza)
    experience_groups = defaultdict(list)
    for fb in feedbacks:
        exp_cred = db.query(models.Credential).filter(
            models.Credential.user_id == fb.user_id,
            models.Credential.type == "PROFESSIONAL_EXPERIENCE"
        ).first()
        
        if exp_cred:
            exp_years = float(exp_cred.value)
            if exp_years < 5:
                group = "junior"
            elif exp_years < 15:
                group = "mid"
            else:
                group = "senior"
            
            experience_groups[group].append(str(fb.feedback_data))
    
    # Calcola omogeneità all'interno dei gruppi
    group_homogeneity_scores = []
    for group, positions in experience_groups.items():
        if len(positions) > 1:
            position_counts = Counter(positions)
            total = len(positions)
            homogeneity = max(position_counts.values()) / total
            group_homogeneity_scores.append(homogeneity)
    
    # Alta omogeneità = alto bias demografico
    return np.mean(group_homogeneity_scores) if group_homogeneity_scores else 0.0

def calculate_temporal_bias(db: Session, task_id: int) -> float:
    """
    Calcola il bias temporale analizzando come le opinioni
    cambiano nel tempo durante la valutazione.
    """
    feedbacks = db.query(models.Feedback).join(models.Response).filter(
        models.Response.task_id == task_id
    ).order_by(models.Feedback.submitted_at).all()
    
    if len(feedbacks) < 4:
        return 0.0
    
    # Dividi in prima metà e seconda metà
    mid_point = len(feedbacks) // 2
    first_half = feedbacks[:mid_point]
    second_half = feedbacks[mid_point:]
    
    # Conta posizioni in ogni metà
    first_positions = Counter(str(fb.feedback_data) for fb in first_half)
    second_positions = Counter(str(fb.feedback_data) for fb in second_half)
    
    # Calcola drift come differenza nelle distribuzioni
    all_positions = set(first_positions.keys()) | set(second_positions.keys())
    
    drift_score = 0.0
    for pos in all_positions:
        first_freq = first_positions.get(pos, 0) / len(first_half)
        second_freq = second_positions.get(pos, 0) / len(second_half)
        drift_score += abs(first_freq - second_freq)
    
    return drift_score / 2  # Normalizza a [0, 1]

def calculate_geographic_bias(db: Session, task_id: int) -> float:
    """
    Calcola il bias geografico se disponibili dati di localizzazione.
    """
    # Placeholder - in produzione useresti dati reali di localizzazione
    # Per ora, simula usando il "campo" professionale come proxy
    feedbacks = db.query(models.Feedback).join(models.Response).filter(
        models.Response.task_id == task_id
    ).all()
    
    field_positions = defaultdict(list)
    
    for fb in feedbacks:
        field_cred = db.query(models.Credential).filter(
            models.Credential.user_id == fb.user_id,
            models.Credential.type == "PROFESSIONAL_FIELD"
        ).first()
        
        if field_cred:
            field_positions[field_cred.value].append(str(fb.feedback_data))
    
    # Calcola omogeneità per campo
    field_homogeneity_scores = []
    for field, positions in field_positions.items():
        if len(positions) > 1:
            position_counts = Counter(positions)
            total = len(positions)
            homogeneity = max(position_counts.values()) / total
            field_homogeneity_scores.append(homogeneity)
    
    return np.mean(field_homogeneity_scores) if field_homogeneity_scores else 0.0

def calculate_confirmation_bias(db: Session, task_id: int) -> float:
    """Calcola il bias di conferma analizzando se gli utenti tendono a confermare le loro posizioni precedenti."""
    feedbacks = db.query(models.Feedback).join(models.Response).filter(
        models.Response.task_id == task_id
    ).all()
    
    confirmation_scores = []
    
    for fb in feedbacks:
        # Trova feedback precedenti dello stesso utente su task simili
        user_task_type = fb.response.task.task_type
        previous_feedbacks = db.query(models.Feedback).join(models.Response).join(models.LegalTask).filter(
            models.Feedback.user_id == fb.user_id,
            models.LegalTask.task_type == user_task_type,
            models.Feedback.submitted_at < fb.submitted_at
        ).all()
        
        if previous_feedbacks:
            # Calcola similarità con posizioni precedenti
            current_position = str(fb.feedback_data)
            similar_previous = sum(1 for prev_fb in previous_feedbacks 
                                 if str(prev_fb.feedback_data) == current_position)
            confirmation_score = similar_previous / len(previous_feedbacks)
            confirmation_scores.append(confirmation_score)
    
    return np.mean(confirmation_scores) if confirmation_scores else 0.0

def calculate_anchoring_bias(db: Session, task_id: int) -> float:
    """Calcola il bias di ancoraggio analizzando l'influenza delle prime risposte sulle successive."""
    feedbacks = db.query(models.Feedback).join(models.Response).filter(
        models.Response.task_id == task_id
    ).order_by(models.Feedback.submitted_at).all()
    
    if len(feedbacks) < 5:
        return 0.0
    
    # Prendi le prime 3 risposte come "ancora"
    anchor_feedbacks = feedbacks[:3]
    subsequent_feedbacks = feedbacks[3:]
    
    # Calcola distribuzione delle posizioni nell'ancora
    anchor_positions = Counter(str(fb.feedback_data) for fb in anchor_feedbacks)
    anchor_dominant = anchor_positions.most_common(1)[0][0]
    
    # Calcola quante risposte successive seguono la posizione dominante dell'ancora
    subsequent_following_anchor = sum(
        1 for fb in subsequent_feedbacks 
        if str(fb.feedback_data) == anchor_dominant
    )
    
    if not subsequent_feedbacks:
        return 0.0
    
    return subsequent_following_anchor / len(subsequent_feedbacks)

def calculate_total_bias(db: Session, task_id: int) -> dict:
    """
    Calcola tutti i tipi di bias e ritorna un report completo.
    """
    b1 = calculate_demographic_bias(db, task_id)
    b2 = calculate_professional_clustering_bias(db, 
        db.query(models.Feedback).join(models.Response).filter(
            models.Response.task_id == task_id
        ).first().user_id if db.query(models.Feedback).join(models.Response).filter(
            models.Response.task_id == task_id
        ).first() else 0, 
        task_id
    )
    b3 = calculate_temporal_bias(db, task_id)
    b4 = calculate_geographic_bias(db, task_id)
    b5 = calculate_confirmation_bias(db, task_id)
    b6 = calculate_anchoring_bias(db, task_id)
    
    # Calcola bias totale come norma euclidea
    bias_components = [b1, b2, b3, b4, b5, b6]
    total_bias = np.sqrt(sum(b**2 for b in bias_components))
    
    return {
        'demographic_bias': round(b1, 3),
        'professional_clustering': round(b2, 3),
        'temporal_drift': round(b3, 3),
        'geographic_concentration': round(b4, 3),
        'confirmation_bias': round(b5, 3),
        'anchoring_bias': round(b6, 3),
        'total_bias_score': round(total_bias, 3),
        'bias_level': 'high' if total_bias > 1.0 else 'medium' if total_bias > 0.5 else 'low',
        'dominant_bias_types': sorted(
            [('demographic', b1), ('professional', b2), ('temporal', b3), 
             ('geographic', b4), ('confirmation', b5), ('anchoring', b6)],
            key=lambda x: x[1], reverse=True
        )[:3]
    }

def generate_bias_mitigation_recommendations(bias_report: dict) -> list:
    """Genera raccomandazioni per mitigare i bias identificati."""
    recommendations = []
    
    if bias_report['demographic_bias'] > 0.6:
        recommendations.append({
            'type': 'demographic',
            'priority': 'high',
            'action': 'Ensure diverse participation across experience levels',
            'implementation': 'Set quotas for junior, mid-level, and senior participants'
        })
    
    if bias_report['professional_clustering'] > 0.6:
        recommendations.append({
            'type': 'professional',
            'priority': 'high', 
            'action': 'Cross-pollinate between professional fields',
            'implementation': 'Require evaluation from at least 2 different specializations'
        })
    
    if bias_report['temporal_drift'] > 0.4:
        recommendations.append({
            'type': 'temporal',
            'priority': 'medium',
            'action': 'Implement blind evaluation periods',
            'implementation': 'Hide timestamps and previous responses during evaluation'
        })
    
    if bias_report['confirmation_bias'] > 0.5:
        recommendations.append({
            'type': 'confirmation',
            'priority': 'medium',
            'action': 'Encourage devil\'s advocate participation',
            'implementation': 'Assign 10-15% of evaluators as devil\'s advocates'
        })
    
    if bias_report['anchoring_bias'] > 0.6:
        recommendations.append({
            'type': 'anchoring',
            'priority': 'high',
            'action': 'Randomize response presentation order',
            'implementation': 'Show responses in random order to each evaluator'
        })
    
    return recommendations

def calculate_authority_correctness_correlation(db: Session) -> float:
    """
    Calcola la correlazione di Pearson tra il punteggio di autorità degli utenti
    e i loro punteggi di correttezza aggregati.
    """
    users = db.query(models.User).all()
    authority_scores = []
    correctness_scores = []

    for user in users:
        user_feedbacks = db.query(models.Feedback).filter(models.Feedback.user_id == user.id).all()
        if not user_feedbacks: continue

        # Aggregate correctness scores for the user
        total_correctness = sum([fb.correctness_score for fb in user_feedbacks if fb.correctness_score is not None])
        num_correctness_scores = len([fb for fb in user_feedbacks if fb.correctness_score is not None])

        if num_correctness_scores > 0:
            avg_correctness = total_correctness / num_correctness_scores
            authority_scores.append(user.authority_score)
            correctness_scores.append(avg_correctness)

    if len(authority_scores) < 2: # Need at least two data points for correlation
        return 0.0

    return np.corrcoef(authority_scores, correctness_scores)[0, 1]
