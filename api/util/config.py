from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OCR_", env_file=".env", extra="ignore")

    models_dir: Path = REPO_ROOT / "models"
    datasets_dir: Path = REPO_ROOT / "datasets"
    collected_dir: Path = REPO_ROOT / "datasets" / "collected"
    ollama_host: str = "http://localhost:11434"


settings = Settings()
