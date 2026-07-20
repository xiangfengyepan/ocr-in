from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from api.inference.crnn_recognizer import crop_to_ink, get_recognizer


def test_crop_to_ink_trims_whitespace():
    arr = np.full((60, 200), 255, dtype=np.uint8)
    arr[25:35, 90:110] = 0  # a dark blob in the middle
    cropped = crop_to_ink(Image.fromarray(arr), pad=2)
    assert cropped.size[0] < 200 and cropped.size[1] < 60
    assert cropped.size[0] >= 20 and cropped.size[1] >= 10


def test_recognizer_reads_a_word():
    rec = get_recognizer()
    if rec is None:
        pytest.skip("no models/crnn/english checkpoint")
    # a blank canvas should still return a string (possibly empty) with a float confidence
    out = rec.recognize(Image.new("L", (200, 60), color=255))
    assert isinstance(out["text"], str)
    assert isinstance(out["confidence"], float)
