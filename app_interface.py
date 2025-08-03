import gradio as gr
import yaml
from sqlalchemy.orm import Session
from typing import Dict, Any

# --- Importazioni dal tuo RLCF Framework ---
# Assicurati che il framework sia installabile o nel PYTHONPATH
from rlcf_framework import models, schemas, services, aggregation_engine, bias_analysis, authority_module, export_dataset
from rlcf_framework.database import SessionLocal, engine
from rlcf_framework.config import load_model_config, load_task_config, model_settings, task_settings
from rlcf_framework.models import TaskType, TaskStatus

# --- Setup del Database ---
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
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
        return "Configurazione del modello salvata e ricaricata con successo!", get_model_config_content()
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
        return "Configurazione dei task salvata e ricaricata con successo!", get_task_config_content()
    except Exception as e:
        return f"Errore: {e}", get_task_config_content()

def run_task_aggregation_orchestration(task_id: int):
    db: Session = next(get_db())
    try:
        db_task = db.query(models.LegalTask).filter(models.LegalTask.id == task_id).first()
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
    return f"Utente '{username}' creato con successo (ID: {db_user.id}).", get_all_users()

def add_credential(user_id: int, cred_type: str, cred_value: str, cred_weight: float):
    db: Session = next(get_db())
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return f"Utente con ID {user_id} non trovato.", None
    
    db_credential = models.Credential(type=cred_type, value=cred_value, weight=cred_weight, user_id=user_id)
    db.add(db_credential)
    db.commit()
    
    # Ricalcola e aggiorna i punteggi
    authority_module.calculate_baseline_credentials(db, user_id)
    authority_module.update_authority_score(db, user_id, user.track_record_score) # Usa il track record esistente come performance recente
    
    return f"Credenziale aggiunta all'utente {user_id}. Punteggi ricalcolati.", get_all_users()

def get_all_users():
    db: Session = next(get_db())
    users = db.query(models.User).all()
    # Formatta per gr.DataFrame
    return [[u.id, u.username, round(u.authority_score, 2), round(u.baseline_credential_score, 2), round(u.track_record_score, 2)] for u in users]

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
        db_task = models.LegalTask(
            task_type=task_data.task_type,
            input_data=task_data.input_data
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        created_tasks_info.append(f"Task ID {db_task.id} ({db_task.task_type}) creato.")

    return "\n".join(created_tasks_info), get_all_db_tasks()

# --- Sezione Data Viewer ---
def get_all_db_tasks():
    db: Session = next(get_db())
    tasks = db.query(models.LegalTask).all()
    return [[t.id, t.task_type, t.status, str(t.input_data), str(t.ground_truth_data)] for t in tasks]

def get_all_db_responses():
    db: Session = next(get_db())
    responses = db.query(models.Response).all()
    return [[r.id, r.task_id, r.model_version, str(r.output_data)] for r in responses]

def get_all_db_feedbacks():
    db: Session = next(get_db())
    feedbacks = db.query(models.Feedback).all()
    return [[f.id, f.user_id, f.response_id, round(f.correctness_score or 0, 2), round(f.consistency_score or 0, 2), str(f.feedback_data)] for f in feedbacks]

# --- Sezione Analysis & Results ---
def get_aggregated_result(task_id: int):
    db: Session = next(get_db())
    result = aggregation_engine.aggregate_with_uncertainty(db, task_id)
    return result

def get_all_bias_reports():
    db: Session = next(get_db())
    reports = db.query(models.BiasReport).all()
    return [[r.id, r.task_id, r.user_id, r.bias_type, round(r.bias_score, 2)] for r in reports]

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
            refresh_button.click(get_dashboard_stats, outputs=[users_box, tasks_box, feedbacks_box])

        # --- TAB 2: Admin & Config ---
        with gr.TabItem("⚙️ Amministrazione e Configurazione"):
            gr.Markdown("## Gestione della Configurazione e dei Processi di Sistema")
            with gr.Accordion("🔧 Configurazione del Modello", open=False):
                model_config_editor = gr.Code(label="model_config.yaml", language="yaml", lines=20)
                with gr.Row():
                    load_model_config_btn = gr.Button("Carica Configurazione")
                    save_model_config_btn = gr.Button("Salva e Ricarica")
                model_config_status = gr.Textbox(label="Stato")
            
            with gr.Accordion("📝 Configurazione dei Task", open=False):
                task_config_editor = gr.Code(label="task_config.yaml", language="yaml", lines=20)
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
                    cred_type = gr.Dropdown(label="Tipo Credenziale", choices=["ACADEMIC_DEGREE", "PROFESSIONAL_EXPERIENCE", "PUBLICATION", "INSTITUTIONAL_ROLE"])
                    cred_value = gr.Textbox(label="Valore (es. 'PhD' o '10' per anni di esperienza)")
                    cred_weight = gr.Slider(label="Peso", minimum=0, maximum=1, step=0.05, value=0.4)
                    add_cred_btn = gr.Button("Aggiungi Credenziale")
                    
                    user_status_msg = gr.Textbox(label="Stato Operazione")
                with gr.Column():
                    gr.Markdown("### Elenco Utenti")
                    all_users_df = gr.DataFrame(headers=["ID", "Username", "Authority", "Baseline", "Track Record"], interactive=False)
                    refresh_users_btn = gr.Button("Aggiorna Elenco")

        # --- TAB 4: Task & Feedback (Esempio semplificato) ---
        with gr.TabItem("📝 Gestione Task e Feedback"):
            gr.Markdown("## Creazione di Task e Invio di Feedback")
            with gr.Accordion("Carica Task da YAML", open=True):
                 yaml_editor = gr.Code(label="Contenuto YAML", language="yaml", lines=15, value="tasks:\n  - task_type: CLASSIFICATION\n    input_data:\n      text: '...'")
                 upload_yaml_btn = gr.Button("Crea Task da YAML")
                 yaml_upload_status = gr.Textbox(label="Stato Creazione")

        # --- TAB 5: Data Viewer ---
        with gr.TabItem("🔍 Visualizzatore Database"):
             with gr.Tabs():
                 with gr.TabItem("Tasks"):
                     tasks_df = gr.DataFrame(headers=["ID", "Tipo", "Stato", "Input Data", "Ground Truth"], interactive=False)
                     gr.Button("Aggiorna Tasks").click(get_all_db_tasks, outputs=tasks_df)
                 with gr.TabItem("Responses"):
                     responses_df = gr.DataFrame(headers=["ID", "Task ID", "Versione Modello", "Output Data"], interactive=False)
                     gr.Button("Aggiorna Responses").click(get_all_db_responses, outputs=responses_df)
                 with gr.TabItem("Feedbacks"):
                     feedbacks_df = gr.DataFrame(headers=["ID", "User ID", "Response ID", "Correctness", "Consistency", "Feedback Data"], interactive=False)
                     gr.Button("Aggiorna Feedbacks").click(get_all_db_feedbacks, outputs=feedbacks_df)
        
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
                    bias_df = gr.DataFrame(headers=["ID", "Task ID", "User ID", "Tipo Bias", "Score"], interactive=False)
                    gr.Button("Aggiorna Report Bias").click(get_all_bias_reports, outputs=bias_df)

        # --- TAB 7: Export Datasets ---
        with gr.TabItem("📤 Esporta Dataset"):
            gr.Markdown("## Esporta i dati per il Fine-Tuning")
            export_task_type = gr.Dropdown(label="Tipo di Task", choices=[t.value for t in TaskType])
            export_format_type = gr.Dropdown(label="Formato di Esportazione", choices=["sft", "preference"])
            export_filename = gr.Textbox(label="Nome File di Output", value="exported_data.jsonl")
            export_btn = gr.Button("Esporta Dataset")
            export_status = gr.Textbox(label="Stato Esportazione")

    # --- Collegamenti Logici per i Pulsanti ---
    # Admin
    load_model_config_btn.click(get_model_config_content, outputs=model_config_editor)
    save_model_config_btn.click(update_model_config_content, inputs=model_config_editor, outputs=[model_config_status, model_config_editor])
    load_task_config_btn.click(get_task_config_content, outputs=task_config_editor)
    save_task_config_btn.click(update_task_config_content, inputs=task_config_editor, outputs=[task_config_status, task_config_editor])
    run_agg_btn.click(run_task_aggregation_orchestration, inputs=agg_task_id, outputs=agg_status)
    
    # Users
    create_user_btn.click(create_user, inputs=new_username, outputs=[user_status_msg, all_users_df])
    add_cred_btn.click(add_credential, inputs=[cred_user_id, cred_type, cred_value, cred_weight], outputs=[user_status_msg, all_users_df])
    refresh_users_btn.click(get_all_users, outputs=all_users_df)

    # Tasks
    upload_yaml_btn.click(create_task_from_yaml, inputs=yaml_editor, outputs=[yaml_upload_status, tasks_df])

    # Analysis
    get_res_btn.click(get_aggregated_result, inputs=res_task_id, outputs=result_output)

    # Export
    export_btn.click(export_data, inputs=[export_task_type, export_format_type, export_filename], outputs=export_status)
    
    # Caricamento dati iniziale
    demo.load(get_dashboard_stats, outputs=[users_box, tasks_box, feedbacks_box])
    demo.load(get_all_users, outputs=all_users_df)

if __name__ == "__main__":
    demo.launch()