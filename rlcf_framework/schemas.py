from pydantic import BaseModel, Field, ConfigDict, ValidationError, model_validator
from typing import List, Optional, Dict, Any, Literal, Union
from typing_extensions import Annotated # For Pydantic v2 discriminated unions
import datetime

from .models import TaskType # Import TaskType Enum

# --- Task-Specific Schemas for Flexible Data ---

# SUMMARIZATION Task
class SummarizationTaskInput(BaseModel):
    document: str

class SummarizationFeedbackData(BaseModel):
    revised_summary: str
    rating: Literal["good", "bad"]

# CLASSIFICATION Task
class ClassificationTaskInput(BaseModel):
    text: str
    unit: str

class ClassificationFeedbackData(BaseModel):
    validated_labels: List[str]

# QA Task
class QATaskInput(BaseModel):
    context: str
    question: str

class QAFeedbackData(BaseModel):
    validated_answer: str
    position: Literal["correct", "incorrect"]

# PREDICTION Task
class PredictionTaskInput(BaseModel):
    facts: str

class PredictionFeedbackData(BaseModel):
    chosen_outcome: Literal["violation", "no_violation"]

# NLI Task
class NLITaskInput(BaseModel):
    premise: str
    hypothesis: str

class NLIFeedbackData(BaseModel):
    chosen_label: Literal["entail", "contradict", "neutral"]

# NER Task
class NERTaskInput(BaseModel):
    tokens: List[str]

class NERFeedbackData(BaseModel):
    validated_tags: List[str]

# DRAFTING Task
class DraftingTaskInput(BaseModel):
    source: str
    instruction: str

class DraftingFeedbackData(BaseModel):
    revised_target: str
    rating: Literal["better", "worse"]

# --- End Task-Specific Schemas ---

class CredentialBase(BaseModel):
    type: str
    value: str
    weight: float

class CredentialCreate(CredentialBase):
    pass

class Credential(CredentialBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    authority_score: float
    track_record_score: float
    baseline_credential_score: float
    credentials: List[Credential] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

# Moved Response and Feedback related schemas here to resolve forward reference
class ResponseBase(BaseModel):
    # response_text: str # Removed, now part of output_data
    output_data: Dict[str, Any] # Flexible output data
    model_version: str

class ResponseCreate(ResponseBase):
    pass

class Response(ResponseBase):
    id: int
    task_id: int
    generated_at: datetime.datetime
    feedback: List['Feedback'] = Field(default_factory=list) # Use string literal for forward reference

    model_config = ConfigDict(from_attributes=True)

class FeedbackBase(BaseModel):
    accuracy_score: float
    utility_score: float
    transparency_score: float
    feedback_data: Dict[str, Any] # Will be validated dynamically

class FeedbackCreate(FeedbackBase):
    user_id: int
    # Dynamic validation for feedback_data based on task_type (fetched from response)
    # This validation will happen in the API endpoint, as it needs the response_id to get the task_type.

class Feedback(FeedbackBase):
    id: int
    user_id: int
    response_id: int
    is_blind_phase: bool
    community_helpfulness_rating: int
    consistency_score: Optional[float] = None
    submitted_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class LegalTaskBase(BaseModel):
    task_type: TaskType
    input_data: Dict[str, Any] # Will be validated dynamically

class LegalTaskCreate(LegalTaskBase):
    # Dynamic validation for input_data based on task_type
    @model_validator(mode='before')
    @classmethod
    def validate_input_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            task_type = data.get('task_type')
            input_data = data.get('input_data')
            if task_type and input_data:
                schema_map = {
                    TaskType.SUMMARIZATION: SummarizationTaskInput,
                    TaskType.CLASSIFICATION: ClassificationTaskInput,
                    TaskType.QA: QATaskInput,
                    TaskType.PREDICTION: PredictionTaskInput,
                    TaskType.NLI: NLITaskInput,
                    TaskType.NER: NERTaskInput,
                    TaskType.DRAFTING: DraftingTaskInput,
                }
                if task_type in schema_map:
                    try:
                        schema_map[task_type].model_validate(input_data)
                    except ValidationError as e:
                        raise ValueError(f"Invalid input_data for task_type {task_type}: {e}")
        return data

class LegalTask(LegalTaskBase):
    id: int
    created_at: datetime.datetime
    status: str
    responses: List[Response] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class FeedbackRatingBase(BaseModel):
    helpfulness_score: int

class FeedbackRatingCreate(FeedbackRatingBase):
    user_id: int

class FeedbackRating(FeedbackRatingBase):
    id: int
    feedback_id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

class BiasReportBase(BaseModel):
    task_id: int
    user_id: int
    bias_type: str
    bias_score: float

class BiasReport(BiasReportBase):
    id: int
    calculated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
