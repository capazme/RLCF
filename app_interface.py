import gradio as gr
import yaml
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
import requests

# --- Importazioni dal tuo RLCF Framework ---
# Assicurati che il framework sia installabile o nel PYTHONPATH
from rlcf_framework import (
    models,
    schemas,
    services,
    aggregation_engine,
    bias_analysis,
    authority_module,
    export_dataset,
)
from rlcf_framework.database import engine as async_engine
from rlcf_framework.config import app_settings

# Create a synchronous engine and session for Gradio interface  
sync_engine = create_engine(app_settings.DATABASE_URL, connect_args={"check_same_thread": False})
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
from rlcf_framework.config import (
    load_model_config,
    load_task_config,
    task_settings,
)
from rlcf_framework.models import TaskType, TaskStatus
from rlcf_framework import devils_advocate, training_scheduler
import json

# --- Setup del Database ---
# Initialize database tables with sync engine for Gradio interface
models.Base.metadata.create_all(bind=sync_engine)

# Also initialize async database for consistency
import asyncio

async def init_async_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# Initialize async database on startup
try:
    # Try to get the current event loop
    loop = asyncio.get_running_loop()
    # If we're already in an async context, schedule the coroutine
    loop.create_task(init_async_db())
except RuntimeError:
    # No event loop is running, create one and run the initialization
    asyncio.run(init_async_db())


def get_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========= Funzioni Helper per l'Interfaccia Gradio =========
# Queste funzioni simulano le chiamate agli endpoint FastAPI interagendo
# direttamente con i moduli del tuo framework.


# --- Sezione Dashboard ---
def get_dashboard_stats():
    db: Session = next(get_db())
    num_users = db.query(models.User).count()
    num_tasks = db.query(models.LegalTask).count()
    num_feedbacks = db.query(models.Feedback).count()
    return num_users, num_tasks, num_feedbacks


# --- Sezione Admin & Config ---
def get_model_config_content():
    with open("rlcf_framework/model_config.yaml", "r") as f:
        return f.read()


def update_model_config_content(new_content):
    try:
        config_data = yaml.safe_load(new_content)
        # Riscrivi il file
        with open("rlcf_framework/model_config.yaml", "w") as f:
            yaml.dump(config_data, f, sort_keys=False, indent=2)
        # Ricarica la configurazione globale
        global model_settings
        model_settings = load_model_config()
        return (
            "Configurazione del modello salvata e ricaricata con successo!",
            get_model_config_content(),
        )
    except Exception as e:
        return f"Errore: {e}", get_model_config_content()


def get_task_config_content():
    with open("rlcf_framework/task_config.yaml", "r") as f:
        return f.read()


def update_task_config_content(new_content):
    try:
        config_data = yaml.safe_load(new_content)
        with open("rlcf_framework/task_config.yaml", "w") as f:
            yaml.dump(config_data, f, sort_keys=False, indent=2)
        global task_settings
        task_settings = load_task_config()
        return (
            "Configurazione dei task salvata e ricaricata con successo!",
            get_task_config_content(),
        )
    except Exception as e:
        return f"Errore: {e}", get_task_config_content()


def run_task_aggregation_orchestration(task_id: int):
    db: Session = next(get_db())
    try:
        db_task = (
            db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
        )
        if not db_task:
            return f"Task con ID {task_id} non trovato."

        # Esegui l'orchestrazione
        services.task_service.orchestrate_task_aggregation(db, task_id)

        # Aggiorna lo stato
        db_task.status = TaskStatus.AGGREGATED.value
        db.commit()

        return f"Processo di aggregazione per il task {task_id} completato. Lo stato è ora AGGREGATED."
    except Exception as e:
        db.rollback()
        return f"Errore durante l'aggregazione per il task {task_id}: {e}"


# --- Sezione User Management ---
def create_user(username: str):
    if not username:
        return "Il nome utente non può essere vuoto.", None
    db: Session = next(get_db())
    db_user = models.User(username=username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return (
        f"Utente '{username}' creato con successo (ID: {db_user.id}).",
        get_all_users(),
    )


def add_credential(user_id: int, cred_type: str, cred_value: str, cred_weight: float):
    db: Session = next(get_db())
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return f"Utente con ID {user_id} non trovato.", None

    db_credential = models.Credential(
        type=cred_type, value=cred_value, weight=cred_weight, user_id=user_id
    )
    db.add(db_credential)
    db.commit()

    # Ricalcola e aggiorna i punteggi
    authority_module.calculate_baseline_credentials(db, user_id)
    authority_module.update_authority_score(
        db, user_id, user.track_record_score
    )  # Usa il track record esistente come performance recente

    return (
        f"Credenziale aggiunta all'utente {user_id}. Punteggi ricalcolati.",
        get_all_users(),
    )


def get_all_users():
    db: Session = next(get_db())
    users = db.query(models.User).all()
    # Formatta per gr.DataFrame
    return [
        [
            u.id,
            u.username,
            round(u.authority_score, 2),
            round(u.baseline_credential_score, 2),
            round(u.track_record_score, 2),
        ]
        for u in users
    ]


# --- Sezione Task & Feedback ---
def create_task_from_yaml(yaml_content: str):
    # Questa funzione è una semplificazione dell'endpoint batch
    db: Session = next(get_db())
    try:
        data = yaml.safe_load(yaml_content)
        tasks_data = schemas.TaskListFromYaml(tasks=data.get("tasks", [])).tasks
    except Exception as e:
        return f"YAML o dati non validi: {e}", None

    created_tasks_info = []
    for task_data in tasks_data:
        # Applica ground truth separation
        task_type_enum = TaskType(task_data.task_type)
        task_type_config = task_settings.task_types.get(task_type_enum.value)

        input_data_for_db = {}
        ground_truth_data_for_db = {}

        if (
            task_type_config
            and hasattr(task_type_config, "ground_truth_keys")
            and task_type_config.ground_truth_keys
        ):
            for key, value in task_data.input_data.items():
                if key in task_type_config.ground_truth_keys:
                    ground_truth_data_for_db[key] = value
                else:
                    input_data_for_db[key] = value
        else:
            input_data_for_db = task_data.input_data

        db_task = models.LegalTask(
            task_type=task_data.task_type,
            input_data=input_data_for_db,
            ground_truth_data=(
                ground_truth_data_for_db if ground_truth_data_for_db else None
            ),
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        created_tasks_info.append(f"Task ID {db_task.id} ({db_task.task_type}) creato.")

    return "\n".join(created_tasks_info), get_all_db_tasks()


def load_dataset_file(file_path: str, task_type: str):
    """Carica un file dataset JSONL e crea task nel database."""
    if not file_path.startswith("/Users/gpuzio/Desktop/ALIS/RLCF/datasets/"):
        return "Errore: Path non valido"

    db: Session = next(get_db())
    created_tasks = []

    try:
        import json

        task_type_enum = TaskType(task_type)
        task_type_config = task_settings.task_types.get(task_type_enum.value)

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)

                    # Separazione ground truth
                    input_data_for_db = {}
                    ground_truth_data_for_db = {}

                    if (
                        task_type_config
                        and hasattr(task_type_config, "ground_truth_keys")
                        and task_type_config.ground_truth_keys
                    ):
                        for key, value in data.items():
                            if key in task_type_config.ground_truth_keys:
                                ground_truth_data_for_db[key] = value
                            elif key != "id":  # Escludiamo ID dai dati del task
                                input_data_for_db[key] = value
                    else:
                        # Se non ci sono ground truth keys, tutti i dati (eccetto ID) vanno in input
                        input_data_for_db = {k: v for k, v in data.items() if k != "id"}

                    # Crea il task
                    db_task = models.LegalTask(
                        task_type=task_type,
                        input_data=input_data_for_db,
                        ground_truth_data=(
                            ground_truth_data_for_db
                            if ground_truth_data_for_db
                            else None
                        ),
                    )
                    db.add(db_task)
                    db.flush()  # Flush per ottenere l'ID

                    # Crea response placeholder
                    dummy_output_data = {
                        "message": f"AI response placeholder for {task_type}"
                    }
                    db_response = models.Response(
                        task_id=db_task.id,
                        output_data=dummy_output_data,
                        model_version="dummy-0.1",
                    )
                    db.add(db_response)
                    db_task.status = models.TaskStatus.BLIND_EVALUATION.value

                    created_tasks.append(db_task.id)

                except json.JSONDecodeError as e:
                    return f"Errore JSON alla riga {line_num}: {e}"
                except Exception as e:
                    return f"Errore alla riga {line_num}: {e}"

        db.commit()
        return (
            f"✅ Caricati {len(created_tasks)} task dal file {file_path.split('/')[-1]}"
        )

    except FileNotFoundError:
        return f"Errore: File {file_path} non trovato"
    except Exception as e:
        db.rollback()
        return f"Errore durante il caricamento: {e}"




def generate_ai_response_for_task(
    task_id: int, model_type: str, model_identifier: str, api_key: str = None
):
    """Genera una risposta AI realistica per un task utilizzando modelli configurati."""
    db: Session = next(get_db())

    task = db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
    if not task:
        return "Task non trovato"

    response_data = {}
    try:
        if model_type == "OpenRouter":
            if not api_key:
                return "Errore: Chiave API OpenRouter non fornita."

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_identifier,
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are an AI specialized in legal tasks. The user will provide a legal task of type {task.task_type} and its input data. Provide a concise and accurate response in JSON format.",
                    },
                    {
                        "role": "user",
                        "content": f"Task Type: {task.task_type}\nInput Data: {json.dumps(task.input_data)}",
                    },
                ],
            }

            openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
            res = requests.post(openrouter_url, headers=headers, json=payload)
            res.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            ai_output = res.json()
            raw_content = ai_output["choices"][0]["message"]["content"]
            try:
                response_data = json.loads(raw_content)
            except json.JSONDecodeError:
                response_data = {
                    "raw_output": raw_content,
                    "error": "Model output was not valid JSON.",
                }

        elif model_type == "Local":
            # Simulazione per modelli locali. model_identifier sarà il percorso/endpoint.
            if task.task_type == "CLASSIFICATION":
                response_data = {
                    "predicted_labels": ["contract_breach", "negligence"],
                    "confidence": 0.85,
                    "explanation": f"Local model simulation ({model_identifier}) for classification based on: {task.input_data.get('text', 'N/A')}",
                }
            elif task.task_type == "QA":
                response_data = {
                    "answer": "The simulated local model states the statute of limitations is 3 years.",
                    "sources": ["Simulated Source 1", "Simulated Source 2"],
                    "confidence": 0.90,
                }
            elif task.task_type == "SUMMARIZATION":
                response_data = {
                    "summary": "This is a simulated summary from a local model.",
                    "key_points": ["Simulated point 1", "Simulated point 2"],
                    "length": (
                        len(task.input_data.get("text", "")) // 2
                        if "text" in task.input_data
                        else 50
                    ),
                }
            elif task.task_type == "PREDICTION":
                response_data = {
                    "predicted_outcome": "violation",
                    "probability": 0.75,
                    "key_factors": ["Simulated factor A", "Simulated factor B"],
                }
            else:
                response_data = {
                    "message": f"Simulated local response for {task.task_type} task with model {model_identifier}"
                }
        else:
            return f"Errore: Tipo di modello '{model_type}' non supportato."

    except requests.exceptions.RequestException as e:
        return f"Errore di rete/API con OpenRouter per {model_identifier}: {e}"
    except Exception as e:
        return f"Errore durante la generazione della risposta AI per {model_identifier}: {e}"

    # Aggiorna la response esistente o creane una nuova
    response = (
        db.query(models.Response).filter(models.Response.task_id == task_id).first()
    )

    if not response:
        response = models.Response(
            task_id=task_id, model_version=model_identifier, output_data=response_data
        )
        db.add(response)
    else:
        response.output_data = response_data
        response.model_version = model_identifier

    db.commit()
    return f"✅ Risposta AI generata per task {task_id} usando {model_identifier}"


# --- Sezione Data Viewer ---
def get_all_db_tasks():
    db: Session = next(get_db())
    tasks = db.query(models.LegalTask).all()
    return [
        [t.id, t.task_type, t.status, str(t.input_data), str(t.ground_truth_data)]
        for t in tasks
    ]


def get_all_db_responses():
    db: Session = next(get_db())
    responses = db.query(models.Response).all()
    return [[r.id, r.task_id, r.model_version, str(r.output_data)] for r in responses]


def get_all_db_feedbacks():
    db: Session = next(get_db())
    feedbacks = db.query(models.Feedback).all()
    return [
        [
            f.id,
            f.user_id,
            f.response_id,
            round(f.correctness_score or 0, 2),
            round(f.consistency_score or 0, 2),
            str(f.feedback_data),
        ]
        for f in feedbacks
    ]


# --- Sezione Analysis & Results ---
def get_aggregated_result(task_id: int):
    db: Session = next(get_db())
    result = aggregation_engine.aggregate_with_uncertainty(db, task_id)
    return result


def get_all_bias_reports():
    db: Session = next(get_db())
    reports = db.query(models.BiasReport).all()
    return [
        [r.id, r.task_id, r.user_id, r.bias_type, round(r.bias_score, 2)]
        for r in reports
    ]


# --- Sezione Export ---
def export_data(task_type: str, export_format: str, output_file: str):
    if not output_file.endswith(".jsonl"):
        output_file += ".jsonl"
    try:
        task_type_enum = TaskType(task_type)
        export_dataset.export_dataset(task_type_enum, export_format, output_file)
        return f"Dataset esportato con successo in `{output_file}`"
    except Exception as e:
        return f"Errore durante l'esportazione: {e}"


# --- Nuove funzioni per visualizzazioni avanzate ---
def visualize_uncertainty_output(task_id: int):
    """Crea una visualizzazione ricca dell'output con incertezza."""
    if not task_id:
        return gr.HTML("<p>Inserisci un ID task valido</p>")

    db: Session = next(get_db())
    try:
        result = aggregation_engine.aggregate_with_uncertainty(db, task_id)

        if "error" in result:
            return gr.HTML(
                f"<div style='color: red;'><strong>Errore:</strong> {result['error']}</div>"
            )

        # Crea HTML per visualizzazione strutturata
        html = f"""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; font-family: Arial, sans-serif;'>
            <h3 style='color: #2c3e50; margin-bottom: 20px;'>📊 Risultato Aggregato per Task {task_id}</h3>
            
            <div style='background-color: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #3498db;'>
                <h4 style='color: #34495e; margin-top: 0;'>🎯 Risposta Primaria</h4>
                <p style='font-size: 16px; margin: 10px 0;'><strong>{result.get('primary_answer', result.get('consensus_answer', 'N/A'))}</strong></p>
                <p style='margin: 5px 0;'>Livello di Confidenza: <span style='color: {"green" if result.get("confidence_level", 0) > 0.7 else "orange" if result.get("confidence_level", 0) > 0.4 else "red"}; font-weight: bold;'>{result.get("confidence_level", 0) * 100:.1f}%</span></p>
            </div>
        """

        if "alternative_positions" in result and result["alternative_positions"]:
            html += """
            <div style='background-color: #fff3cd; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #f39c12;'>
                <h4 style='color: #8b7d3a; margin-top: 0;'>🔄 Posizioni Alternative</h4>
            """
            for i, alt in enumerate(result["alternative_positions"][:3]):
                html += f"""
                <div style='margin: 8px 0; padding: 8px; background-color: #fefefe; border-radius: 4px;'>
                    <strong>Alternativa {i+1}:</strong> {alt.get('position', 'N/A')}<br>
                    <small>Supporto: {alt.get('support', 'N/A')} | Sostenitori: {', '.join(alt.get('supporters', [])[:2])}</small>
                </div>
                """
            html += "</div>"

        if "expert_disagreement" in result:
            disagreement = result["expert_disagreement"]
            html += """
            <div style='background-color: #d1ecf1; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #17a2b8;'>
                <h4 style='color: #0c5460; margin-top: 0;'>⚖️ Analisi del Disaccordo</h4>
            """

            if disagreement.get("consensus_areas"):
                html += "<p><strong>✅ Aree di Consenso:</strong></p><ul>"
                for area in disagreement["consensus_areas"][:3]:
                    html += f"<li style='margin: 2px 0;'>{area}</li>"
                html += "</ul>"

            if disagreement.get("contention_points"):
                html += "<p><strong>⚠️ Punti di Contesa:</strong></p><ul>"
                for point in disagreement["contention_points"][:3]:
                    html += f"<li style='margin: 2px 0;'>{point.get('aspect', 'N/A')} (Disaccordo: {point.get('disagreement_level', 0):.2f})</li>"
                html += "</ul>"

            if disagreement.get("reasoning_patterns"):
                html += "<p><strong>🧠 Pattern di Ragionamento:</strong></p>"
                for pattern, users in disagreement["reasoning_patterns"].items():
                    html += f"<span style='display: inline-block; margin: 3px; padding: 3px 8px; background-color: #e9ecef; border-radius: 12px; font-size: 12px;'>{pattern}: {len(users)}</span>"

            html += "</div>"

        if "transparency_metrics" in result:
            metrics = result["transparency_metrics"]
            html += f"""
            <div style='background-color: #d4edda; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #28a745;'>
                <h4 style='color: #155724; margin-top: 0;'>📈 Metriche di Trasparenza</h4>
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;'>
                    <div><strong>Valutatori:</strong> {metrics.get('evaluator_count', 'N/A')}</div>
                    <div><strong>Peso Autorità:</strong> {metrics.get('total_authority_weight', 'N/A'):.2f}</div>
                    <div><strong>Disaccordo:</strong> {metrics.get('disagreement_score', 'N/A'):.3f}</div>
                </div>
            </div>
            """

        html += "</div>"
        return gr.HTML(html)

    except Exception as e:
        return gr.HTML(
            f"<div style='color: red;'>Errore nell'elaborazione: {str(e)}</div>"
        )
    finally:
        db.close()


def get_bias_analysis_report(task_id: int):
    """Genera un report dettagliato sui bias per un task."""
    if not task_id:
        return "Inserisci un ID task valido"

    db: Session = next(get_db())
    try:
        bias_report = bias_analysis.calculate_total_bias(db, task_id)

        # Genera HTML report
        html = f"""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px;'>
            <h3 style='color: #dc3545;'>🔍 Analisi Bias - Task {task_id}</h3>
            
            <div style='background-color: white; padding: 15px; margin: 10px 0; border-radius: 8px;'>
                <h4>📊 Punteggi Bias</h4>
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;'>
        """

        bias_types = [
            ("demographic_bias", "Demografico", "👥"),
            ("professional_clustering", "Clustering Prof.", "💼"),
            ("temporal_drift", "Deriva Temporale", "⏰"),
            ("geographic_concentration", "Concentrazione Geo.", "🌍"),
            ("confirmation_bias", "Conferma", "✅"),
            ("anchoring_bias", "Ancoraggio", "⚓"),
        ]

        for bias_key, bias_name, icon in bias_types:
            if bias_key in bias_report:
                score = bias_report[bias_key]
                color = "red" if score > 0.6 else "orange" if score > 0.3 else "green"
                html += f"""
                <div style='text-align: center; padding: 10px; border: 1px solid #dee2e6; border-radius: 5px;'>
                    <div style='font-size: 24px;'>{icon}</div>
                    <div style='font-weight: bold; color: {color};'>{score:.3f}</div>
                    <div style='font-size: 12px; color: #6c757d;'>{bias_name}</div>
                </div>
                """

        html += f"""
                </div>
                
                <div style='margin-top: 20px; padding: 15px; background-color: {"#f8d7da" if bias_report.get("bias_level") == "high" else "#fff3cd" if bias_report.get("bias_level") == "medium" else "#d4edda"}; border-radius: 5px;'>
                    <strong>Livello Complessivo: {bias_report.get('bias_level', 'unknown').upper()}</strong>
                    (Punteggio: {bias_report.get('total_bias_score', 0):.3f})
                </div>
                
                <div style='margin-top: 15px;'>
                    <h5>🏆 Bias Dominanti:</h5>
                    <ol>
        """

        for bias_name, score in bias_report.get("dominant_bias_types", [])[:3]:
            html += f"<li>{bias_name.replace('_', ' ').title()}: {score:.3f}</li>"

        html += """
                    </ol>
                </div>
            </div>
        </div>
        """

        return html

    except Exception as e:
        return f"Errore nell'analisi bias: {str(e)}"
    finally:
        db.close()


def assign_devils_advocates(task_id: int, percentage: float = 10):
    """Assegna devil's advocates a un task."""
    if not task_id:
        return "Inserisci un ID task valido"

    db: Session = next(get_db())
    try:
        assigner = devils_advocate.DevilsAdvocateAssigner(percentage / 100)
        advocates = assigner.assign_advocates_for_task(db, task_id)

        return f"✅ Assegnati {len(advocates)} devil's advocates al task {task_id}: {advocates}"

    except Exception as e:
        return f"Errore nell'assegnazione: {str(e)}"
    finally:
        db.close()


def get_training_cycle_status():
    """Mostra lo stato del ciclo di training corrente."""
    db: Session = next(get_db())
    try:
        scheduler = training_scheduler.PeriodicTrainingScheduler(db)
        phase = scheduler.get_current_cycle_phase()

        cycle_dates = scheduler.get_cycle_dates()

        html = f"""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px;'>
            <h3 style='color: #495057;'>🔄 Stato Ciclo di Training</h3>
            
            <div style='background-color: white; padding: 15px; margin: 10px 0; border-radius: 8px; text-align: center;'>
                <h4 style='color: #28a745; margin: 0;'>Fase Corrente: {phase.upper()}</h4>
            </div>
            
            <div style='background-color: white; padding: 15px; margin: 10px 0; border-radius: 8px;'>
                <h4>📅 Date del Ciclo</h4>
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;'>
                    <div><strong>Inizio:</strong> {cycle_dates['cycle_start'].strftime('%Y-%m-%d')}</div>
                    <div><strong>Fine Raccolta:</strong> {cycle_dates['collection_end'].strftime('%Y-%m-%d')}</div>
                    <div><strong>Fine Validazione:</strong> {cycle_dates['validation_end'].strftime('%Y-%m-%d')}</div>
                    <div><strong>Fine Ciclo:</strong> {cycle_dates['cycle_end'].strftime('%Y-%m-%d')}</div>
                </div>
            </div>
        </div>
        """

        return html

    except Exception as e:
        return f"Errore nel recupero stato: {str(e)}"
    finally:
        db.close()


# ========= Definizione dell'Interfaccia Gradio =========
with gr.Blocks(theme=gr.themes.Soft(), title="RLCF Management UI") as demo:
    gr.Markdown("# 🚀 Interfaccia di Gestione e Testing per RLCF Framework")

    with gr.Tabs():
        # --- TAB 1: Dashboard ---
        with gr.TabItem("📊 Dashboard"):
            gr.Markdown("## Panoramica del Sistema")
            with gr.Row():
                users_box = gr.Number(label="👥 Utenti Totali", interactive=False)
                tasks_box = gr.Number(label="📝 Task Totali", interactive=False)
                feedbacks_box = gr.Number(label="💬 Feedback Totali", interactive=False)

            refresh_button = gr.Button("🔄 Aggiorna Statistiche")
            refresh_button.click(
                get_dashboard_stats, outputs=[users_box, tasks_box, feedbacks_box]
            )

        # --- TAB 2: Admin & Config ---
        with gr.TabItem("⚙️ Amministrazione e Configurazione"):
            gr.Markdown("## Gestione della Configurazione e dei Processi di Sistema")
            with gr.Accordion("🔧 Configurazione del Modello", open=False):
                model_config_editor = gr.Code(
                    label="model_config.yaml", language="yaml", lines=20
                )
                with gr.Row():
                    load_model_config_btn = gr.Button("Carica Configurazione")
                    save_model_config_btn = gr.Button("Salva e Ricarica")
                model_config_status = gr.Textbox(label="Stato")

            with gr.Accordion("📝 Configurazione dei Task", open=False):
                task_config_editor = gr.Code(
                    label="task_config.yaml", language="yaml", lines=20
                )
                with gr.Row():
                    load_task_config_btn = gr.Button("Carica Configurazione")
                    save_task_config_btn = gr.Button("Salva e Ricarica")
                task_config_status = gr.Textbox(label="Stato")

            with gr.Accordion("🏃‍♂️ Esecuzione Processi", open=True):
                gr.Markdown("### Avvia Processo di Aggregazione per un Task")
                with gr.Row():
                    agg_task_id = gr.Number(label="ID del Task", precision=0)
                    run_agg_btn = gr.Button("Avvia Aggregazione")
                agg_status = gr.Textbox(label="Log di Esecuzione")

        # --- TAB 3: User Management ---
        with gr.TabItem("👥 Gestione Utenti"):
            gr.Markdown("## Creazione e Gestione degli Utenti e delle Loro Credenziali")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Crea Nuovo Utente")
                    new_username = gr.Textbox(label="Username")
                    create_user_btn = gr.Button("Crea Utente")

                    gr.Markdown("### Aggiungi Credenziale a Utente")
                    cred_user_id = gr.Number(label="ID Utente", precision=0)
                    cred_type = gr.Dropdown(
                        label="Tipo Credenziale",
                        choices=[
                            "ACADEMIC_DEGREE",
                            "PROFESSIONAL_EXPERIENCE",
                            "PUBLICATION",
                            "INSTITUTIONAL_ROLE",
                        ],
                    )
                    cred_value = gr.Textbox(
                        label="Valore (es. 'PhD' o '10' per anni di esperienza)"
                    )
                    cred_weight = gr.Slider(
                        label="Peso", minimum=0, maximum=1, step=0.05, value=0.4
                    )
                    add_cred_btn = gr.Button("Aggiungi Credenziale")

                    user_status_msg = gr.Textbox(label="Stato Operazione")
                with gr.Column():
                    gr.Markdown("### Elenco Utenti")
                    all_users_df = gr.DataFrame(
                        headers=[
                            "ID",
                            "Username",
                            "Authority",
                            "Baseline",
                            "Track Record",
                        ],
                        interactive=False,
                    )
                    refresh_users_btn = gr.Button("Aggiorna Elenco")

        # --- TAB 4: Task & Feedback (Esempio semplificato) ---
        with gr.TabItem("📝 Gestione Task e Feedback"):
            gr.Markdown("## Creazione di Task e Invio di Feedback")
            with gr.Accordion("Carica Task da YAML", open=True):
                yaml_editor = gr.Code(
                    label="Contenuto YAML",
                    language="yaml",
                    lines=15,
                    value="tasks:\n  - task_type: CLASSIFICATION\n    input_data:\n      text: '...' ",
                )
                upload_yaml_btn = gr.Button("Crea Task da YAML")
                yaml_upload_status = gr.Textbox(label="Stato Creazione")

            with gr.Accordion("Genera Risposta AI per Task", open=True):
                with gr.Row():
                    ai_task_id = gr.Number(label="ID Task", precision=0)
                    ai_model_type = gr.Radio(
                        label="Tipo Modello",
                        choices=["OpenRouter", "Local"],
                        value="OpenRouter",
                    )
                with gr.Row():
                    ai_openrouter_api_key = gr.Textbox(
                        label="OpenRouter API Key (se OpenRouter)",
                        type="password",
                        interactive=True,
                    )
                    ai_model_identifier = gr.Textbox(
                        label="Nome Modello (OpenRouter) / Percorso (Locale)",
                        value="gpt-3.5-turbo",
                    )
                generate_ai_response_btn = gr.Button("Genera Risposta AI")
                ai_response_status = gr.Textbox(label="Stato Generazione Risposta AI")

        # --- TAB 5: Data Viewer ---
        with gr.TabItem("🔍 Visualizzatore Database"):
            with gr.Tabs():
                with gr.TabItem("Tasks"):
                    tasks_df = gr.DataFrame(
                        headers=["ID", "Tipo", "Stato", "Input Data", "Ground Truth"],
                        interactive=False,
                    )
                    gr.Button("Aggiorna Tasks").click(
                        get_all_db_tasks, outputs=tasks_df
                    )
                with gr.TabItem("Responses"):
                    responses_df = gr.DataFrame(
                        headers=["ID", "Task ID", "Versione Modello", "Output Data"],
                        interactive=False,
                    )
                    gr.Button("Aggiorna Responses").click(
                        get_all_db_responses, outputs=responses_df
                    )
                with gr.TabItem("Feedbacks"):
                    feedbacks_df = gr.DataFrame(
                        headers=[
                            "ID",
                            "User ID",
                            "Response ID",
                            "Correctness",
                            "Consistency",
                            "Feedback Data",
                        ],
                        interactive=False,
                    )
                    gr.Button("Aggiorna Feedbacks").click(
                        get_all_db_feedbacks, outputs=feedbacks_df
                    )

        # --- TAB 6: Analysis & Results ---
        with gr.TabItem("📈 Analisi e Risultati"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Risultato Aggregato del Task")
                    res_task_id = gr.Number(label="ID del Task", precision=0)
                    get_res_btn = gr.Button("Mostra Risultato")
                    result_output = gr.JSON(label="Risultato Aggregato")
                with gr.Column():
                    gr.Markdown("### Report sui Bias")
                    bias_df = gr.DataFrame(
                        headers=["ID", "Task ID", "User ID", "Tipo Bias", "Score"],
                        interactive=False,
                    )
                    gr.Button("Aggiorna Report Bias").click(
                        get_all_bias_reports, outputs=bias_df
                    )

        # --- TAB 7: Advanced Analysis & Uncertainty ---
        with gr.TabItem("🔬 Analisi Avanzata"):
            gr.Markdown("## Visualizzazioni Avanzate e Analisi dell'Incertezza")

            with gr.Accordion("📊 Visualizzazione Output con Incertezza", open=True):
                with gr.Row():
                    uncertainty_task_id = gr.Number(label="ID del Task", precision=0)
                    show_uncertainty_btn = gr.Button("Mostra Analisi Dettagliata")
                uncertainty_output = gr.HTML()

            with gr.Accordion("🔍 Analisi Bias Dettagliata", open=False):
                with gr.Row():
                    bias_task_id = gr.Number(label="ID del Task", precision=0)
                    show_bias_btn = gr.Button("Genera Report Bias")
                bias_report_output = gr.HTML()

        # --- TAB 8: Devil's Advocate Management ---
        with gr.TabItem("👹 Devil's Advocate"):
            gr.Markdown("## Gestione Devil's Advocates")

            with gr.Accordion("Assegnazione Devil's Advocates", open=True):
                gr.Markdown("### Assegna Devil's Advocates a un Task")
                with gr.Row():
                    devils_task_id = gr.Number(label="ID del Task", precision=0)
                    devils_percentage = gr.Slider(
                        label="Percentuale (%)", minimum=5, maximum=30, value=10, step=5
                    )
                    assign_devils_btn = gr.Button("Assegna Devil's Advocates")
                devils_status = gr.Textbox(label="Stato Assegnazione")

        # --- TAB 9: Training Cycles ---
        with gr.TabItem("🔄 Cicli di Training"):
            gr.Markdown("## Gestione dei Cicli di Training Periodici")

            with gr.Row():
                cycle_refresh_btn = gr.Button("🔄 Aggiorna Stato Ciclo")
            cycle_status_display = gr.HTML()

            with gr.Accordion("📈 Accountability Report", open=False):
                gr.Markdown("### Genera Report di Accountability")
                with gr.Row():
                    cycle_start_date = gr.Textbox(
                        label="Data Inizio Ciclo (YYYY-MM-DD)", value="2024-01-01"
                    )
                    generate_report_btn = gr.Button("Genera Report")
                accountability_output = gr.JSON(label="Report di Accountability")

        # --- TAB 10: Export Datasets ---
        with gr.TabItem("📤 Esporta Dataset"):
            gr.Markdown("## Esporta i dati per il Fine-Tuning")
            export_task_type = gr.Dropdown(
                label="Tipo di Task", choices=[t.value for t in TaskType]
            )
            export_format_type = gr.Dropdown(
                label="Formato di Esportazione", choices=["sft", "preference"]
            )
            export_filename = gr.Textbox(
                label="Nome File di Output", value="exported_data.jsonl"
            )
            export_btn = gr.Button("Esporta Dataset")
            export_status = gr.Textbox(label="Stato Esportazione")

    # --- Collegamenti Logici per i Pulsanti ---
    # Admin
    load_model_config_btn.click(get_model_config_content, outputs=model_config_editor)
    save_model_config_btn.click(
        update_model_config_content,
        inputs=model_config_editor,
        outputs=[model_config_status, model_config_editor],
    )
    load_task_config_btn.click(get_task_config_content, outputs=task_config_editor)
    save_task_config_btn.click(
        update_task_config_content,
        inputs=task_config_editor,
        outputs=[task_config_status, task_config_editor],
    )
    run_agg_btn.click(
        run_task_aggregation_orchestration, inputs=agg_task_id, outputs=agg_status
    )

    # Users
    create_user_btn.click(
        create_user, inputs=new_username, outputs=[user_status_msg, all_users_df]
    )
    add_cred_btn.click(
        add_credential,
        inputs=[cred_user_id, cred_type, cred_value, cred_weight],
        outputs=[user_status_msg, all_users_df],
    )
    refresh_users_btn.click(get_all_users, outputs=all_users_df)

    # Tasks
    upload_yaml_btn.click(
        create_task_from_yaml,
        inputs=yaml_editor,
        outputs=[yaml_upload_status, tasks_df],
    )
    generate_ai_response_btn.click(
        generate_ai_response_for_task,
        inputs=[ai_task_id, ai_model_type, ai_model_identifier, ai_openrouter_api_key],
        outputs=ai_response_status,
    )

    # Analysis
    get_res_btn.click(get_aggregated_result, inputs=res_task_id, outputs=result_output)

    # Export
    export_btn.click(
        export_data,
        inputs=[export_task_type, export_format_type, export_filename],
        outputs=export_status,
    )

    # Advanced Analysis
    show_uncertainty_btn.click(
        visualize_uncertainty_output,
        inputs=uncertainty_task_id,
        outputs=uncertainty_output,
    )
    show_bias_btn.click(
        get_bias_analysis_report, inputs=bias_task_id, outputs=bias_report_output
    )

    # Devil's Advocate
    assign_devils_btn.click(
        assign_devils_advocates,
        inputs=[devils_task_id, devils_percentage],
        outputs=devils_status,
    )

    # Training Cycles
    cycle_refresh_btn.click(get_training_cycle_status, outputs=cycle_status_display)

    # Caricamento dati iniziale
    demo.load(get_dashboard_stats, outputs=[users_box, tasks_box, feedbacks_box])
    demo.load(get_all_users, outputs=all_users_df)
    demo.load(get_training_cycle_status, outputs=cycle_status_display)

if __name__ == "__main__":
    demo.launch()
