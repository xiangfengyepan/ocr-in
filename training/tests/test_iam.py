from __future__ import annotations

from pathlib import Path

from PIL import Image

from training.datasets.iam import (
    form_id_of,
    parse_form_writers,
    parse_words,
    word_image_path,
    writer_split,
)


def _make_image(path: Path, empty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if empty:
        path.write_bytes(b"")
    else:
        Image.new("L", (40, 20), color=255).save(path)


def test_path_and_form_helpers(tmp_path: Path):
    assert form_id_of("a01-000u-00-00") == "a01-000u"
    assert word_image_path("a01-000u-00-00", tmp_path) == (
        tmp_path / "a01" / "a01-000u" / "a01-000u-00-00.png"
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    words_dir = tmp_path / "words"
    for wid in ["a01-000u-00-00", "a01-000u-00-01", "b02-010-00-00"]:
        _make_image(word_image_path(wid, words_dir))
    _make_image(word_image_path("a01-000u-00-99", words_dir), empty=True)
    words_txt = tmp_path / "words.txt"
    words_txt.write_text(
        "\n".join(
            [
                "#comment",
                "a01-000u-00-00 ok 154 408 768 27 51 AT A",
                "a01-000u-00-01 ok 154 507 766 213 48 NN MOVE",
                "a01-000u-00-02 err 156 430 1290 177 59 NPTS M Ps",
                "a01-000u-00-99 ok 154 1 2 3 4 XX zero",
                "b02-010-00-00 ok 154 1 2 3 4 NN cat",
            ]
        ),
        encoding="utf-8",
    )
    return words_txt, words_dir


def test_parse_words_filters(tmp_path: Path):
    words_txt, words_dir = _fixture(tmp_path)
    samples = parse_words(words_txt, words_dir)
    ids = {s.word_id for s in samples}
    assert ids == {"a01-000u-00-00", "a01-000u-00-01", "b02-010-00-00"}
    texts = {s.word_id: s.text for s in samples}
    assert texts["a01-000u-00-00"] == "A"
    assert texts["a01-000u-00-01"] == "MOVE"


def test_parse_words_include_err(tmp_path: Path):
    words_txt, words_dir = _fixture(tmp_path)
    _make_image(word_image_path("a01-000u-00-02", words_dir))
    samples = parse_words(words_txt, words_dir, include_err=True)
    err = next(s for s in samples if s.word_id == "a01-000u-00-02")
    assert err.text == "M Ps"


def test_writer_split_no_leakage(tmp_path: Path):
    forms_txt = tmp_path / "forms.txt"
    forms_txt.write_text("a01-000u 000 2 prt\nb02-010 001 2 prt\n", encoding="utf-8")
    mapping = parse_form_writers(forms_txt)
    assert mapping == {"a01-000u": "000", "b02-010": "001"}
    words_txt, words_dir = _fixture(tmp_path)
    samples = parse_words(words_txt, words_dir)
    splits = writer_split(samples, forms_txt, val_frac=0.34, test_frac=0.33, seed=1)
    writers_per_split = {
        name: {mapping[form_id_of(s.word_id)] for s in items}
        for name, items in splits.items()
    }
    seen: set[str] = set()
    for writers in writers_per_split.values():
        assert not (writers & seen)
        seen |= writers
