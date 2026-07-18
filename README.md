# ocr-in

OCR of handwritten PDFs into **searchable PDFs** (original page image preserved +
invisible, selectable text layer) plus a plain-text export. Accuracy comes from
deep-learning handwriting recognition, a fine-tuning pipeline, and an
active-learning labeling tool.

See `PLAN.md` for the full design, `TODO.md` for progress, and `RULE.md` for the
development rules. `CLAUDE.md` holds project context for future sessions.

## Layout

```
api/       FastAPI, engine layer, inference pipeline, model registry
training/  PyTorch/HF training + eval, dataset loaders, augmentation
app/       Angular SPA (OCR app + labeling app)
models/    checkpoints / registry storage
datasets/  raw + labeled data
docs/      additional design notes
```

## Development environment

System Python is 3.14 (no PyTorch wheels yet), so the Python stack runs on an
isolated **Python 3.12** provisioned by [uv](https://docs.astral.sh/uv/).

```bash
uv sync                       # create .venv and install all dependencies
uv run uvicorn api.main:app --reload --port 8000   # run the API
uv run pytest                 # run tests
```

PyTorch is installed from the CUDA 12.8 wheel index (compatible with the
server's CUDA 13.2 driver). The frontend lives in `app/` (Angular, latest).
