from __future__ import annotations

import base64
import io
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel

from api.inference.crnn_recognizer import crop_to_ink, get_recognizer
from api.labeling.store import SampleStore
from api.util import settings

router = APIRouter(prefix="/label", tags=["labeling"])
store = SampleStore(settings.collected_dir)

Rating = Literal["correct", "incorrect"]


def _decode_png(image: str) -> bytes:
    if "," in image and image.strip().startswith("data:"):
        image = image.split(",", 1)[1]
    return base64.b64decode(image)


class GuessRequest(BaseModel):
    image: str


class GuessResponse(BaseModel):
    guess: str
    confidence: float


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
