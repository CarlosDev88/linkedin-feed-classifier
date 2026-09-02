"""Configuración central del clasificador de intención del feed."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "/data/raw"))
LABELS_DIR = PROJECT_ROOT / "data" / "labels"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MLRUNS_DIR = PROJECT_ROOT / "mlruns"

MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI", f"file://{MLRUNS_DIR.as_posix()}"
)
MLFLOW_EXPERIMENT_NAME = os.getenv(
    "MLFLOW_EXPERIMENT_NAME", "feed-intent-classifier"
)
MODEL_NAME = os.getenv("MODEL_NAME", "feed-intent-classifier")
MODEL_STAGE = os.getenv("MODEL_STAGE", "Production")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
HIGH_THRESHOLD = float(os.getenv("HIGH_THRESHOLD", "0.75"))
LOW_THRESHOLD = float(os.getenv("LOW_THRESHOLD", "0.40"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.95"))
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))

