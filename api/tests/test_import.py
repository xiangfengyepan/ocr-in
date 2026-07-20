from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from api import main
from api.import_jobs import routes


class _FakeRecognizer:
    def recognize(self, crop):
        return {"text": "hi", "confidence": 1.0}


def _png_bytes(w: int = 20, h: int = 20) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _patch_models(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "segment_lines", lambda img: [[0, 0, 10, 10]])
    monkeypatch.setattr(routes, "get_trocr_recognizer", lambda: _FakeRecognizer())
    monkeypatch.setattr(routes, "correct_text", lambda t, lang, k: (t.upper(), lang))
    monkeypatch.setattr(routes, "store", routes.SampleStore(tmp_path))


def test_process_job_saves_pending_sample(monkeypatch, tmp_path):
    _patch_models(monkeypatch, tmp_path)
    job = routes._new_job("scan.png")
    result = routes.process_job(job, _png_bytes())

    assert result["state"] == "done"
    assert result["pages_total"] == 1
    assert result["pages_done"] == result["pages_total"]
    assert result["lines"] == 1
    assert result["error"] is None

    samples = routes.store.list_samples()
    assert len(samples) == 1
    sample = samples[0]
    assert sample["text"] == "HI"
    assert sample["engine_guess"] == "hi"
    assert sample["rating"] == "pending"
    assert sample["language"] == "auto"


def test_process_job_failure_sets_error(monkeypatch, tmp_path):
    _patch_models(monkeypatch, tmp_path)
    monkeypatch.setattr(routes, "get_trocr_recognizer", lambda: None)
    job = routes._new_job("scan.png")
    result = routes.process_job(job, _png_bytes())
    assert result["state"] == "failed"
    assert result["error"]


def test_import_endpoint_and_status(monkeypatch, tmp_path):
    _patch_models(monkeypatch, tmp_path)
    client = TestClient(main.app)

    resp = client.post(
        "/import",
        files={"files": ("scan.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    assert len(jobs) == 1
    job_id = jobs[0]["id"]
    assert jobs[0]["state"] in ("queued", "processing", "done")

    routes._job_queue.join()

    status = client.get("/import/status").json()
    entry = next(j for j in status if j["id"] == job_id)
    assert entry["state"] == "done"
    assert entry["pages_total"] == 1
    assert entry["pages_done"] == 1
    assert entry["lines"] == 1
