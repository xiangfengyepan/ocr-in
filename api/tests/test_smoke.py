from __future__ import annotations

from pathlib import Path

import pytest

from api.engines import ENGINES, OcrEngine, OcrResult
from api.registry import ModelRegistry
from api.util import build_engine


def test_engines_registered():
    assert set(ENGINES) == {"tesseract", "crnn", "trocr", "ollama_vlm"}
    for cls in ENGINES.values():
        assert issubclass(cls, OcrEngine)


def test_registry_falls_back_to_pretrained(tmp_path: Path):
    registry = ModelRegistry(tmp_path)
    entry = registry.resolve("trocr", "english")
    assert entry.pretrained is True
    assert entry.weights is None


def test_registry_finds_finetuned(tmp_path: Path):
    weights_dir = tmp_path / "trocr" / "english"
    weights_dir.mkdir(parents=True)
    (weights_dir / "model.safetensors").write_bytes(b"")
    entry = ModelRegistry(tmp_path).resolve("trocr", "english")
    assert entry.pretrained is False
    assert entry.weights == weights_dir


def test_build_engine(tmp_path: Path):
    registry = ModelRegistry(tmp_path)
    engine = build_engine("tesseract", ["english"], registry)
    assert isinstance(engine, OcrEngine)
    assert engine.engine == "tesseract"


def test_build_engine_unknown(tmp_path: Path):
    registry = ModelRegistry(tmp_path)
    with pytest.raises(ValueError):
        build_engine("nope", ["english"], registry)


def test_ocrresult_shape():
    r = OcrResult(text="hi", bbox=(0.0, 0.0, 1.0, 1.0), confidence=0.9)
    assert r.text == "hi"
    assert len(r.bbox) == 4
