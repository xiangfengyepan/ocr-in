from __future__ import annotations

MODEL_CATALOG: list[dict] = [
    {
        "id": "crnn-words",
        "name": "CRNN",
        "detail": "CNN + BiLSTM + CTC, trained from scratch on IAM words",
        "engine": "crnn",
        "available": True,
        "source": "models/crnn/english",
        "best_for": "words",
        "metrics": {
            "words": {"cer": 0.103, "wer": 0.240},
            "lines": {"cer": 0.431, "wer": 1.0},
        },
    },
    {
        "id": "trocr-stock",
        "name": "TrOCR-base (stock)",
        "detail": "microsoft/trocr-base-handwritten, used as-is (pretrained on IAM lines)",
        "engine": "trocr",
        "available": True,
        "source": "pretrained (HuggingFace)",
        "best_for": "lines",
        "metrics": {
            "words": {"cer": 0.38, "wer": 0.74},
            "lines": {"cer": 0.028, "wer": 0.071},
        },
    },
    {
        "id": "trocr-ft-words",
        "name": "TrOCR-base (fine-tuned on words)",
        "detail": "trocr-base fine-tuned on IAM words (worse than CRNN on words)",
        "engine": "trocr",
        "available": True,
        "source": "models/trocr/english",
        "best_for": None,
        "metrics": {
            "words": {"cer": 0.21, "wer": 0.26},
            "lines": None,
        },
    },
    {
        "id": "tesseract",
        "name": "Tesseract 5.5",
        "detail": "classical OCR, printed-text model, CPU only",
        "engine": "tesseract",
        "available": True,
        "source": "system",
        "best_for": None,
        "metrics": {
            "words": {"cer": 0.792, "wer": 1.18},
            "lines": {"cer": 0.518, "wer": 0.893},
        },
    },
    {
        "id": "ollama-vlm",
        "name": "Ollama VLM (gemma3:4b)",
        "detail": "quantized general vision model via Ollama",
        "engine": "ollama_vlm",
        "available": True,
        "source": "ollama",
        "best_for": None,
        "metrics": {
            "words": {"cer": 0.473, "wer": 0.619},
            "lines": {"cer": 0.336, "wer": 0.549},
        },
    },
]
