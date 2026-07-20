from __future__ import annotations

import re


def script_guess(text: str) -> str | None:
    """Fast, model-free language guess from the writing system.

    Only resolves scripts that are unambiguous by codepoint; returns None for
    Latin-script text (English/Spanish/Catalan), which needs the LLM to tell apart.
    """
    if re.search(r"[぀-ヿ]", text):  # hiragana / katakana -> Japanese
        return "japanese"
    if re.search(r"[一-鿿]", text):  # Han characters -> Chinese
        return "chinese"
    return None
