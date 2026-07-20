from __future__ import annotations

import io
import itertools
import queue
import threading

import fitz
from fastapi import APIRouter, File, UploadFile
from PIL import Image

from api.inference.corrector import correct as correct_text
from api.inference.segmenter import segment_lines
from api.inference.trocr_recognizer import get_trocr_recognizer
from api.labeling.store import SampleStore
from api.util import settings

router = APIRouter(prefix="/import", tags=["import"])
store = SampleStore(settings.collected_dir)

_PDF_MAGIC = b"%PDF"

_jobs: list[dict] = []
_jobs_lock = threading.Lock()
_ids = itertools.count(1)

_job_queue: "queue.Queue[tuple[dict, bytes]]" = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _is_pdf(filename: str, data: bytes) -> bool:
    return filename.lower().endswith(".pdf") or data[:4] == _PDF_MAGIC


def _page_images(data: bytes, is_pdf: bool, job: dict) -> list[Image.Image]:
    if is_pdf:
        doc = fitz.open(stream=data, filetype="pdf")
        job["pages_total"] = doc.page_count
        images: list[Image.Image] = []
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72))
            images.append(Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB"))
        return images
    job["pages_total"] = 1
    return [Image.open(io.BytesIO(data)).convert("RGB")]


def _process_page(img: Image.Image, recognizer, job: dict) -> None:
    width, height = img.size
    boxes = segment_lines(img) or [[0, 0, width, height]]
    for box in boxes:
        x0, y0, x1, y1 = (int(round(v)) for v in box)
        crop = img.crop((x0, y0, x1, y1))
        text = recognizer.recognize(crop)["text"]
        corrected, _ = correct_text(text, "auto", "line")
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        store.add_sample(buf.getvalue(), corrected, "auto", "pending", text)
        job["lines"] += 1


def process_job(job: dict, data: bytes) -> dict:
    try:
        job["state"] = "processing"
        recognizer = get_trocr_recognizer()
        if recognizer is None:
            raise RuntimeError("trocr recognizer not available")
        is_pdf = _is_pdf(job["filename"], data)
        for img in _page_images(data, is_pdf, job):
            _process_page(img, recognizer, job)
            job["pages_done"] += 1
        job["state"] = "done"
    except Exception as exc:  # noqa: BLE001 - worker must never crash on a job
        job["state"] = "failed"
        job["error"] = str(exc)
    return job


def _worker_loop() -> None:
    while True:
        job, data = _job_queue.get()
        try:
            process_job(job, data)
        finally:
            _job_queue.task_done()


def _ensure_worker() -> None:
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            threading.Thread(target=_worker_loop, daemon=True).start()
            _worker_started = True


def _new_job(filename: str) -> dict:
    return {
        "id": next(_ids),
        "filename": filename,
        "state": "queued",
        "pages_total": 0,
        "pages_done": 0,
        "lines": 0,
        "error": None,
    }


@router.post("")
async def import_files(files: list[UploadFile] = File(...)) -> dict:
    _ensure_worker()
    created: list[dict] = []
    for upload in files:
        data = await upload.read()
        job = _new_job(upload.filename or "upload")
        with _jobs_lock:
            _jobs.append(job)
        _job_queue.put((job, data))
        created.append(dict(job))
    return {"jobs": created}


@router.get("/status")
def import_status() -> list[dict]:
    with _jobs_lock:
        return [dict(job) for job in reversed(_jobs)]
