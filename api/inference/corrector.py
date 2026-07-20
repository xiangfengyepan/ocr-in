from __future__ import annotations

import ollama

from api.util import settings

CORRECTOR_MODEL = "gemma3:4b"

LANG_NAMES = {
    "english": "English",
    "spanish": "Spanish",
    "catalan": "Catalan",
    "chinese": "Chinese",
    "japanese": "Japanese",
}


def _client() -> ollama.Client:
    return ollama.Client(host=settings.ollama_host)


def correct(text: str, language: str, kind: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    lang = LANG_NAMES.get(language, "English")
    unit = "sentence" if kind == "line" else "word"
    grammar = " and grammar" if unit == "sentence" else ""
    prompt = (
        f"You are correcting handwriting-OCR output written in {lang}. "
        f"The text is a single {unit}. Fix OCR and spelling{grammar} errors while staying "
        f"faithful to what was written; do not translate or add words. "
        f"Reply with ONLY the corrected {unit} in {lang} — no quotes, labels, or explanation.\n\n{text}"
    )
    try:
        resp = _client().generate(
            model=CORRECTOR_MODEL,
            prompt=prompt,
            options={"temperature": 0, "num_predict": 64},
        )
        lines = [ln for ln in resp["response"].strip().splitlines() if ln.strip()]
        return lines[0].strip().strip('"').strip("'") if lines else text
    except Exception:
        return text


def detect_and_correct(text: str, kind: str) -> tuple[str, str]:
    """Auto mode: gemma identifies the language and corrects in one call.

    Returns (corrected_text, language).
    """
    text = (text or "").strip()
    if not text:
        return text, "english"
    unit = "sentence" if kind == "line" else "word"
    grammar = " and grammar" if unit == "sentence" else ""
    prompt = (
        f"You are processing handwriting-OCR output: a single {unit}.\n"
        f"1) Identify its language: one of english, spanish, catalan, chinese, japanese.\n"
        f"2) Fix OCR and spelling{grammar} errors, staying faithful; do not translate.\n"
        f"Respond in exactly two lines:\nLANG: <language>\nTEXT: <corrected {unit}>\n\n{text}"
    )
    try:
        resp = _client().generate(
            model=CORRECTOR_MODEL,
            prompt=prompt,
            options={"temperature": 0, "num_predict": 96},
        )
        language, corrected = "english", text
        for line in resp["response"].splitlines():
            stripped = line.strip()
            low = stripped.lower()
            if low.startswith("lang:"):
                value = stripped.split(":", 1)[1].strip().lower()
                if value in LANG_NAMES:
                    language = value
            elif low.startswith("text:"):
                corrected = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        return corrected, language
    except Exception:
        return text, "english"
