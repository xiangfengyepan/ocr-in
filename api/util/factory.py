from __future__ import annotations

from collections.abc import Sequence

from api.engines import ENGINES, OcrEngine
from api.registry import ModelRegistry


def build_engine(
    engine: str, languages: Sequence[str], registry: ModelRegistry
) -> OcrEngine:
    if engine not in ENGINES:
        raise ValueError(f"unknown engine: {engine!r}; available: {sorted(ENGINES)}")
    entry = registry.resolve(engine, languages[0])
    weights = str(entry.weights) if entry.weights is not None else None
    return ENGINES[engine](languages=languages, weights=weights)
