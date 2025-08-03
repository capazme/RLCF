import random
from sqlalchemy.orm import Session
from . import models
from typing import List

class DevilsAdvocateAssigner:
    """Gestisce l'assegnazione casuale di devil's advocates."""
    
    def __init__(self, advocate_percentage: float = 0.1):
        self.advocate_percentage = advocate_percentage
    
    def assign_advocates_for_task(self, db: Session, task_id: int) -> List[int]:
        """
        Assegna casualmente devil's advocates per un task.
        Ritorna lista di user_id assegnati come advocates.
        """
        # Trova tutti gli utenti che potrebbero valutare questo task
        # In produzione, useresti criteri più sofisticati
        all_users = db.query(models.User).filter(
            models.User.authority_score > 0.5  # Solo utenti con minima autorità
        ).all()
        
        num_advocates = max(1, int(len(all_users) * self.advocate_percentage))
        advocates = random.sample(all_users, min(num_advocates, len(all_users)))
        
        # Salva l'assegnazione nel database
        for user in advocates:
            advocate_assignment = models.DevilsAdvocateAssignment(
                task_id=task_id,
                user_id=user.id,
                instructions="Your role is to critically evaluate this response. "
                           "Look for weaknesses, alternative interpretations, and "
                           "potential issues. Be constructively critical."
            )
            db.add(advocate_assignment)
        
        db.commit()
        return [user.id for user in advocates]
    
    def is_devils_advocate(self, db: Session, task_id: int, user_id: int) -> bool:
        """Verifica se un utente è devil's advocate per un task."""
        assignment = db.query(models.DevilsAdvocateAssignment).filter(
            models.DevilsAdvocateAssignment.task_id == task_id,
            models.DevilsAdvocateAssignment.user_id == user_id
        ).first()
        return assignment is not None
    
    def get_advocates_for_task(self, db: Session, task_id: int) -> List[dict]:
        """Ottiene tutti i devil's advocates per un task."""
        assignments = db.query(models.DevilsAdvocateAssignment).filter(
            models.DevilsAdvocateAssignment.task_id == task_id
        ).all()
        
        return [{
            'user_id': assignment.user_id,
            'username': assignment.user.username,
            'instructions': assignment.instructions,
            'assigned_at': assignment.assigned_at
        } for assignment in assignments]
    
    def generate_critical_prompts(self, task_type: str) -> List[str]:
        """
        Genera prompt specifici per tipo di task per guidare la critica costruttiva.
        """
        base_prompts = [
            "What are the potential weaknesses in this reasoning?",
            "Are there alternative interpretations that weren't considered?",
            "What assumptions might be flawed or questionable?",
            "How might this conclusion be challenged by opposing counsel?",
            "What additional evidence would strengthen or weaken this position?"
        ]
        
        task_specific_prompts = {
            "CLASSIFICATION": [
                "Are the classification criteria clearly defined and consistently applied?",
                "Could this text legitimately belong to multiple categories?",
                "What edge cases might challenge this classification?"
            ],
            "QA": [
                "Is the answer complete and directly responsive to the question?",
                "What important nuances or exceptions are missing?",
                "How might the context change the interpretation?"
            ],
            "SUMMARIZATION": [
                "Does this summary capture all essential points?",
                "What important details or caveats are omitted?",
                "Is the summary biased toward any particular viewpoint?"
            ],
            "PREDICTION": [
                "What factors could lead to a different outcome?",
                "How reliable are the precedents being used?",
                "What changed circumstances might affect this prediction?"
            ]
        }
        
        return base_prompts + task_specific_prompts.get(task_type, [])
    
    def evaluate_advocate_effectiveness(self, db: Session, task_id: int) -> dict:
        """
        Valuta l'efficacia del processo devil's advocate per un task.
        """
        advocates = self.get_advocates_for_task(db, task_id)
        
        # Ottieni feedback dei devil's advocates
        advocate_feedback = []
        for advocate in advocates:
            feedback = db.query(models.Feedback).join(models.Response).filter(
                models.Response.task_id == task_id,
                models.Feedback.user_id == advocate['user_id']
            ).all()
            advocate_feedback.extend(feedback)
        
        # Ottieni feedback generale
        all_feedback = db.query(models.Feedback).join(models.Response).filter(
            models.Response.task_id == task_id
        ).all()
        
        if not all_feedback:
            return {"error": "No feedback available for evaluation"}
        
        # Calcola metriche di efficacia
        advocate_ids = [a['user_id'] for a in advocates]
        regular_feedback = [f for f in all_feedback if f.user_id not in advocate_ids]
        
        # Analizza differenze nella distribuzione delle posizioni
        advocate_positions = {}
        regular_positions = {}
        
        for fb in advocate_feedback:
            pos_key = str(sorted(fb.feedback_data.items()))
            advocate_positions[pos_key] = advocate_positions.get(pos_key, 0) + 1
        
        for fb in regular_feedback:
            pos_key = str(sorted(fb.feedback_data.items()))
            regular_positions[pos_key] = regular_positions.get(pos_key, 0) + 1
        
        # Calcola diversità introdotta
        all_positions = set(advocate_positions.keys()) | set(regular_positions.keys())
        positions_only_advocates = set(advocate_positions.keys()) - set(regular_positions.keys())
        
        diversity_introduced = len(positions_only_advocates) / len(all_positions) if all_positions else 0
        
        return {
            "advocates_count": len(advocates),
            "advocate_feedback_count": len(advocate_feedback),
            "regular_feedback_count": len(regular_feedback),
            "unique_positions_by_advocates": len(set(advocate_positions.keys())),
            "unique_positions_by_regulars": len(set(regular_positions.keys())),
            "diversity_introduced": round(diversity_introduced, 3),
            "effectiveness_score": round(diversity_introduced * 0.7 + 
                                       (len(advocate_feedback) / max(len(advocates), 1)) * 0.3, 3)
        }


def assign_devils_advocates_batch(db: Session, task_ids: List[int], 
                                advocate_percentage: float = 0.1) -> dict:
    """
    Assegna devil's advocates a un batch di task.
    Utile per esperimenti controllati.
    """
    assigner = DevilsAdvocateAssigner(advocate_percentage)
    results = {}
    
    for task_id in task_ids:
        try:
            advocates = assigner.assign_advocates_for_task(db, task_id)
            results[task_id] = {
                "success": True,
                "advocates_assigned": len(advocates),
                "advocate_user_ids": advocates
            }
        except Exception as e:
            results[task_id] = {
                "success": False,
                "error": str(e)
            }
    
    return results


def generate_devils_advocate_report(db: Session, task_id: int) -> dict:
    """
    Genera un report completo sull'efficacia del devil's advocate per un task.
    """
    assigner = DevilsAdvocateAssigner()
    
    # Ottieni informazioni base
    advocates = assigner.get_advocates_for_task(db, task_id)
    effectiveness = assigner.evaluate_advocate_effectiveness(db, task_id)
    
    # Analizza quality dei feedback critici
    advocate_ids = [a['user_id'] for a in advocates]
    advocate_feedback = db.query(models.Feedback).join(models.Response).filter(
        models.Response.task_id == task_id,
        models.Feedback.user_id.in_(advocate_ids)
    ).all()
    
    # Calcola metriche di quality
    avg_reasoning_length = 0
    critical_elements_found = 0
    
    critical_keywords = [
        'however', 'although', 'but', 'weakness', 'problem', 'issue',
        'alternative', 'concern', 'risk', 'limitation', 'exception'
    ]
    
    for fb in advocate_feedback:
        reasoning = fb.feedback_data.get('reasoning', '').lower()
        avg_reasoning_length += len(reasoning.split())
        
        # Conta elementi critici
        critical_elements_found += sum(1 for keyword in critical_keywords 
                                     if keyword in reasoning)
    
    if advocate_feedback:
        avg_reasoning_length /= len(advocate_feedback)
    
    return {
        "task_id": task_id,
        "devils_advocate_summary": {
            "advocates_assigned": len(advocates),
            "advocates_participated": len(advocate_feedback),
            "participation_rate": len(advocate_feedback) / max(len(advocates), 1)
        },
        "effectiveness_metrics": effectiveness,
        "quality_analysis": {
            "avg_reasoning_length": round(avg_reasoning_length, 1),
            "critical_elements_per_feedback": round(critical_elements_found / max(len(advocate_feedback), 1), 2),
            "engagement_score": round((avg_reasoning_length / 50) * 0.6 + 
                                    (critical_elements_found / max(len(advocate_feedback), 1)) * 0.4, 3)
        },
        "recommendations": [
            "Increase advocate participation" if len(advocate_feedback) < len(advocates) * 0.8 else None,
            "Improve critical engagement" if critical_elements_found < len(advocate_feedback) * 2 else None,
            "Expand advocate pool" if effectiveness.get('diversity_introduced', 0) < 0.2 else None
        ]
    }