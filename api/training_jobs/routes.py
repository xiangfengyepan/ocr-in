from __future__ import annotations

import itertools
import queue
import threading
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.labeling.store import SampleStore
from api.registry import ModelRegistry
from api.training_jobs.dataset import build_split
from api.util import settings
from api.util.gpu_lock import GPU_LOCK
from training.personalize import eval_rows, train_from_rows

KIND_ENGINE = {"line": "trocr", "word": "crnn"}
MIN_TRAIN_ROWS = 50
LANGUAGE = "english"
DEFAULT_EPOCHS = 8

router = APIRouter(prefix="/train", tags=["train"])
store = SampleStore(settings.collected_dir)
registry = ModelRegistry(settings.models_dir)

_jobs: list[dict] = []
_jobs_lock = threading.Lock()
_ids = itertools.count(1)

_job_queue: "queue.Queue[dict]" = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


class TrainRequest(BaseModel):
    kind: Literal["line", "word"]


class PromoteRequest(BaseModel):
    job_id: int


def _new_job(kind: str) -> dict:
    return {
        "id": next(_ids),
        "kind": kind,
        "state": "queued",
        "epoch": 0,
        "epochs_total": DEFAULT_EPOCHS,
        "base_cer": None,
        "base_wer": None,
        "new_cer": None,
        "new_wer": None,
        "candidate_path": None,
        "promoted": False,
        "error": None,
    }


def run_training_job(job: dict) -> dict:
    try:
        kind = job["kind"]
        engine = KIND_ENGINE[kind]
        train, val = build_split(store, kind)
        if len(train) + len(val) < MIN_TRAIN_ROWS:
            job["state"] = "failed"
            job["error"] = "need >= 50 labeled samples"
            return job
        with GPU_LOCK:
            base = eval_rows(kind, registry.resolve(engine, LANGUAGE).weights, val)
            job["state"] = "training"
            cand = settings.models_dir / "_candidates" / f"{engine}-{job['id']}"
            train_from_rows(kind, train, cand, job["epochs_total"] or DEFAULT_EPOCHS)
            job["state"] = "evaluating"
            new = eval_rows(kind, cand, val)
        job["base_cer"] = base["cer"]
        job["base_wer"] = base["wer"]
        job["new_cer"] = new["cer"]
        job["new_wer"] = new["wer"]
        job["candidate_path"] = str(cand)
        job["state"] = "done"
    except Exception as exc:  # noqa: BLE001 - worker must never crash on a job
        job["state"] = "failed"
        job["error"] = str(exc)
    return job


def _worker_loop() -> None:
    while True:
        job = _job_queue.get()
        try:
            run_training_job(job)
        finally:
            _job_queue.task_done()


def _ensure_worker() -> None:
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            threading.Thread(target=_worker_loop, daemon=True).start()
            _worker_started = True


@router.post("")
def start_train(body: TrainRequest) -> dict:
    _ensure_worker()
    job = _new_job(body.kind)
    with _jobs_lock:
        _jobs.append(job)
    _job_queue.put(job)
    return {"job": dict(job)}


@router.get("/status")
def train_status() -> list[dict]:
    with _jobs_lock:
        return [dict(job) for job in reversed(_jobs)]


@router.post("/promote")
def promote(body: PromoteRequest) -> dict:
    with _jobs_lock:
        job = next((j for j in _jobs if j["id"] == body.job_id), None)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job["state"] != "done":
        raise HTTPException(status_code=400, detail="job is not done")
    engine = KIND_ENGINE[job["kind"]]
    registry.promote(engine, LANGUAGE, Path(job["candidate_path"]))
    job["promoted"] = True
    return {"promoted": True, "engine": engine, "kind": job["kind"]}
