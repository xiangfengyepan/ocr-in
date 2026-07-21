from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image

from api.registry import ModelRegistry
from api.util import settings
from api.util.gpu_lock import GPU_LOCK
from training.augmentation.transforms import IMG_HEIGHT, IMG_WIDTH, Preprocess
from training.models import CRNN, greedy_decode
from training.util.charset import Charset


def crop_to_ink(image: Image.Image, pad: int = 8, thresh: int = 250) -> Image.Image:
    gray = image.convert("L")
    arr = np.array(gray)
    mask = arr < thresh
    if not mask.any():
        return gray
    ys, xs = np.where(mask)
    y0 = max(0, int(ys.min()) - pad)
    x0 = max(0, int(xs.min()) - pad)
    y1 = min(arr.shape[0], int(ys.max()) + pad + 1)
    x1 = min(arr.shape[1], int(xs.max()) + pad + 1)
    return gray.crop((x0, y0, x1, y1))


class CrnnRecognizer:
    def __init__(self, weights_dir: Path, device: str | None = None) -> None:
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.charset = Charset.load(Path(weights_dir) / "charset.json")
        self.model = CRNN(self.charset.num_classes)
        self.model.load_state_dict(
            torch.load(Path(weights_dir) / "model.pt", map_location=self.device)
        )
        self.model.to(self.device).eval()
        self.preprocess = Preprocess(IMG_HEIGHT, IMG_WIDTH, train=False)

    @torch.no_grad()
    def recognize(self, image: Image.Image) -> dict:
        cropped = crop_to_ink(image)
        x = self.preprocess(cropped).unsqueeze(0).to(self.device)
        with GPU_LOCK:
            log_probs = self.model(x)  # (T, 1, C)
        text = greedy_decode(log_probs.cpu(), self.charset)[0]
        probs = log_probs.exp().squeeze(1)  # (T, C)
        max_prob, idx = probs.max(dim=1)  # (T,)
        non_blank = idx != 0
        confidence = float(max_prob[non_blank].mean()) if bool(non_blank.any()) else 0.0
        return {"text": text, "confidence": confidence}


_recognizer: CrnnRecognizer | None = None
_loaded = False


def get_recognizer() -> CrnnRecognizer | None:
    global _recognizer, _loaded
    if not _loaded:
        entry = ModelRegistry(settings.models_dir).resolve("crnn", "english")
        _recognizer = None if entry.weights is None else CrnnRecognizer(entry.weights)
        _loaded = True
    return _recognizer
