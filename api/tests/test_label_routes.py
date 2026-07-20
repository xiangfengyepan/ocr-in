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


def _blob_png_data_url(w=800, h=200):
    img = Image.new("L", (w, h), color=255)
    for x in range(60, 120):
        for y in range(80, 120):
            img.putpixel((x, y), 0)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), (w, h)


def test_sample_stores_cropped_image(tmp_path):
    client = _client(tmp_path)
    data_url, (w, h) = _blob_png_data_url()
    resp = client.post(
        "/label/sample",
        json={
            "image": data_url,
            "language": "english",
            "rating": "wrong",
            "text": "hi",
            "engine_guess": "h1",
        },
    )
    assert resp.status_code == 200
    saved = Image.open(tmp_path / "english" / "1.png")
    assert saved.size[0] < w and saved.size[1] < h  # cropped, not full canvas


def test_sample_bad_language_returns_400(tmp_path):
    client = _client(tmp_path)
    resp = client.post(
        "/label/sample",
        json={
            "image": _png_data_url(),
            "language": "../evil",
            "rating": "correct",
            "text": "x",
            "engine_guess": "x",
        },
    )
    assert resp.status_code == 400
