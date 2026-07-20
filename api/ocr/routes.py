from __future__ import annotations

import base64
import io
from typing import Literal

from fastapi import APIRouter
from PIL import Image
from pydantic import BaseModel

from api.inference.corrector import correct as correct_text
from api.inference.segmenter import segment_lines
from api.inference.trocr_recognizer import get_trocr_recognizer

router = APIRouter(prefix="/ocr", tags=["ocr"])

Language = Literal["auto", "english", "spanish", "catalan", "chinese", "japanese"]


def _decode_png(image: str) -> bytes:
    if "," in image and image.strip().startswith("data:"):
        image = image.split(",", 1)[1]
    return base64.b64decode(image)


class RecognizeRequest(BaseModel):
    image: str
    correct: bool = False
    language: Language = "auto"


class RecognizedLine(BaseModel):
    box: list[float]
    text: str


class RecognizeResponse(BaseModel):
    width: int
    height: int
    lines: list[RecognizedLine]
    text: str


@router.post("/recognize", response_model=RecognizeResponse)
def recognize(req: RecognizeRequest) -> RecognizeResponse:
    image = Image.open(io.BytesIO(_decode_png(req.image))).convert("RGB")
    width, height = image.size
    boxes = segment_lines(image)
    if not boxes:  # detector unavailable/failed -> treat whole image as one line
        boxes = [[0.0, 0.0, float(width), float(height)]]

    recognizer = get_trocr_recognizer()
    lines: list[RecognizedLine] = []
    for box in boxes:
        x0, y0, x1, y1 = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
        crop = image.crop((x0, y0, x1, y1))
        text = recognizer.recognize(crop)["text"] if recognizer else ""
        if req.correct and text.strip():
            text, _ = correct_text(text, req.language, "line")
        lines.append(RecognizedLine(box=[x0, y0, x1, y1], text=text))

    return RecognizeResponse(
        width=width, height=height, lines=lines, text="\n".join(ln.text for ln in lines)
    )
