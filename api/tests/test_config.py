from __future__ import annotations

from fastapi.testclient import TestClient

from api import main


def test_get_and_set_ollama_host(monkeypatch):
    monkeypatch.setattr(main.settings, "ollama_host", "http://localhost:11434")
    client = TestClient(main.app)

    assert client.get("/config").json() == {"ollama_host": "http://localhost:11434"}

    resp = client.post("/config", json={"ollama_host": "  http://box:11434  "})
    assert resp.status_code == 200
    assert resp.json() == {"ollama_host": "http://box:11434"}  # trimmed

    # the change is reflected for subsequent reads (runtime override)
    assert client.get("/config").json()["ollama_host"] == "http://box:11434"
