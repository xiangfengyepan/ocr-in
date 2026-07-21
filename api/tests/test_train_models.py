from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api import main
from api.registry import ModelRegistry
from api.training_jobs import routes


def _patch(monkeypatch, models_dir: Path) -> None:
    monkeypatch.setattr(routes, "registry", ModelRegistry(models_dir))
    monkeypatch.setattr(routes.settings, "models_dir", models_dir)


def test_train_models_reports_finetuned_and_stock(monkeypatch, tmp_path):
    models_dir = tmp_path / "models"
    trocr_dir = models_dir / "trocr" / "english"
    trocr_dir.mkdir(parents=True)
    (trocr_dir / "w").write_text("x")
    (trocr_dir / "meta.json").write_text(json.dumps({"epoch": 7, "cer": 0.05, "wer": 0.12}))
    (trocr_dir / "history.json").write_text(
        json.dumps([{"epoch": 1, "cer": 0.3, "wer": 0.5}, {"epoch": 7, "cer": 0.05, "wer": 0.12}])
    )
    _patch(monkeypatch, models_dir)

    client = TestClient(main.app)
    resp = client.get("/train/models")
    assert resp.status_code == 200
    entries = {m["id"]: m for m in resp.json()}

    line = entries["trocr-line-personal"]
    assert line["available"] is True
    assert line["engine"] == "trocr"
    assert line["best_for"] == "lines"
    assert line["source"] == "models/trocr/english"
    assert line["meta"] == {"epoch": 7, "cer": 0.05, "wer": 0.12}
    assert line["history"][-1]["epoch"] == 7
    assert line["metrics"]["lines"] == {"cer": 0.05, "wer": 0.12}
    assert line["metrics"]["words"] is None

    word = entries["crnn-word-personal"]
    assert word["available"] is False
    assert word["engine"] == "crnn"
    assert word["best_for"] == "words"
    assert word["meta"] is None
    assert word["history"] is None
    assert word["metrics"] == {"words": None, "lines": None}
