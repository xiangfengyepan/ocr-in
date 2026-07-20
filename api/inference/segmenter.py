from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DETECT_SCRIPT = _REPO_ROOT / "detector" / "doctr_detect.py"
_DETECT_CMD = [
    "uv", "run", "--no-project", "--with", "python-doctr",
    "python", str(_DETECT_SCRIPT),
]


def segment_lines(image: Image.Image, timeout: int = 600) -> list[list[float]]:
    """Return line bounding boxes [x0, y0, x1, y1] via the isolated docTR detector.

    Returns [] if detection fails (the caller can fall back to the whole image).
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        tmp = handle.name
    try:
        image.convert("RGB").save(tmp)
        proc = subprocess.run(
            [*_DETECT_CMD, tmp],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(_REPO_ROOT),
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        data = json.loads(proc.stdout.strip().splitlines()[-1])
        return [[float(v) for v in box] for box in data.get("lines", [])]
    except Exception:
        return []
    finally:
        Path(tmp).unlink(missing_ok=True)
