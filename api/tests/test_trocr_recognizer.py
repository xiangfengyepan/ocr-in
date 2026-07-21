from __future__ import annotations

import transformers

from api.inference import trocr_recognizer as tr


class _FakeProcessor:
    pass


class _FakeModel:
    def to(self, device):
        return self

    def eval(self):
        return self


def _patch_hf(monkeypatch) -> dict:
    captured: dict[str, str] = {}

    def _proc(cls, source, *a, **k):
        captured["proc"] = str(source)
        return _FakeProcessor()

    def _model(cls, source, *a, **k):
        captured["model"] = str(source)
        return _FakeModel()

    monkeypatch.setattr(
        transformers.TrOCRProcessor, "from_pretrained", classmethod(_proc), raising=False
    )
    monkeypatch.setattr(
        transformers.VisionEncoderDecoderModel,
        "from_pretrained",
        classmethod(_model),
        raising=False,
    )
    return captured


def _patch_serving(monkeypatch, weights):
    monkeypatch.setattr(
        tr.ModelRegistry,
        "serving_weights",
        lambda self, engine, language: weights,
    )


def test_loads_from_registry_weights_when_present(monkeypatch, tmp_path):
    captured = _patch_hf(monkeypatch)
    weights = tmp_path / "trocr" / "english__personal"
    weights.mkdir(parents=True)
    _patch_serving(monkeypatch, weights)
    tr.reset_trocr_recognizer()
    rec = tr.get_trocr_recognizer()
    assert rec is not None
    assert captured["model"] == str(weights)
    assert captured["proc"] == str(weights)


def test_falls_back_to_stock_when_no_weights(monkeypatch, tmp_path):
    captured = _patch_hf(monkeypatch)
    _patch_serving(monkeypatch, None)
    tr.reset_trocr_recognizer()
    rec = tr.get_trocr_recognizer()
    assert rec is not None
    assert captured["model"] == tr.STOCK_MODEL


def test_reset_clears_cache(monkeypatch, tmp_path):
    _patch_hf(monkeypatch)
    _patch_serving(monkeypatch, None)
    tr.reset_trocr_recognizer()
    tr.get_trocr_recognizer()
    assert tr._loaded is True
    tr.reset_trocr_recognizer()
    assert tr._recognizer is None
    assert tr._loaded is False
