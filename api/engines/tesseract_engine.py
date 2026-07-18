from __future__ import annotations

from collections.abc import Sequence

from PIL import Image

from .base import BBox, OcrEngine, OcrResult


class TesseractEngine(OcrEngine):
    engine = "tesseract"

    def recognize(
        self, page: Image.Image, boxes: Sequence[BBox] | None = None
    ) -> list[OcrResult]:
        raise NotImplementedError
