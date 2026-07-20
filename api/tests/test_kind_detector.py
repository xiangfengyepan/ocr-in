from __future__ import annotations

import numpy as np
from PIL import Image

from api.inference.kind_detector import detect_kind


def _img(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(arr, mode="L")


def test_compact_blob_is_word():
    arr = np.full((60, 90), 255, dtype=np.uint8)
    arr[20:40, 20:70] = 0  # single compact blob
    assert detect_kind(_img(arr)) == "word"


def test_wide_aspect_is_line():
    arr = np.full((40, 600, ), 255, dtype=np.uint8)
    arr[15:25, 10:590] = 0  # long thin stroke -> wide aspect
    assert detect_kind(_img(arr)) == "line"


def test_two_blobs_with_gap_is_line():
    arr = np.full((60, 260), 255, dtype=np.uint8)
    arr[20:40, 10:70] = 0     # word 1
    arr[20:40, 180:240] = 0   # word 2, separated by a wide gap
    assert detect_kind(_img(arr)) == "line"


def test_blank_is_word():
    assert detect_kind(_img(np.full((50, 50), 255, dtype=np.uint8))) == "word"
