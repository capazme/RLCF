from .base import BaseTaskHandler
from typing import Dict, Any, List
from .. import models
import numpy as np

class QAHandler(BaseTaskHandler):
    """Handler per task di Question Answering."""
    
    def aggregate_feedback(self) -> Dict[str, Any]:
        """Aggrega feedback per QA tasks."""
        if not self.feedbacks:
            return {"error": "No feedback available for this QA task."}
        
        answer_scores = {}
        answer_details = {}
        
        for fb in self.feedbacks:
            answer = fb.feedback_data.get("validated_answer", "")
            if not answer:
                continue
            
            # Normalizza la risposta per aggregazione
            normalized_answer = answer.strip().lower()
            
            if normalized_answer not in answer_scores:
                answer_scores[normalized_answer] = 0
                answer_details[normalized_answer] = {
                    'original_answers': [],
                    'supporters': [],
                    'reasoning': []
                }
            
            # Accumula peso basato sull'autorità
            weight = fb.author.authority_score
            answer_scores[normalized_answer] += weight
            
            # Colleziona dettagli
            answer_details[normalized_answer]['original_answers'].append(answer)
            answer_details[normalized_answer]['supporters'].append({
                'username': fb.author.username,
                'authority': fb.author.authority_score
            })
            
            if 'reasoning' in fb.feedback_data:
                answer_details[normalized_answer]['reasoning'].append(fb.feedback_data['reasoning'])
        
        if not answer_scores:
            return {"error": "No valid answers found."}
        
        # Trova risposta con maggior peso
        sorted_answers = sorted(answer_scores.items(), key=lambda x: x[1], reverse=True)
        best_answer_key, best_score = sorted_answers[0]
        
        # Prepara alternative answers
        alternative_answers = []
        total_weight = sum(answer_scores.values())
        
        for answer_key, score in sorted_answers[1:4]:  # Top 3 alternative
            details = answer_details[answer_key]
            alternative_answers.append({
                "answer": details['original_answers'][0] if details['original_answers'] else answer_key,
                "support_percentage": round((score / total_weight) * 100, 1),
                "supporter_count": len(details['supporters']),
                "top_reasoning": details['reasoning'][0] if details['reasoning'] else ""
            })
        
        # Calcola confidence basato sulla distribuzione
        confidence = best_score / total_weight if total_weight > 0 else 0
        
        # Seleziona la migliore versione dell'answer vincente
        best_answer_details = answer_details[best_answer_key]
        consensus_answer = best_answer_details['original_answers'][0] if best_answer_details['original_answers'] else best_answer_key
        
        return {
            "consensus_answer": consensus_answer,
            "confidence": round(confidence, 3),
            "support_percentage": round((best_score / total_weight) * 100, 1),
            "alternative_answers": alternative_answers,
            "total_evaluators": len(self.feedbacks),
            "details": answer_scores  # Per il calcolo del disagreement
        }
    
    def calculate_consistency(self, feedback: models.Feedback, aggregated_result: Dict[str, Any]) -> float:
        """Calcola consistency per QA."""
        user_answer = feedback.feedback_data.get("validated_answer", "").strip().lower()
        consensus_answer = aggregated_result.get("consensus_answer", "").strip().lower()
        
        if not user_answer or not consensus_answer:
            return 0.0
        
        # Exact match
        if user_answer == consensus_answer:
            return 1.0
        
        # Partial match basato su parole chiave comuni
        user_words = set(user_answer.split())
        consensus_words = set(consensus_answer.split())
        
        if not user_words or not consensus_words:
            return 0.0
        
        # Jaccard similarity
        intersection = len(user_words & consensus_words)
        union = len(user_words | consensus_words)
        
        jaccard_similarity = intersection / union if union > 0 else 0
        
        # Bonus per semantica simile (semplificato)
        semantic_bonus = 0
        key_legal_terms = ['guilty', 'liable', 'breach', 'violation', 'compliance', 'valid', 'invalid']
        
        user_legal_terms = [term for term in key_legal_terms if term in user_answer]
        consensus_legal_terms = [term for term in key_legal_terms if term in consensus_answer]
        
        if user_legal_terms and consensus_legal_terms:
            legal_match = len(set(user_legal_terms) & set(consensus_legal_terms))
            semantic_bonus = legal_match / max(len(user_legal_terms), len(consensus_legal_terms)) * 0.3
        
        return min(1.0, jaccard_similarity + semantic_bonus)
    
    def calculate_correctness(self, feedback: models.Feedback, ground_truth: Dict[str, Any]) -> float:
        """Calcola correctness rispetto al ground truth."""
        if not ground_truth:
            return 0.0
        
        user_answer = feedback.feedback_data.get("validated_answer", "").strip().lower()
        correct_answer = ground_truth.get("answer", "").strip().lower()
        
        if not user_answer or not correct_answer:
            return 0.0
        
        # Exact match
        if user_answer == correct_answer:
            return 1.0
        
        # Semantic similarity per risposte legali
        user_words = set(user_answer.split())
        correct_words = set(correct_answer.split())
        
        # Jaccard similarity with legal term weighting
        intersection = user_words & correct_words
        union = user_words | correct_words
        
        if not union:
            return 0.0
        
        # Peso maggiore per termini legali importanti
        legal_terms = {'yes', 'no', 'guilty', 'not guilty', 'liable', 'not liable', 
                      'valid', 'invalid', 'breach', 'no breach', 'violation', 'compliance'}
        
        legal_intersection = intersection & legal_terms
        legal_union = union & legal_terms
        
        if legal_union:
            # Se ci sono termini legali, pesali di più
            legal_score = len(legal_intersection) / len(legal_union)
            general_score = len(intersection - legal_terms) / len(union - legal_terms) if (union - legal_terms) else 0
            return min(1.0, legal_score * 0.8 + general_score * 0.2)
        else:
            # Altrimenti usa Jaccard standard
            return len(intersection) / len(union)


class SummarizationHandler(BaseTaskHandler):
    """Handler per task di Summarization."""
    
    def aggregate_feedback(self) -> Dict[str, Any]:
        """Aggrega feedback per Summarization tasks."""
        if not self.feedbacks:
            return {"error": "No feedback available for this summarization task."}
        
        # Raggruppa per rating e revisioni
        rating_weights = {'good': 0, 'bad': 0}
        revised_summaries = []
        
        for fb in self.feedbacks:
            rating = fb.feedback_data.get("rating")
            if rating in rating_weights:
                rating_weights[rating] += fb.author.authority_score
            
            revised_summary = fb.feedback_data.get("revised_summary")
            if revised_summary:
                revised_summaries.append({
                    'summary': revised_summary,
                    'author': fb.author.username,
                    'authority': fb.author.authority_score,
                    'rating': rating
                })
        
        total_weight = sum(rating_weights.values())
        if total_weight == 0:
            return {"error": "No valid ratings found."}
        
        # Determina consensus su quality
        good_percentage = (rating_weights['good'] / total_weight) * 100
        
        # Trova le migliori revisioni (da utenti con alta autorità e rating "good")
        good_revisions = [r for r in revised_summaries if r['rating'] == 'good']
        good_revisions.sort(key=lambda x: x['authority'], reverse=True)
        
        consensus_answer = "Summary quality acceptable" if good_percentage > 60 else "Summary needs improvement"
        
        if good_revisions and good_percentage <= 60:
            # Se la maggioranza dice "bad", usa la migliore revisione
            consensus_answer = good_revisions[0]['summary']
        
        return {
            "consensus_answer": consensus_answer,
            "confidence": abs(good_percentage - 50) / 50,  # Higher when more extreme
            "quality_assessment": {
                "good_percentage": round(good_percentage, 1),
                "bad_percentage": round(100 - good_percentage, 1)
            },
            "revised_summaries": good_revisions[:3],  # Top 3
            "details": rating_weights
        }
    
    def calculate_consistency(self, feedback: models.Feedback, aggregated_result: Dict[str, Any]) -> float:
        """Calcola consistency per Summarization."""
        user_rating = feedback.feedback_data.get("rating")
        quality_assessment = aggregated_result.get("quality_assessment", {})
        
        if not user_rating or not quality_assessment:
            return 0.0
        
        good_percentage = quality_assessment.get("good_percentage", 50)
        
        if user_rating == "good" and good_percentage > 50:
            return 1.0
        elif user_rating == "bad" and good_percentage < 50:
            return 1.0
        else:
            # Partial consistency based on how close to the threshold
            distance_from_threshold = abs(good_percentage - 50) / 50
            return 1 - distance_from_threshold


class PredictionHandler(BaseTaskHandler):
    """Handler per task di Prediction (outcome prediction)."""
    
    def aggregate_feedback(self) -> Dict[str, Any]:
        """Aggrega feedback per Prediction tasks."""
        if not self.feedbacks:
            return {"error": "No feedback available for this prediction task."}
        
        outcome_weights = {}
        
        for fb in self.feedbacks:
            outcome = fb.feedback_data.get("chosen_outcome")
            if outcome:
                if outcome not in outcome_weights:
                    outcome_weights[outcome] = 0
                outcome_weights[outcome] += fb.author.authority_score
        
        if not outcome_weights:
            return {"error": "No valid predictions found."}
        
        # Trova outcome più probabile
        sorted_outcomes = sorted(outcome_weights.items(), key=lambda x: x[1], reverse=True)
        predicted_outcome, max_weight = sorted_outcomes[0]
        
        total_weight = sum(outcome_weights.values())
        confidence = max_weight / total_weight if total_weight > 0 else 0
        
        # Calcola probabilità per ogni outcome
        outcome_probabilities = {
            outcome: round((weight / total_weight) * 100, 1)
            for outcome, weight in outcome_weights.items()
        }
        
        return {
            "consensus_answer": f"Predicted outcome: {predicted_outcome}",
            "confidence": round(confidence, 3),
            "predicted_outcome": predicted_outcome,
            "outcome_probabilities": outcome_probabilities,
            "details": outcome_weights
        }
    
    def calculate_consistency(self, feedback: models.Feedback, aggregated_result: Dict[str, Any]) -> float:
        """Calcola consistency per Prediction."""
        user_prediction = feedback.feedback_data.get("chosen_outcome")
        predicted_outcome = aggregated_result.get("predicted_outcome")
        
        if not user_prediction or not predicted_outcome:
            return 0.0
        
        return 1.0 if user_prediction == predicted_outcome else 0.0


class NLIHandler(BaseTaskHandler):
    """Handler per Natural Language Inference tasks."""
    
    def aggregate_feedback(self) -> Dict[str, Any]:
        """Aggrega feedback per NLI tasks."""
        if not self.feedbacks:
            return {"error": "No feedback available for this NLI task."}
        
        label_weights = {}
        
        for fb in self.feedbacks:
            label = fb.feedback_data.get("chosen_label")
            if label:
                if label not in label_weights:
                    label_weights[label] = 0
                label_weights[label] += fb.author.authority_score
        
        if not label_weights:
            return {"error": "No valid labels found."}
        
        # Trova label più probabile
        sorted_labels = sorted(label_weights.items(), key=lambda x: x[1], reverse=True)
        consensus_label, max_weight = sorted_labels[0]
        
        total_weight = sum(label_weights.values())
        confidence = max_weight / total_weight if total_weight > 0 else 0
        
        return {
            "consensus_answer": f"Relationship: {consensus_label}",
            "confidence": round(confidence, 3),
            "consensus_label": consensus_label,
            "label_distribution": {
                label: round((weight / total_weight) * 100, 1)
                for label, weight in label_weights.items()
            },
            "details": label_weights
        }
    
    def calculate_consistency(self, feedback: models.Feedback, aggregated_result: Dict[str, Any]) -> float:
        """Calcola consistency per NLI."""
        user_label = feedback.feedback_data.get("chosen_label")
        consensus_label = aggregated_result.get("consensus_label")
        
        return 1.0 if user_label == consensus_label else 0.0


class NERHandler(BaseTaskHandler):
    """Handler per Named Entity Recognition tasks."""
    
    def aggregate_feedback(self) -> Dict[str, Any]:
        """Aggrega feedback per NER tasks."""
        if not self.feedbacks:
            return {"error": "No feedback available for this NER task."}
        
        # Aggrega tags per posizione
        tag_positions = {}
        
        for fb in self.feedbacks:
            validated_tags = fb.feedback_data.get("validated_tags", [])
            if not isinstance(validated_tags, list):
                continue
            
            for i, tag in enumerate(validated_tags):
                if i not in tag_positions:
                    tag_positions[i] = {}
                
                if tag not in tag_positions[i]:
                    tag_positions[i][tag] = 0
                
                tag_positions[i][tag] += fb.author.authority_score
        
        if not tag_positions:
            return {"error": "No valid tags found."}
        
        # Determina consensus tags
        consensus_tags = []
        confidence_scores = []
        
        max_position = max(tag_positions.keys())
        
        for i in range(max_position + 1):
            if i in tag_positions:
                position_tags = tag_positions[i]
                total_weight = sum(position_tags.values())
                
                if total_weight > 0:
                    best_tag = max(position_tags.items(), key=lambda x: x[1])
                    consensus_tags.append(best_tag[0])
                    confidence_scores.append(best_tag[1] / total_weight)
                else:
                    consensus_tags.append("O")
                    confidence_scores.append(0.0)
            else:
                consensus_tags.append("O")
                confidence_scores.append(0.0)
        
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
        
        return {
            "consensus_answer": f"NER tags: {' '.join(consensus_tags)}",
            "confidence": round(avg_confidence, 3),
            "consensus_tags": consensus_tags,
            "position_confidence": confidence_scores,
            "details": {str(i): tags for i, tags in tag_positions.items()}
        }
    
    def calculate_consistency(self, feedback: models.Feedback, aggregated_result: Dict[str, Any]) -> float:
        """Calcola consistency per NER."""
        user_tags = feedback.feedback_data.get("validated_tags", [])
        consensus_tags = aggregated_result.get("consensus_tags", [])
        
        if not user_tags or not consensus_tags:
            return 0.0
        
        # Calcola accuracy per posizione
        min_length = min(len(user_tags), len(consensus_tags))
        if min_length == 0:
            return 0.0
        
        matches = sum(1 for i in range(min_length) if user_tags[i] == consensus_tags[i])
        return matches / max(len(user_tags), len(consensus_tags))


class DraftingHandler(BaseTaskHandler):
    """Handler per Legal Drafting tasks."""
    
    def aggregate_feedback(self) -> Dict[str, Any]:
        """Aggrega feedback per Drafting tasks."""
        if not self.feedbacks:
            return {"error": "No feedback available for this drafting task."}
        
        # Raggruppa per rating e revisioni
        rating_weights = {'better': 0, 'worse': 0}
        revised_drafts = []
        
        for fb in self.feedbacks:
            rating = fb.feedback_data.get("rating")
            if rating in rating_weights:
                rating_weights[rating] += fb.author.authority_score
            
            revised_target = fb.feedback_data.get("revised_target")
            reasoning = fb.feedback_data.get("reasoning", "")
            if revised_target:
                revised_drafts.append({
                    'draft': revised_target,
                    'author': fb.author.username,
                    'authority': fb.author.authority_score,
                    'rating': rating,
                    'reasoning': reasoning
                })
        
        total_weight = sum(rating_weights.values())
        if total_weight == 0:
            return {"error": "No valid ratings found."}
        
        better_percentage = (rating_weights['better'] / total_weight) * 100
        
        # Trova le migliori revisioni
        better_revisions = [r for r in revised_drafts if r['rating'] == 'better']
        better_revisions.sort(key=lambda x: x['authority'], reverse=True)
        
        if better_percentage > 60:
            consensus_answer = "Draft quality is acceptable"
        else:
            consensus_answer = better_revisions[0]['draft'] if better_revisions else "Draft needs significant improvement"
        
        return {
            "consensus_answer": consensus_answer,
            "confidence": abs(better_percentage - 50) / 50,
            "quality_assessment": {
                "better_percentage": round(better_percentage, 1),
                "worse_percentage": round(100 - better_percentage, 1)
            },
            "revised_drafts": better_revisions[:3],
            "details": rating_weights
        }
    
    def calculate_consistency(self, feedback: models.Feedback, aggregated_result: Dict[str, Any]) -> float:
        """Calcola consistency per Drafting."""
        user_rating = feedback.feedback_data.get("rating")
        quality_assessment = aggregated_result.get("quality_assessment", {})
        
        if not user_rating or not quality_assessment:
            return 0.0
        
        better_percentage = quality_assessment.get("better_percentage", 50)
        
        if user_rating == "better" and better_percentage > 50:
            return 1.0
        elif user_rating == "worse" and better_percentage < 50:
            return 1.0
        else:
            distance_from_threshold = abs(better_percentage - 50) / 50
            return 1 - distance_from_threshold
    
    def calculate_correctness(self, feedback: models.Feedback, ground_truth: Dict[str, Any]) -> float:
        """Calcola correctness per Drafting confrontando con il target ground truth."""
        if not ground_truth or 'target' not in ground_truth:
            return 0.0
        
        user_revision = feedback.feedback_data.get("revised_target", "").strip()
        ground_truth_target = ground_truth['target'].strip()
        
        if not user_revision or not ground_truth_target:
            return 0.0
        
        # Semantic similarity semplificata per drafting legale
        user_words = set(user_revision.lower().split())
        gt_words = set(ground_truth_target.lower().split())
        
        # Jaccard similarity
        intersection = len(user_words & gt_words)
        union = len(user_words | gt_words)
        
        if union == 0:
            return 0.0
        
        # Bonus per preservare termini legali chiave
        legal_terms = {'shall', 'agreement', 'party', 'hereby', 'whereas', 'pursuant', 'notwithstanding'}
        gt_legal_terms = gt_words & legal_terms
        user_legal_terms = user_words & legal_terms
        
        legal_preservation = len(gt_legal_terms & user_legal_terms) / max(len(gt_legal_terms), 1)
        
        base_similarity = intersection / union
        return min(1.0, base_similarity * 0.7 + legal_preservation * 0.3)