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
        json={"image": _png_data_url(), "rating": "nope", "text": "x"},
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
            "rating": "incorrect",
            "text": "hi",
            "engine_guess": "h1",
        },
    )
    assert resp.status_code == 200
    saved = Image.open(tmp_path / "english" / "1.png")
    assert saved.size[0] < w and saved.size[1] < h  # cropped, not full canvas


def test_correct_manual_language(tmp_path, monkeypatch):
    from api.labeling import routes

    monkeypatch.setattr(routes, "correct_text", lambda text, language, kind: (text.upper(), language))
    client = _client(tmp_path)
    resp = client.post(
        "/label/correct", json={"text": "hi", "language": "english", "kind": "word"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"corrected": "HI", "language": "english"}


def test_correct_auto_returns_detected_language(tmp_path, monkeypatch):
    from api.labeling import routes

    monkeypatch.setattr(routes, "correct_text", lambda text, language, kind: ("corregido", "spanish"))
    client = _client(tmp_path)
    resp = client.post(
        "/label/correct", json={"text": "hola", "language": "auto", "kind": "line"}
    )
    assert resp.json() == {"corrected": "corregido", "language": "spanish"}


def _add(client, text, rating="correct"):
    return client.post(
        "/label/sample",
        json={
            "image": _png_data_url(),
            "rating": rating,
            "text": text,
            "engine_guess": text,
        },
    ).json()["id"]


def test_samples_list_and_image(tmp_path):
    client = _client(tmp_path)
    _add(client, "one")
    sid = _add(client, "two", rating="incorrect")
    rows = client.get("/label/samples").json()
    assert [r["text"] for r in rows] == ["two", "one"]  # newest first
    img = client.get(f"/label/image/{sid}")
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"
    assert client.get("/label/image/9999").status_code == 404


def test_patch_sample(tmp_path):
    client = _client(tmp_path)
    sid = _add(client, "gues", rating="incorrect")
    resp = client.patch(f"/label/sample/{sid}", json={"text": "guess", "rating": "correct"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "guess" and body["rating"] == "correct"
    assert client.patch(f"/label/sample/{sid}", json={"rating": "maybe"}).status_code == 422
    assert client.patch("/label/sample/9999", json={"text": "x"}).status_code == 404


def test_delete_sample(tmp_path):
    client = _client(tmp_path)
    sid = _add(client, "junk")
    assert client.delete(f"/label/sample/{sid}").status_code == 200
    assert client.get("/label/samples").json() == []
    assert client.delete(f"/label/sample/{sid}").status_code == 404
