from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelEntry:
    engine: str
    language: str
    weights: Path | None
    pretrained: bool


class ModelRegistry:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _weights_dir(self, engine: str, language: str) -> Path:
        return self.root / engine / language

    def resolve(self, engine: str, language: str) -> ModelEntry:
        weights_dir = self._weights_dir(engine, language)
        if weights_dir.is_dir() and any(weights_dir.iterdir()):
            return ModelEntry(engine, language, weights_dir, pretrained=False)
        return ModelEntry(engine, language, weights=None, pretrained=True)

    def has_finetuned(self, engine: str, language: str) -> bool:
        return not self.resolve(engine, language).pretrained

    def _previous_dir(self, engine: str, language: str) -> Path:
        return self.root / engine / f"{language}__previous"

    def promote(self, engine: str, language: str, candidate_dir: Path) -> None:
        candidate_dir = Path(candidate_dir)
        live_dir = self._weights_dir(engine, language)
        previous_dir = self._previous_dir(engine, language)

        if previous_dir.exists():
            shutil.rmtree(previous_dir)

        if live_dir.exists():
            live_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(live_dir), str(previous_dir))

        live_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(candidate_dir, live_dir)

    def rollback(self, engine: str, language: str) -> bool:
        previous_dir = self._previous_dir(engine, language)
        if not previous_dir.is_dir():
            return False

        live_dir = self._weights_dir(engine, language)
        if live_dir.exists():
            shutil.rmtree(live_dir)
        shutil.move(str(previous_dir), str(live_dir))
        return True
