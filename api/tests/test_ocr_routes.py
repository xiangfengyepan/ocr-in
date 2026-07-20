from __future__ import annotations

import base64
import io

from fastapi.testclient import TestClient
from PIL import Image

from api import main


def _png() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (255, 255, 255)).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class _Recognizer:
    def recognize(self, image):
        return {"text": "hi", "confidence": 1.0}


def test_recognize_segments_and_reads(monkeypatch):
    from api.ocr import routes

    monkeypatch.setattr(routes, "segment_lines", lambda image: [[0, 0, 20, 10], [0, 10, 20, 20]])
    monkeypatch.setattr(routes, "get_trocr_recognizer", lambda: _Recognizer())
    client = TestClient(main.app)
    resp = client.post("/ocr/recognize", json={"image": _png(), "correct": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["width"] == 40 and body["height"] == 30
    assert len(body["lines"]) == 2
    assert body["text"] == "hi\nhi"


def test_recognize_falls_back_to_whole_image(monkeypatch):
    from api.ocr import routes

    monkeypatch.setattr(routes, "segment_lines", lambda image: [])
    monkeypatch.setattr(routes, "get_trocr_recognizer", lambda: _Recognizer())
    client = TestClient(main.app)
    body = client.post("/ocr/recognize", json={"image": _png()}).json()
    assert body["lines"][0]["box"] == [0, 0, 40, 30]


def test_recognize_applies_correction(monkeypatch):
    from api.ocr import routes

    monkeypatch.setattr(routes, "segment_lines", lambda image: [[0, 0, 20, 10]])
    monkeypatch.setattr(routes, "get_trocr_recognizer", lambda: _Recognizer())
    monkeypatch.setattr(routes, "correct_text", lambda text, language, kind: (text.upper(), language))
    client = TestClient(main.app)
    body = client.post("/ocr/recognize", json={"image": _png(), "correct": True}).json()
    assert body["lines"][0]["text"] == "HI"
