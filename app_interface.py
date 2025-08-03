import gradio as gr
import requests
import json

# --- Configurazione Globale ---
API_URL = "http://127.0.0.1:8000"
# Per semplicità, la chiave API è qui. In un'app reale, sarebbe gestita in modo più sicuro.
ADMIN_API_KEY = "supersecretkey"
HEADERS = {"Content-Type": "application/json"}
ADMIN_HEADERS = {"Content-Type": "application/json", "X-API-KEY": ADMIN_API_KEY}

# --- Funzioni Helper per le Chiamate API ---

def get_model_config():
    try:
        response = requests.get(f"{API_URL}/config/model", headers=ADMIN_HEADERS)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"Errore: {e}"

def update_model_config(config_text):
    try:
        config_data = json.loads(config_text)
        response = requests.put(f"{API_URL}/config/model", json=config_data, headers=ADMIN_HEADERS)
        response.raise_for_status()
        return "Configurazione aggiornata con successo!", json.dumps(response.json(), indent=2)
    except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
        return f"Errore: {e}", config_text

def update_task_status(task_id, new_status):
    try:
        response = requests.post(f"{API_URL}/tasks/{task_id}/status?new_status={new_status}", headers=ADMIN_HEADERS)
        response.raise_for_status()
        return f"Stato del Task {task_id} aggiornato a {new_status}", json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"Errore: {e}", ""

def create_user(username):
    try:
        response = requests.post(f"{API_URL}/users/", json={"username": username}, headers=HEADERS)
        response.raise_for_status()
        return f"Utente '{username}' creato con successo!", json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"Errore: {e}", ""

def add_credential(user_id, cred_type, cred_value, cred_weight):
    try:
        data = {"type": cred_type, "value": cred_value, "weight": float(cred_weight)}
        response = requests.post(f"{API_URL}/users/{user_id}/credentials/", json=data, headers=HEADERS)
        response.raise_for_status()
        return f"Credenziale aggiunta all'utente {user_id}", json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"Errore: {e}", ""

def create_task(task_type, input_data_json):
    try:
        input_data = json.loads(input_data_json)
        data = {"task_type": task_type, "input_data": input_data}
        response = requests.post(f"{API_URL}/tasks/", json=data, headers=HEADERS)
        response.raise_for_status()
        return "Task creato con successo!", json.dumps(response.json(), indent=2)
    except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
        return f"Errore: {e}", ""

def submit_feedback(response_id, user_id, accuracy, utility, transparency, feedback_data_json):
    try:
        feedback_data = json.loads(feedback_data_json)
        data = {
            "user_id": int(user_id),
            "accuracy_score": float(accuracy),
            "utility_score": float(utility),
            "transparency_score": float(transparency),
            "feedback_data": feedback_data
        }
        response = requests.post(f"{API_URL}/responses/{response_id}/feedback/", json=data, headers=HEADERS)
        response.raise_for_status()
        return "Feedback inviato con successo!", json.dumps(response.json(), indent=2)
    except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
        return f"Errore: {e}", ""

def rate_feedback(feedback_id, user_id, helpfulness):
    try:
        data = {"user_id": int(user_id), "helpfulness_score": int(helpfulness)}
        response = requests.post(f"{API_URL}/feedback/{feedback_id}/rate/", json=data, headers=HEADERS)
        response.raise_for_status()
        return "Valutazione inviata con successo!", json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"Errore: {e}", ""

def get_task_result(task_id):
    try:
        response = requests.get(f"{API_URL}/tasks/{task_id}/result/", headers=HEADERS)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"Errore: {e}"

def get_all_data(table_name):
    try:
        endpoint_map = {
            "Users": "users/all",
            "Credentials": "credentials/all",
            "Legal Tasks": "tasks/all",
            "Responses": "responses/all",
            "Feedback": "feedback/all",
            "Feedback Ratings": "feedback_ratings/all",
            "Bias Reports": "bias_reports/all",
        }
        endpoint = endpoint_map.get(table_name)
        if not endpoint:
            return "Seleziona una tabella valida.", None

        response = requests.get(f"{API_URL}/{endpoint}", headers=ADMIN_HEADERS)
        response.raise_for_status()
        data = response.json()
        if not data:
            return "Nessun dato trovato.", None
        
        # Gradio DataFrame expects a list of lists (rows) and a list of strings (headers)
        headers = list(data[0].keys())
        rows = [[item[key] for key in headers] for item in data]
        return "", gr.DataFrame(value=rows, headers=headers, row_count=len(rows), col_count=len(headers), interactive=False)

    except requests.exceptions.RequestException as e:
        return f"Errore: {e}", None

# --- Costruzione dell'Interfaccia Gradio ---
with gr.Blocks(theme=gr.themes.Soft(), title="RLCF Testing Interface") as demo:
    gr.Markdown("# Interfaccia di Test per il Framework RLCF")

    with gr.Tabs():
        with gr.TabItem("1. Admin & Config"):
            gr.Markdown("## Gestione della Configurazione del Modello e dello Stato dei Task")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Configurazione Modello (`model_config.yaml`)")
                    config_display = gr.Code(label="Configurazione Attuale", language="yaml", interactive=False)
                    update_config_btn = gr.Button("Aggiorna Configurazione")
                    refresh_config_btn = gr.Button("Visualizza/Aggiorna Configurazione Attuale")
                with gr.Column():
                    gr.Markdown("### Gestione Stato Task")
                    task_id_status = gr.Number(label="Task ID", precision=0)
                    status_dropdown = gr.Dropdown(label="Nuovo Stato", choices=["OPEN", "BLIND_EVALUATION", "AGGREGATED", "CLOSED"])
                    update_status_btn = gr.Button("Imposta Nuovo Stato")
            status_output = gr.Textbox(label="Output Stato", interactive=False)
            config_output_display = gr.Code(label="Risposta API (Config)", language="json", interactive=False)

        with gr.TabItem("2. User & Task Setup"):
            gr.Markdown("## Creazione di Utenti, Task e Credenziali")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Crea Utente")
                    username_input = gr.Textbox(label="Username")
                    create_user_btn = gr.Button("Crea Utente")
                with gr.Column():
                    gr.Markdown("### Crea Task Legale")
                    task_type_dropdown = gr.Dropdown(label="Tipo di Task", choices=["SUMMARIZATION", "CLASSIFICATION", "QA", "PREDICTION", "NLI", "NER", "DRAFTING"])
                    input_data_textbox = gr.Textbox(label="Input Data (JSON)", lines=5, placeholder='Es. {"document": "Testo da riassumere..."}')
                    create_task_btn = gr.Button("Crea Task")
            with gr.Column():
                gr.Markdown("### Aggiungi Credenziale a Utente")
                cred_user_id = gr.Number(label="User ID", precision=0)
                cred_type = gr.Dropdown(label="Tipo Credenziale", choices=["ACADEMIC_DEGREE", "PROFESSIONAL_EXPERIENCE", "PUBLICATION", "INSTITUTIONAL_ROLE", "PROFESSIONAL_FIELD"])
                cred_value = gr.Textbox(label="Valore (es. PhD, 10, Diritto Civile)")
                cred_weight = gr.Slider(label="Peso (w_i)", minimum=0, maximum=1, step=0.05, value=0.2)
                add_cred_btn = gr.Button("Aggiungi Credenziale")
            setup_output = gr.Code(label="Risposta API", language="json", interactive=False)

        with gr.TabItem("3. Community Feedback"):
            gr.Markdown("## Invio di Feedback e Valutazioni")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Invia Feedback su una Risposta")
                    fb_response_id = gr.Number(label="Response ID", precision=0)
                    fb_user_id = gr.Number(label="User ID", precision=0)
                    fb_accuracy = gr.Slider(label="Accuracy Score", minimum=1, maximum=5, step=0.1)
                    fb_utility = gr.Slider(label="Utility Score", minimum=1, maximum=5, step=0.1)
                    fb_transparency = gr.Slider(label="Transparency Score", minimum=1, maximum=5, step=0.1)
                    feedback_data_textbox = gr.Textbox(label="Feedback Data (JSON)", lines=5, placeholder='Es. {\"revised_summary\": \"Nuovo riassunto\", \"rating\": \"good\"}')
                    submit_fb_btn = gr.Button("Invia Feedback")
                with gr.Column():
                    gr.Markdown("### Valuta il Feedback di un Altro Utente")
                    rate_feedback_id = gr.Number(label="Feedback ID da valutare", precision=0)
                    rate_user_id = gr.Number(label="User ID (chi valuta)", precision=0)
                    rate_helpfulness = gr.Slider(label="Helpfulness Score", minimum=1, maximum=5, step=1)
                    rate_fb_btn = gr.Button("Invia Valutazione")
            feedback_output = gr.Code(label="Risposta API", language="json", interactive=False)

        with gr.TabItem("4. Results & Analysis"):
            gr.Markdown("## Visualizzazione dei Risultati Aggregati")
            task_id_result = gr.Number(label="Task ID", precision=0)
            get_result_btn = gr.Button("Ottieni Risultato Aggregato")
            result_output = gr.Code(label="Risultato Aggregato (JSON)", language="json")

        with gr.TabItem("5. Database Viewer"):
            gr.Markdown("## Visualizza Contenuto del Database")
            with gr.Row():
                db_table_dropdown = gr.Dropdown(
                    label="Seleziona Tabella",
                    choices=["Users", "Credentials", "Legal Tasks", "Responses", "Feedback", "Feedback Ratings", "Bias Reports"]
                )
                get_db_data_btn = gr.Button("Carica Dati")
            db_output_message = gr.Textbox(label="Messaggio", interactive=False)
            db_data_display = gr.DataFrame(label="Dati della Tabella", interactive=False)

    # --- Collegamenti Funzioni -> Interfaccia ---
    refresh_config_btn.click(get_model_config, outputs=config_display)
    update_config_btn.click(update_model_config, inputs=config_display, outputs=[status_output, config_output_display])
    update_status_btn.click(update_task_status, inputs=[task_id_status, status_dropdown], outputs=[status_output, config_output_display])

    create_user_btn.click(create_user, inputs=username_input, outputs=[status_output, setup_output])
    add_cred_btn.click(add_credential, inputs=[cred_user_id, cred_type, cred_value, cred_weight], outputs=[status_output, setup_output])
    create_task_btn.click(create_task, inputs=[task_type_dropdown, input_data_textbox], outputs=[status_output, setup_output])

    submit_fb_btn.click(submit_feedback, inputs=[fb_response_id, fb_user_id, fb_accuracy, fb_utility, fb_transparency, feedback_data_textbox], outputs=[status_output, feedback_output])
    rate_fb_btn.click(rate_feedback, inputs=[rate_feedback_id, rate_user_id, rate_helpfulness], outputs=[status_output, feedback_output])

    get_result_btn.click(get_task_result, inputs=task_id_result, outputs=result_output)

    get_db_data_btn.click(get_all_data, inputs=db_table_dropdown, outputs=[db_output_message, db_data_display])

if __name__ == "__main__":
    demo.launch()
