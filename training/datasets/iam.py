from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset

from training.util.charset import Charset


@dataclass(frozen=True)
class IamSample:
    word_id: str
    image_path: Path
    text: str


def word_image_path(word_id: str, words_dir: Path) -> Path:
    prefix = word_id.split("-")[0]
    form_id = "-".join(word_id.split("-")[:2])
    return words_dir / prefix / form_id / f"{word_id}.png"


def form_id_of(word_id: str) -> str:
    return "-".join(word_id.split("-")[:2])


def parse_words(words_txt: Path, words_dir: Path, include_err: bool = False) -> list[IamSample]:
    samples: list[IamSample] = []
    for line in Path(words_txt).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 9:
            continue
        word_id, result = fields[0], fields[1]
        if result != "ok" and not include_err:
            continue
        text = " ".join(fields[8:])
        if not text:
            continue
        path = word_image_path(word_id, words_dir)
        if not path.exists() or path.stat().st_size == 0:
            continue
        samples.append(IamSample(word_id, path, text))
    return samples


def parse_lines(lines_txt: Path, lines_dir: Path, include_err: bool = False) -> list[IamSample]:
    samples: list[IamSample] = []
    for line in Path(lines_txt).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 9:
            continue
        line_id, result = fields[0], fields[1]
        if result != "ok" and not include_err:
            continue
        text = fields[-1].replace("|", " ").strip()
        if not text:
            continue
        path = word_image_path(line_id, lines_dir)
        if not path.exists() or path.stat().st_size == 0:
            continue
        samples.append(IamSample(line_id, path, text))
    return samples


def _writer_of(word_id: str, form_to_writer: dict[str, str]) -> str:
    return form_to_writer.get(form_id_of(word_id), form_id_of(word_id))


def parse_form_writers(forms_txt: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in Path(forms_txt).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) >= 2:
            mapping[fields[0]] = fields[1]
    return mapping


def _bucket(writer: str, seed: int) -> float:
    digest = hashlib.md5(f"{seed}:{writer}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def writer_split(
    samples: Sequence[IamSample],
    forms_txt: Path,
    val_frac: float = 0.1,
    test_frac: float = 0.1,
    seed: int = 0,
) -> dict[str, list[IamSample]]:
    form_to_writer = parse_form_writers(forms_txt)
    splits: dict[str, list[IamSample]] = {"train": [], "val": [], "test": []}
    for s in samples:
        b = _bucket(_writer_of(s.word_id, form_to_writer), seed)
        if b < test_frac:
            splits["test"].append(s)
        elif b < test_frac + val_frac:
            splits["val"].append(s)
        else:
            splits["train"].append(s)
    return splits


class IamWordsDataset(Dataset):
    def __init__(self, samples: Sequence[IamSample], charset: Charset, transform) -> None:
        self.samples = list(samples)
        self.charset = charset
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, str]:
        s = self.samples[index]
        image = Image.open(s.image_path).convert("L")
        tensor = self.transform(image)
        target = torch.tensor(self.charset.encode(s.text), dtype=torch.long)
        return tensor, target, s.text


class IamTrocrDataset(Dataset):
    def __init__(self, samples: Sequence[IamSample], processor, augment, max_target_length: int = 64) -> None:
        self.samples = list(samples)
        self.processor = processor
        self.augment = augment
        self.max_target_length = max_target_length

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, str]:
        s = self.samples[index]
        image = self.augment(Image.open(s.image_path))
        pixel_values = self.processor(images=image, return_tensors="pt").pixel_values.squeeze(0)
        labels = self.processor.tokenizer(
            s.text, truncation=True, max_length=self.max_target_length
        ).input_ids
        return pixel_values, torch.tensor(labels, dtype=torch.long), s.text
