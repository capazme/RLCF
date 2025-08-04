

# user_dashboard.py

import gradio as gr
import yaml
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import json

# Importazioni dal framework RLCF
from rlcf_framework import models, schemas, authority_module, devils_advocate
from rlcf_framework.database import SessionLocal, engine
from rlcf_framework.models import TaskType, TaskStatus
import requests

# Setup del Database
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========= Stato Globale Utente =========
current_user_id = None

# ========= Funzioni Helper =========

def login_user(username: str):
    """Simula il login di un utente."""
    global current_user_id
    db: Session = next(get_db())
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return None, "Utente non trovato. Verifica il nome utente."
    
    current_user_id = user.id
    return user.id, f"Benvenuto, {username}!"

def get_user_profile():
    """Ottiene il profilo dell'utente corrente."""
    if not current_user_id:
        return None
    
    db: Session = next(get_db())
    user = db.query(models.User).filter(models.User.id == current_user_id).first()
    
    if not user:
        return None
    
    credentials = [
        f"{cred.type}: {cred.value}" 
        for cred in user.credentials
    ]
    
    return {
        'username': user.username,
        'authority_score': round(user.authority_score, 3),
        'track_record': round(user.track_record_score, 3),
        'baseline_credentials': round(user.baseline_credential_score, 3),
        'credentials': credentials
    }

def get_available_tasks():
    """Ottiene tutti i task disponibili per valutazione."""
    if not current_user_id:
        return []
    
    db: Session = next(get_db())
    
    # Trova task in BLIND_EVALUATION che l'utente non ha ancora valutato
    evaluated_task_ids = db.query(models.Response.task_id).join(
        models.Feedback
    ).filter(
        models.Feedback.user_id == current_user_id
    ).distinct().all()
    
    evaluated_ids = [t[0] for t in evaluated_task_ids]
    
    available_tasks = db.query(models.LegalTask).filter(
        models.LegalTask.status == TaskStatus.BLIND_EVALUATION.value,
        ~models.LegalTask.id.in_(evaluated_ids) if evaluated_ids else True
    ).all()
    
    # Controlla se l'utente è devil's advocate per qualche task
    task_info = []
    for task in available_tasks:
        da_assigner = devils_advocate.DevilsAdvocateAssigner()
        is_da = da_assigner.is_devils_advocate(db, task.id, current_user_id)
        
        task_info.append({
            'id': task.id,
            'type': task.task_type,
            'created': task.created_at.strftime("%Y-%m-%d %H:%M"),
            'is_devils_advocate': is_da,
            'input_preview': str(task.input_data)[:100] + "..."
        })
    
    return task_info

def get_task_for_evaluation(task_id: int):
    """Ottiene i dettagli di un task per la valutazione."""
    if not current_user_id:
        return None, None, None, None
    
    db: Session = next(get_db())
    
    task = db.query(models.LegalTask).filter(
        models.LegalTask.id == task_id
    ).first()
    
    if not task:
        return None, None, None, None
    
    # Ottieni la risposta AI
    response = db.query(models.Response).filter(
        models.Response.task_id == task_id
    ).first()
    
    if not response:
        return None, None, None, None
    
    # Controlla se è devil's advocate
    da_assigner = devils_advocate.DevilsAdvocateAssigner()
    is_da = da_assigner.is_devils_advocate(db, task_id, current_user_id)
    
    # Se è devil's advocate, ottieni i prompt critici
    critical_prompts = []
    if is_da:
        critical_prompts = da_assigner.generate_critical_prompts(task.task_type)
    
    return task, response, is_da, critical_prompts

def submit_task_feedback(
    task_id: int,
    accuracy: float,
    utility: float,
    transparency: float,
    feedback_json: str,
    is_devils_advocate: bool = False
):
    """Sottomette il feedback per un task."""
    if not current_user_id:
        return "Errore: Nessun utente loggato"
    
    db: Session = next(get_db())
    
    try:
        # Parse del feedback JSON
        feedback_data = json.loads(feedback_json)
        
        # Se è devil's advocate, aggiungi flag
        if is_devils_advocate:
            feedback_data['is_devils_advocate'] = True
        
        # Trova la response
        response = db.query(models.Response).join(models.LegalTask).filter(
            models.LegalTask.id == task_id
        ).first()
        
        if not response:
            return "Errore: Response non trovata"
        
        # Crea il feedback
        feedback = models.Feedback(
            user_id=current_user_id,
            response_id=response.id,
            accuracy_score=accuracy,
            utility_score=utility,
            transparency_score=transparency,
            feedback_data=feedback_data,
            is_blind_phase=True
        )
        
        db.add(feedback)
        db.commit()
        
        # Aggiorna authority score
        quality_score = authority_module.calculate_quality_score(db, feedback)
        authority_module.update_track_record(db, current_user_id, quality_score)
        
        return "✅ Feedback inviato con successo!"
        
    except json.JSONDecodeError:
        return "Errore: Feedback data non è un JSON valido"
    except Exception as e:
        db.rollback()
        return f"Errore: {str(e)}"

def get_my_feedback_history():
    """Ottiene lo storico dei feedback dell'utente."""
    if not current_user_id:
        return []
    
    db: Session = next(get_db())
    
    feedbacks = db.query(models.Feedback).filter(
        models.Feedback.user_id == current_user_id
    ).order_by(models.Feedback.submitted_at.desc()).limit(20).all()
    
    history = []
    for fb in feedbacks:
        task = fb.response.task
        history.append({
            'task_id': task.id,
            'task_type': task.task_type,
            'submitted': fb.submitted_at.strftime("%Y-%m-%d %H:%M"),
            'accuracy': fb.accuracy_score,
            'utility': fb.utility_score,
            'transparency': fb.transparency_score,
            'consistency': fb.consistency_score if fb.consistency_score else "N/A",
            'correctness': fb.correctness_score if fb.correctness_score else "N/A"
        })
    
    return history

def generate_feedback_template(task_type: str) -> str:
    """Genera un template JSON per il feedback basato sul tipo di task."""
    templates = {
        "CLASSIFICATION": {
            "validated_labels": ["label1", "label2"],
            "reasoning": "Explain your label choices..."
        },
        "QA": {
            "validated_answer": "Your answer here...",
            "position": "correct",
            "reasoning": "Explain why this answer is correct..."
        },
        "SUMMARIZATION": {
            "revised_summary": "Your improved summary...",
            "rating": "good",
            "reasoning": "What makes this summary good/bad..."
        },
        "PREDICTION": {
            "chosen_outcome": "violation",
            "reasoning": "Legal basis for your prediction..."
        },
        "NLI": {
            "chosen_label": "entail",
            "reasoning": "Why this relationship holds..."
        },
        "NER": {
            "validated_tags": ["O", "PERSON", "O", "ORG"],
            "reasoning": "Tag assignment rationale..."
        },
        "DRAFTING": {
            "revised_target": "Your improved draft...",
            "rating": "better",
            "reasoning": "What improvements were made..."
        }
    }
    
    template = templates.get(task_type, {"reasoning": "Your feedback..."})
    return json.dumps(template, indent=2)

# ========= Interfaccia Gradio =========

with gr.Blocks(theme=gr.themes.Soft(), title="RLCF User Dashboard") as demo:
    gr.Markdown("#  RLCF User Dashboard - Valutazione Feedback")
    
    with gr.Row():
        with gr.Column(scale=1):
            # Login Section
            with gr.Accordion(" Login", open=True):
                username_input = gr.Textbox(label="Username", placeholder="Inserisci il tuo username")
                login_btn = gr.Button("Login", variant="primary")
                login_status = gr.Textbox(label="Status", interactive=False)
            
            # User Profile
            with gr.Accordion(" Il Mio Profilo", open=False):
                profile_display = gr.JSON(label="Profilo Utente")
                refresh_profile_btn = gr.Button(" Aggiorna Profilo")
        
        with gr.Column(scale=3):
            with gr.Tabs():
                # Tab 1: Available Tasks
                with gr.TabItem(" Task Disponibili"):
                    gr.Markdown("### Task in attesa di valutazione")
                    
                    available_tasks_df = gr.DataFrame(
                        headers=["ID", "Tipo", "Creato", "Devil's Advocate", "Preview"],
                        label="Task Disponibili",
                        interactive=False
                    )
                    
                    refresh_tasks_btn = gr.Button(" Aggiorna Lista Task")
                    
                    with gr.Row():
                        selected_task_id = gr.Number(label="ID Task da Valutare", precision=0)
                        load_task_btn = gr.Button(" Carica Task", variant="primary")
                
                # Tab 2: Evaluate Task
                with gr.TabItem("✍️ Valuta Task"):
                    gr.Markdown("### Valutazione del Task")
                    
                    # Task Details
                    with gr.Accordion(" Dettagli Task", open=True):
                        task_type_display = gr.Textbox(label="Tipo Task", interactive=False)
                        task_input_display = gr.JSON(label="Input del Task")
                        ai_response_display = gr.JSON(label="Risposta AI da Valutare")
                        is_da_display = gr.Checkbox(label="Sei Devil's Advocate per questo task", interactive=False)
                    
                    # Critical Prompts (solo per Devil's Advocate)
                    critical_prompts_box = gr.Textbox(
                        label=" Prompts Critici (Devil's Advocate)",
                        lines=5,
                        visible=False,
                        interactive=False
                    )
                    
                    # Evaluation Form
                    gr.Markdown("###  Il Tuo Feedback")
                    
                    with gr.Row():
                        accuracy_score = gr.Slider(
                            label="Accuratezza (1-10)",
                            minimum=1, maximum=10, step=0.5, value=5
                        )
                        utility_score = gr.Slider(
                            label="Utilità (1-10)",
                            minimum=1, maximum=10, step=0.5, value=5
                        )
                        transparency_score = gr.Slider(
                            label="Trasparenza (1-10)",
                            minimum=1, maximum=10, step=0.5, value=5
                        )
                    
                    feedback_template_btn = gr.Button(" Genera Template Feedback")
                    
                    feedback_json_input = gr.Code(
                        label="Feedback Data (JSON)",
                        language="json",
                        lines=10
                    )
                    
                    submit_feedback_btn = gr.Button(" Invia Feedback", variant="primary")
                    feedback_status = gr.Textbox(label="Stato Invio", interactive=False)
                
                # Tab 3: My History
                with gr.TabItem(" Il Mio Storico"):
                    gr.Markdown("### I miei feedback precedenti")
                    
                    history_df = gr.DataFrame(
                        headers=["Task ID", "Tipo", "Inviato", "Accuracy", "Utility", 
                                "Transparency", "Consistency", "Correctness"],
                        label="Storico Feedback"
                    )
                    
                    refresh_history_btn = gr.Button(" Aggiorna Storico")
                    
                    # Performance Summary
                    with gr.Accordion(" Le Mie Performance", open=False):
                        performance_summary = gr.Markdown()
    
    # ========= Event Handlers =========
    
    def login_handler(username):
        user_id, message = login_user(username)
        if user_id:
            profile = get_user_profile()
            tasks = get_available_tasks()
            return (
                message,
                profile,
                [[t['id'], t['type'], t['created'], "✓" if t['is_devils_advocate'] else "", t['input_preview']] 
                 for t in tasks]
            )
        return message, None, []
    
    def load_task_handler(task_id):
        if not task_id:
            return None, None, None, False, gr.update(visible=False), None
        
        task, response, is_da, critical_prompts = get_task_for_evaluation(int(task_id))
        
        if not task:
            return "Task non trovato", None, None, False, gr.update(visible=False), None
        
        prompts_text = ""
        if is_da and critical_prompts:
            prompts_text = "Considera questi aspetti critici nella tua valutazione:\n\n"
            prompts_text += "\n".join(f"• {prompt}" for prompt in critical_prompts)
        
        return (
            task.task_type,
            task.input_data,
            response.output_data,
            is_da,
            gr.update(visible=is_da, value=prompts_text),
            generate_feedback_template(task.task_type)
        )
    
    def submit_feedback_handler(task_id, accuracy, utility, transparency, feedback_json, is_da):
        if not task_id:
            return "Seleziona prima un task"
        
        result = submit_task_feedback(
            int(task_id), accuracy, utility, transparency, feedback_json, is_da
        )
        
        # Aggiorna liste dopo invio
        tasks = get_available_tasks()
        history = get_my_feedback_history()
        
        return (
            result,
            [[t['id'], t['type'], t['created'], "✓" if t['is_devils_advocate'] else "", t['input_preview']] 
             for t in tasks],
            [[h['task_id'], h['task_type'], h['submitted'], h['accuracy'], 
              h['utility'], h['transparency'], h['consistency'], h['correctness']] 
             for h in history]
        )
    
    def generate_template_handler(task_type):
        if not task_type:
            return "Carica prima un task"
        return generate_feedback_template(task_type)
    
    def calculate_performance_summary():
        if not current_user_id:
            return "Effettua il login per vedere le tue performance"
        
        db: Session = next(get_db())
        user = db.query(models.User).filter(models.User.id == current_user_id).first()
        
        feedbacks = db.query(models.Feedback).filter(
            models.Feedback.user_id == current_user_id
        ).all()
        
        if not feedbacks:
            return "Nessun feedback ancora inviato"
        
        import numpy as np
        avg_consistency = np.mean([f.consistency_score for f in feedbacks 
                                  if f.consistency_score is not None])
        avg_correctness = np.mean([f.correctness_score for f in feedbacks 
                                  if f.correctness_score is not None])
        
        summary = f"""
        ###  Le Tue Statistiche
        
        - **Authority Score**: {user.authority_score:.3f}
        - **Track Record**: {user.track_record_score:.3f}
        - **Feedback Totali**: {len(feedbacks)}
        - **Consistency Media**: {avg_consistency:.2%} (quando disponibile)
        - **Correctness Media**: {avg_correctness:.2%} (quando disponibile)
        
        ###  Ranking
        La tua autorità ti posiziona nel top {calculate_percentile(db, user.authority_score):.0%} degli evaluatori!
        """
        
        return summary
    
    def calculate_percentile(db, score):
        all_scores = db.query(models.User.authority_score).all()
        scores_list = [s[0] for s in all_scores]
        return (sum(1 for s in scores_list if s <= score) / len(scores_list))
    
    # Collegamenti
    login_btn.click(
        login_handler,
        inputs=[username_input],
        outputs=[login_status, profile_display, available_tasks_df]
    )
    
    refresh_profile_btn.click(
        lambda: get_user_profile(),
        outputs=[profile_display]
    )
    
    refresh_tasks_btn.click(
        lambda: [[t['id'], t['type'], t['created'], "✓" if t['is_devils_advocate'] else "", t['input_preview']] 
                 for t in get_available_tasks()],
        outputs=[available_tasks_df]
    )
    
    load_task_btn.click(
        load_task_handler,
        inputs=[selected_task_id],
        outputs=[
            task_type_display, task_input_display, ai_response_display,
            is_da_display, critical_prompts_box, feedback_json_input
        ]
    )
    
    feedback_template_btn.click(
        generate_template_handler,
        inputs=[task_type_display],
        outputs=[feedback_json_input]
    )
    
    submit_feedback_btn.click(
        submit_feedback_handler,
        inputs=[
            selected_task_id, accuracy_score, utility_score, 
            transparency_score, feedback_json_input, is_da_display
        ],
        outputs=[feedback_status, available_tasks_df, history_df]
    )
    
    def refresh_history_and_summary():
        """Aggiorna sia lo storico che il sommario delle performance"""
        history_data = [[h['task_id'], h['task_type'], h['submitted'], h['accuracy'], 
                        h['utility'], h['transparency'], h['consistency'], h['correctness']] 
                       for h in get_my_feedback_history()]
        summary_data = calculate_performance_summary()
        return history_data, summary_data
    
    refresh_history_btn.click(
        refresh_history_and_summary,
        outputs=[history_df, performance_summary]
    )

if __name__ == "__main__":
    demo.launch(server_port=7861)  # Porta diversa per non conflitto con admin
