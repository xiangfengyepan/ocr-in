from __future__ import annotations

from api.registry.registry import ModelRegistry


def test_promote_keeps_single_previous(tmp_path):
    reg = ModelRegistry(tmp_path)
    live = tmp_path / "trocr" / "english"
    live.mkdir(parents=True)
    (live / "w").write_text("v1")
    cand = tmp_path / "cand"
    cand.mkdir()
    (cand / "w").write_text("v2")

    reg.promote("trocr", "english", cand)

    assert (live / "w").read_text() == "v2"
    assert (tmp_path / "trocr" / "english__previous" / "w").read_text() == "v1"
    assert reg.rollback("trocr", "english") is True
    assert (live / "w").read_text() == "v1"


def test_promote_without_existing_live_installs_candidate(tmp_path):
    reg = ModelRegistry(tmp_path)
    cand = tmp_path / "cand"
    cand.mkdir()
    (cand / "w").write_text("v1")

    reg.promote("trocr", "english", cand)

    live = tmp_path / "trocr" / "english"
    assert (live / "w").read_text() == "v1"
    assert not (tmp_path / "trocr" / "english__previous").exists()
