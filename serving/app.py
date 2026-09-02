"""API inicial del modelo. La carga desde MLflow se implementará después."""

from fastapi import FastAPI


app = FastAPI(title="Feed Intent Classifier API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": "not_loaded"}


