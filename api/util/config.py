from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OCR_", env_file=str(API_DIR / ".env"), extra="ignore"
    )

    models_dir: Path = REPO_ROOT / "models"
    datasets_dir: Path = REPO_ROOT / "datasets"
    collected_dir: Path = REPO_ROOT / "datasets" / "collected"
    ollama_host: str = "http://localhost:11434"
    # Comma-separated list of allowed CORS origins (the web app's URL).
    cors_origins: str = "http://localhost:4200"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
