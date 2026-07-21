from __future__ import annotations

import base64
import io

from fastapi.testclient import TestClient
from PIL import Image

from api import main


def _png_data_url() -> str:
    buf = io.BytesIO()
    Image.new("L", (40, 30), color=255).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_engines_availability_idle():
    resp = TestClient(main.app).get("/engines/availability")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"trocr": True, "crnn": True, "tesseract": True, "training": False}


def test_engines_availability_during_training(monkeypatch):
    monkeypatch.setattr(main, "training_active", lambda: True)
    body = TestClient(main.app).get("/engines/availability").json()
    assert body == {"trocr": False, "crnn": False, "tesseract": True, "training": True}


def test_guess_routes_to_tesseract(monkeypatch):
    from api.labeling import routes

    class FakeRecognizer:
        def recognize(self, image):
            return {"text": "t", "confidence": 0.5}

    monkeypatch.setattr(routes, "get_tesseract_recognizer", lambda: FakeRecognizer())
    client = TestClient(main.app)
    resp = client.post(
        "/label/guess",
        json={"image": _png_data_url(), "mode": "word", "engine": "tesseract"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["engine"] == "tesseract"
    assert body["guess"] == "t"
    assert body["confidence"] == 0.5
