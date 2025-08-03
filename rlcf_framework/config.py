import yaml
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal

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

def load_model_config() -> ModelConfig:
    """Carica, valida e restituisce la configurazione del modello dal file YAML."""
    with open("rlcf_framework/model_config.yaml", "r") as f:
        config_data = yaml.safe_load(f)
    return ModelConfig(**config_data)

# Istanza globale della configurazione caricata
model_settings = load_model_config()

# Manteniamo le impostazioni dell'app separate
class AppSettings(BaseModel):
    DATABASE_URL: str = "sqlite:///./rlcf.db"

app_settings = AppSettings()