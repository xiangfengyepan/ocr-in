from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.engines import ENGINES
from api.import_jobs.routes import router as import_router
from api.labeling.routes import router as labeling_router
from api.model_catalog import build_catalog
from api.ocr.routes import router as ocr_router
from api.registry import ModelRegistry
from api.training_jobs.routes import router as training_router
from api.training_jobs.routes import training_active
from api.util import settings

app = FastAPI(title="ocr-in", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
registry = ModelRegistry(settings.models_dir)
app.include_router(labeling_router)
app.include_router(ocr_router)
app.include_router(import_router)
app.include_router(training_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class RuntimeConfig(BaseModel):
    ollama_host: str


@app.get("/config")
def get_config() -> dict:
    return {"ollama_host": settings.ollama_host}


@app.post("/config")
def set_config(body: RuntimeConfig) -> dict:
    # Runtime override (in-memory, resets on restart). The corrector reads
    # settings.ollama_host per call, so this takes effect immediately.
    settings.ollama_host = body.ollama_host.strip()
    return {"ollama_host": settings.ollama_host}


@app.get("/engines")
def list_engines() -> dict[str, list[str]]:
    return {"engines": sorted(ENGINES)}


@app.get("/models")
def list_models() -> list[dict]:
    return build_catalog(settings.models_dir)


@app.get("/engines/availability")
def engines_availability() -> dict:
    training = training_active()
    return {
        "trocr": not training,
        "crnn": not training,
        "tesseract": True,
        "training": training,
    }
