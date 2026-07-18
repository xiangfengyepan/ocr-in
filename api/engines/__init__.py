from __future__ import annotations

from .base import BBox, OcrEngine, OcrResult
from .crnn_engine import CrnnEngine
from .ollama_vlm_engine import OllamaVlmEngine
from .tesseract_engine import TesseractEngine
from .trocr_engine import TrocrEngine

ENGINES: dict[str, type[OcrEngine]] = {
    TesseractEngine.engine: TesseractEngine,
    CrnnEngine.engine: CrnnEngine,
    TrocrEngine.engine: TrocrEngine,
    OllamaVlmEngine.engine: OllamaVlmEngine,
}

__all__ = [
    "BBox",
    "OcrEngine",
    "OcrResult",
    "TesseractEngine",
    "CrnnEngine",
    "TrocrEngine",
    "OllamaVlmEngine",
    "ENGINES",
]
