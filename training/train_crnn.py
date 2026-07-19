from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from training.augmentation.transforms import IMG_HEIGHT, IMG_WIDTH, Preprocess
from training.datasets.iam import IamWordsDataset, parse_lines, parse_words, writer_split
from training.eval.metrics import cer, wer
from training.models import CRNN, greedy_decode
from training.util.charset import Charset
from training.util.collate import ctc_collate

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_loaders(args) -> tuple[DataLoader, DataLoader, Charset]:
    if args.level == "lines":
        samples = parse_lines(args.data_root / "ascii" / "lines.txt", args.data_root / "lines")
    else:
        samples = parse_words(args.data_root / "ascii" / "words.txt", args.data_root / "words")
    if args.limit:
        samples = samples[: args.limit]
    splits = writer_split(
        samples, args.data_root / "ascii" / "forms.txt", args.val_frac, args.test_frac, args.seed
    )
    charset = Charset.from_texts(s.text for s in splits["train"])
    train_ds = IamWordsDataset(
        splits["train"], charset, Preprocess(args.height, args.width, train=True)
    )
    val_ds = IamWordsDataset(
        splits["val"], charset, Preprocess(args.height, args.width, train=False)
    )
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=ctc_collate,
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=ctc_collate,
        pin_memory=True,
    )
    print(f"samples: train={len(train_ds)} val={len(val_ds)} classes={charset.num_classes}")
    return train_loader, val_loader, charset


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, charset: Charset, device: str) -> dict:
    model.eval()
    refs: list[str] = []
    hyps: list[str] = []
    for images, _, _, texts in loader:
        log_probs = model(images.to(device))
        hyps.extend(greedy_decode(log_probs.cpu(), charset))
        refs.extend(texts)
    samples = list(zip(refs[:5], hyps[:5], strict=False))
    return {"cer": cer(refs, hyps), "wer": wer(refs, hyps), "samples": samples}


def train(args) -> None:
    device = args.device
    torch.manual_seed(args.seed)
    train_loader, val_loader, charset = build_loaders(args)

    model = CRNN(charset.num_classes).to(device)
    criterion = nn.CTCLoss(blank=0, zero_infinity=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    use_amp = device.startswith("cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    args.out.mkdir(parents=True, exist_ok=True)
    charset.save(args.out / "charset.json")
    best_cer = float("inf")

    for epoch in range(1, args.epochs + 1):
        model.train()
        optimizer.zero_grad()
        running = 0.0
        for step, (images, targets, target_lengths, _) in enumerate(train_loader, start=1):
            images = images.to(device)
            with torch.amp.autocast("cuda", enabled=use_amp):
                log_probs = model(images)
                input_lengths = torch.full(
                    (images.size(0),), log_probs.size(0), dtype=torch.long
                )
                loss = criterion(log_probs, targets, input_lengths, target_lengths)
                loss = loss / args.grad_accum
            scaler.scale(loss).backward()
            running += loss.item() * args.grad_accum
            if step % args.grad_accum == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
            if step % args.log_every == 0:
                print(f"epoch {epoch} step {step} loss {running / step:.4f}")

        metrics = evaluate(model, val_loader, charset, device)
        print(f"epoch {epoch} val CER {metrics['cer']:.4f} WER {metrics['wer']:.4f}")
        for ref, hyp in metrics["samples"]:
            print(f"    ref={ref!r} hyp={hyp!r}")
        if metrics["cer"] < best_cer:
            best_cer = metrics["cer"]
            torch.save(model.state_dict(), args.out / "model.pt")
            (args.out / "meta.json").write_text(
                json.dumps(
                    {
                        "epoch": epoch,
                        "cer": metrics["cer"],
                        "wer": metrics["wer"],
                        "num_classes": charset.num_classes,
                    }
                )
            )
            print(f"saved best (CER {best_cer:.4f}) -> {args.out}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train CRNN on IAM words")
    p.add_argument("--data-root", type=Path, default=REPO_ROOT / "datasets")
    p.add_argument("--out", type=Path, default=REPO_ROOT / "models" / "crnn" / "english")
    p.add_argument("--level", choices=["words", "lines"], default="words")
    p.add_argument("--height", type=int, default=IMG_HEIGHT)
    p.add_argument("--width", type=int, default=IMG_WIDTH)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--grad-accum", type=int, default=1)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--clip", type=float, default=5.0)
    p.add_argument("--num-workers", type=int, default=8)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--val-frac", type=float, default=0.1)
    p.add_argument("--test-frac", type=float, default=0.1)
    p.add_argument("--log-every", type=int, default=50)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument(
        "--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu"
    )
    return p.parse_args()


if __name__ == "__main__":
    train(parse_args())
