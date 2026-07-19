from __future__ import annotations

import argparse
from multiprocessing import Pool
from pathlib import Path

import pytesseract
from PIL import Image

from training.datasets.iam import parse_lines, parse_words, writer_split
from training.eval.metrics import cer, wer

REPO_ROOT = Path(__file__).resolve().parents[1]

PSM = {"words": 8, "lines": 7}


def _ocr(job: tuple[Path, str, int]) -> str:
    path, lang, psm = job
    image = Image.open(path).convert("L")
    text = pytesseract.image_to_string(image, lang=lang, config=f"--psm {psm}")
    return " ".join(text.split())


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate Tesseract (CPU) on an IAM split")
    p.add_argument("--data-root", type=Path, default=REPO_ROOT / "datasets")
    p.add_argument("--level", choices=["words", "lines"], default="words")
    p.add_argument("--split", choices=["train", "val", "test"], default="test")
    p.add_argument("--lang", type=str, default="eng")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--val-frac", type=float, default=0.1)
    p.add_argument("--test-frac", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.level == "lines":
        samples = parse_lines(args.data_root / "ascii" / "lines.txt", args.data_root / "lines")
    else:
        samples = parse_words(args.data_root / "ascii" / "words.txt", args.data_root / "words")
    split = writer_split(
        samples, args.data_root / "ascii" / "forms.txt", args.val_frac, args.test_frac, args.seed
    )[args.split]
    if args.limit:
        split = split[: args.limit]
    psm = PSM[args.level]
    jobs = [(s.image_path, args.lang, psm) for s in split]
    with Pool(args.workers) as pool:
        hyps = pool.map(_ocr, jobs)
    refs = [s.text for s in split]
    print(
        f"tesseract {args.level} {args.split}: n={len(refs)} "
        f"CER {cer(refs, hyps):.4f} WER {wer(refs, hyps):.4f}"
    )
    for r, h in list(zip(refs, hyps, strict=False))[:8]:
        print(f"    ref={r!r} hyp={h!r}")


if __name__ == "__main__":
    main()
