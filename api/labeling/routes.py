from __future__ import annotations

import base64
import io
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel

from api.inference.crnn_recognizer import crop_to_ink, get_recognizer
from api.inference.kind_detector import detect_kind
from api.inference.trocr_recognizer import get_trocr_recognizer
from api.labeling.store import SampleStore
from api.util import settings

router = APIRouter(prefix="/label", tags=["labeling"])
store = SampleStore(settings.collected_dir)

Rating = Literal["correct", "incorrect"]
Kind = Literal["word", "line"]
Mode = Literal["auto", "word", "line"]


def _decode_png(image: str) -> bytes:
    if "," in image and image.strip().startswith("data:"):
        image = image.split(",", 1)[1]
    return base64.b64decode(image)


class DetectRequest(BaseModel):
    image: str


class DetectResponse(BaseModel):
    kind: Kind


class GuessRequest(BaseModel):
    image: str
    mode: Mode = "auto"


class GuessResponse(BaseModel):
    guess: str
    confidence: float
    kind: Kind
    engine: str


class SampleRequest(BaseModel):
    image: str
    rating: Rating
    text: str
    engine_guess: str | None = None


class SampleResponse(BaseModel):
    id: int
    image_path: str


class UpdateRequest(BaseModel):
    text: str | None = None
    rating: Rating | None = None


@router.post("/detect", response_model=DetectResponse)
def detect(req: DetectRequest) -> DetectResponse:
    image = Image.open(io.BytesIO(_decode_png(req.image)))
    return DetectResponse(kind=detect_kind(image))


@router.post("/guess", response_model=GuessResponse)
def guess(req: GuessRequest) -> GuessResponse:
    image = Image.open(io.BytesIO(_decode_png(req.image)))
    kind: Kind = detect_kind(image) if req.mode == "auto" else req.mode
    if kind == "line":
        recognizer = get_trocr_recognizer()
        engine = "trocr"
    else:
        recognizer = get_recognizer()
        engine = "crnn"
    if recognizer is None:
        raise HTTPException(status_code=503, detail=f"{engine} model not available")
    result = recognizer.recognize(image)
    return GuessResponse(
        guess=result["text"], confidence=result["confidence"], kind=kind, engine=engine
    )


@router.post("/sample", response_model=SampleResponse)
def sample(req: SampleRequest) -> SampleResponse:
    image = Image.open(io.BytesIO(_decode_png(req.image)))
    cropped = crop_to_ink(image)
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    result = store.add_sample(buf.getvalue(), req.text, "english", req.rating, req.engine_guess)
    return SampleResponse(**result)


@router.get("/samples")
def samples(limit: int = 100, offset: int = 0) -> list[dict]:
    return store.list_samples(limit, offset)


@router.get("/image/{sample_id}")
def image(sample_id: int) -> FileResponse:
    record = store.get_sample(sample_id)
    if record is None:
        raise HTTPException(status_code=404, detail="sample not found")
    path = store.root / record["image_path"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="image file missing")
    return FileResponse(path, media_type="image/png")


@router.patch("/sample/{sample_id}")
def update(sample_id: int, req: UpdateRequest) -> dict:
    try:
        updated = store.update_sample(sample_id, text=req.text, rating=req.rating)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="sample not found")
    return updated


@router.delete("/sample/{sample_id}")
def delete(sample_id: int) -> dict:
    if not store.delete_sample(sample_id):
        raise HTTPException(status_code=404, detail="sample not found")
    return {"deleted": sample_id}


@router.get("/stats")
def stats() -> dict:
    return store.stats()
