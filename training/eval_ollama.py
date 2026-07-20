from __future__ import annotations

import argparse
import base64
from pathlib import Path

import ollama

from training.datasets.iam import parse_lines, parse_words, writer_split
from training.eval.metrics import cer, wer

REPO_ROOT = Path(__file__).resolve().parents[1]

PROMPT = {
    "words": (
        "Transcribe the single handwritten word in this image. "
        "Output only the word itself, with no quotes, labels, or explanation."
    ),
    "lines": (
        "Transcribe the handwritten text line in this image exactly. "
        "Output only the transcription on one line, with no quotes, labels, or explanation."
    ),
}


def _clean(response: str) -> str:
    text = response.strip().splitlines()[0] if response.strip() else ""
    return text.strip().strip('"').strip("'").strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate an Ollama vision model on an IAM split")
    p.add_argument("--data-root", type=Path, default=REPO_ROOT / "datasets")
    p.add_argument("--level", choices=["words", "lines"], default="words")
    p.add_argument("--split", choices=["train", "val", "test"], default="test")
    p.add_argument("--model", type=str, default="gemma3:4b")
    p.add_argument("--host", type=str, default="http://localhost:11434")
    p.add_argument("--limit", type=int, default=200)
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

    client = ollama.Client(host=args.host)
    refs: list[str] = []
    hyps: list[str] = []
    errors = 0
    for i, s in enumerate(split, start=1):
        img_b64 = base64.b64encode(s.image_path.read_bytes()).decode()
        try:
            resp = client.generate(model=args.model, prompt=PROMPT[args.level], images=[img_b64])
            hyps.append(_clean(resp["response"]))
        except Exception as exc:
            errors += 1
            hyps.append("")
            print(f"  [error {i}] {str(exc)[:100]}", flush=True)
        refs.append(s.text)
        if i % 25 == 0:
            print(f"  {args.level} {i}/{len(split)} (errors={errors})", flush=True)
    print(
        f"ollama_vlm ({args.model}) {args.level} {args.split}: n={len(refs)} "
        f"CER {cer(refs, hyps):.4f} WER {wer(refs, hyps):.4f}"
    )
    for r, h in list(zip(refs, hyps, strict=False))[:8]:
        print(f"    ref={r!r} hyp={h!r}")


if __name__ == "__main__":
    main()
