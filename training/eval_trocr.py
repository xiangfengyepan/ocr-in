from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from training.augmentation.transforms import TrocrAugment
from training.datasets.iam import IamTrocrDataset, parse_lines, parse_words, writer_split
from training.eval.metrics import cer, wer
from training.util.collate import trocr_collate

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate a TrOCR checkpoint on an IAM split")
    p.add_argument("--data-root", type=Path, default=REPO_ROOT / "datasets")
    p.add_argument("--ckpt", type=Path, default=REPO_ROOT / "models" / "trocr" / "english")
    p.add_argument("--split", choices=["train", "val", "test"], default="test")
    p.add_argument("--level", choices=["words", "lines"], default="words")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--num-workers", type=int, default=8)
    p.add_argument("--max-new-tokens", type=int, default=32)
    p.add_argument("--no-repeat-ngram-size", type=int, default=0)
    p.add_argument("--num-beams", type=int, default=1)
    p.add_argument("--val-frac", type=float, default=0.1)
    p.add_argument("--test-frac", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    processor = TrOCRProcessor.from_pretrained(args.ckpt)
    model = VisionEncoderDecoderModel.from_pretrained(args.ckpt).to(args.device).eval()
    if args.level == "lines":
        samples = parse_lines(args.data_root / "ascii" / "lines.txt", args.data_root / "lines")
    else:
        samples = parse_words(args.data_root / "ascii" / "words.txt", args.data_root / "words")
    split = writer_split(
        samples, args.data_root / "ascii" / "forms.txt", args.val_frac, args.test_frac, args.seed
    )[args.split]
    if args.limit:
        split = split[: args.limit]
    ds = IamTrocrDataset(split, processor, TrocrAugment(train=False))
    loader = DataLoader(
        ds,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        collate_fn=trocr_collate,
        pin_memory=True,
    )
    gen_kwargs = {"max_new_tokens": args.max_new_tokens, "num_beams": args.num_beams}
    if args.no_repeat_ngram_size:
        gen_kwargs["no_repeat_ngram_size"] = args.no_repeat_ngram_size

    refs: list[str] = []
    hyps: list[str] = []
    with torch.no_grad():
        for pixel_values, _, texts in loader:
            generated = model.generate(pixel_values.to(args.device), **gen_kwargs)
            hyps.extend(h.strip() for h in processor.batch_decode(generated, skip_special_tokens=True))
            refs.extend(texts)
    print(
        f"{args.split}: n={len(refs)} CER {cer(refs, hyps):.4f} WER {wer(refs, hyps):.4f} "
        f"(no_repeat={args.no_repeat_ngram_size} beams={args.num_beams})"
    )
    for r, h in list(zip(refs, hyps, strict=False))[:8]:
        print(f"    ref={r!r} hyp={h!r}")


if __name__ == "__main__":
    main()
