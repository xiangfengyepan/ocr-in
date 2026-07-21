from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.engines import ENGINES
from api.import_jobs.routes import router as import_router
from api.labeling.routes import router as labeling_router
from api.model_catalog import build_catalog
from api.ocr.routes import router as ocr_router
from api.registry import ModelRegistry
from api.util import settings
from api.util.gpu_lock import gpu_busy

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/engines")
def list_engines() -> dict[str, list[str]]:
    return {"engines": sorted(ENGINES)}


@app.get("/models")
def list_models() -> list[dict]:
    return build_catalog(settings.models_dir)


@app.get("/engines/availability")
def engines_availability() -> dict:
    busy = gpu_busy()
    return {"trocr": not busy, "crnn": not busy, "tesseract": True, "training": busy}
