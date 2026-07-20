from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

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
    store.add_sample(_png_bytes(), "b", "english", "incorrect", "x")
    store.add_sample(_png_bytes(), "c", "spanish", "correct", "c")
    s = store.stats()
    assert s["total"] == 3
    assert s["by_rating"] == {"pending": 0, "correct": 2, "incorrect": 1}


def test_add_sample_rejects_unsafe_language(tmp_path: Path):
    store = SampleStore(tmp_path)
    with pytest.raises(ValueError):
        store.add_sample(_png_bytes(), "x", "../evil", "correct", "x")


def test_add_sample_rejects_legacy_rating(tmp_path: Path):
    store = SampleStore(tmp_path)
    with pytest.raises(ValueError):
        store.add_sample(_png_bytes(), "x", "english", "wrong", "x")


def test_list_samples_newest_first(tmp_path: Path):
    store = SampleStore(tmp_path)
    store.add_sample(_png_bytes(), "one", "english", "correct", "one")
    store.add_sample(_png_bytes(), "two", "english", "incorrect", "tow")
    rows = store.list_samples()
    assert [r["id"] for r in rows] == [2, 1]
    assert rows[0]["text"] == "two"
    assert rows[0]["rating"] == "incorrect"


def test_list_samples_paginates_and_counts(tmp_path: Path):
    store = SampleStore(tmp_path)
    for i in range(5):
        store.add_sample(_png_bytes(), f"row {i}", "english", "pending", None)
    page1 = store.list_samples(limit=2, offset=0)
    page2 = store.list_samples(limit=2, offset=2)
    assert [r["id"] for r in page1] == [5, 4]
    assert [r["id"] for r in page2] == [3, 2]
    assert store.count() == 5
    assert store.count(rating="pending") == 5
    assert store.count(rating="correct") == 0


def test_list_samples_filters_by_query(tmp_path: Path):
    store = SampleStore(tmp_path)
    store.add_sample(_png_bytes(), "hello world", "english", "correct", "helo")
    store.add_sample(_png_bytes(), "goodbye", "english", "incorrect", "gudbye")
    rows = store.list_samples(q="hello")
    assert [r["text"] for r in rows] == ["hello world"]
    assert store.count(q="good") == 1
    # matches engine_guess too, case-insensitive
    assert store.count(q="GUD") == 1


def test_update_sample_text_and_rating(tmp_path: Path):
    store = SampleStore(tmp_path)
    store.add_sample(_png_bytes(), "gues", "english", "incorrect", "gues")
    updated = store.update_sample(1, text="guess", rating="correct")
    assert updated is not None
    assert updated["text"] == "guess"
    assert updated["rating"] == "correct"


def test_update_sample_rejects_bad_rating(tmp_path: Path):
    store = SampleStore(tmp_path)
    store.add_sample(_png_bytes(), "x", "english", "correct", "x")
    with pytest.raises(ValueError):
        store.update_sample(1, rating="maybe")


def test_delete_sample_removes_row_and_file(tmp_path: Path):
    store = SampleStore(tmp_path)
    store.add_sample(_png_bytes(), "x", "english", "correct", "x")
    assert (tmp_path / "english" / "1.png").exists()
    assert store.delete_sample(1) is True
    assert not (tmp_path / "english" / "1.png").exists()
    assert store.get_sample(1) is None
    assert store.delete_sample(1) is False


def test_legacy_ratings_migrated_on_init(tmp_path: Path):
    db = tmp_path / "labels.db"
    SampleStore(tmp_path)  # create schema
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO samples (image_path, text, language, rating, engine_guess, created_at) "
            "VALUES ('english/9.png', 't', 'english', 'partial', 'g', '2026-01-01T00:00:00')"
        )
        conn.execute(
            "INSERT INTO samples (image_path, text, language, rating, engine_guess, created_at) "
            "VALUES ('english/10.png', 't', 'english', 'wrong', 'g', '2026-01-01T00:00:00')"
        )
    reopened = SampleStore(tmp_path)  # migration runs on init
    ratings = {r["rating"] for r in reopened.list_samples()}
    assert ratings == {"incorrect"}
