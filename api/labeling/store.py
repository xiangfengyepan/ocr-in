from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_RATINGS = ("correct", "partial", "wrong")


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

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

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

    def stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            rows = conn.execute(
                "SELECT rating, COUNT(*) FROM samples GROUP BY rating"
            ).fetchall()
        by_rating = {r: 0 for r in _RATINGS}
        for rating, count in rows:
            if rating in by_rating:
                by_rating[rating] = count
        return {"total": int(total), "by_rating": by_rating}
