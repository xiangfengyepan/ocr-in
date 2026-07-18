from __future__ import annotations

from pathlib import Path

from training.util.charset import BLANK, Charset


def test_encode_decode_roundtrip():
    cs = Charset.from_texts(["cat", "dog"])
    assert cs.num_classes == len(set("catdog")) + 1
    encoded = cs.encode("cat")
    assert BLANK not in encoded
    assert cs.decode_greedy(encoded) == "cat"


def test_decode_collapses_repeats_and_blanks():
    cs = Charset(["a", "b"])
    a, b = cs.stoi["a"], cs.stoi["b"]
    seq = [a, a, BLANK, a, b, b, BLANK, b]
    assert cs.decode_greedy(seq) == "aabb"


def test_encode_skips_unknown():
    cs = Charset(["a", "b"])
    assert cs.encode("axb") == [cs.stoi["a"], cs.stoi["b"]]


def test_save_load(tmp_path: Path):
    cs = Charset.from_texts(["hello", "world"])
    p = tmp_path / "charset.json"
    cs.save(p)
    loaded = Charset.load(p)
    assert loaded.chars == cs.chars
    assert loaded.decode_greedy(loaded.encode("world")) == "world"
