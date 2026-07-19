from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from transformers.optimization import Adafactor, get_linear_schedule_with_warmup

from training.augmentation.transforms import TrocrAugment
from training.datasets.iam import IamTrocrDataset, parse_lines, parse_words, writer_split
from training.eval.metrics import cer, wer
from training.util.collate import trocr_collate

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_samples(data_root: Path, level: str):
    if level == "lines":
        return parse_lines(data_root / "ascii" / "lines.txt", data_root / "lines")
    return parse_words(data_root / "ascii" / "words.txt", data_root / "words")


def build_loaders(args, processor) -> tuple[DataLoader, DataLoader]:
    samples = load_samples(args.data_root, args.level)
    if args.limit:
        samples = samples[: args.limit]
    splits = writer_split(
        samples, args.data_root / "ascii" / "forms.txt", args.val_frac, args.test_frac, args.seed
    )
    max_len = 128 if args.level == "lines" else 64
    train_ds = IamTrocrDataset(splits["train"], processor, TrocrAugment(train=True), max_len)
    val_ds = IamTrocrDataset(splits["val"], processor, TrocrAugment(train=False), max_len)
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=trocr_collate,
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=trocr_collate,
        pin_memory=True,
    )
    print(f"samples: train={len(train_ds)} val={len(val_ds)}")
    return train_loader, val_loader


@torch.no_grad()
def evaluate(model, loader, processor, device, max_new_tokens) -> dict:
    model.eval()
    refs: list[str] = []
    hyps: list[str] = []
    for pixel_values, _, texts in loader:
        generated = model.generate(pixel_values.to(device), max_new_tokens=max_new_tokens)
        decoded = processor.batch_decode(generated, skip_special_tokens=True)
        hyps.extend(d.strip() for d in decoded)
        refs.extend(texts)
    samples = list(zip(refs[:5], hyps[:5], strict=False))
    return {"cer": cer(refs, hyps), "wer": wer(refs, hyps), "samples": samples}


def train(args) -> None:
    device = args.device
    torch.manual_seed(args.seed)
    processor = TrOCRProcessor.from_pretrained(args.model)
    train_loader, val_loader = build_loaders(args, processor)

    model = VisionEncoderDecoderModel.from_pretrained(args.model)
    model.config.decoder_start_token_id = model.generation_config.decoder_start_token_id
    model.config.eos_token_id = model.generation_config.eos_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size
    if args.freeze_encoder:
        for p in model.encoder.parameters():
            p.requires_grad = False
    model.to(device)
    if args.grad_checkpointing:
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    params = [p for p in model.parameters() if p.requires_grad]
    if args.optimizer == "adafactor":
        optimizer = Adafactor(
            params, lr=args.lr, scale_parameter=False, relative_step=False, warmup_init=False
        )
    else:
        optimizer = torch.optim.AdamW(params, lr=args.lr)
    steps_per_epoch = max(1, len(train_loader) // args.grad_accum)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, args.warmup_steps, steps_per_epoch * args.epochs
    )
    use_amp = device.startswith("cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    args.out.mkdir(parents=True, exist_ok=True)
    best_cer = float("inf")

    for epoch in range(1, args.epochs + 1):
        model.train()
        optimizer.zero_grad()
        running = 0.0
        for step, (pixel_values, labels, _) in enumerate(train_loader, start=1):
            pixel_values = pixel_values.to(device)
            labels = labels.to(device)
            with torch.amp.autocast("cuda", enabled=use_amp):
                loss = model(pixel_values=pixel_values, labels=labels).loss / args.grad_accum
            scaler.scale(loss).backward()
            running += loss.item() * args.grad_accum
            if step % args.grad_accum == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad()
            if step % args.log_every == 0:
                print(f"epoch {epoch} step {step} loss {running / step:.4f}")

        metrics = evaluate(model, val_loader, processor, device, args.max_new_tokens)
        print(f"epoch {epoch} val CER {metrics['cer']:.4f} WER {metrics['wer']:.4f}")
        for ref, hyp in metrics["samples"]:
            print(f"    ref={ref!r} hyp={hyp!r}")
        if metrics["cer"] < best_cer:
            best_cer = metrics["cer"]
            model.save_pretrained(args.out)
            processor.save_pretrained(args.out)
            (args.out / "meta.json").write_text(
                json.dumps({"epoch": epoch, "cer": metrics["cer"], "wer": metrics["wer"]})
            )
            print(f"saved best (CER {best_cer:.4f}) -> {args.out}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fine-tune TrOCR on IAM words")
    p.add_argument("--data-root", type=Path, default=REPO_ROOT / "datasets")
    p.add_argument("--out", type=Path, default=REPO_ROOT / "models" / "trocr" / "english")
    p.add_argument("--model", type=str, default="microsoft/trocr-small-handwritten")
    p.add_argument("--level", choices=["words", "lines"], default="words")
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--optimizer", choices=["adamw", "adafactor"], default="adamw")
    p.add_argument("--warmup-steps", type=int, default=500)
    p.add_argument("--freeze-encoder", action="store_true")
    p.add_argument("--clip", type=float, default=1.0)
    p.add_argument("--num-workers", type=int, default=8)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--val-frac", type=float, default=0.1)
    p.add_argument("--test-frac", type=float, default=0.1)
    p.add_argument("--max-new-tokens", type=int, default=32)
    p.add_argument("--log-every", type=int, default=100)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--grad-checkpointing", action="store_true")
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


if __name__ == "__main__":
    train(parse_args())
