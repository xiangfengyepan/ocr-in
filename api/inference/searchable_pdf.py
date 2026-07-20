from __future__ import annotations

import fitz  # PyMuPDF


def build_searchable_pdf(image_bytes: bytes, width: int, height: int, lines: list[dict]) -> bytes:
    """Build a searchable PDF: the page image + an invisible, selectable text layer.

    Each line's text is placed (render_mode 3 = invisible) at its box, so the PDF
    is selectable and Ctrl+F searchable while showing the original image.
    """
    doc = fitz.open()
    page = doc.new_page(width=float(width), height=float(height))
    page.insert_image(fitz.Rect(0, 0, width, height), stream=image_bytes)
    for line in lines:
        text = (line.get("text") or "").strip()
        if not text:
            continue
        x0, y0, x1, y1 = (float(v) for v in line["box"])
        fontsize = (y1 - y0) * 0.75
        # cap so the whole line fits the box width (avg glyph width ~0.5*fontsize)
        width_fit = (x1 - x0) / (0.5 * max(len(text), 1))
        fontsize = max(4.0, min(fontsize, width_fit))
        # baseline near the bottom of the box; invisible (render_mode=3) but extractable
        page.insert_text((x0, y1 - (y1 - y0) * 0.15), text, fontsize=fontsize, render_mode=3)
    data = doc.tobytes()
    doc.close()
    return data
