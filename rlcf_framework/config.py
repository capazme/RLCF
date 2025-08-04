import yaml
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal, List
import os

# Modelli Pydantic per validare la struttura del file YAML
class ScoringFunction(BaseModel):
    type: Literal["map", "formula"]
    values: Dict[str, float] = Field(default_factory=dict)
    expression: str = ""
    default: float = 0.0

class CredentialTypeConfig(BaseModel):
    weight: float
    scoring_function: ScoringFunction

class BaselineCredentialsConfig(BaseModel):
    types: Dict[str, CredentialTypeConfig]

class ModelConfig(BaseModel):
    authority_weights: Dict[str, float]
    track_record: Dict[str, float]
    thresholds: Dict[str, float]
    baseline_credentials: BaselineCredentialsConfig

class TaskSchemaDefinition(BaseModel):
    # Using Any for now, will be parsed into actual types later
    # This represents the structure like {"field_name": "str", "another_field": "List[int]"}
    input_data: Dict[str, str]
    feedback_data: Dict[str, str]
    ground_truth_keys: List[str] = Field(default_factory=list)

class TaskConfig(BaseModel):
    task_types: Dict[str, TaskSchemaDefinition]

def load_model_config() -> ModelConfig:
    """Carica, valida e restituisce la configurazione del modello dal file YAML."""
    config_path = os.path.join(os.path.dirname(__file__), "model_config.yaml")
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    return ModelConfig(**config_data)

def load_task_config() -> TaskConfig:
    """Carica, valida e restituisce la configurazione dei task dal file YAML."""
    config_path = os.path.join(os.path.dirname(__file__), "task_config.yaml")
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    return TaskConfig(**config_data)

# Istanza globale della configurazione caricata
model_settings = load_model_config()
task_settings = load_task_config()

# Manteniamo le impostazioni dell'app separate
class AppSettings(BaseModel):
    DATABASE_URL: str = "sqlite:///./rlcf.db"

app_settings = AppSettings()