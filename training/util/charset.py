from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path

BLANK = 0


class Charset:
    def __init__(self, chars: Sequence[str]) -> None:
        if BLANK != 0:
            raise ValueError("blank index must be 0")
        self.chars = list(chars)
        self.stoi = {c: i + 1 for i, c in enumerate(self.chars)}
        self.itos = {i + 1: c for i, c in enumerate(self.chars)}

    @property
    def num_classes(self) -> int:
        return len(self.chars) + 1

    def encode(self, text: str) -> list[int]:
        return [self.stoi[c] for c in text if c in self.stoi]

    def decode_greedy(self, indices: Iterable[int]) -> str:
        out: list[str] = []
        prev = BLANK
        for idx in indices:
            if idx != prev and idx != BLANK:
                out.append(self.itos.get(idx, ""))
            prev = idx
        return "".join(out)

    @classmethod
    def from_texts(cls, texts: Iterable[str]) -> Charset:
        chars = sorted({c for t in texts for c in t})
        return cls(chars)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.chars, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> Charset:
        chars = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(chars)
