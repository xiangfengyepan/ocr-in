from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from PIL import Image

BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class OcrResult:
    text: str
    bbox: BBox
    confidence: float


class OcrEngine(ABC):
    engine: str

    def __init__(self, languages: Sequence[str], weights: str | None = None) -> None:
        self.languages = list(languages)
        self.weights = weights

    @abstractmethod
    def recognize(
        self, page: Image.Image, boxes: Sequence[BBox] | None = None
    ) -> list[OcrResult]:
        """Return one OcrResult per detected region.

        When ``boxes`` is provided (from the shared detector), the engine
        recognizes each crop. When it is ``None``, the engine may detect
        regions itself or transcribe the whole page.
        """
