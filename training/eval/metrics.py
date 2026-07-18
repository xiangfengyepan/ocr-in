from __future__ import annotations

from collections.abc import Sequence

import jiwer


def cer(references: Sequence[str], hypotheses: Sequence[str]) -> float:
    refs = [r if r else " " for r in references]
    return float(jiwer.cer(refs, list(hypotheses)))


def wer(references: Sequence[str], hypotheses: Sequence[str]) -> float:
    refs = [r if r else " " for r in references]
    return float(jiwer.wer(refs, list(hypotheses)))
