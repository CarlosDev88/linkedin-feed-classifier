"""Configuración central del clasificador de intención del feed."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carga las variables definidas en el archivo .env
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# Rutas principales del proyecto
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "/data/raw"))
LABELS_DIR = PROJECT_ROOT / "data" / "labels"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MLRUNS_DIR = PROJECT_ROOT / "mlruns"


# Clases que el modelo aprenderá a distinguir
CLASS_NAMES = ("no_vacante","vacante")
CLASS_TO_ID = {"no_vacante":0,"vacante":1}

# Embeddings son los modelos que compararemos
EMBEDDING_MODELS = {
    "minilm": "paraphrase-multilingual-MiniLM-L12-v2",
    "e5": "intfloat/multilingual-e5-base",
}

DEFAULT_EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    EMBEDDING_MODELS["minilm"],
)

# Límite inicial de texto que se utilizará para generar embeddings
TEXT_MAX_CHARS = int(os.getenv("TEXT_MAX_CHARS", "500"))

# Umbrales para las tres posibles decisiones
HIGH_THRESHOLD = float(os.getenv("HIGH_THRESHOLD", "0.75"))
LOW_THRESHOLD = float(os.getenv("LOW_THRESHOLD", "0.40"))

# Agrupamiento de publicaciones casi duplicadas
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.95"))

# Reproducibilidad
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))

# Configuración de MLflow
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "file:///workspace/mlruns",
)

MLFLOW_EXPERIMENT_NAME = os.getenv(
    "MLFLOW_EXPERIMENT_NAME",
    "feed-intent-classifier",
)

# Configuración del modelo publicado
MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "feed-intent-classifier",
)

MODEL_STAGE = os.getenv(
    "MODEL_STAGE",
    "Production",
)
