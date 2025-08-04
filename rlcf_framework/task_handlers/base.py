from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from .. import models


class BaseTaskHandler(ABC):
    """
    Abstract base class for handling different types of legal tasks.

    This class defines the interface that all concrete task handlers must implement,
    ensuring a consistent structure for task-specific logic such as feedback aggregation,
    consistency calculation, and data formatting for export.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the BaseTaskHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        self.db = db
        self.task = task
        self._feedbacks = None  # Will be loaded async

    async def get_feedbacks(self):
        """Load feedbacks asynchronously if not already loaded."""
        if self._feedbacks is None:
            result = await self.db.execute(
                select(models.Feedback)
                .join(models.Response)
                .filter(models.Response.task_id == self.task.id)
            )
            self._feedbacks = result.scalars().all()
        return self._feedbacks

    @abstractmethod
    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback specific to the task type.

        This method should encapsulate the logic for combining individual feedback
        entries into a single, aggregated result, potentially considering authority scores.

        Returns:
            A dictionary representing the aggregated feedback result.
        """
        pass

    @abstractmethod
    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """
        Calculates the consistency score for a given feedback against the aggregated result.

        This method determines how well an individual feedback aligns with the overall
        aggregated consensus for the task.

        Args:
            feedback: The individual Feedback instance to evaluate.
            aggregated_result: The aggregated result for the task.

        Returns:
            A float representing the consistency score (e.g., 0.0 to 1.0).
        """
        pass

    @abstractmethod
    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """
        Prepares the task data for export in specified formats (e.g., SFT or Preference).

        This method should transform the task's feedback and aggregated results into
        a structure suitable for external consumption or model training.

        Args:
            format_type: A string indicating the desired export format (e.g., "SFT", "Preference").

        Returns:
            A list of dictionaries, each representing a formatted data entry for export.
        """
        pass

    @abstractmethod
    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """
        Calculates the correctness score for a given feedback against the ground truth.

        This method determines if an individual feedback is correct based on the provided
        ground truth data for the task.

        Args:
            feedback: The individual Feedback instance to evaluate.
            ground_truth: The ground truth data for the task.

        Returns:
            A float representing the correctness score (e.g., 0.0 or 1.0).
        """
        pass
