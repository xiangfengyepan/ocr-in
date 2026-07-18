from __future__ import annotations

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
