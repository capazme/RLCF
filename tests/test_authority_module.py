"""
Tests for the authority module.

This module tests the Dynamic Authority Scoring Model implementation,
including credential calculations, track record updates, and authority scores.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from rlcf_framework import authority_module


class TestCalculateBaselineCredentials:
    """Test cases for calculate_baseline_credentials function."""

    @pytest.mark.asyncio
    async def test_calculate_baseline_credentials_valid_user(self):
        """Test baseline credential calculation for a valid user."""
        # Mock database session
        db = AsyncMock(spec=AsyncSession)

        # Create mock user with credentials
        mock_user = MagicMock()
        mock_user.credentials = [
            MagicMock(type="PROFESSIONAL_EXPERIENCE", value="10"),
            MagicMock(type="EDUCATION_LEVEL", value="PhD"),
        ]

        # Mock database result
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = result_mock

        # Test with valid formulas and map values
        score = await authority_module.calculate_baseline_credentials(db, 1)

        # Verify database query was called
        db.execute.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mock_user)

        # Score should be calculated based on model_settings
        assert isinstance(score, float)
        assert score >= 0.0

    @pytest.mark.asyncio
    async def test_calculate_baseline_credentials_nonexistent_user(self):
        """Test baseline credential calculation for non-existent user."""
        db = AsyncMock(spec=AsyncSession)

        # Mock empty result
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        score = await authority_module.calculate_baseline_credentials(db, 999)

        assert score == 0.0
        db.execute.assert_called_once()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculate_baseline_credentials_invalid_formula(self):
        """Test handling of invalid formulas in credentials."""
        db = AsyncMock(spec=AsyncSession)

        # Mock user with credential that will cause formula error
        mock_user = MagicMock()
        mock_user.credentials = [
            MagicMock(type="PROFESSIONAL_EXPERIENCE", value="invalid_number")
        ]

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = result_mock

        # Should handle errors gracefully and return 0 for invalid credentials
        score = await authority_module.calculate_baseline_credentials(db, 1)

        assert isinstance(score, float)
        assert score >= 0.0


class TestCalculateQualityScore:
    """Test cases for calculate_quality_score function."""

    @pytest.mark.asyncio
    async def test_calculate_quality_score_with_ratings(self):
        """Test quality score calculation with feedback ratings."""
        db = AsyncMock(spec=AsyncSession)

        # Mock feedback
        mock_feedback = MagicMock()
        mock_feedback.id = 1
        mock_feedback.accuracy_score = 4
        mock_feedback.consistency_score = 0.8
        mock_feedback.community_helpfulness_rating = 4

        # Mock ratings
        mock_ratings = [
            MagicMock(helpfulness_score=4),
            MagicMock(helpfulness_score=5),
            MagicMock(helpfulness_score=3),
        ]

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = mock_ratings
        db.execute.return_value = result_mock

        score = await authority_module.calculate_quality_score(db, mock_feedback)

        # Score should be average of normalized components
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_quality_score_no_ratings(self):
        """Test quality score calculation without ratings."""
        db = AsyncMock(spec=AsyncSession)

        mock_feedback = MagicMock()
        mock_feedback.id = 1
        mock_feedback.accuracy_score = 3
        mock_feedback.consistency_score = None
        mock_feedback.community_helpfulness_rating = None

        # Mock empty ratings
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute.return_value = result_mock

        score = await authority_module.calculate_quality_score(db, mock_feedback)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestUpdateTrackRecord:
    """Test cases for update_track_record function."""

    @pytest.mark.asyncio
    async def test_update_track_record_valid_user(self):
        """Test track record update for valid user."""
        db = AsyncMock(spec=AsyncSession)

        mock_user = MagicMock()
        mock_user.track_record_score = 0.7

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = result_mock

        new_score = await authority_module.update_track_record(db, 1, 0.9)

        assert isinstance(new_score, float)
        assert 0.0 <= new_score <= 1.0
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_update_track_record_nonexistent_user(self):
        """Test track record update for non-existent user."""
        db = AsyncMock(spec=AsyncSession)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        score = await authority_module.update_track_record(db, 999, 0.8)

        assert score == 0.0
        db.commit.assert_not_called()


class TestUpdateAuthorityScore:
    """Test cases for update_authority_score function."""

    @pytest.mark.asyncio
    async def test_update_authority_score_valid_user(self):
        """Test authority score update for valid user."""
        db = AsyncMock(spec=AsyncSession)

        mock_user = MagicMock()
        mock_user.baseline_credential_score = 0.6
        mock_user.track_record_score = 0.8

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = result_mock

        new_score = await authority_module.update_authority_score(db, 1, 0.7)

        assert isinstance(new_score, float)
        assert new_score >= 0.0
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_update_authority_score_nonexistent_user(self):
        """Test authority score update for non-existent user."""
        db = AsyncMock(spec=AsyncSession)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        score = await authority_module.update_authority_score(db, 999, 0.5)

        assert score == 0.0
        db.commit.assert_not_called()


class TestEvaluatorSafety:
    """Test cases for the asteval evaluator safety."""

    def test_evaluator_initialization(self):
        """Test that the evaluator is properly initialized with safe functions."""
        from rlcf_framework.authority_module import _get_evaluator

        evaluator = _get_evaluator()

        # Check that safe functions are available
        assert "sqrt" in evaluator.symtable
        assert "min" in evaluator.symtable
        assert "max" in evaluator.symtable

        # Test safe evaluation
        evaluator.symtable["value"] = 16
        result = evaluator.eval("sqrt(value)")
        assert result == 4.0

    def test_evaluator_reuse(self):
        """Test that the evaluator instance is reused."""
        from rlcf_framework.authority_module import _get_evaluator

        evaluator1 = _get_evaluator()
        evaluator2 = _get_evaluator()

        # Should be the same instance
        assert evaluator1 is evaluator2


# Fixtures for test setup
@pytest.fixture
def mock_model_settings():
    """Mock model settings for testing."""
    settings = MagicMock()
    settings.baseline_credentials.types = {
        "PROFESSIONAL_EXPERIENCE": MagicMock(
            weight=0.4,
            scoring_function=MagicMock(
                type="formula", expression="min(value / 20, 1.0)"
            ),
        ),
        "EDUCATION_LEVEL": MagicMock(
            weight=0.3,
            scoring_function=MagicMock(
                type="map",
                values={"PhD": 1.0, "Master": 0.8, "Bachelor": 0.6},
                default=0.5,
            ),
        ),
    }
    settings.track_record = {"update_factor": 0.05}
    settings.authority_weights = {
        "baseline_credentials": 0.3,
        "track_record": 0.5,
        "recent_performance": 0.2,
    }
    return settings


if __name__ == "__main__":
    pytest.main([__file__])
