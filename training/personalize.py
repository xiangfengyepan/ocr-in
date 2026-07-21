from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from training.eval.metrics import cer, wer

OnEpoch = Callable[[int], None] | None

STOCK_TROCR = "microsoft/trocr-base-handwritten"

TROCR_GRAD_ACCUM = 8
TROCR_MAX_TARGET_LEN = 128
TROCR_LR = 5e-5
CRNN_BATCH_SIZE = 8
CRNN_LR = 3e-4


@dataclass(frozen=True)
class _Row:
    image_path: str
    text: str


def _rows_to_samples(rows: list[dict]) -> list[_Row]:
    return [_Row(str(r["image"]), r["text"]) for r in rows]


def train_from_rows(
    kind: str, rows: list[dict], out_dir: Path, epochs: int = 8, on_epoch: OnEpoch = None
) -> None:
    out_dir = Path(out_dir)
    if kind == "line":
        _train_trocr(rows, out_dir, epochs, on_epoch)
    elif kind == "word":
        _train_crnn(rows, out_dir, epochs, on_epoch)
    else:
        raise ValueError(f"unknown kind: {kind!r}")


def eval_rows(kind: str, weights: Path | None, rows: list[dict]) -> dict:
    if kind == "line":
        return _eval_trocr(weights, rows)
    if kind == "word":
        return _eval_crnn(weights, rows)
    raise ValueError(f"unknown kind: {kind!r}")


def _train_trocr(rows: list[dict], out_dir: Path, epochs: int, on_epoch: OnEpoch = None) -> None:
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    import torch
    from torch.utils.data import DataLoader
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    from transformers.optimization import Adafactor

    from training.augmentation.transforms import TrocrAugment
    from training.datasets.iam import IamTrocrDataset
    from training.util.collate import trocr_collate

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = TrOCRProcessor.from_pretrained(STOCK_TROCR)
    model = VisionEncoderDecoderModel.from_pretrained(STOCK_TROCR)
    model.config.decoder_start_token_id = model.generation_config.decoder_start_token_id
    model.config.eos_token_id = model.generation_config.eos_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size
    model.to(device)

    dataset = IamTrocrDataset(
        _rows_to_samples(rows), processor, TrocrAugment(train=True), TROCR_MAX_TARGET_LEN
    )
    loader = DataLoader(
        dataset,
        batch_size=1,
        shuffle=True,
        num_workers=0,
        collate_fn=trocr_collate,
        drop_last=True,
    )

    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = Adafactor(
        params, lr=TROCR_LR, scale_parameter=False, relative_step=False, warmup_init=False
    )
    use_amp = device.startswith("cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        for step, (pixel_values, labels, _texts) in enumerate(loader, start=1):
            pixel_values = pixel_values.to(device)
            labels = labels.to(device)
            with torch.amp.autocast("cuda", enabled=use_amp):
                loss = model(pixel_values=pixel_values, labels=labels).loss / TROCR_GRAD_ACCUM
            scaler.scale(loss).backward()
            if step % TROCR_GRAD_ACCUM == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
        if on_epoch is not None:
            on_epoch(epoch + 1)

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    processor.save_pretrained(out_dir)


def _eval_trocr(weights: Path | None, rows: list[dict]) -> dict:
    import torch
    from PIL import Image
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    source = str(weights) if weights else STOCK_TROCR
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = TrOCRProcessor.from_pretrained(source)
    model = VisionEncoderDecoderModel.from_pretrained(source).to(device).eval()

    refs: list[str] = []
    hyps: list[str] = []
    with torch.no_grad():
        for row in rows:
            image = Image.open(row["image"]).convert("RGB")
            pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)
            generated = model.generate(pixel_values, max_new_tokens=TROCR_MAX_TARGET_LEN)
            hyps.append(processor.batch_decode(generated, skip_special_tokens=True)[0].strip())
            refs.append(row["text"])
    return {"cer": cer(refs, hyps), "wer": wer(refs, hyps)}


def _train_crnn(rows: list[dict], out_dir: Path, epochs: int, on_epoch: OnEpoch = None) -> None:
    import json

    import torch
    from torch import nn
    from torch.utils.data import DataLoader

    from training.augmentation.transforms import IMG_HEIGHT, IMG_WIDTH, Preprocess
    from training.datasets.iam import IamWordsDataset
    from training.models import CRNN
    from training.util.charset import Charset
    from training.util.collate import ctc_collate

    device = "cuda" if torch.cuda.is_available() else "cpu"
    charset = Charset.from_texts(r["text"] for r in rows)
    dataset = IamWordsDataset(
        _rows_to_samples(rows), charset, Preprocess(IMG_HEIGHT, IMG_WIDTH, train=True)
    )
    loader = DataLoader(
        dataset,
        batch_size=CRNN_BATCH_SIZE,
        shuffle=True,
        num_workers=0,
        collate_fn=ctc_collate,
        drop_last=True,
    )

    model = CRNN(charset.num_classes).to(device)
    criterion = nn.CTCLoss(blank=0, zero_infinity=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=CRNN_LR)
    use_amp = device.startswith("cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        for images, targets, target_lengths, _texts in loader:
            images = images.to(device)
            with torch.amp.autocast("cuda", enabled=use_amp):
                log_probs = model(images)
                input_lengths = torch.full(
                    (images.size(0),), log_probs.size(0), dtype=torch.long
                )
                loss = criterion(log_probs, targets, input_lengths, target_lengths)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad()
        if on_epoch is not None:
            on_epoch(epoch + 1)

    out_dir.mkdir(parents=True, exist_ok=True)
    charset.save(out_dir / "charset.json")
    torch.save(model.state_dict(), out_dir / "model.pt")
    (out_dir / "meta.json").write_text(json.dumps({"num_classes": charset.num_classes}))


def _eval_crnn(weights: Path | None, rows: list[dict]) -> dict:
    import torch
    from PIL import Image

    from training.augmentation.transforms import IMG_HEIGHT, IMG_WIDTH, Preprocess
    from training.models import CRNN, greedy_decode
    from training.util.charset import Charset

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if weights:
        weights = Path(weights)
        charset = Charset.load(weights / "charset.json")
        model = CRNN(charset.num_classes)
        model.load_state_dict(torch.load(weights / "model.pt", map_location=device))
    else:
        charset = Charset.from_texts(r["text"] for r in rows)
        model = CRNN(charset.num_classes)
    model.to(device).eval()
    preprocess = Preprocess(IMG_HEIGHT, IMG_WIDTH, train=False)

    refs: list[str] = []
    hyps: list[str] = []
    with torch.no_grad():
        for row in rows:
            image = Image.open(row["image"]).convert("L")
            x = preprocess(image).unsqueeze(0).to(device)
            log_probs = model(x)
            hyps.append(greedy_decode(log_probs.cpu(), charset)[0])
            refs.append(row["text"])
    return {"cer": cer(refs, hyps), "wer": wer(refs, hyps)}
