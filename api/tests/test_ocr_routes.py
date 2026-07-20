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


def test_correct_lines_is_separate_step(monkeypatch):
    from api.ocr import routes

    monkeypatch.setattr(routes, "correct_text", lambda text, language, kind: (text.upper(), language))
    client = TestClient(main.app)
    body = client.post(
        "/ocr/correct",
        json={
            "language": "english",
            "lines": [
                {"box": [0, 0, 20, 10], "text": "hi"},
                {"box": [0, 10, 20, 20], "text": "  "},
            ],
        },
    ).json()
    assert body["lines"][0]["text"] == "HI"
    assert body["lines"][1]["text"] == "  "
    assert body["lines"][0]["box"] == [0, 0, 20, 10]


def test_save_crops_lines_into_the_data_store(monkeypatch, tmp_path):
    from api.labeling.store import SampleStore
    from api.ocr import routes

    tmp_store = SampleStore(tmp_path)
    monkeypatch.setattr(routes, "store", tmp_store)
    client = TestClient(main.app)
    resp = client.post(
        "/ocr/save",
        json={
            "image": _png(),
            "language": "english",
            "lines": [
                {"box": [0, 0, 20, 15], "text": "hello", "guess": "helo"},
                {"box": [0, 15, 20, 30], "text": "   "},
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"saved": 1}
    rows = tmp_store.list_samples()
    assert len(rows) == 1
    assert rows[0]["text"] == "hello"
    assert rows[0]["rating"] == "correct"
    assert rows[0]["engine_guess"] == "helo"


def test_pdf_is_searchable():
    import fitz

    client = TestClient(main.app)
    resp = client.post(
        "/ocr/pdf",
        json={
            "image": _png(),
            "width": 40,
            "height": 30,
            "lines": [{"box": [0, 0, 40, 15], "text": "hello world"}],
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    doc = fitz.open(stream=resp.content, filetype="pdf")
    text = doc[0].get_text()
    doc.close()
    assert "hello world" in text
