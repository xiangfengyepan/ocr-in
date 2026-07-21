from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.labeling.store import SampleStore


def build_split(
    store: "SampleStore", kind: str, seed: int = 1234, val_frac: float = 0.15
) -> tuple[list[dict], list[dict]]:
    rows = store.training_rows(kind)
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    cut = round(len(shuffled) * (1 - val_frac))
    train_rows = shuffled[:cut]
    val_rows = shuffled[cut:]

    def _to_row(r: dict) -> dict:
        return {"image": str((store.root / r["image_path"]).resolve()), "text": r["text"]}

    return [_to_row(r) for r in train_rows], [_to_row(r) for r in val_rows]
