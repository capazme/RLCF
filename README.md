# Reinforcement Learning from Community Feedback (RLCF) - Framework Implementation

Questo repository contiene l'implementazione Python del framework **Reinforcement Learning from Community Feedback (RLCF)**, come descritto nel paper scientifico. Il progetto è una piattaforma di ricerca ad alte prestazioni per studiare e validare sistemi di IA Giuridica attraverso meccanismi di validazione distribuita, punteggi di autorità dinamici e aggregazione che preserva l'incertezza.

## 🚀 Caratteristiche Principali

- **Architettura Async**: Framework completamente asincrono basato su FastAPI e SQLAlchemy async per prestazioni ottimali
- **Sicurezza**: Valutazione sicura delle formule tramite asteval invece di eval()
- **Atomicità**: Operazioni di aggregazione atomiche e resilienti ai fallimenti
- **Testabilità**: Suite di test completa con pytest e mocking avanzato
- **Code Quality**: Formattazione automatica con Black e linting con Ruff
- **Dependency Injection**: Sistema centralizzato di iniezione delle dipendenze per migliorare testabilità

## Architettura e Workflow dei Componenti

Il framework è costruito su un'architettura modulare che mappa direttamente i concetti teorici del paper in componenti software interagenti. Il workflow principale è orchestrato da un'API FastAPI asincrona che espone la logica di business definita in un livello di servizi atomici.

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Async Layer                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Dependencies  │  │      Main       │  │    Endpoints    │  │
│  │   (DI System)   │  │   (Routing)     │  │   (Handlers)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Async Service Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Task Service   │  │ Post Processing │  │ Bias Analysis   │  │
│  │  (Orchestration)│  │  (Consistency)  │  │  (Detection)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Core Algorithm Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Authority Module│  │ Aggregation     │  │ Task Handlers   │  │
│  │  (Safe Eval)    │  │   Engine        │  │  (Polymorphic)  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                  Async Database Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   AsyncSession  │  │   Models        │  │   Config        │  │
│  │   (aiosqlite)   │  │ (SQLAlchemy)    │  │  (YAML/Pydantic)│  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1. Configurazione del Modello (`model_config.yaml`)

- **Concetto (Paper):** L'intero modello matematico (pesi, soglie, formule) è parametrizzabile.
- **Implementazione:** Un file `model_config.yaml` definisce tutti i parametri del modello, come i pesi di autorità (α, β, γ), il fattore di decadimento (λ) e le regole per calcolare le credenziali. Questo permette ai ricercatori di testare diverse teorie senza modificare il codice.
- **Modulo Chiave:** `config.py` carica e valida questo file utilizzando Pydantic, rendendo la configurazione accessibile globalmente in modo sicuro.

### 2. Modulo di Autorità (`authority_module.py`) - 🔒 Async & Secure

- **Concetto (Paper):** Il **Modello di Punteggio di Autorità Dinamica** (Sez. 2.1).
- **Implementazione:** Questo modulo funge da motore di calcolo asincrono e sicuro che applica le regole definite in `model_config.yaml`.
  - `calculate_baseline_credentials`: Implementa la **Sez. 2.2**, calcolando **B_u** applicando dinamicamente le funzioni di punteggio (mappa o formula) e i pesi (w_i) definiti nel YAML. **Sicurezza**: Utilizza `asteval` per valutazione sicura delle formule invece di `eval()`.
  - `update_track_record`: Implementa l'**Eq. 3 (Sez. 2.3)**, aggiornando lo storico delle performance **T_u** con una media mobile esponenziale.
  - `update_authority_score`: Implementa l'**Eq. 1 (Sez. 2.1)**, calcolando il punteggio di autorità finale **A_u** come combinazione lineare dei suoi componenti.
  - **Nuove Feature**: Tutte le funzioni sono async e utilizzano transazioni database atomiche.

### 3. Motore di Aggregazione (`aggregation_engine.py`) - ⚡ Async & Optimized

- **Concetto (Paper):** L'**Algoritmo di Aggregazione con Preservazione dell'Incertezza** (Sez. 3.1).
- **Implementazione:**
  - `calculate_disagreement`: Implementa l'**Eq. 4 (Sez. 3.2)**, quantificando il disaccordo **δ** tramite l'entropia di Shannon normalizzata.
  - `aggregate_with_uncertainty`: Implementa l'**Algoritmo 1**, orchestrando il processo di aggregazione asincrona. Se il disaccordo calcolato supera la soglia **τ** (definita nel config), produce un output strutturato che preserva le diverse posizioni (Sez. 3.3).
  - **Nuove Feature**: Completamente asincrono, pattern di aggregazione ottimizzati e analisi avanzata dei pattern di ragionamento.

### 4. Moduli di Governance e Analisi - 🔍 Advanced Analytics

- **Concetto (Paper):** I **Meccanismi di Garanzia della Qualità** (Sez. 4) e la necessità di un processo auditabile.
- **Implementazione:**
  - `post_processing.py`: Logica asincrona per calcolare il **punteggio di coerenza** e correttezza di un utente dopo aggregazione.
  - `bias_analysis.py`: Implementa il **Framework di Rilevamento Bias** (Sez. 4.3) completamente asincrono con:
    - Calcolo del **clustering professionale (b_2)**
    - Analisi bias demografico, temporale, geografico
    - Bias di conferma e ancoraggio
    - Correlazione autorità-correttezza
  - `models.py`: Definisce un `Enum` `TaskStatus` per gestire esplicitamente il ciclo di vita di un task (OPEN, BLIND_EVALUATION, AGGREGATED, CLOSED).
  - **Nuove Feature**: Analisi bias multi-dimensionale e reporting automatico.

### 5. Livello di Servizi e API (`services/` e `main.py`) - 🎯 Atomic & Resilient

- **Concetto (Paper):** Un'architettura robusta e un processo di governance chiaro (Sez. 5).
- **Implementazione:**
  - `services/task_service.py`: Logica di business asincrona con **operazioni atomiche**:
    - `orchestrate_task_aggregation`: Workflow completo resiliente ai fallimenti
    - `_aggregate_and_save_result`: Operazione atomica di aggregazione  
    - `_calculate_and_store_consistency`: Operazione atomica di calcolo coerenza
    - `_calculate_and_store_bias`: Operazione atomica di analisi bias
  - `main.py`: API FastAPI completamente asincrona con endpoint ottimizzati e dependency injection centralizzata.
  - `dependencies.py`: **Nuovo**: Sistema centralizzato di dependency injection per migliorare testabilità e manutenibilità.
  - **Nuove Feature**: Transazioni atomiche, gestione errori granulare, alta disponibilità.

## 🧪 Qualità e Testing

Il framework include una suite di test completa e strumenti per garantire la qualità del codice:

### Test Suite
- **Posizione**: `tests/` directory
- **Framework**: pytest con supporto asyncio
- **Copertura**: Test unitari per tutti i moduli core
- **Mocking**: AsyncMock per operazioni database asincrone
- **Esecuzione**: `pytest tests/`

### Strumenti di Qualità
- **Formattazione**: Black per formattazione automatica del codice
- **Linting**: Ruff per analisi statica e rilevamento errori
- **Configurazione**: `pytest.ini`, `dev-requirements.txt`

### Fixtures e Helper
- `conftest.py`: Fixtures comuni per mock di database, utenti, task
- Generatori di dati di test per scenari complessi
- Performance timer per test di performance

### Comandi di Sviluppo
```bash
# Installa dipendenze di sviluppo
pip install -r dev-requirements.txt

# Esegui test
pytest

# Formatta codice
black .

# Lint codice
ruff check . --fix
```

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

## 🚀 Setup e Installazione

### Requisiti del Sistema
- Python 3.8+
- SQLite (incluso con Python)

### Installazione
1.  **Clona il repository:**
    ```bash
    git clone <repository-url>
    cd RLCF
    ```

2.  **Crea ambiente virtuale (raccomandato):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # or
    venv\Scripts\activate     # Windows
    ```

3.  **Installa le dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Installa dipendenze di sviluppo (opzionale):**
    ```bash
    pip install -r dev-requirements.txt
    ```

### Avvio dell'Applicazione

**FastAPI Server:**
```bash
uvicorn rlcf_framework.main:app --reload
```

**Gradio Interface:**
```bash
python app_interface.py
```

### Accesso
- **API Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`  
- **Gradio Interface**: `http://127.0.0.1:7860`

### Verifica Installazione
```bash
# Esegui test di base
pytest tests/test_authority_module.py -v

# Verifica linting
ruff check .

# Verifica formattazione
black --check .
```

## 📈 Performance Features

- **Async/Await**: Tutte le operazioni database sono asincrone per massime prestazioni
- **Connection Pooling**: Pool di connessioni database ottimizzato
- **Atomic Transactions**: Operazioni atomiche per consistency e resilienza  
- **Lazy Loading**: Caricamento asincrono dei dati secondo necessità
- **Efficient Querying**: Query ottimizzate con SQLAlchemy async

## 🔒 Sicurezza

- **Safe Evaluation**: asteval invece di eval() per valutazione sicura formule
- **API Key Protection**: Endpoint admin protetti da API key
- **Input Validation**: Validazione Pydantic per tutti gli input
- **SQL Injection Protection**: SQLAlchemy ORM protegge da SQL injection
- **Connection Security**: Connessioni database sicure con parametri controllati