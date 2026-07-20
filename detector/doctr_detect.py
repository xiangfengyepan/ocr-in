"""Standalone docTR line detector.

Runs in its OWN environment (its torch), isolated from the main API:
    uv run --no-project --with python-doctr python detector/doctr_detect.py <image>

Prints one JSON line: {"width": W, "height": H, "lines": [[x0,y0,x1,y1], ...]}
(pixel coordinates, top-to-bottom). Word boxes from docTR's detector are grouped
into text lines by vertical overlap.
"""

from __future__ import annotations

import json
import sys

import numpy as np
from PIL import Image


def group_lines(words: list[list[float]]) -> list[list[float]]:
    if not words:
        return []
    words = sorted(words, key=lambda b: (b[1] + b[3]) / 2)
    groups: list[list[list[float]]] = [[words[0]]]
    for box in words[1:]:
        prev = groups[-1][-1]
        prev_c = (prev[1] + prev[3]) / 2
        box_c = (box[1] + box[3]) / 2
        tol = 0.6 * max(prev[3] - prev[1], box[3] - box[1], 1.0)
        if abs(box_c - prev_c) <= tol:
            groups[-1].append(box)
        else:
            groups.append([box])
    lines = []
    for grp in groups:
        lines.append([
            min(w[0] for w in grp),
            min(w[1] for w in grp),
            max(w[2] for w in grp),
            max(w[3] for w in grp),
        ])
    return lines


def main() -> None:
    from doctr.models import detection_predictor

    image = Image.open(sys.argv[1]).convert("RGB")
    arr = np.array(image)
    height, width = arr.shape[:2]

    predictor = detection_predictor(pretrained=True)
    result = predictor([arr])[0]
    raw = result["words"] if isinstance(result, dict) else result

    words = []
    for row in np.asarray(raw):
        x0, y0, x1, y1 = float(row[0]), float(row[1]), float(row[2]), float(row[3])
        words.append([x0 * width, y0 * height, x1 * width, y1 * height])

    print(json.dumps({"width": width, "height": height, "lines": group_lines(words)}))


if __name__ == "__main__":
    main()
