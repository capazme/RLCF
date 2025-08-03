from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import ValidationError
from sqlalchemy.orm import Session
from . import models, schemas, authority_module, aggregation_engine, post_processing, bias_analysis, services
from .models import TaskStatus, TaskType # Import TaskType Enum

from .config import ModelConfig, load_model_config, model_settings
import yaml
from .database import SessionLocal, engine
import os
import numpy

# --- Sicurezza Semplice per l'Endpoint di Configurazione ---
# In produzione, usare OAuth2 o un sistema più robusto.
API_KEY = os.getenv("ADMIN_API_KEY", "supersecretkey") 
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

# --- App e DB Setup ---
models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="RLCF Framework API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoint di Amministrazione / Governance ---

@app.get("/config/model", response_model=ModelConfig, tags=["Admin & Config"])
def get_model_config():
    """Restituisce la configurazione del modello attualmente in uso dal file YAML."""
    return model_settings

@app.put("/config/model", response_model=ModelConfig, tags=["Admin & Config"])
def update_model_config(config: ModelConfig, api_key: str = Depends(get_api_key)):
    """
    Aggiorna il file di configurazione del modello (richiede API Key).
    Questa operazione sovrascrive model_config.yaml e ricarica la configurazione
    per tutti i processi successivi senza riavviare il server.
    """
    try:
        with open("rlcf_framework/model_config.yaml", "w") as f:
            yaml.dump(config.dict(), f, sort_keys=False, indent=2)
        
        # Ricarica la configurazione globale per renderla subito attiva
        global model_settings
        model_settings = load_model_config()
        
        return model_settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write or reload config: {e}")

@app.post("/users/", response_model=schemas.User, tags=["Users"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(username=user.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/users/{user_id}/credentials/", response_model=schemas.User, tags=["Users"])
def add_credential_to_user(user_id: int, credential: schemas.CredentialCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_credential = models.Credential(**credential.dict(), user_id=user_id)
    db.add(db_credential)
    db.commit()
    
    authority_module.calculate_baseline_credentials(db, user_id)
    db.refresh(db_user)
    return db_user

@app.post("/tasks/", response_model=schemas.LegalTask, tags=["Tasks"])
def create_legal_task(task: schemas.LegalTaskCreate, db: Session = Depends(get_db)):
    db_task = models.LegalTask(task_type=task.task_type.value, input_data=task.input_data)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Create a dummy response with flexible output_data
    # In a real scenario, this would come from an AI model
    dummy_output_data = {"message": "AI response placeholder for " + task.task_type.value}
    db_response = models.Response(task_id=db_task.id, output_data=dummy_output_data, model_version="dummy-0.1")
    db.add(db_response)
    db_task.status = models.TaskStatus.BLIND_EVALUATION.value # Imposta lo stato iniziale per la valutazione
    db.commit()
    db.refresh(db_task)

    return db_task

# --- New GET Endpoints for Database Viewer ---
@app.get("/users/all", response_model=list[schemas.User], tags=["Database Viewer"])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

@app.get("/credentials/all", response_model=list[schemas.Credential], tags=["Database Viewer"])
def get_all_credentials(db: Session = Depends(get_db)):
    return db.query(models.Credential).all()

@app.get("/tasks/all", response_model=list[schemas.LegalTask], tags=["Database Viewer"])
def get_all_tasks(db: Session = Depends(get_db)):
    return db.query(models.LegalTask).all()

@app.get("/responses/all", response_model=list[schemas.Response], tags=["Database Viewer"])
def get_all_responses(db: Session = Depends(get_db)):
    return db.query(models.Response).all()

@app.get("/feedback/all", response_model=list[schemas.Feedback], tags=["Database Viewer"])
def get_all_feedback(db: Session = Depends(get_db)):
    return db.query(models.Feedback).all()

@app.get("/feedback_ratings/all", response_model=list[schemas.FeedbackRating], tags=["Database Viewer"])
def get_all_feedback_ratings(db: Session = Depends(get_db)):
    return db.query(models.FeedbackRating).all()

@app.get("/bias_reports/all", response_model=list[schemas.BiasReport], tags=["Database Viewer"])
def get_all_bias_reports(db: Session = Depends(get_db)):
    return db.query(models.BiasReport).all()

@app.post("/responses/{response_id}/feedback/", response_model=schemas.Feedback, tags=["Feedback"])
def submit_feedback(response_id: int, feedback: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    db_response = db.query(models.Response).filter(models.Response.id == response_id).first()
    if not db_response:
        raise HTTPException(status_code=404, detail="Response not found")

    if db_response.task.status != models.TaskStatus.BLIND_EVALUATION.value:
        raise HTTPException(
            status_code=403, 
            detail=f"Feedback can only be submitted during the BLIND_EVALUATION phase. Current status: {db_response.task.status}"
        )

    db_feedback = models.Feedback(**feedback.dict(exclude={'feedback_data'}), feedback_data=feedback.feedback_data, response_id=response_id)
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)

    # Dynamic validation of feedback_data based on task_type
    task_type = db_response.task.task_type
    feedback_data_schema_map = {
        TaskType.SUMMARIZATION: schemas.SummarizationFeedbackData,
        TaskType.CLASSIFICATION: schemas.ClassificationFeedbackData,
        TaskType.QA: schemas.QAFeedbackData,
        TaskType.PREDICTION: schemas.PredictionFeedbackData,
        TaskType.NLI: schemas.NLIFeedbackData,
        TaskType.NER: schemas.NERFeedbackData,
        TaskType.DRAFTING: schemas.DraftingFeedbackData,
    }
    if task_type in feedback_data_schema_map:
        try:
            feedback_data_schema_map[task_type].model_validate(feedback.feedback_data)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Invalid feedback_data for task_type {task_type}: {e}")

    quality_score = authority_module.calculate_quality_score(db, db_feedback)
    authority_module.update_track_record(db, feedback.user_id, quality_score)
    
    return db_feedback

@app.get("/tasks/{task_id}/result/", tags=["Tasks"])
def get_task_result(task_id: int, db: Session = Depends(get_db)):
    result = aggregation_engine.aggregate_with_uncertainty(db, task_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.post("/feedback/{feedback_id}/rate/", response_model=schemas.FeedbackRating, tags=["Feedback"])
def rate_feedback(feedback_id: int, rating: schemas.FeedbackRatingCreate, db: Session = Depends(get_db)):
    db_feedback = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    db_rating = models.FeedbackRating(**rating.dict(), feedback_id=feedback_id)
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)

    ratings = db.query(models.FeedbackRating.helpfulness_score).filter(models.FeedbackRating.feedback_id == feedback_id).all()
    avg_rating = numpy.mean([r[0] for r in ratings])
    db_feedback.community_helpfulness_rating = int(round(avg_rating))
    db.commit()

    return db_rating

@app.post("/tasks/{task_id}/status", response_model=schemas.LegalTask, tags=["Admin & Config"])
def update_task_status(task_id: int, new_status: TaskStatus, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    db_task = db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if new_status == TaskStatus.AGGREGATED and db_task.status == TaskStatus.BLIND_EVALUATION.value:
        services.task_service.orchestrate_task_aggregation(db, task_id)

    db_task.status = new_status.value
    db.commit()
    db.refresh(db_task)
    return db_task