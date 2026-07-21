from __future__ import annotations

import pytesseract
from PIL import Image


class TesseractRecognizer:
    def recognize(self, image: Image.Image) -> dict:
        data = pytesseract.image_to_data(
            image, config="--psm 7", output_type=pytesseract.Output.DICT
        )
        words = [w for w in data["text"] if w.strip()]
        confs = [
            int(c)
            for c, w in zip(data["conf"], data["text"])
            if w.strip() and str(c) != "-1"
        ]
        text = " ".join(words)
        conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        return {"text": text, "confidence": conf}


_rec: TesseractRecognizer | None = None


def get_tesseract_recognizer() -> TesseractRecognizer:
    global _rec
    if _rec is None:
        _rec = TesseractRecognizer()
    return _rec
