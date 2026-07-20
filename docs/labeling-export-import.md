# Labeling data — export / import format

The labeling tool stores collected samples on the server (`datasets/collected/`:
SQLite index + PNG files). Samples come from two places: the **Labeling** tab
(drawn/uploaded words and lines) and the **OCR** tab's **Save to Data** button
(each recognized line saved as its own crop with `language: auto`). Two
endpoints move that data in and out:

- `GET /label/export` → downloads a **`.zip`** of all collected samples.
- `POST /label/import` → merges an uploaded **`.zip`** back into the store.

Both use the **same, strict format** described below. The two are
round-trippable: a file produced by export always imports cleanly.

## Archive layout

A single ZIP containing:

```
labels_export.zip
├── manifest.jsonl          # one JSON object per line (JSON Lines)
└── images/
    └── <language>/
        └── <n>.png         # one PNG per sample, referenced by the manifest
```

## `manifest.jsonl`

One JSON object per line (not a JSON array). One line = one sample.

| field | type | required | notes |
|---|---|---|---|
| `text` | string | yes | The label (the corrected/verified transcription). |
| `image` | string | yes | Path of the PNG **inside the zip**, e.g. `images/english/1.png`. |
| `language` | string | no | `auto` \| `english` \| `spanish` \| `catalan` \| `chinese` \| `japanese`. Default `english`. (`auto` is what the OCR tab's Save-to-Data writes.) |
| `rating` | string | no | `correct` \| `incorrect`. Default `incorrect`. |
| `engine_guess` | string \| null | no | The raw OCR output before correction (metadata). |

Example (`manifest.jsonl`, two samples):

```json
{"text": "hello", "language": "english", "rating": "correct", "engine_guess": "helo", "image": "images/english/1.png"}
{"text": "café", "language": "spanish", "rating": "incorrect", "engine_guess": "cafe", "image": "images/spanish/2.png"}
```

## Images

- Format: **PNG**. Each is the ink-cropped drawing/crop for one sample.
- Location inside the zip must match its manifest line's `image` value exactly.

## Import behavior

- Each manifest line becomes a **new** sample (fresh auto-increment id). Import
  **merges** — it never replaces or deduplicates existing samples.
- Coercion for robustness:
  - `rating` not in {`correct`, `incorrect`} → stored as `incorrect`.
  - `language` that is not purely alphabetic → stored as `english`.
- Response: `{"imported": <count>}`.
- **Rejected with HTTP 400** if the upload is not a zip, or the zip has no
  `manifest.jsonl`. Lines whose `image` is missing from the zip are skipped.

## Examples

Export, then re-import (round trip):

```bash
curl -s http://localhost:8000/label/export -o labels_export.zip
curl -s -F "file=@labels_export.zip;type=application/zip" http://localhost:8000/label/import
# -> {"imported": 12}
```

The multipart field name **must** be `file`. In the UI, the **Import** button
does exactly this: pick a `.zip`, it is uploaded as the `file` field.

## Building an import file from another source

To bring in data that did not come from Export, package it into the same shape:
create the `images/<language>/<name>.png` files, write one `manifest.jsonl` line
per image (with at least `text` and a matching `image` path), and zip the two
together.
