# Handwriting OCR

Turn handwritten pages into **searchable PDFs** and clean text. Upload an image
or PDF; the app detects the lines, reads the handwriting with a deep-learning
model, optionally cleans up the text with a local language model, and lets you
select, edit, and export the result — as a **PDF whose text is selectable and
Ctrl+F searchable** on top of the original page image.

It also includes a labeling tool so you can correct results and use them to
improve the models over time.

## Features

- **Image/PDF → text** with automatic line detection and handwriting
  recognition.
- **Selectable, editable overlay** — the recognized text sits directly on the
  image (Microsoft-style); click any line to fix it.
- **Optional AI correction** — toggle between the raw reading and a
  grammar/spelling-corrected version (runs locally, no cloud).
- **Searchable PDF export** — original page image + an invisible, searchable
  text layer.
- **Labeling & review tools** — rate results Correct/Incorrect, fast-review a
  queue of pending items, and browse/edit everything in a Data tab.

## Prerequisites

| Requirement | Notes |
|---|---|
| **Linux** (Ubuntu recommended) | Developed/tested on Ubuntu. |
| **NVIDIA GPU, ~6 GB VRAM** | Strongly recommended. Runs on CPU but much slower. |
| **[uv](https://docs.astral.sh/uv/)** | Manages the Python 3.12 environment (system Python can be newer). |
| **Node.js 20+ and npm** | To build/run the web app (Angular). |
| **[Ollama](https://ollama.com/)** | Powers the optional text correction. Pull the model below. |

The first run downloads the handwriting model automatically (needs internet
once).

## Setup

**1. Backend (API)**

```bash
uv sync                       # creates .venv and installs Python dependencies
```

**2. Correction model (Ollama)**

```bash
ollama pull gemma3:4b         # ~3.3 GB; used for the optional text correction
```

**3. Frontend (web app)**

```bash
cd app
npm install
```

## Running

Open two terminals.

**API** (from the project root):

```bash
uv run uvicorn api.main:app --port 8000
```

**Web app** (from `app/`):

```bash
npm start                     # serves the app at http://localhost:4200
```

Then open **http://localhost:4200** in your browser.

> If Ollama is not running or the model isn't pulled, everything works except
> the correction step. Start it with `ollama serve` (or the Ollama app).

## Using the app

- **OCR** — upload/drag/paste an image, click **Recognize**. Select or edit text
  on the image, toggle **Original / Corrected**, **Copy all**, or **Export
  searchable PDF**. **Save to Data** keeps the lines for later model training.
- **Labeling** — draw or upload a single word/line, get a guess, and mark it
  Correct/Incorrect (typing the fix when it's wrong).
- **Data** — browse everything you've labeled, filter and search, edit or delete
  samples, and import/export the dataset.
- **Models** — see the available recognition models and their accuracy.

## Configuration

The web app reads its backend URL from `app/public/config.json`:

```json
{ "apiBase": "http://localhost:8000" }
```

Change `apiBase` to point the app at an API running elsewhere. No rebuild is
required for a deployed site — just edit the served `config.json`.

## Troubleshooting

- **Recognition fails / "is the API running?"** — confirm the API terminal is up
  on port 8000 and reachable at the `apiBase` above.
- **Correction does nothing** — Ollama isn't running or `gemma3:4b` isn't pulled
  (see Setup step 2). Recognition still works without it.
- **First recognition is slow** — the model loads on first use (~10–20 s), then
  subsequent runs are fast.
