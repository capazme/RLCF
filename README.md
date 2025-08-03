# Reinforcement Learning from Community Feedback (RLCF) - Framework Implementation

Questo repository contiene l'implementazione Python del framework **Reinforcement Learning from Community Feedback (RLCF)**, come descritto nel paper scientifico. Il progetto è una piattaforma di ricerca funzionante per studiare e validare sistemi di IA Giuridica attraverso meccanismi di validazione distribuita, punteggi di autorità dinamici e aggregazione che preserva l'incertezza.

## Architettura e Workflow dei Componenti

Il framework è costruito su un'architettura modulare che mappa direttamente i concetti teorici del paper in componenti software interagenti. Il workflow principale è orchestrato da un'API FastAPI che espone la logica di business definita in un livello di servizi.

![RLCF Architecture Diagram](https://i.imgur.com/your-diagram-image.png)  <!-- Placeholder per un futuro diagramma -->

### 1. Configurazione del Modello (`model_config.yaml`)

- **Concetto (Paper):** L'intero modello matematico (pesi, soglie, formule) è parametrizzabile.
- **Implementazione:** Un file `model_config.yaml` definisce tutti i parametri del modello, come i pesi di autorità (α, β, γ), il fattore di decadimento (λ) e le regole per calcolare le credenziali. Questo permette ai ricercatori di testare diverse teorie senza modificare il codice.
- **Modulo Chiave:** `config.py` carica e valida questo file utilizzando Pydantic, rendendo la configurazione accessibile globalmente in modo sicuro.

### 2. Modulo di Autorità (`authority_module.py`)

- **Concetto (Paper):** Il **Modello di Punteggio di Autorità Dinamica** (Sez. 2.1).
- **Implementazione:** Questo modulo funge da motore di calcolo generico che applica le regole definite in `model_config.yaml`.
  - `calculate_baseline_credentials`: Implementa la **Sez. 2.2**, calcolando **B_u** applicando dinamicamente le funzioni di punteggio (mappa o formula) e i pesi (w_i) definiti nel YAML.
  - `update_track_record`: Implementa l'**Eq. 3 (Sez. 2.3)**, aggiornando lo storico delle performance **T_u** con una media mobile esponenziale.
  - `update_authority_score`: Implementa l'**Eq. 1 (Sez. 2.1)**, calcolando il punteggio di autorità finale **A_u** come combinazione lineare dei suoi componenti.

### 3. Motore di Aggregazione (`aggregation_engine.py`)

- **Concetto (Paper):** L'**Algoritmo di Aggregazione con Preservazione dell'Incertezza** (Sez. 3.1).
- **Implementazione:**
  - `calculate_disagreement`: Implementa l'**Eq. 4 (Sez. 3.2)**, quantificando il disaccordo **δ** tramite l'entropia di Shannon normalizzata.
  - `aggregate_with_uncertainty`: Implementa l'**Algoritmo 1**, orchestrando il processo di aggregazione. Se il disaccordo calcolato supera la soglia **τ** (definita nel config), produce un output strutturato che preserva le diverse posizioni (Sez. 3.3).

### 4. Moduli di Governance e Analisi

- **Concetto (Paper):** I **Meccanismi di Garanzia della Qualità** (Sez. 4) e la necessità di un processo auditabile.
- **Implementazione:**
  - `post_processing.py`: Contiene la logica per calcolare il **punteggio di coerenza** di un utente dopo che un task è stato aggregato.
  - `bias_analysis.py`: Implementa il **Framework di Rilevamento Bias** (Sez. 4.3), con una funzione iniziale per il calcolo del **clustering professionale (b_2)**.
  - `models.py`: Definisce un `Enum` `TaskStatus` per gestire esplicitamente il ciclo di vita di un task (OPEN, BLIND_EVALUATION, AGGREGATED, CLOSED).

### 5. Livello di Servizi e API (`services/` e `main.py`)

- **Concetto (Paper):** Un'architettura robusta e un processo di governance chiaro (Sez. 5).
- **Implementazione:**
  - `services/task_service.py`: Contiene la logica di business di alto livello, come `orchestrate_task_aggregation`, che gestisce il workflow completo di aggregazione, calcolo della coerenza e analisi dei bias. Questo disaccoppia la logica dall'API.
  - `main.py`: Fornisce gli endpoint FastAPI. Gli endpoint sono "sottili" e delegano il lavoro pesante al livello di servizi. Include endpoint per la gestione del ciclo di vita (`POST /tasks/{task_id}/status`) e per la governance del modello (`GET /config/model`, `PUT /config/model`).

## Workflow Sperimentale (Come Usare il Framework)

1.  **Configurare il Modello:** Definire i parametri dell'esperimento in `model_config.yaml`.
2.  **Creare Utenti e Credenziali:** Usare `POST /users/` e `POST /users/{user_id}/credentials/` per popolare la comunità. Le credenziali devono corrispondere ai tipi definiti nel config (es. `type: "PROFESSIONAL_FIELD"`, `value: "Diritto Civile"`).
3.  **Creare un Task Legale:** Usare `POST /tasks/` per creare una nuova query.
4.  **Avviare la Valutazione:** L'amministratore dell'esperimento imposta lo stato del task su `BLIND_EVALUATION` usando `POST /tasks/{task_id}/status`.
5.  **Raccogliere Feedback:** I partecipanti inviano il loro feedback tramite `POST /responses/{response_id}/feedback/`. L'API impedirà l'invio se il task non è nella fase corretta.
6.  **Aggregare i Risultati:** L'amministratore imposta lo stato su `AGGREGATED`. Questa azione triggera il `task_service` che:
    a. Esegue `aggregate_with_uncertainty`.
    b. Esegue `calculate_and_store_consistency`.
    c. Esegue `calculate_professional_clustering_bias` per ogni partecipante.
7.  **Analizzare i Risultati:** I ricercatori possono interrogare `GET /tasks/{task_id}/result/` per ottenere l'output aggregato e analizzare i dati salvati nelle tabelle `feedback` e `bias_reports`.
8.  **Iterare:** I ricercatori possono modificare la configurazione del modello tramite `PUT /config/model` e avviare un nuovo esperimento per testare diverse ipotesi.

## Setup e Installazione

1.  **Installare le dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Avviare l'applicazione:**
    ```bash
    uvicorn rlcf_framework.main:app --reload
    ```
L'API sarà disponibile all'indirizzo `http://127.0.0.1:8000/docs` per la documentazione interattiva di Swagger UI.