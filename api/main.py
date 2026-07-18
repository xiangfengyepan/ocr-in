from __future__ import annotations

from fastapi import FastAPI

from api.engines import ENGINES
from api.registry import ModelRegistry
from api.util import settings

app = FastAPI(title="ocr-in", version="0.1.0")
registry = ModelRegistry(settings.models_dir)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/engines")
def list_engines() -> dict[str, list[str]]:
    return {"engines": sorted(ENGINES)}
