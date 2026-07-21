from __future__ import annotations

import torch
from PIL import Image

from api.inference.crnn_recognizer import crop_to_ink
from api.util.gpu_lock import GPU_LOCK

STOCK_MODEL = "microsoft/trocr-base-handwritten"


class TrocrRecognizer:
    def __init__(self, model_name: str = STOCK_MODEL, device: str | None = None) -> None:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = TrOCRProcessor.from_pretrained(model_name)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name).to(self.device).eval()

    @torch.no_grad()
    def recognize(self, image: Image.Image) -> dict:
        rgb = crop_to_ink(image).convert("RGB")
        pixel_values = self.processor(images=rgb, return_tensors="pt").pixel_values.to(self.device)
        with GPU_LOCK:
            out = self.model.generate(
                pixel_values,
                max_new_tokens=64,
                no_repeat_ngram_size=3,
                output_scores=True,
                return_dict_in_generate=True,
            )
        text = self.processor.batch_decode(out.sequences, skip_special_tokens=True)[0].strip()
        return {"text": text, "confidence": self._confidence(out)}

    def _confidence(self, out) -> float:
        try:
            scores = self.model.compute_transition_scores(
                out.sequences, out.scores, normalize_logits=True
            )
            probs = scores[0].exp()
            probs = probs[torch.isfinite(probs)]
            return float(probs.mean()) if probs.numel() else 0.0
        except Exception:
            return 0.0


_recognizer: TrocrRecognizer | None = None
_loaded = False


def get_trocr_recognizer() -> TrocrRecognizer | None:
    global _recognizer, _loaded
    if not _loaded:
        try:
            _recognizer = TrocrRecognizer()
        except Exception:
            _recognizer = None
        _loaded = True
    return _recognizer
