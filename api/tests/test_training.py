from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from api import main
from api.labeling.store import SampleStore
from api.registry import ModelRegistry
from api.training_jobs import routes


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("L", (30, 20), color=255).save(buf, format="PNG")
    return buf.getvalue()


def _base_job(job_id: int = 1, kind: str = "line") -> dict:
    return {
        "id": job_id,
        "kind": kind,
        "state": "queued",
        "epoch": 0,
        "epochs_total": 0,
        "base_cer": None,
        "base_wer": None,
        "new_cer": None,
        "new_wer": None,
        "candidate_path": None,
        "promoted": False,
        "error": None,
    }


def _seed_store(tmp_path: Path, n: int, kind: str = "line") -> SampleStore:
    store = SampleStore(tmp_path / "collected")
    for i in range(n):
        store.add_sample(_png_bytes(), f"t{i}", "english", "correct", None, kind=kind)
    return store


def _train_stub(kind, rows, out, epochs):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "w").write_text("x")


def _eval_stub(kind, weights, rows):
    return {"cer": 0.1 if weights else 0.5, "wer": 0.2}


def _patch(monkeypatch, tmp_path, store):
    monkeypatch.setattr(routes, "store", store)
    monkeypatch.setattr(routes, "train_from_rows", _train_stub)
    monkeypatch.setattr(routes, "eval_rows", _eval_stub)
    monkeypatch.setattr(routes, "registry", ModelRegistry(tmp_path / "models"))
    monkeypatch.setattr(routes.settings, "models_dir", tmp_path / "models")


def test_run_training_job_done_and_metrics(monkeypatch, tmp_path):
    store = _seed_store(tmp_path, 60)
    _patch(monkeypatch, tmp_path, store)
    job = routes.run_training_job(_base_job())
    assert job["state"] == "done"
    assert job["base_cer"] == 0.5
    assert job["new_cer"] == 0.1
    assert job["candidate_path"] is not None
    assert Path(job["candidate_path"]).exists()


def test_run_training_job_too_few_rows_fails(monkeypatch, tmp_path):
    store = _seed_store(tmp_path, 10)
    _patch(monkeypatch, tmp_path, store)
    job = routes.run_training_job(_base_job())
    assert job["state"] == "failed"
    assert job["error"] == "need >= 50 labeled samples"


def test_post_train_enqueues(monkeypatch, tmp_path):
    store = _seed_store(tmp_path, 60)
    _patch(monkeypatch, tmp_path, store)
    monkeypatch.setattr(routes, "_ensure_worker", lambda: None)
    routes._jobs.clear()
    client = TestClient(main.app)

    resp = client.post("/train", json={"kind": "line"})
    assert resp.status_code == 200
    job = resp.json()["job"]
    assert job["kind"] == "line"
    assert job["state"] == "queued"

    queued = routes._job_queue.get_nowait()
    routes.run_training_job(queued)
    assert queued["state"] == "done"

    status = client.get("/train/status").json()
    assert status[0]["state"] == "done"


def test_promote_on_done_job(monkeypatch, tmp_path):
    store = _seed_store(tmp_path, 60)
    _patch(monkeypatch, tmp_path, store)
    monkeypatch.setattr(routes, "_ensure_worker", lambda: None)
    routes._jobs.clear()

    promoted_calls: list[tuple] = []
    monkeypatch.setattr(
        routes.registry,
        "promote",
        lambda engine, language, cand: promoted_calls.append((engine, language, cand)),
    )

    client = TestClient(main.app)
    job = client.post("/train", json={"kind": "line"}).json()["job"]
    queued = routes._job_queue.get_nowait()
    routes.run_training_job(queued)

    resp = client.post("/train/promote", json={"job_id": job["id"]})
    assert resp.status_code == 200
    assert resp.json() == {"promoted": True, "engine": "trocr", "kind": "line"}
    assert len(promoted_calls) == 1
    assert promoted_calls[0][0] == "trocr" and promoted_calls[0][1] == "english"


def test_promote_rejects_unfinished_job(monkeypatch, tmp_path):
    store = _seed_store(tmp_path, 60)
    _patch(monkeypatch, tmp_path, store)
    monkeypatch.setattr(routes, "_ensure_worker", lambda: None)
    routes._jobs.clear()

    client = TestClient(main.app)
    job = client.post("/train", json={"kind": "line"}).json()["job"]
    resp = client.post("/train/promote", json={"job_id": job["id"]})
    assert resp.status_code == 400


def test_train_job_evaluates_and_awaits_promote(monkeypatch, tmp_path):
    from api.labeling.store import SampleStore
    from api.training_jobs import routes

    store = SampleStore(tmp_path)
    for i in range(60):
        store.add_sample(_png_bytes(), f"t{i}", "english", "correct", None, kind="line")
    monkeypatch.setattr(routes, "store", store)
    monkeypatch.setattr(routes, "registry", ModelRegistry(tmp_path / "models"))
    monkeypatch.setattr(routes.settings, "models_dir", tmp_path / "models")
    monkeypatch.setattr(
        routes,
        "train_from_rows",
        lambda kind, rows, out, epochs: out.mkdir(parents=True, exist_ok=True)
        or (out / "w").write_text("x"),
    )
    monkeypatch.setattr(
        routes,
        "eval_rows",
        lambda kind, weights, rows: {"cer": 0.1 if weights else 0.5, "wer": 0.2},
    )
    job = routes.run_training_job(
        {
            "id": 1,
            "kind": "line",
            "state": "queued",
            "epoch": 0,
            "epochs_total": 0,
            "base_cer": None,
            "base_wer": None,
            "new_cer": None,
            "new_wer": None,
            "candidate_path": None,
            "promoted": False,
            "error": None,
        }
    )
    assert job["state"] == "done" and job["new_cer"] == 0.1 and job["base_cer"] == 0.5
