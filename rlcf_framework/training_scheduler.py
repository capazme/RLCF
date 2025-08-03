from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from . import models, authority_module, bias_analysis
from typing import Dict, Any, List
import json
import numpy as np

class PeriodicTrainingScheduler:
    """
    Gestisce il ciclo di training periodico di 14 giorni.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.training_cycle_days = 14
    
    def get_current_cycle_phase(self) -> str:
        """Determina in quale fase del ciclo ci troviamo."""
        day_of_cycle = datetime.utcnow().day % self.training_cycle_days
        
        if day_of_cycle <= 7:
            return "collection"
        elif day_of_cycle <= 10:
            return "validation"
        elif day_of_cycle <= 12:
            return "training"
        else:
            return "accountability"
    
    def get_cycle_dates(self, cycle_start: datetime = None) -> Dict[str, datetime]:
        """Calcola le date chiave per un ciclo di training."""
        if cycle_start is None:
            cycle_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return {
            'cycle_start': cycle_start,
            'collection_end': cycle_start + timedelta(days=7),
            'validation_end': cycle_start + timedelta(days=10),
            'training_end': cycle_start + timedelta(days=12),
            'cycle_end': cycle_start + timedelta(days=self.training_cycle_days)
        }
    
    def collect_feedback_batch(self, start_date: datetime, end_date: datetime) -> List[models.Feedback]:
        """Raccoglie tutti i feedback in un periodo."""
        return self.db.query(models.Feedback).filter(
            models.Feedback.submitted_at >= start_date,
            models.Feedback.submitted_at <= end_date
        ).all()
    
    def validate_feedback_batch(self, feedbacks: List[models.Feedback]) -> List[models.Feedback]:
        """Valida un batch di feedback con review degli esperti."""
        validated_feedbacks = []
        
        for fb in feedbacks:
            is_valid = True
            
            # Controllo autorità dell'autore
            if fb.author.authority_score < 0.5:
                is_valid = False
            
            # Controllo completezza del feedback
            if not fb.feedback_data or len(str(fb.feedback_data)) < 20:
                is_valid = False
            
            # Controllo qualità tecnica
            quality_scores = [
                fb.accuracy_score or 0,
                fb.utility_score or 0,
                fb.transparency_score or 0
            ]
            avg_quality = np.mean([s for s in quality_scores if s > 0])
            
            if avg_quality < 6.0:
                is_valid = False
            
            if is_valid:
                validated_feedbacks.append(fb)
        
        return validated_feedbacks
    
    def calculate_training_metrics(self, cycle_start: datetime) -> Dict[str, Any]:
        """Calcola metriche per il training del ciclo."""
        cycle_dates = self.get_cycle_dates(cycle_start)
        
        cycle_feedbacks = self.collect_feedback_batch(
            cycle_dates['cycle_start'],
            cycle_dates['cycle_end']
        )
        
        if not cycle_feedbacks:
            return {'error': 'No feedback collected in cycle'}
        
        validated_feedbacks = self.validate_feedback_batch(cycle_feedbacks)
        
        participating_users = set(fb.user_id for fb in cycle_feedbacks)
        validated_users = set(fb.user_id for fb in validated_feedbacks)
        
        quality_metrics = self._calculate_quality_metrics(validated_feedbacks)
        
        return {
            'cycle_period': {
                'start': cycle_dates['cycle_start'].isoformat(),
                'end': cycle_dates['cycle_end'].isoformat()
            },
            'participation': {
                'total_feedbacks': len(cycle_feedbacks),
                'validated_feedbacks': len(validated_feedbacks),
                'validation_rate': len(validated_feedbacks) / max(len(cycle_feedbacks), 1),
                'unique_participants': len(participating_users),
                'validated_participants': len(validated_users)
            },
            'quality': quality_metrics
        }
    
    def _calculate_quality_metrics(self, feedbacks: List[models.Feedback]) -> Dict[str, float]:
        """Calcola metriche di qualità aggregate."""
        if not feedbacks:
            return {}
        
        accuracy_scores = [fb.accuracy_score for fb in feedbacks if fb.accuracy_score is not None]
        utility_scores = [fb.utility_score for fb in feedbacks if fb.utility_score is not None]
        transparency_scores = [fb.transparency_score for fb in feedbacks if fb.transparency_score is not None]
        
        return {
            'avg_accuracy': round(np.mean(accuracy_scores), 2) if accuracy_scores else 0,
            'avg_utility': round(np.mean(utility_scores), 2) if utility_scores else 0,
            'avg_transparency': round(np.mean(transparency_scores), 2) if transparency_scores else 0,
        }
    
    def generate_accountability_report(self, cycle_start: datetime) -> Dict[str, Any]:
        """Genera il report di accountability per il ciclo."""
        cycle_dates = self.get_cycle_dates(cycle_start)
        
        training_metrics = self.calculate_training_metrics(cycle_start)
        
        if 'error' in training_metrics:
            return training_metrics
        
        report = {
            'cycle_id': f"{cycle_start.date()}_to_{cycle_dates['cycle_end'].date()}",
            'timestamp': datetime.utcnow().isoformat(),
            'training_metrics': training_metrics,
            'recommendations': ["System performance is stable - maintain current practices"]
        }
        
        # Salva il report
        db_report = models.AccountabilityReport(
            cycle_start=cycle_start,
            cycle_end=cycle_dates['cycle_end'],
            report_data=report,
            published_at=datetime.utcnow()
        )
        self.db.add(db_report)
        self.db.commit()
        
        return report