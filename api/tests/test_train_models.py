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


def test_train_models_only_counts_personalized_marker(monkeypatch, tmp_path):
    models_dir = tmp_path / "models"
    # line/trocr: a personalized checkpoint (stamped by our promote flow)
    trocr_dir = models_dir / "trocr" / "english__personal"
    trocr_dir.mkdir(parents=True)
    (trocr_dir / "personalized.json").write_text(
        json.dumps({"epoch": 7, "cer": 0.05, "wer": 0.12, "base_cer": 0.3, "base_wer": 0.5})
    )
    (trocr_dir / "history.json").write_text(
        json.dumps([{"epoch": 0, "cer": 0.3, "wer": 0.5}, {"epoch": 7, "cer": 0.05, "wer": 0.12}])
    )
    # word/crnn: a BASELINE-only checkpoint (baseline dir, NO personal dir) ->
    # must NOT be reported as personalized.
    crnn_dir = models_dir / "crnn" / "english"
    crnn_dir.mkdir(parents=True)
    (crnn_dir / "w").write_text("x")
    (crnn_dir / "meta.json").write_text(json.dumps({"epoch": 9, "cer": 0.077, "wer": 0.2}))
    _patch(monkeypatch, models_dir)

    client = TestClient(main.app)
    resp = client.get("/train/models")
    assert resp.status_code == 200
    entries = {m["id"]: m for m in resp.json()}

    line = entries["trocr-line-personal"]
    assert line["available"] is True
    assert line["meta"]["cer"] == 0.05
    assert line["history"][-1]["epoch"] == 7
    assert line["metrics"]["lines"] == {"cer": 0.05, "wer": 0.12}
    assert line["metrics"]["words"] is None

    # baseline CRNN is NOT reported as personalized (no personalized.json)
    word = entries["crnn-word-personal"]
    assert word["available"] is False
    assert word["meta"] is None
    assert word["history"] is None
    assert word["metrics"] == {"words": None, "lines": None}
