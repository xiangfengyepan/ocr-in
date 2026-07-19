from __future__ import annotations

import base64
import io
from typing import Literal

from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel

from api.inference.crnn_recognizer import get_recognizer
from api.labeling.store import SampleStore
from api.util import settings

router = APIRouter(prefix="/label", tags=["labeling"])
store = SampleStore(settings.collected_dir)


def _decode_png(image: str) -> bytes:
    if "," in image and image.strip().startswith("data:"):
        image = image.split(",", 1)[1]
    return base64.b64decode(image)


class GuessRequest(BaseModel):
    image: str
    language: str


class GuessResponse(BaseModel):
    guess: str
    confidence: float


class SampleRequest(BaseModel):
    image: str
    language: str
    rating: Literal["correct", "partial", "wrong"]
    text: str
    engine_guess: str | None = None


class SampleResponse(BaseModel):
    id: int
    image_path: str


@router.post("/guess", response_model=GuessResponse)
def guess(req: GuessRequest) -> GuessResponse:
    recognizer = get_recognizer()
    if recognizer is None:
        raise HTTPException(status_code=503, detail="crnn/english checkpoint not available")
    image = Image.open(io.BytesIO(_decode_png(req.image)))
    result = recognizer.recognize(image)
    return GuessResponse(guess=result["text"], confidence=result["confidence"])


@router.post("/sample", response_model=SampleResponse)
def sample(req: SampleRequest) -> SampleResponse:
    result = store.add_sample(
        _decode_png(req.image), req.text, req.language, req.rating, req.engine_guess
    )
    return SampleResponse(**result)


@router.get("/stats")
def stats() -> dict:
    return store.stats()
