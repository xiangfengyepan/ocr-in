# Engine benchmarks — handwriting recognition (IAM)

Accuracy of the OCR engines on the IAM Handwriting Database. Metrics are **CER**
(character error rate) and **WER** (word error rate) — lower is better. Splits
are writer-independent (train/val/test by writer, seed 0). Status: 2026-07-19.

## Dataset

- **IAM words**: 96,456 `ok`-segmented word crops → split 77,027 train / 9,952 val / 9,475 test.
- **IAM lines**: 11,344 `ok`-segmented lines → split 9,180 train / 1,133 val / 1,031 test.
- Loaders: `training/datasets/iam.py` (`parse_words`, `parse_lines`, `writer_split`).

## Setup

- Python 3.12 (uv), PyTorch 2.11.0+cu128, transformers 4.57, GPU RTX A3000 (6 GB).
- CRNN: trained from scratch (CNN+BiLSTM+CTC), fp16, augmentation, best-CER checkpoint.
- TrOCR: `microsoft/trocr-base-handwritten`; evaluated stock and fine-tuned (Adafactor, warmup).

## Results (IAM test split unless noted)

| Engine | Trained on | Words CER / WER | Lines CER / WER |
|---|---|---|---|
| **Ollama VLM** (`gemma3:4b`, Q4) | — (general VLM) | 47.3% / 61.9% ⁶ | 33.6% / 54.9% ⁶ |
| **Tesseract 5.5** (no AI, CPU) | — (printed-text model) | 79.2% / 118% | 51.8% / 89.3% ⁵ |
| **CRNN** | words | **10.3% / 24.0%** | 43.1% / ~100% ¹ |
| **CRNN** | lines | — | 10.8% / 31.0% ² |
| **TrOCR-base (stock)** | — (pretrained on IAM lines) | 38% / 74% (val) | **2.8% / 7.1%** |
| **TrOCR-base (fine-tuned)** | words | 21% / 26% (val) ³ | — |
| **TrOCR-base (fine-tuned)** | lines | — | 52% / 66% (val) ⁴ |

¹ Word-trained CRNN applied to lines (width 1024, aspect-preserved). At the trained
  width 256 it is 70.7% / ~100%. WER ~100% because a word-trained model never learned
  line-scale word spacing, so words run together.
² Line-CRNN trained from scratch on lines (width 1024, 80 epochs, best epoch 71).
  Val CER 8.9% / WER 27.2%; test CER 10.8% / WER 31.0%. It learned line-scale word
  spacing (unlike the word-CRNN), but at ~4× TrOCR-lines' CER it lost the comparison,
  so the checkpoint was reverted (deleted); TrOCR-base is the line engine.
³ Val, greedy CER 0.25 / `no_repeat_ngram=3` CER 0.21. Best epoch 6.
⁴ Best epoch 2; degraded to 71% by epoch 8 (checkpoint deleted). See key findings.
⁵ Tesseract uses a printed-text model, so on handwriting it is the weakest engine.
  WER > 100% is possible: error rate = edits / reference-length, and edits include
  *insertions*; a noisy multi-token output for a short reference produces more edits
  than the reference has words (e.g. ref "some" → hyp "SO oer ge." = 1 substitution +
  2 insertions = 3 edits over 1 ref word = 300%). Averaged over the set this lands at 118%.
⁶ Ollama `gemma3:4b` (quantized general vision model, not OCR-specialised), n=200 subset
  (VLM inference is slow and serial). Reads many words but lowercases, adds punctuation,
  and hallucinates on ambiguous crops — inflating CER/WER. Better than Tesseract, well
  behind CRNN/TrOCR. A dedicated OCR VLM could do better; model choice revisited in Phase 3.

### CRNN on words — extra detail

- Validation best (epoch 54/60): CER 7.7% / WER 20.2%.
- Test: CER 10.3% / WER 24.0%.

### TrOCR-base (stock) on lines — extra detail

- Validation (n=300): CER 1.4% / WER 3.3%.
- Test (n=1,031): CER 2.8% / WER 7.1% (matches the reported ~2.9%).

## Key findings

1. **Best engine so far: stock TrOCR-base on lines (2.8% CER).** No fine-tuning.
2. **CRNN is the word engine** (10.3% CER on words); TrOCR is the line engine.
   Each is poor at the other's granularity (word-CRNN can't space lines; stock
   TrOCR is off-distribution on isolated words).
3. **Fine-tuning TrOCR-base on *clean* IAM damages it** (lines 2.8% → 52%, words
   worse too). Its pretrained weights are already near-optimal on this clean data;
   aggressive augmentation + LR overwrite them. Fine-tuning / augmentation is for
   **domain adaptation to real scanned PDFs**, not for data that matches pretraining.
4. **Architecture implication (Phase 3):** the searchable-PDF overlay needs per-word
   boxes, but TrOCR wins at line level. The pipeline must reconcile these — e.g.
   detect lines → TrOCR line text → derive word boxes (whitespace split + alignment),
   or use CRNN/Tesseract when word boxes are required.

## Reproduce

```bash
# CRNN
uv run python -m training.train_crnn --out models/crnn/english                 # words
uv run python -m training.train_crnn --level lines --width 1024 --out models/crnn/english_lines
uv run python -m training.eval_crnn  --split test [--level lines --width 1024]

# TrOCR
uv run python -m training.train_trocr --model microsoft/trocr-base-handwritten [--level lines]
uv run python -m training.eval_trocr --split test --level lines --ckpt microsoft/trocr-base-handwritten
```
