from __future__ import annotations

import json
from pathlib import Path

# Curated benchmark facts. `dir_rel` (relative to models/) marks engines we
# trained here — availability, training metrics, and per-epoch history are read
# live from that directory at request time.
_BASE: list[dict] = [
    {
        "id": "crnn-words",
        "name": "CRNN",
        "detail": "CNN + BiLSTM + CTC, trained from scratch on IAM words",
        "engine": "crnn",
        "dir_rel": "crnn/english",
        "source": "models/crnn/english",
        "best_for": "words",
        "metrics": {"words": {"cer": 0.103, "wer": 0.240}, "lines": {"cer": 0.431, "wer": 1.0}},
    },
    {
        "id": "trocr-stock",
        "name": "TrOCR-base (stock)",
        "detail": "microsoft/trocr-base-handwritten, used as-is (pretrained on IAM lines)",
        "engine": "trocr",
        "dir_rel": None,
        "source": "pretrained (HuggingFace)",
        "best_for": "lines",
        "metrics": {"words": {"cer": 0.38, "wer": 0.74}, "lines": {"cer": 0.028, "wer": 0.071}},
    },
    {
        "id": "tesseract",
        "name": "Tesseract 5.5",
        "detail": "classical OCR, printed-text model, CPU only",
        "engine": "tesseract",
        "dir_rel": None,
        "source": "system",
        "best_for": None,
        "metrics": {"words": {"cer": 0.792, "wer": 1.18}, "lines": {"cer": 0.518, "wer": 0.893}},
    },
    {
        "id": "ollama-vlm",
        "name": "Ollama VLM (gemma3:4b)",
        "detail": "quantized general vision model via Ollama",
        "engine": "ollama_vlm",
        "dir_rel": None,
        "source": "ollama",
        "best_for": None,
        "metrics": {"words": {"cer": 0.473, "wer": 0.619}, "lines": {"cer": 0.336, "wer": 0.549}},
    },
]


def build_catalog(models_dir: Path) -> list[dict]:
    catalog: list[dict] = []
    for base in _BASE:
        entry = {k: v for k, v in base.items() if k != "dir_rel"}
        dir_rel = base["dir_rel"]
        meta: dict | None = None
        history: list | None = None
        available = True
        if dir_rel:
            path = Path(models_dir) / dir_rel
            available = path.is_dir() and any(path.iterdir())
            if (path / "meta.json").is_file():
                meta = json.loads((path / "meta.json").read_text())
            if (path / "history.json").is_file():
                history = json.loads((path / "history.json").read_text())
        entry["available"] = available
        entry["meta"] = meta
        entry["history"] = history
        catalog.append(entry)
    return catalog
