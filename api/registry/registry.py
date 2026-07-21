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

    def _personal_dir(self, engine: str, language: str) -> Path:
        return self.root / engine / f"{language}__personal"

    def _personal_previous_dir(self, engine: str, language: str) -> Path:
        return self.root / engine / f"{language}__personal__previous"

    def resolve(self, engine: str, language: str) -> ModelEntry:
        weights_dir = self._weights_dir(engine, language)
        if weights_dir.is_dir() and any(weights_dir.iterdir()):
            return ModelEntry(engine, language, weights_dir, pretrained=False)
        return ModelEntry(engine, language, weights=None, pretrained=True)

    def has_finetuned(self, engine: str, language: str) -> bool:
        return not self.resolve(engine, language).pretrained

    @staticmethod
    def _is_populated(path: Path) -> bool:
        return path.is_dir() and any(path.iterdir())

    def personalized(self, engine: str, language: str) -> Path | None:
        personal_dir = self._personal_dir(engine, language)
        return personal_dir if self._is_populated(personal_dir) else None

    def serving_weights(self, engine: str, language: str) -> Path | None:
        personal_dir = self.personalized(engine, language)
        if personal_dir is not None:
            return personal_dir
        baseline_dir = self._weights_dir(engine, language)
        return baseline_dir if self._is_populated(baseline_dir) else None

    def promote(self, engine: str, language: str, candidate_dir: Path) -> None:
        candidate_dir = Path(candidate_dir)
        personal_dir = self._personal_dir(engine, language)
        previous_dir = self._personal_previous_dir(engine, language)

        if previous_dir.exists():
            shutil.rmtree(previous_dir)

        if personal_dir.exists():
            personal_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(personal_dir), str(previous_dir))

        personal_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(candidate_dir, personal_dir)

    def rollback(self, engine: str, language: str) -> bool:
        personal_dir = self._personal_dir(engine, language)
        previous_dir = self._personal_previous_dir(engine, language)

        if previous_dir.is_dir():
            if personal_dir.exists():
                shutil.rmtree(personal_dir)
            shutil.move(str(previous_dir), str(personal_dir))
            return True

        if personal_dir.exists():
            shutil.rmtree(personal_dir)
            return True

        return False
