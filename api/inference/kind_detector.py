from __future__ import annotations

import numpy as np
from PIL import Image

INK_THRESHOLD = 250
LINE_ASPECT = 5.0
GAP_RATIO = 0.6


def detect_kind(image: Image.Image) -> str:
    """Classify a handwriting crop as 'word' or 'line' from its ink geometry.

    A line is either much wider than it is tall, or contains at least one
    internal blank gap wide enough to be a space between words.
    """
    arr = np.array(image.convert("L"))
    mask = arr < INK_THRESHOLD
    if not mask.any():
        return "word"

    ys = np.where(mask.any(axis=1))[0]
    xs = np.where(mask.any(axis=0))[0]
    height = int(ys.max() - ys.min() + 1)
    width = int(xs.max() - xs.min() + 1)
    if width / max(height, 1) >= LINE_ASPECT:
        return "line"

    cols = mask.any(axis=0)[xs.min() : xs.max() + 1]
    gap_threshold = max(3, int(GAP_RATIO * height))
    run = 0
    for filled in cols:
        if filled:
            if run >= gap_threshold:
                return "line"
            run = 0
        else:
            run += 1
    return "word"
