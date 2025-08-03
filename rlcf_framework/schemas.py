from pydantic import BaseModel, Field, ConfigDict, ValidationError, model_validator, create_model
from typing import List, Optional, Dict, Any, Literal, Union
from typing_extensions import Annotated # For Pydantic v2 discriminated unions
import datetime

from .models import TaskType # Import TaskType Enum
from .config import task_settings # Import the new task_settings

# Helper function to convert string type hints from YAML to actual Python types
def _parse_type_string(type_str: str):
    if type_str == "str":
        return str
    elif type_str == "int":
        return int
    elif type_str == "float":
        return float
    elif type_str.startswith("List["):
        inner_type_str = type_str[len("List["):-1]
        return List[_parse_type_string(inner_type_str)]
    elif type_str.startswith("Literal["):
        values_str = type_str[len("Literal["):-1]
        values = [val.strip().strip('\'"') for val in values_str.split(',')]
        return Literal[tuple(values)]
    # Add more types as needed
    return Any # Fallback

class TaskCreateFromYaml(BaseModel):
    task_type: str
    input_data: Any # Use Any for flexible JSON data

class TaskListFromYaml(BaseModel):
    tasks: List[TaskCreateFromYaml]

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
            task_type_str = data.get('task_type')
            input_data = data.get('input_data')
            
            if task_type_str and input_data:
                task_type_enum = TaskType(task_type_str)
                task_schema_def = task_settings.task_types.get(task_type_enum.value)
                
                if task_schema_def and task_schema_def.input_data:
                    # Dynamically create a Pydantic model for input_data
                    fields = {
                        field_name: (_parse_type_string(type_str), ...)
                        for field_name, type_str in task_schema_def.input_data.items()
                    }
                    DynamicInputModel = create_model(f'{task_type_enum.value}Input', **fields)
                    
                    try:
                        DynamicInputModel.model_validate(input_data)
                    except ValidationError as e:
                        raise ValueError(f"Invalid input_data for task_type {task_type_str}: {e}")
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
