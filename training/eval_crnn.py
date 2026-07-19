from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from training.augmentation.transforms import IMG_HEIGHT, IMG_WIDTH, Preprocess
from training.datasets.iam import IamWordsDataset, parse_words, writer_split
from training.models import CRNN
from training.train_crnn import evaluate
from training.util.charset import Charset
from training.util.collate import ctc_collate

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate a trained CRNN on an IAM split")
    p.add_argument("--data-root", type=Path, default=REPO_ROOT / "datasets")
    p.add_argument("--ckpt", type=Path, default=REPO_ROOT / "models" / "crnn" / "english")
    p.add_argument("--split", choices=["train", "val", "test"], default="test")
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--num-workers", type=int, default=12)
    p.add_argument("--val-frac", type=float, default=0.1)
    p.add_argument("--test-frac", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    charset = Charset.load(args.ckpt / "charset.json")
    samples = parse_words(args.data_root / "ascii" / "words.txt", args.data_root / "words")
    splits = writer_split(
        samples, args.data_root / "ascii" / "forms.txt", args.val_frac, args.test_frac, args.seed
    )
    dataset = IamWordsDataset(
        splits[args.split], charset, Preprocess(IMG_HEIGHT, IMG_WIDTH, train=False)
    )
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=ctc_collate,
        pin_memory=True,
    )
    model = CRNN(charset.num_classes).to(args.device)
    model.load_state_dict(torch.load(args.ckpt / "model.pt", map_location=args.device))
    metrics = evaluate(model, loader, charset, args.device)
    print(f"{args.split}: n={len(dataset)} CER {metrics['cer']:.4f} WER {metrics['wer']:.4f}")
    for ref, hyp in metrics["samples"]:
        print(f"    ref={ref!r} hyp={hyp!r}")


if __name__ == "__main__":
    main()
