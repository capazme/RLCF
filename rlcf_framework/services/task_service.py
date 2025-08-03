from sqlalchemy.orm import Session
from .. import models, aggregation_engine, post_processing, bias_analysis

def orchestrate_task_aggregation(db: Session, task_id: int):
    """
    Orchestra il processo completo di aggregazione, post-processing e analisi bias per un task.
    """
    # 1. Calcola il risultato aggregato
    result = aggregation_engine.aggregate_with_uncertainty(db, task_id)
    if "error" in result:
        # In un sistema reale, gestire l'errore in modo più robusto
        return

    # 2. Calcola e salva il punteggio di coerenza per ogni feedback
    post_processing.calculate_and_store_consistency(db, task_id, result)

    # 3. Calcola e salva il punteggio di correttezza per ogni feedback (se ground truth disponibile)
    post_processing.calculate_and_store_correctness(db, task_id)

    # 4. Calcola e salva il bias per ogni partecipante
    participants = db.query(models.User).join(models.Feedback).join(models.Response).filter(models.Response.task_id == task_id).distinct().all()
    
    for user in participants:
        bias_score = bias_analysis.calculate_professional_clustering_bias(db, user.id, task_id)
        db_report = models.BiasReport(
            task_id=task_id,
            user_id=user.id,
            bias_type="PROFESSIONAL_CLUSTERING",
            bias_score=bias_score
        )
        db.add(db_report)
    
    db.commit()

