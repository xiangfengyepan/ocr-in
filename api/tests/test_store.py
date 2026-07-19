from __future__ import annotations

from pathlib import Path

from PIL import Image
import io

from api.labeling.store import SampleStore


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("L", (30, 20), color=255).save(buf, format="PNG")
    return buf.getvalue()


def test_add_sample_writes_file_and_row(tmp_path: Path):
    store = SampleStore(tmp_path)
    res = store.add_sample(_png_bytes(), "hello", "english", "correct", "helo")
    assert res["id"] == 1
    assert res["image_path"] == "english/1.png"
    assert (tmp_path / "english" / "1.png").exists()


def test_stats_counts_by_rating(tmp_path: Path):
    store = SampleStore(tmp_path)
    store.add_sample(_png_bytes(), "a", "english", "correct", "a")
    store.add_sample(_png_bytes(), "b", "english", "wrong", "x")
    store.add_sample(_png_bytes(), "c", "spanish", "correct", "c")
    s = store.stats()
    assert s["total"] == 3
    assert s["by_rating"] == {"correct": 2, "partial": 0, "wrong": 1}
