from __future__ import annotations

from pathlib import Path

import ollama

from api.inference.language_detect import script_guess
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


def _build_hint(language: str, text: str) -> tuple[str, str | None]:
    """Return (hint_text, resolved_hint_language). A null hint (auto) yields None."""
    if language in LANG_NAMES:
        return (
            f'The text is expected to be in {LANG_NAMES[language]}, but treat this ONLY as a hint '
            f"to help read ambiguous characters — if it is clearly another language, keep it as-is.",
            language,
        )
    scripted = script_guess(text)
    if scripted:
        return (f"The text is written in {LANG_NAMES[scripted]}.", scripted)
    return ("The language is not given — determine which language the text is actually written in.", None)


def correct(text: str, language: str, kind: str) -> tuple[str, str]:
    """Correct OCR output. Returns (corrected_text, language).

    `language` is one of the supported codes or "auto". In auto mode the hint is
    null and the model identifies the language itself (with a fast script check
    for Japanese/Chinese first).
    """
    text = (text or "").strip()
    default_lang = language if language in LANG_NAMES else "english"
    if not text:
        return text, default_lang

    unit = "sentence" if kind == "line" else "word"
    grammar = " and grammar" if unit == "sentence" else ""
    is_auto = language not in LANG_NAMES
    hint_text, hint_lang = _build_hint(language, text)
    prompt = _render_prompt("correct.md", HINT=hint_text, UNIT=unit, GRAMMAR=grammar, TEXT=text)

    try:
        resp = _client().generate(
            model=CORRECTOR_MODEL,
            prompt=prompt,
            options={"temperature": 0, "num_predict": 96},
        )
        raw = resp["response"]
        corrected: str | None = None
        reported: str | None = None
        for line in raw.splitlines():
            stripped = line.strip()
            low = stripped.lower()
            if low.startswith("lang:"):
                value = stripped.split(":", 1)[1].strip().lower()
                if value in LANG_NAMES:
                    reported = value
            elif low.startswith("text:"):
                corrected = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        if corrected is None:
            fallback = [
                ln.strip() for ln in raw.strip().splitlines()
                if ln.strip() and not ln.strip().lower().startswith("lang:")
            ]
            corrected = fallback[0].strip('"').strip("'") if fallback else text

        language_out = (hint_lang or reported or "english") if is_auto else language
        return corrected, language_out
    except Exception:
        return text, default_lang
