from __future__ import annotations

import base64
import io
import json
import zipfile
from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image
from pydantic import BaseModel

from api.inference.corrector import correct as correct_text
from api.inference.crnn_recognizer import crop_to_ink, get_recognizer
from api.inference.kind_detector import detect_kind
from api.inference.tesseract_recognizer import get_tesseract_recognizer
from api.inference.trocr_recognizer import get_trocr_recognizer
from api.labeling.store import SampleStore
from api.util import settings

router = APIRouter(prefix="/label", tags=["labeling"])
store = SampleStore(settings.collected_dir)

Rating = Literal["correct", "incorrect"]
Kind = Literal["word", "line"]
Mode = Literal["auto", "word", "line"]
Language = Literal["auto", "english", "spanish", "catalan", "chinese", "japanese"]


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
    engine: Literal["crnn", "trocr", "tesseract"] | None = None


class GuessResponse(BaseModel):
    guess: str
    confidence: float
    kind: Kind
    engine: str


class CorrectRequest(BaseModel):
    text: str
    language: Language = "auto"
    kind: Kind = "word"


class CorrectResponse(BaseModel):
    corrected: str
    language: str


class SampleRequest(BaseModel):
    image: str
    rating: Rating
    text: str
    engine_guess: str | None = None
    confidence: float | None = None


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


@router.post("/correct", response_model=CorrectResponse)
def correct(req: CorrectRequest) -> CorrectResponse:
    corrected, language = correct_text(req.text, req.language, req.kind)
    return CorrectResponse(corrected=corrected, language=language)


@router.post("/guess", response_model=GuessResponse)
def guess(req: GuessRequest) -> GuessResponse:
    image = Image.open(io.BytesIO(_decode_png(req.image)))
    kind: Kind = detect_kind(image) if req.mode == "auto" else req.mode
    if req.engine == "tesseract":
        recognizer = get_tesseract_recognizer()
        engine = "tesseract"
    elif req.engine == "trocr" or (req.engine is None and kind == "line"):
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
    result = store.add_sample(
        buf.getvalue(), req.text, "english", req.rating, req.engine_guess, confidence=req.confidence
    )
    return SampleResponse(**result)


def _check_rating(rating: str | None) -> None:
    if rating is not None and rating not in ("pending", "correct", "incorrect"):
        raise HTTPException(status_code=400, detail=f"invalid rating: {rating!r}")


@router.get("/samples")
def samples(
    limit: int = 100,
    offset: int = 0,
    rating: str | None = None,
    q: str | None = None,
    order: str = "id",
) -> list[dict]:
    _check_rating(rating)
    return store.list_samples(limit, offset, rating=rating, q=q, order=order)


@router.get("/samples/count")
def samples_count(rating: str | None = None, q: str | None = None) -> dict:
    _check_rating(rating)
    return {"count": store.count(rating=rating, q=q)}


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


@router.get("/export")
def export() -> StreamingResponse:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest: list[str] = []
        for s in store.list_samples(limit=10**9):
            image = store.root / s["image_path"]
            if not image.is_file():
                continue
            arc = f"images/{s['image_path']}"
            zf.write(image, arc)
            manifest.append(
                json.dumps(
                    {
                        "text": s["text"],
                        "language": s["language"],
                        "rating": s["rating"],
                        "engine_guess": s["engine_guess"],
                        "image": arc,
                    }
                )
            )
        zf.writestr("manifest.jsonl", "\n".join(manifest))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=labels_export.zip"},
    )


@router.post("/import")
def import_labels(file: UploadFile = File(...)) -> dict:
    try:
        archive = zipfile.ZipFile(io.BytesIO(file.file.read()))
        manifest = archive.read("manifest.jsonl").decode("utf-8").splitlines()
    except (zipfile.BadZipFile, KeyError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid export archive: {exc}") from exc
    imported = 0
    for line in manifest:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            png = archive.read(record["image"])
        except (KeyError, ValueError):
            continue
        rating = record.get("rating") if record.get("rating") in ("correct", "incorrect") else "incorrect"
        language = record.get("language", "english")
        if not language.isalpha():
            language = "english"
        store.add_sample(png, record.get("text", ""), language, rating, record.get("engine_guess"))
        imported += 1
    return {"imported": imported}
