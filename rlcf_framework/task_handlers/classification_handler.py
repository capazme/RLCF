from .base import BaseTaskHandler
from collections import Counter
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models


class ClassificationHandler(BaseTaskHandler):
    """
    A concrete task handler for classification tasks.

    This handler implements the specific logic for aggregating feedback,
    calculating consistency, and formatting data for export related to
    classification tasks.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the ClassificationHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for classification tasks.

        It calculates a weighted count of validated labels based on the
        authority score of the feedback authors.

        Returns:
            A dictionary containing the consensus answer (primary labels)
            and detailed weighted label counts.
        """
        feedbacks = await self.get_feedbacks()
        weighted_labels = Counter()
        for fb in feedbacks:
            labels_tuple = tuple(sorted(fb.feedback_data.get("validated_labels", [])))
            if not labels_tuple:
                continue
            weighted_labels[labels_tuple] += fb.author.authority_score

        if not weighted_labels:
            return {"error": "No valid feedback."}

        primary_labels = list(weighted_labels.most_common(1)[0][0])
        return {"consensus_answer": primary_labels, "details": weighted_labels}

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """
        Calculates the consistency of a single feedback with the aggregated result
        for a classification task.

        Consistency is 1.0 if the feedback's validated labels match the aggregated
        consensus labels, otherwise 0.0.

        Args:
            feedback: The individual Feedback instance.
            aggregated_result: The aggregated result for the task.

        Returns:
            A float representing the consistency score.
        """
        validated_labels = feedback.feedback_data.get("validated_labels")
        if validated_labels is None:
            return 0.0
        return (
            1.0
            if sorted(validated_labels)
            == sorted(aggregated_result.get("consensus_answer"))
            else 0.0
        )

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """
        Formats the data for export for classification tasks.

        Currently returns an empty list as the export logic is not yet implemented.

        Args:
            format_type: The desired export format (e.g., "SFT", "Preference").

        Returns:
            A list of dictionaries, each representing a formatted data entry for export.
        """
        # Implementa la logica di esportazione per questo task
        # ...
        return []

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """
        Calculates the correctness score for a classification feedback.

        Compares the feedback's validated labels with the ground truth labels.

        Args:
            feedback: The individual Feedback instance.
            ground_truth: The ground truth data for the task, expected to contain 'labels'.

        Returns:
            1.0 if the validated labels match the ground truth labels, otherwise 0.0.
        """
        validated_labels = feedback.feedback_data.get("validated_labels")
        if validated_labels is None:
            return 0.0

        ground_truth_labels = ground_truth.get("labels")
        if ground_truth_labels is None:
            return 0.0

        return 1.0 if sorted(validated_labels) == sorted(ground_truth_labels) else 0.0
