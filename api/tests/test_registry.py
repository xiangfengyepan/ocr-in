from __future__ import annotations

from api.registry.registry import ModelRegistry


def test_promote_installs_into_personal_and_keeps_single_previous(tmp_path):
    reg = ModelRegistry(tmp_path)
    baseline = tmp_path / "trocr" / "english"
    baseline.mkdir(parents=True)
    (baseline / "w").write_text("baseline")

    personal = tmp_path / "trocr" / "english__personal"
    personal.mkdir(parents=True)
    (personal / "w").write_text("v1")

    cand = tmp_path / "cand"
    cand.mkdir()
    (cand / "w").write_text("v2")

    reg.promote("trocr", "english", cand)

    # candidate installed into the PERSONAL slot
    assert (personal / "w").read_text() == "v2"
    # baseline is untouched
    assert (baseline / "w").read_text() == "baseline"
    # single previous holds the prior personal
    assert (tmp_path / "trocr" / "english__personal__previous" / "w").read_text() == "v1"
    # candidate survives
    assert (cand / "w").read_text() == "v2"
    # serving prefers the personal dir
    assert reg.serving_weights("trocr", "english") == personal

    # rollback restores the previous personal
    assert reg.rollback("trocr", "english") is True
    assert (personal / "w").read_text() == "v1"


def test_promote_without_existing_personal_installs_candidate(tmp_path):
    reg = ModelRegistry(tmp_path)
    cand = tmp_path / "cand"
    cand.mkdir()
    (cand / "w").write_text("v1")

    reg.promote("trocr", "english", cand)

    personal = tmp_path / "trocr" / "english__personal"
    assert (personal / "w").read_text() == "v1"
    assert not (tmp_path / "trocr" / "english__personal__previous").exists()


def test_promote_does_not_touch_baseline(tmp_path):
    reg = ModelRegistry(tmp_path)
    baseline = tmp_path / "crnn" / "english"
    baseline.mkdir(parents=True)
    (baseline / "model.pt").write_text("iam")

    cand = tmp_path / "cand"
    cand.mkdir()
    (cand / "model.pt").write_text("personal")

    reg.promote("crnn", "english", cand)

    assert (baseline / "model.pt").read_text() == "iam"
    assert (tmp_path / "crnn" / "english__personal" / "model.pt").read_text() == "personal"


def test_serving_weights_prefers_personal_then_baseline_then_none(tmp_path):
    reg = ModelRegistry(tmp_path)
    assert reg.serving_weights("trocr", "english") is None

    baseline = tmp_path / "trocr" / "english"
    baseline.mkdir(parents=True)
    (baseline / "w").write_text("baseline")
    assert reg.serving_weights("trocr", "english") == baseline

    personal = tmp_path / "trocr" / "english__personal"
    personal.mkdir(parents=True)
    (personal / "w").write_text("personal")
    assert reg.serving_weights("trocr", "english") == personal
    assert reg.personalized("trocr", "english") == personal


def test_rollback_removes_personal_when_no_previous(tmp_path):
    reg = ModelRegistry(tmp_path)
    baseline = tmp_path / "trocr" / "english"
    baseline.mkdir(parents=True)
    (baseline / "w").write_text("baseline")
    personal = tmp_path / "trocr" / "english__personal"
    personal.mkdir(parents=True)
    (personal / "w").write_text("v1")

    # no previous exists -> rollback removes personal, serving falls back to baseline
    assert reg.rollback("trocr", "english") is True
    assert not personal.exists()
    assert reg.serving_weights("trocr", "english") == baseline

    # nothing left to roll back
    assert reg.rollback("trocr", "english") is False


def test_personalized_none_when_empty_dir(tmp_path):
    reg = ModelRegistry(tmp_path)
    (tmp_path / "trocr" / "english__personal").mkdir(parents=True)
    assert reg.personalized("trocr", "english") is None
