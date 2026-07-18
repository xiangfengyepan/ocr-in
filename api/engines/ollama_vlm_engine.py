from __future__ import annotations

from collections.abc import Sequence

from PIL import Image

from .base import BBox, OcrEngine, OcrResult


class OllamaVlmEngine(OcrEngine):
    engine = "ollama_vlm"

    def recognize(
        self, page: Image.Image, boxes: Sequence[BBox] | None = None
    ) -> list[OcrResult]:
        raise NotImplementedError
