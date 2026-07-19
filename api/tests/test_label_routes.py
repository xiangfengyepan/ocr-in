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


def _client(tmp_path):
    from api.labeling import routes

    routes.store = routes.SampleStore(tmp_path)  # isolate storage
    return TestClient(main.app)


def test_sample_and_stats_roundtrip(tmp_path):
    client = _client(tmp_path)
    resp = client.post(
        "/label/sample",
        json={
            "image": _png_data_url(),
            "language": "english",
            "rating": "correct",
            "text": "hi",
            "engine_guess": "hi",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert body["image_path"] == "english/1.png"
    assert (tmp_path / "english" / "1.png").exists()

    stats = client.get("/label/stats").json()
    assert stats["total"] == 1
    assert stats["by_rating"]["correct"] == 1


def test_sample_rejects_bad_rating(tmp_path):
    client = _client(tmp_path)
    resp = client.post(
        "/label/sample",
        json={"image": _png_data_url(), "language": "english", "rating": "nope", "text": "x"},
    )
    assert resp.status_code == 422
