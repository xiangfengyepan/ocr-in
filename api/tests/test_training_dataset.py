from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from api.labeling.store import SampleStore
from api.training_jobs.dataset import build_split


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("L", (30, 20), color=255).save(buf, format="PNG")
    return buf.getvalue()


def _seeded_store(tmp_path: Path) -> SampleStore:
    store = SampleStore(tmp_path)
    for i in range(10):
        store.add_sample(_png_bytes(), f"line{i}", "english", "correct", None, kind="line")
    return store


def test_build_split_sizes(tmp_path: Path):
    store = _seeded_store(tmp_path)
    train_rows, val_rows = build_split(store, "line")
    assert len(train_rows) == 8
    assert len(val_rows) == 2


def test_build_split_deterministic(tmp_path: Path):
    store = _seeded_store(tmp_path)
    train1, val1 = build_split(store, "line", seed=1234)
    train2, val2 = build_split(store, "line", seed=1234)
    assert train1 == train2
    assert val1 == val2


def test_build_split_image_paths_absolute_and_exist(tmp_path: Path):
    store = _seeded_store(tmp_path)
    train_rows, val_rows = build_split(store, "line")
    for row in [*train_rows, *val_rows]:
        image_path = Path(row["image"])
        assert image_path.is_absolute()
        assert image_path.exists()
