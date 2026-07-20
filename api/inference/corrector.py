from __future__ import annotations

from pathlib import Path

import ollama

from api.util import settings

CORRECTOR_MODEL = "gemma3:4b"
_PROMPT_DIR = Path(__file__).parent / "prompts"

LANG_NAMES = {
    "english": "English",
    "spanish": "Spanish",
    "catalan": "Catalan",
    "chinese": "Chinese",
    "japanese": "Japanese",
}

_prompt_cache: dict[str, str] = {}


def _client() -> ollama.Client:
    return ollama.Client(host=settings.ollama_host)


def _render_prompt(name: str, **tokens: str) -> str:
    template = _prompt_cache.get(name)
    if template is None:
        template = (_PROMPT_DIR / name).read_text(encoding="utf-8")
        _prompt_cache[name] = template
    rendered = template
    for key, value in tokens.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def correct(text: str, language: str, kind: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    lang = LANG_NAMES.get(language, "English")
    unit = "sentence" if kind == "line" else "word"
    grammar = " and grammar" if unit == "sentence" else ""
    prompt = _render_prompt("correct.md", LANG=lang, UNIT=unit, GRAMMAR=grammar, TEXT=text)
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
    prompt = _render_prompt("detect_correct.md", UNIT=unit, GRAMMAR=grammar, TEXT=text)
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
