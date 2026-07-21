from __future__ import annotations

import itertools
import json
import queue
import shutil
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
ACTIVE_STATES = ("queued", "training", "evaluating")
TRAINING_STATES = ("training", "evaluating")

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
            epochs = job["epochs_total"] or DEFAULT_EPOCHS
            job["epochs_total"] = epochs
            cand = settings.models_dir / "_candidates" / f"{engine}-{job['id']}"
            train_from_rows(
                kind, train, cand, epochs, on_epoch=lambda e: job.__setitem__("epoch", e)
            )
            job["state"] = "evaluating"
            new = eval_rows(kind, cand, val)
        job["base_cer"] = base["cer"]
        job["base_wer"] = base["wer"]
        job["new_cer"] = new["cer"]
        job["new_wer"] = new["wer"]
        # Stamp the candidate as trained-on-user-labels so the Models tab can tell
        # a personalized checkpoint apart from a baseline (IAM-trained) one.
        _write_personalized_marker(cand, kind, base, new, epochs)
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


def training_active() -> bool:
    with _jobs_lock:
        return any(j["state"] in TRAINING_STATES for j in _jobs)


@router.post("")
def start_train(body: TrainRequest) -> dict:
    _ensure_worker()
    with _jobs_lock:
        if any(j["kind"] == body.kind and j["state"] in ACTIVE_STATES for j in _jobs):
            raise HTTPException(status_code=409, detail=f"a {body.kind} job is already running")
        job = _new_job(body.kind)
        _jobs.append(job)
    _job_queue.put(job)
    return {"job": dict(job)}


def _read_json(path: Path) -> dict | list | None:
    return json.loads(path.read_text()) if path.is_file() else None


def _write_personalized_marker(cand: Path, kind: str, base: dict, new: dict, epochs: int) -> None:
    cand.mkdir(parents=True, exist_ok=True)
    (cand / "personalized.json").write_text(
        json.dumps(
            {
                "kind": kind,
                "epoch": epochs,
                "cer": new["cer"],
                "wer": new["wer"],
                "base_cer": base["cer"],
                "base_wer": base["wer"],
            }
        )
    )
    (cand / "history.json").write_text(
        json.dumps(
            [
                {"epoch": 0, "cer": base["cer"], "wer": base["wer"]},
                {"epoch": epochs, "cer": new["cer"], "wer": new["wer"]},
            ]
        )
    )


@router.get("/models")
def trainable_models() -> list[dict]:
    kinds = [
        ("line", "trocr", "trocr-line-personal", "TrOCR (line) — personalized", "lines"),
        ("word", "crnn", "crnn-word-personal", "CRNN (word) — personalized", "words"),
    ]
    out: list[dict] = []
    for _kind, engine, model_id, name, best_for in kinds:
        path = settings.models_dir / engine / LANGUAGE
        # "Personalized" = trained on the user's labels via our promote flow,
        # marked by personalized.json. A bare baseline checkpoint does NOT count.
        available = (path / "personalized.json").is_file()
        meta = _read_json(path / "personalized.json") if available else None
        history = _read_json(path / "history.json") if available else None
        metric = (
            {"cer": meta.get("cer"), "wer": meta.get("wer")}
            if isinstance(meta, dict)
            else None
        )
        out.append(
            {
                "id": model_id,
                "name": name,
                "detail": (
                    "Fine-tuned on your labeled data"
                    if available
                    else "Not yet trained — using stock/default"
                ),
                "engine": engine,
                "available": available,
                "source": f"models/{engine}/{LANGUAGE}",
                "best_for": best_for,
                "metrics": {
                    "words": metric if best_for == "words" else None,
                    "lines": metric if best_for == "lines" else None,
                },
                "meta": meta if isinstance(meta, dict) else None,
                "history": history if isinstance(history, list) else None,
            }
        )
    return out


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
    engine = KIND_ENGINE[job["kind"]]
    if job["promoted"]:
        return {"promoted": True, "engine": engine, "kind": job["kind"]}
    if job["state"] != "done":
        raise HTTPException(status_code=400, detail="job is not done")
    candidate_path = Path(job["candidate_path"])
    registry.promote(engine, LANGUAGE, candidate_path)
    job["promoted"] = True
    shutil.rmtree(candidate_path, ignore_errors=True)
    _reset_recognizer(engine)
    return {"promoted": True, "engine": engine, "kind": job["kind"]}


def _reset_recognizer(engine: str) -> None:
    if engine == "trocr":
        from api.inference.trocr_recognizer import reset_trocr_recognizer

        reset_trocr_recognizer()
    elif engine == "crnn":
        from api.inference.crnn_recognizer import reset_recognizer

        reset_recognizer()
