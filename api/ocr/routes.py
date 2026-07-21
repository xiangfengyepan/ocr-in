from __future__ import annotations

import base64
import io
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from PIL import Image
from pydantic import BaseModel

from api.inference.corrector import correct as correct_text
from api.inference.searchable_pdf import build_searchable_pdf
from api.inference.segmenter import segment_lines
from api.inference.trocr_recognizer import get_trocr_recognizer
from api.labeling.store import SampleStore
from api.util import settings

router = APIRouter(prefix="/ocr", tags=["ocr"])
store = SampleStore(settings.collected_dir)

Language = Literal["auto", "english", "spanish", "catalan", "chinese", "japanese"]


def _decode_png(image: str) -> bytes:
    if "," in image and image.strip().startswith("data:"):
        image = image.split(",", 1)[1]
    return base64.b64decode(image)


class RecognizeRequest(BaseModel):
    image: str


class RecognizedLine(BaseModel):
    box: list[float]
    text: str


class RecognizeResponse(BaseModel):
    width: int
    height: int
    lines: list[RecognizedLine]
    text: str


class PdfRequest(BaseModel):
    image: str
    width: int
    height: int
    lines: list[RecognizedLine]


class CorrectLinesRequest(BaseModel):
    lines: list[RecognizedLine]
    language: Language = "auto"


class CorrectLinesResponse(BaseModel):
    lines: list[RecognizedLine]


class SaveLine(BaseModel):
    box: list[float]
    text: str
    guess: str | None = None
    confidence: float | None = None


class SaveRequest(BaseModel):
    image: str
    language: Language = "auto"
    lines: list[SaveLine]


class SaveResponse(BaseModel):
    saved: int


@router.post("/recognize", response_model=RecognizeResponse)
def recognize(req: RecognizeRequest) -> RecognizeResponse:
    raw = _decode_png(req.image)
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    width, height = image.size
    lines: list[RecognizedLine] = []

    boxes = segment_lines(image) or [[0.0, 0.0, float(width), float(height)]]
    recognizer = get_trocr_recognizer()
    for box in boxes:
        x0, y0, x1, y1 = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
        crop = image.crop((x0, y0, x1, y1))
        text = recognizer.recognize(crop)["text"] if recognizer else ""
        lines.append(RecognizedLine(box=[x0, y0, x1, y1], text=text))

    return RecognizeResponse(
        width=width, height=height, lines=lines, text="\n".join(ln.text for ln in lines)
    )


@router.post("/correct", response_model=CorrectLinesResponse)
def correct_lines(req: CorrectLinesRequest) -> CorrectLinesResponse:
    out: list[RecognizedLine] = []
    for ln in req.lines:
        text = ln.text
        if text.strip():
            text, _ = correct_text(text, req.language, "line")
        out.append(RecognizedLine(box=ln.box, text=text))
    return CorrectLinesResponse(lines=out)


@router.post("/save", response_model=SaveResponse)
def save(req: SaveRequest) -> SaveResponse:
    image = Image.open(io.BytesIO(_decode_png(req.image))).convert("RGB")
    w, h = image.size
    saved = 0
    for ln in req.lines:
        text = ln.text.strip()
        if not text:
            continue
        x0, y0, x1, y1 = (int(ln.box[0]), int(ln.box[1]), int(ln.box[2]), int(ln.box[3]))
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        buf = io.BytesIO()
        image.crop((x0, y0, x1, y1)).save(buf, format="PNG")
        store.add_sample(
            buf.getvalue(),
            text,
            req.language,
            "correct",
            ln.guess,
            confidence=ln.confidence,
            kind="line",
        )
        saved += 1
    return SaveResponse(saved=saved)


@router.post("/pdf")
def pdf(req: PdfRequest) -> StreamingResponse:
    data = build_searchable_pdf(
        _decode_png(req.image),
        req.width,
        req.height,
        [{"box": ln.box, "text": ln.text} for ln in req.lines],
    )
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=ocr.pdf"},
    )
