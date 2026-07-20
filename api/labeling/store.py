from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_RATINGS = ("correct", "incorrect")
_LEGACY_RATINGS = ("partial", "wrong")
_COLUMNS = ("id", "image_path", "text", "language", "rating", "engine_guess", "created_at")


class SampleStore:
    def __init__(self, root: Path, db_path: Path | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path else self.root / "labels.db"
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL,
                    text TEXT NOT NULL,
                    language TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    engine_guess TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "UPDATE samples SET rating = 'incorrect' WHERE rating IN (?, ?)",
                _LEGACY_RATINGS,
            )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_sample(
        self,
        png_bytes: bytes,
        text: str,
        language: str,
        rating: str,
        engine_guess: str | None,
    ) -> dict:
        if rating not in _RATINGS:
            raise ValueError(f"invalid rating: {rating!r}")
        if not re.fullmatch(r"[A-Za-z_]+", language):
            raise ValueError(f"invalid language: {language!r}")
        created = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO samples (image_path, text, language, rating, engine_guess, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("", text, language, rating, engine_guess, created),
            )
            sample_id = int(cur.lastrowid)
            image_dir = self.root / language
            image_dir.mkdir(parents=True, exist_ok=True)
            path = image_dir / f"{sample_id}.png"
            path.write_bytes(png_bytes)
            rel = str(path.relative_to(self.root))
            conn.execute("UPDATE samples SET image_path = ? WHERE id = ?", (rel, sample_id))
        return {"id": sample_id, "image_path": rel}

    def list_samples(self, limit: int = 100, offset: int = 0) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM samples ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_sample(self, sample_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM samples WHERE id = ?", (sample_id,)
            ).fetchone()
        return dict(row) if row else None

    def update_sample(
        self, sample_id: int, text: str | None = None, rating: str | None = None
    ) -> dict | None:
        if rating is not None and rating not in _RATINGS:
            raise ValueError(f"invalid rating: {rating!r}")
        sets: list[str] = []
        params: list[object] = []
        if text is not None:
            sets.append("text = ?")
            params.append(text)
        if rating is not None:
            sets.append("rating = ?")
            params.append(rating)
        if sets:
            params.append(sample_id)
            with self._conn() as conn:
                conn.execute(f"UPDATE samples SET {', '.join(sets)} WHERE id = ?", params)
        return self.get_sample(sample_id)

    def delete_sample(self, sample_id: int) -> bool:
        sample = self.get_sample(sample_id)
        if sample is None:
            return False
        image_path = self.root / sample["image_path"]
        if image_path.is_file():
            image_path.unlink()
        with self._conn() as conn:
            conn.execute("DELETE FROM samples WHERE id = ?", (sample_id,))
        return True

    def stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            rows = conn.execute(
                "SELECT rating, COUNT(*) FROM samples GROUP BY rating"
            ).fetchall()
        by_rating = {r: 0 for r in _RATINGS}
        for row in rows:
            if row["rating"] in by_rating:
                by_rating[row["rating"]] = row[1]
        return {"total": int(total), "by_rating": by_rating}
