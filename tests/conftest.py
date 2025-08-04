"""
Pytest configuration and fixtures for RLCF framework tests.

This module provides common fixtures and configuration for all test modules.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from rlcf_framework import models
from rlcf_framework.config import ModelConfig, TaskConfig


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_db_session():
    """Provide a mock async database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_user():
    """Create a mock user object for testing."""
    user = MagicMock(spec=models.User)
    user.id = 1
    user.username = "test_user"
    user.authority_score = 0.8
    user.baseline_credential_score = 0.7
    user.track_record_score = 0.9
    user.credentials = []
    return user


@pytest.fixture
def mock_task():
    """Create a mock legal task object for testing."""
    task = MagicMock(spec=models.LegalTask)
    task.id = 1
    task.task_type = "QA"
    task.input_data = {"question": "Is this legal?"}
    task.ground_truth_data = {"answer": "yes"}
    task.status = "BLIND_EVALUATION"
    return task


@pytest.fixture
def mock_feedback():
    """Create a mock feedback object for testing."""
    feedback = MagicMock(spec=models.Feedback)
    feedback.id = 1
    feedback.user_id = 1
    feedback.response_id = 1
    feedback.feedback_data = {"answer": "yes", "confidence": "high"}
    feedback.accuracy_score = 4
    feedback.consistency_score = 0.8
    feedback.community_helpfulness_rating = 4
    feedback.submitted_at = "2023-01-01T12:00:00"

    # Mock author relationship
    feedback.author = MagicMock()
    feedback.author.username = "test_user"
    feedback.author.authority_score = 0.8

    return feedback


@pytest.fixture
def mock_response():
    """Create a mock response object for testing."""
    response = MagicMock(spec=models.Response)
    response.id = 1
    response.task_id = 1
    response.output_data = {"answer": "AI response"}
    response.model_version = "test-1.0"
    return response


@pytest.fixture
def mock_credential():
    """Create a mock credential object for testing."""
    credential = MagicMock(spec=models.Credential)
    credential.id = 1
    credential.user_id = 1
    credential.type = "PROFESSIONAL_EXPERIENCE"
    credential.value = "10"
    return credential


@pytest.fixture
def mock_model_settings():
    """Create mock model settings for testing."""
    settings = MagicMock(spec=ModelConfig)

    # Mock baseline credentials configuration
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

    # Mock track record settings
    settings.track_record = {"update_factor": 0.05}

    # Mock authority weights
    settings.authority_weights = {
        "baseline_credentials": 0.3,
        "track_record": 0.5,
        "recent_performance": 0.2,
    }

    # Mock thresholds
    settings.thresholds = {"disagreement": 0.3, "authority_min": 0.1}

    return settings


@pytest.fixture
def mock_task_settings():
    """Create mock task settings for testing."""
    settings = MagicMock(spec=TaskConfig)

    settings.task_types = {
        "QA": MagicMock(
            input_data={"question": "str"},
            feedback_data={"answer": "str", "confidence": "str"},
            ground_truth_keys=["answer"],
        ),
        "CLASSIFICATION": MagicMock(
            input_data={"text": "str"},
            feedback_data={"category": "str", "confidence": "float"},
            ground_truth_keys=["category"],
        ),
        "DRAFTING": MagicMock(
            input_data={"source": "str", "task": "str"},
            feedback_data={"quality": "int", "improvements": "str"},
            ground_truth_keys=["target"],
        ),
    }

    return settings


@pytest.fixture
def sample_database_data():
    """Create a set of related mock objects for integration testing."""
    # Create user
    user = MagicMock(spec=models.User)
    user.id = 1
    user.username = "expert1"
    user.authority_score = 0.8
    user.baseline_credential_score = 0.7
    user.track_record_score = 0.9

    # Create credential
    credential = MagicMock(spec=models.Credential)
    credential.id = 1
    credential.user_id = 1
    credential.type = "PROFESSIONAL_EXPERIENCE"
    credential.value = "15"
    user.credentials = [credential]

    # Create task
    task = MagicMock(spec=models.LegalTask)
    task.id = 1
    task.task_type = "QA"
    task.input_data = {"question": "Is this contract valid?"}
    task.ground_truth_data = {"answer": "yes"}
    task.status = "BLIND_EVALUATION"

    # Create response
    response = MagicMock(spec=models.Response)
    response.id = 1
    response.task_id = 1
    response.output_data = {"answer": "The contract appears valid based on..."}
    response.model_version = "gpt-4"
    response.task = task

    # Create feedback
    feedback = MagicMock(spec=models.Feedback)
    feedback.id = 1
    feedback.user_id = 1
    feedback.response_id = 1
    feedback.feedback_data = {
        "answer": "yes",
        "confidence": "high",
        "reasoning": "All elements present",
    }
    feedback.accuracy_score = 5
    feedback.consistency_score = 0.9
    feedback.community_helpfulness_rating = 4
    feedback.author = user
    feedback.response = response

    return {
        "user": user,
        "credential": credential,
        "task": task,
        "response": response,
        "feedback": feedback,
    }


@pytest.fixture
def mock_async_db_calls():
    """Helper fixture to mock common async database call patterns."""

    def create_mock_result(return_value, is_list=False):
        result_mock = MagicMock()
        if is_list:
            result_mock.scalars.return_value.all.return_value = return_value
        else:
            result_mock.scalar_one_or_none.return_value = return_value
        return result_mock

    return create_mock_result


# Performance test helpers
@pytest.fixture
def performance_timer():
    """Simple performance timing helper for tests."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


# Test data generators
@pytest.fixture
def generate_test_feedback():
    """Generator function for creating multiple test feedback objects."""

    def _generate(count=3, task_id=1):
        feedbacks = []
        for i in range(count):
            feedback = MagicMock(spec=models.Feedback)
            feedback.id = i + 1
            feedback.user_id = i + 1
            feedback.response_id = 1
            feedback.feedback_data = {
                "answer": "yes" if i % 2 == 0 else "no",
                "confidence": ["high", "medium", "low"][i % 3],
                "reasoning": f"Reasoning {i + 1}",
            }
            feedback.accuracy_score = 3 + (i % 3)
            feedback.consistency_score = 0.7 + (i * 0.1)
            feedback.community_helpfulness_rating = 3 + (i % 3)

            # Add author
            feedback.author = MagicMock()
            feedback.author.username = f"user{i + 1}"
            feedback.author.authority_score = 0.6 + (i * 0.1)

            feedbacks.append(feedback)

        return feedbacks

    return _generate
