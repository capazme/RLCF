from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import ValidationError, create_model
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import (
    models,
    schemas,
    authority_module,
    aggregation_engine,
    services,
)
from .models import TaskStatus, TaskType  # Import TaskType Enum
from .dependencies import get_db, get_model_settings, get_task_settings
from .config import (
    ModelConfig,
    load_model_config,
    TaskConfig,
    load_task_config,
    ModelConfig,
    TaskConfig,
)
import yaml
from .database import engine
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
app = FastAPI(title="RLCF Framework API")


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


# --- Endpoint di Amministrazione / Governance ---


@app.get("/config/model", response_model=ModelConfig, tags=["Admin & Config"])
async def get_model_config(model_settings: ModelConfig = Depends(get_model_settings)):
    """Restituisce la configurazione del modello attualmente in uso dal file YAML."""
    return model_settings


@app.put("/config/model", response_model=ModelConfig, tags=["Admin & Config"])
async def update_model_config(config: ModelConfig, api_key: str = Depends(get_api_key)):
    """
    Aggiorna il file di configurazione del modello (richiede API Key).
    Questa operazione sovrascrive model_config.yaml e ricarica la configurazione
    per tutti i processi successivi senza riavviare il server.
    """
    try:
        with open("rlcf_framework/model_config.yaml", "w") as f:
            yaml.dump(config.dict(), f, sort_keys=False, indent=2)

        # Ricarica la configurazione globale per renderla subito attiva
        from . import config

        config.model_settings = load_model_config()

        return config.model_settings
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to write or reload config: {e}"
        )


@app.get("/config/tasks", response_model=TaskConfig, tags=["Admin & Config"])
async def get_task_config(task_settings: TaskConfig = Depends(get_task_settings)):
    """Restituisce la configurazione dei task attualmente in uso dal file YAML."""
    return task_settings


@app.put("/config/tasks", response_model=TaskConfig, tags=["Admin & Config"])
async def update_task_config(config: TaskConfig, api_key: str = Depends(get_api_key)):
    """
    Aggiorna il file di configurazione dei task (richiede API Key).
    Questa operazione sovrascrive task_config.yaml e ricarica la configurazione
    per tutti i processi successivi senza riavviare il server.
    """
    try:
        with open("rlcf_framework/task_config.yaml", "w") as f:
            yaml.dump(config.dict(), f, sort_keys=False, indent=2)

        # Ricarica la configurazione globale per renderla subito attiva
        from . import config

        config.task_settings = load_task_config()

        return config.task_settings
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to write or reload config: {e}"
        )


@app.post("/users/", response_model=schemas.User, tags=["Users"])
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = models.User(username=user.username)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@app.post("/users/{user_id}/credentials/", response_model=schemas.User, tags=["Users"])
async def add_credential_to_user(
    user_id: int,
    credential: schemas.CredentialCreate,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_credential = models.Credential(**credential.dict(), user_id=user_id)
    db.add(db_credential)
    await db.commit()

    await authority_module.calculate_baseline_credentials(db, user_id)
    await db.refresh(db_user)
    return db_user


@app.post("/tasks/", response_model=schemas.LegalTask, tags=["Tasks"])
async def create_legal_task(
    task: schemas.LegalTaskCreate, db: AsyncSession = Depends(get_db)
):
    db_task = models.LegalTask(
        task_type=task.task_type.value, input_data=task.input_data
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)

    # Create a dummy response with flexible output_data
    # In a real scenario, this would come from an AI model
    dummy_output_data = {
        "message": "AI response placeholder for " + task.task_type.value
    }
    db_response = models.Response(
        task_id=db_task.id, output_data=dummy_output_data, model_version="dummy-0.1"
    )
    db.add(db_response)
    db_task.status = (
        models.TaskStatus.BLIND_EVALUATION.value
    )  # Imposta lo stato iniziale per la valutazione
    await db.commit()
    await db.refresh(db_task)

    return db_task


@app.post(
    "/tasks/batch_from_yaml/", response_model=List[schemas.LegalTask], tags=["Tasks"]
)
async def create_legal_tasks_from_yaml(
    yaml_content: str,
    db: AsyncSession = Depends(get_db),
    task_settings: TaskConfig = Depends(get_task_settings),
    api_key: str = Depends(get_api_key),  # Richiede API Key per sicurezza
):
    """
    Crea uno o più task legali da un contenuto YAML fornito.
    Il YAML deve contenere una lista di task, ognuno con 'task_type' e 'input_data'.
    """
    try:
        data = yaml.safe_load(yaml_content)
        tasks_data = schemas.TaskListFromYaml(tasks=data.get("tasks", [])).tasks
    except (yaml.YAMLError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML or data format: {e}")

    created_tasks = []
    for task_data in tasks_data:
        try:
            # Validate input_data using the existing LegalTaskCreate schema's validator
            validated_task_data = schemas.LegalTaskCreate(
                task_type=task_data.task_type, input_data=task_data.input_data
            )

            # Separate input_data and ground_truth_data based on task_config
            task_type_enum = TaskType(task_data.task_type)
            task_type_config = task_settings.task_types.get(task_type_enum.value)

            input_data_for_db = {}
            ground_truth_data_for_db = {}

            if task_type_config and task_type_config.ground_truth_keys:
                for key, value in task_data.input_data.items():
                    if key in task_type_config.ground_truth_keys:
                        ground_truth_data_for_db[key] = value
                    else:
                        input_data_for_db[key] = value
            else:
                input_data_for_db = (
                    task_data.input_data
                )  # If no ground_truth_keys, all is input

            db_task = models.LegalTask(
                task_type=validated_task_data.task_type.value,
                input_data=input_data_for_db,
                ground_truth_data=(
                    ground_truth_data_for_db if ground_truth_data_for_db else None
                ),
            )
            db.add(db_task)
            await db.flush()  # Flush to get the task ID before creating response

            # Create a dummy response with flexible output_data
            dummy_output_data = {
                "message": "AI response placeholder for " + db_task.task_type
            }
            db_response = models.Response(
                task_id=db_task.id,
                output_data=dummy_output_data,
                model_version="dummy-0.1",
            )
            db.add(db_response)
            db_task.status = (
                models.TaskStatus.BLIND_EVALUATION.value
            )  # Imposta lo stato iniziale per la valutazione

            await db.refresh(db_task)
            created_tasks.append(db_task)
        except ValidationError as e:
            await db.rollback()  # Rollback any partial changes for this task
            raise HTTPException(
                status_code=422, detail=f"Validation error for a task: {e}"
            )
        except Exception as e:
            await db.rollback()  # Rollback any partial changes for this task
            raise HTTPException(status_code=500, detail=f"Error processing task: {e}")

    await db.commit()
    return created_tasks


# --- New GET Endpoints for Database Viewer ---
@app.get("/users/all", response_model=list[schemas.User], tags=["Database Viewer"])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User))
    return result.scalars().all()


@app.get(
    "/credentials/all",
    response_model=list[schemas.Credential],
    tags=["Database Viewer"],
)
async def get_all_credentials(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Credential))
    return result.scalars().all()


@app.get("/tasks/all", response_model=list[schemas.LegalTask], tags=["Database Viewer"])
async def get_all_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.LegalTask))
    return result.scalars().all()


@app.get(
    "/responses/all", response_model=list[schemas.Response], tags=["Database Viewer"]
)
async def get_all_responses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Response))
    return result.scalars().all()


@app.get(
    "/feedback/all", response_model=list[schemas.Feedback], tags=["Database Viewer"]
)
async def get_all_feedback(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Feedback))
    return result.scalars().all()


@app.get(
    "/feedback_ratings/all",
    response_model=list[schemas.FeedbackRating],
    tags=["Database Viewer"],
)
async def get_all_feedback_ratings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.FeedbackRating))
    return result.scalars().all()


@app.get(
    "/bias_reports/all",
    response_model=list[schemas.BiasReport],
    tags=["Database Viewer"],
)
async def get_all_bias_reports(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.BiasReport))
    return result.scalars().all()


@app.post(
    "/responses/{response_id}/feedback/",
    response_model=schemas.Feedback,
    tags=["Feedback"],
)
async def submit_feedback(
    response_id: int,
    feedback: schemas.FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    task_settings: TaskConfig = Depends(get_task_settings),
):
    result = await db.execute(
        select(models.Response).filter(models.Response.id == response_id)
    )
    db_response = result.scalar_one_or_none()
    if not db_response:
        raise HTTPException(status_code=404, detail="Response not found")

    if db_response.task.status != models.TaskStatus.BLIND_EVALUATION.value:
        raise HTTPException(
            status_code=403,
            detail=f"Feedback can only be submitted during the BLIND_EVALUATION phase. Current status: {db_response.task.status}",
        )

    db_feedback = models.Feedback(
        **feedback.dict(exclude={"feedback_data"}),
        feedback_data=feedback.feedback_data,
        response_id=response_id,
    )
    db.add(db_feedback)
    await db.commit()
    await db.refresh(db_feedback)

    # Dynamic validation of feedback_data based on task_type
    task_type_enum = TaskType(db_response.task.task_type)
    feedback_schema_def = task_settings.task_types.get(task_type_enum.value)

    if feedback_schema_def and feedback_schema_def.feedback_data:
        fields = {
            field_name: (schemas._parse_type_string(type_str), ...)
            for field_name, type_str in feedback_schema_def.feedback_data.items()
        }
        DynamicFeedbackModel = create_model(
            f"{task_type_enum.value}FeedbackData", **fields
        )
        try:
            DynamicFeedbackModel.model_validate(feedback.feedback_data)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid feedback_data for task_type {task_type_enum.value}: {e}",
            )

    quality_score = authority_module.calculate_quality_score(db, db_feedback)
    authority_module.update_track_record(db, feedback.user_id, quality_score)

    return db_feedback


@app.get("/tasks/{task_id}/result/", tags=["Tasks"])
async def get_task_result(task_id: int, db: AsyncSession = Depends(get_db)):
    result = aggregation_engine.aggregate_with_uncertainty(db, task_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post(
    "/feedback/{feedback_id}/rate/",
    response_model=schemas.FeedbackRating,
    tags=["Feedback"],
)
async def rate_feedback(
    feedback_id: int,
    rating: schemas.FeedbackRatingCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.Feedback).filter(models.Feedback.id == feedback_id)
    )
    db_feedback = result.scalar_one_or_none()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    db_rating = models.FeedbackRating(**rating.dict(), feedback_id=feedback_id)
    db.add(db_rating)
    await db.commit()
    await db.refresh(db_rating)

    result = await db.execute(
        select(models.FeedbackRating.helpfulness_score).filter(
            models.FeedbackRating.feedback_id == feedback_id
        )
    )
    ratings = result.scalars().all()
    avg_rating = numpy.mean([r for r in ratings])
    db_feedback.community_helpfulness_rating = int(round(avg_rating))
    await db.commit()

    return db_rating


@app.post(
    "/tasks/{task_id}/status", response_model=schemas.LegalTask, tags=["Admin & Config"]
)
async def update_task_status(
    task_id: int,
    new_status: TaskStatus,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    result = await db.execute(
        select(models.LegalTask).filter(models.LegalTask.id == task_id)
    )
    db_task = result.scalar_one_or_none()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if (
        new_status == TaskStatus.AGGREGATED
        and db_task.status == TaskStatus.BLIND_EVALUATION.value
    ):
        services.task_service.orchestrate_task_aggregation(db, task_id)

    db_task.status = new_status.value
    await db.commit()
    await db.refresh(db_task)
    return db_task
