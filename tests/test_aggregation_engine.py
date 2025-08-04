"""
Tests for the aggregation engine.

This module tests the Uncertainty-Preserving Aggregation Algorithm,
including disagreement calculation, position extraction, and consensus building.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from rlcf_framework import aggregation_engine


class TestCalculateDisagreement:
    """Test cases for calculate_disagreement function."""

    def test_calculate_disagreement_high_disagreement(self):
        """Test disagreement calculation with high disagreement."""
        # Equal weights - maximum disagreement
        weighted_feedback = {"position_a": 1.0, "position_b": 1.0, "position_c": 1.0}

        disagreement = aggregation_engine.calculate_disagreement(weighted_feedback)

        # Should be close to 1.0 (maximum disagreement)
        assert isinstance(disagreement, float)
        assert 0.8 <= disagreement <= 1.0

    def test_calculate_disagreement_low_disagreement(self):
        """Test disagreement calculation with low disagreement."""
        # One dominant position
        weighted_feedback = {"position_a": 10.0, "position_b": 1.0, "position_c": 1.0}

        disagreement = aggregation_engine.calculate_disagreement(weighted_feedback)

        # Should be lower than high disagreement case
        assert isinstance(disagreement, float)
        assert 0.0 <= disagreement <= 0.8

    def test_calculate_disagreement_consensus(self):
        """Test disagreement calculation with perfect consensus."""
        # Only one position
        weighted_feedback = {"position_a": 5.0}

        disagreement = aggregation_engine.calculate_disagreement(weighted_feedback)

        assert disagreement == 0.0

    def test_calculate_disagreement_empty_feedback(self):
        """Test disagreement calculation with empty feedback."""
        disagreement = aggregation_engine.calculate_disagreement({})
        assert disagreement == 0.0

        disagreement = aggregation_engine.calculate_disagreement(None)
        assert disagreement == 0.0

    def test_calculate_disagreement_zero_weights(self):
        """Test disagreement calculation with zero weights."""
        weighted_feedback = {"position_a": 0.0, "position_b": 0.0}

        disagreement = aggregation_engine.calculate_disagreement(weighted_feedback)
        assert disagreement == 0.0


class TestExtractPositionsFromFeedback:
    """Test cases for extract_positions_from_feedback function."""

    def test_extract_positions_basic(self):
        """Test basic position extraction from feedback."""
        # Mock feedback objects
        feedback1 = MagicMock()
        feedback1.feedback_data = {"answer": "yes", "confidence": "high"}
        feedback1.user_id = 1
        feedback1.author.username = "user1"
        feedback1.author.authority_score = 0.8

        feedback2 = MagicMock()
        feedback2.feedback_data = {"answer": "no", "confidence": "medium"}
        feedback2.user_id = 2
        feedback2.author.username = "user2"
        feedback2.author.authority_score = 0.6

        feedback3 = MagicMock()
        feedback3.feedback_data = {"answer": "yes", "confidence": "high"}
        feedback3.user_id = 3
        feedback3.author.username = "user3"
        feedback3.author.authority_score = 0.9

        feedbacks = [feedback1, feedback2, feedback3]

        positions = aggregation_engine.extract_positions_from_feedback(feedbacks)

        # Should have 2 unique positions
        assert len(positions) == 2

        # Check that similar feedback is grouped together
        for position_key, supporters in positions.items():
            assert len(supporters) >= 1
            for supporter in supporters:
                assert "user_id" in supporter
                assert "username" in supporter
                assert "authority" in supporter
                assert "reasoning" in supporter

    def test_extract_positions_empty_feedback(self):
        """Test position extraction with empty feedback."""
        positions = aggregation_engine.extract_positions_from_feedback([])
        assert len(positions) == 0

    def test_extract_positions_with_reasoning(self):
        """Test position extraction with reasoning field."""
        feedback = MagicMock()
        feedback.feedback_data = {"answer": "yes", "reasoning": "Based on precedent X"}
        feedback.user_id = 1
        feedback.author.username = "user1"
        feedback.author.authority_score = 0.8

        positions = aggregation_engine.extract_positions_from_feedback([feedback])

        assert len(positions) == 1
        position_key = list(positions.keys())[0]
        supporters = positions[position_key]
        assert supporters[0]["reasoning"] == "Based on precedent X"


class TestIdentifyConsensusAndContention:
    """Test cases for identify_consensus_and_contention function."""

    def test_identify_consensus_and_contention_mixed(self):
        """Test identification with both consensus and contention areas."""
        # Mock feedback with mixed agreement patterns
        feedback1 = MagicMock()
        feedback1.feedback_data = {"verdict": "guilty", "confidence": "high"}
        feedback1.author.authority_score = 0.8

        feedback2 = MagicMock()
        feedback2.feedback_data = {"verdict": "guilty", "confidence": "medium"}
        feedback2.author.authority_score = 0.7

        feedback3 = MagicMock()
        feedback3.feedback_data = {"verdict": "not_guilty", "confidence": "high"}
        feedback3.author.authority_score = 0.9

        feedbacks = [feedback1, feedback2, feedback3]

        consensus_areas, contention_points = (
            aggregation_engine.identify_consensus_and_contention(feedbacks)
        )

        # Should have some consensus or contention areas
        assert isinstance(consensus_areas, list)
        assert isinstance(contention_points, list)

        # Check contention point structure
        for point in contention_points:
            assert "aspect" in point
            assert "positions" in point
            assert "disagreement_level" in point
            assert isinstance(point["disagreement_level"], float)

    def test_identify_consensus_only(self):
        """Test identification with only consensus."""
        # All feedback agrees
        feedback1 = MagicMock()
        feedback1.feedback_data = {"verdict": "guilty"}
        feedback1.author.authority_score = 0.8

        feedback2 = MagicMock()
        feedback2.feedback_data = {"verdict": "guilty"}
        feedback2.author.authority_score = 0.7

        feedbacks = [feedback1, feedback2]

        consensus_areas, contention_points = (
            aggregation_engine.identify_consensus_and_contention(feedbacks)
        )

        # Should have consensus areas
        assert len(consensus_areas) >= 1
        # Should have no or minimal contention
        assert len(contention_points) == 0


class TestExtractReasoningPatterns:
    """Test cases for extract_reasoning_patterns function."""

    def test_extract_reasoning_patterns_categorization(self):
        """Test reasoning pattern categorization."""
        feedback1 = MagicMock()
        feedback1.feedback_data = {"reasoning": "Based on precedent Smith v. Jones"}
        feedback1.user_id = 1

        feedback2 = MagicMock()
        feedback2.feedback_data = {"reasoning": "The fundamental principle of justice"}
        feedback2.user_id = 2

        feedback3 = MagicMock()
        feedback3.feedback_data = {"reasoning": "Practical consequences suggest"}
        feedback3.user_id = 3

        feedback4 = MagicMock()
        feedback4.feedback_data = {"reasoning": "This is my opinion"}
        feedback4.user_id = 4

        feedbacks = [feedback1, feedback2, feedback3, feedback4]

        patterns = aggregation_engine.extract_reasoning_patterns(feedbacks)

        assert isinstance(patterns, dict)

        # Check that different patterns are identified
        if "precedent-based" in patterns:
            assert 1 in patterns["precedent-based"]
        if "principle-based" in patterns:
            assert 2 in patterns["principle-based"]
        if "pragmatic" in patterns:
            assert 3 in patterns["pragmatic"]
        if "other" in patterns:
            assert 4 in patterns["other"]

    def test_extract_reasoning_patterns_no_reasoning(self):
        """Test reasoning pattern extraction without reasoning field."""
        feedback = MagicMock()
        feedback.feedback_data = {"answer": "yes"}  # No reasoning field
        feedback.user_id = 1

        patterns = aggregation_engine.extract_reasoning_patterns([feedback])

        # Should return empty or minimal patterns
        assert isinstance(patterns, dict)


class TestAggregateWithUncertainty:
    """Test cases for aggregate_with_uncertainty function."""

    @pytest.mark.asyncio
    async def test_aggregate_with_uncertainty_task_not_found(self):
        """Test aggregation with non-existent task."""
        db = AsyncMock(spec=AsyncSession)

        # Mock empty task result
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        result = await aggregation_engine.aggregate_with_uncertainty(db, 999)

        assert "error" in result
        assert "Task not found" in result["error"]
        assert result["type"] == "Error"

    @pytest.mark.asyncio
    async def test_aggregate_with_uncertainty_no_feedback(self):
        """Test aggregation with no feedback available."""
        db = AsyncMock(spec=AsyncSession)

        # Mock task exists but no feedback
        mock_task = MagicMock()
        mock_task.id = 1

        # First call returns task, second call returns empty feedback
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            result_mock = MagicMock()
            if call_count[0] == 1:
                result_mock.scalar_one_or_none.return_value = mock_task
            else:
                result_mock.scalars.return_value.all.return_value = []
            return result_mock

        db.execute.side_effect = side_effect

        result = await aggregation_engine.aggregate_with_uncertainty(db, 1)

        assert "error" in result
        assert "No feedback found" in result["error"]
        assert result["type"] == "NoFeedback"

    @pytest.mark.asyncio
    async def test_aggregate_with_uncertainty_low_disagreement(self):
        """Test aggregation with low disagreement (consensus case)."""
        db = AsyncMock(spec=AsyncSession)

        # Mock task and feedback
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.task_type = "QA"

        # Mock consensus feedback
        mock_feedback = MagicMock()
        mock_feedback.feedback_data = {"answer": "yes"}
        mock_feedback.author.authority_score = 0.8
        mock_feedback.author.username = "user1"

        # Mock handler
        mock_handler = AsyncMock()
        mock_handler.aggregate_feedback.return_value = {"consensus_answer": "yes"}

        # Setup database calls
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            result_mock = MagicMock()
            if call_count[0] == 1:
                result_mock.scalar_one_or_none.return_value = mock_task
            else:
                result_mock.scalars.return_value.all.return_value = [mock_feedback]
            return result_mock

        db.execute.side_effect = side_effect

        # Mock get_handler to return our mock handler
        with pytest.MonkeyPatch().context() as mp:

            async def mock_get_handler(db, task):
                return mock_handler

            mp.setattr("rlcf_framework.task_handlers.get_handler", mock_get_handler)

            result = await aggregation_engine.aggregate_with_uncertainty(db, 1)

        # Should return consensus result
        assert "consensus_answer" in result
        assert "confidence_level" in result
        assert "transparency_metrics" in result
        assert result["transparency_metrics"]["consensus_strength"] == "high"

    @pytest.mark.asyncio
    async def test_aggregate_with_uncertainty_high_disagreement(self):
        """Test aggregation with high disagreement (uncertainty-preserving case)."""
        db = AsyncMock(spec=AsyncSession)

        # Mock task
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.task_type = "QA"

        # Mock conflicting feedback
        feedback1 = MagicMock()
        feedback1.feedback_data = {"answer": "yes"}
        feedback1.author.authority_score = 0.8
        feedback1.author.username = "user1"

        feedback2 = MagicMock()
        feedback2.feedback_data = {"answer": "no"}
        feedback2.author.authority_score = 0.7
        feedback2.author.username = "user2"

        feedbacks = [feedback1, feedback2]

        # Mock handler
        mock_handler = AsyncMock()
        mock_handler.aggregate_feedback.return_value = {"consensus_answer": "uncertain"}

        # Setup database calls
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            result_mock = MagicMock()
            if call_count[0] == 1:
                result_mock.scalar_one_or_none.return_value = mock_task
            else:
                result_mock.scalars.return_value.all.return_value = feedbacks
            return result_mock

        db.execute.side_effect = side_effect

        # Mock model settings to have low disagreement threshold
        with pytest.MonkeyPatch().context() as mp:

            async def mock_get_handler(db, task):
                return mock_handler

            mp.setattr("rlcf_framework.task_handlers.get_handler", mock_get_handler)
            mp.setattr(
                "rlcf_framework.aggregation_engine.model_settings.thresholds",
                {"disagreement": 0.1},
            )

            result = await aggregation_engine.aggregate_with_uncertainty(db, 1)

        # Should return uncertainty-aware result with alternative positions
        assert "primary_answer" in result
        assert "confidence_level" in result
        assert "alternative_positions" in result
        assert "expert_disagreement" in result
        assert "epistemic_metadata" in result
        assert "transparency_metrics" in result


# Integration test fixtures
@pytest.fixture
def sample_feedbacks():
    """Create sample feedback objects for testing."""
    feedback1 = MagicMock()
    feedback1.feedback_data = {
        "answer": "yes",
        "confidence": "high",
        "reasoning": "Based on precedent",
    }
    feedback1.user_id = 1
    feedback1.author.username = "expert1"
    feedback1.author.authority_score = 0.9

    feedback2 = MagicMock()
    feedback2.feedback_data = {
        "answer": "no",
        "confidence": "medium",
        "reasoning": "Fundamental principle",
    }
    feedback2.user_id = 2
    feedback2.author.username = "expert2"
    feedback2.author.authority_score = 0.8

    feedback3 = MagicMock()
    feedback3.feedback_data = {
        "answer": "yes",
        "confidence": "low",
        "reasoning": "Practical consequences",
    }
    feedback3.user_id = 3
    feedback3.author.username = "expert3"
    feedback3.author.authority_score = 0.7

    return [feedback1, feedback2, feedback3]


if __name__ == "__main__":
    pytest.main([__file__])
