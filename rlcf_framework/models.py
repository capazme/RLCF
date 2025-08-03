import datetime
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON # Import for JSON type
from .database import Base

class TaskType(str, enum.Enum):
    SUMMARIZATION = "SUMMARIZATION"
    CLASSIFICATION = "CLASSIFICATION"
    QA = "QA"
    PREDICTION = "PREDICTION"
    NLI = "NLI"
    NER = "NER"
    DRAFTING = "DRAFTING"

class TaskStatus(str, enum.Enum):
    OPEN = "OPEN"
    BLIND_EVALUATION = "BLIND_EVALUATION"
    AGGREGATED = "AGGREGATED"
    CLOSED = "CLOSED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    authority_score = Column(Float, default=0.0)
    track_record_score = Column(Float, default=0.0)
    baseline_credential_score = Column(Float, default=0.0)

    credentials = relationship("Credential", back_populates="owner")
    feedback = relationship("Feedback", back_populates="author")


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)
    value = Column(String)
    weight = Column(Float)

    owner = relationship("User", back_populates="credentials")


class LegalTask(Base):
    __tablename__ = "legal_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String, nullable=False) # New: Type of task
    input_data = Column(JSON, nullable=False) # New: Flexible input data
    ground_truth_data = Column(JSON, nullable=True) # Nuovo campo!
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default=TaskStatus.OPEN)

    responses = relationship("Response", back_populates="task")
    bias_reports = relationship("BiasReport")


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("legal_tasks.id"))
    output_data = Column(JSON, nullable=False) # New: Flexible output data
    model_version = Column(String)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("LegalTask", back_populates="responses")
    feedback = relationship("Feedback", back_populates="response")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    response_id = Column(Integer, ForeignKey("responses.id"))
    is_blind_phase = Column(Boolean, default=True)
    accuracy_score = Column(Float)
    utility_score = Column(Float)
    transparency_score = Column(Float)
    feedback_data = Column(JSON, nullable=False) # New: Flexible feedback data
    community_helpfulness_rating = Column(Integer, default=0)
    consistency_score = Column(Float, nullable=True)
    correctness_score = Column(Float, nullable=True) # Nuovo campo per il ground truth
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)

    author = relationship("User", back_populates="feedback")
    response = relationship("Response", back_populates="feedback")
    ratings = relationship("FeedbackRating", back_populates="rated_feedback")


class FeedbackRating(Base):
    __tablename__ = "feedback_ratings"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    helpfulness_score = Column(Integer)  # e.g., from 1 to 5

    rated_feedback = relationship("Feedback", back_populates="ratings")
    rater = relationship("User")

class BiasReport(Base):
    __tablename__ = "bias_reports"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("legal_tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    bias_type = Column(String) # es. "PROFESSIONAL_CLUSTERING"
    bias_score = Column(Float)
    calculated_at = Column(DateTime, default=datetime.datetime.utcnow)
