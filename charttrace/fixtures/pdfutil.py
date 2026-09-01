"""Minimal deterministic PDF-1.4 writer/reader for synthetic fixtures."""

from __future__ import annotations

import re
from typing import Iterable


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(pages: Iterable[str]) -> bytes:
    page_list = list(pages)
    if not page_list:
        raise ValueError("pdf requires at least one page")
    font_id = 3 + len(page_list) * 2
    kids = []
    content_ids = []
    page_ids = []
    next_id = 3
    for _ in page_list:
        page_ids.append(next_id)
        kids.append(f"{next_id} 0 R")
        content_ids.append(next_id + 1)
        next_id += 2

    catalog = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    pages_obj = (
        f"2 0 obj << /Type /Pages /Kids [{' '.join(kids)}] /Count {len(page_list)} >> endobj\n"
    ).encode("ascii")

    chunks: list[bytes] = [catalog, pages_obj]
    for page_id, content_id, text in zip(page_ids, content_ids, page_list):
        stream_body = f"BT /F1 10 Tf 36 756 Td ({_escape(text[:1800])}) Tj ET\n".encode("latin-1", "replace")
        page = (
            f"{page_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >> endobj\n"
        ).encode("ascii")
        contents = (
            f"{content_id} 0 obj << /Length {len(stream_body)} >> stream\n".encode("ascii")
            + stream_body
            + b"endstream\nendobj\n"
        )
        chunks.extend([page, contents])
    font = (
        f"{font_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj\n"
    ).encode("ascii")
    chunks.append(font)

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    running = len(header)
    assembled = [header]
    for chunk in chunks:
        offsets.append(running)
        assembled.append(chunk)
        running += len(chunk)
    xref_pos = running
    n = len(offsets)
    xref = [f"xref\n0 {n}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer << /Size {n} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode("ascii")
    return b"".join(assembled + xref + [trailer])


def extract_text_layers(pdf: bytes) -> list[str]:
    """Best-effort extraction of Tj strings in order (one per page for this writer)."""
    parts = re.findall(rb"BT /F1 10 Tf 36 756 Td \((.*?)\) Tj ET", pdf, flags=re.S)
    out = []
    for raw in parts:
        text = raw.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
        out.append(text.decode("latin-1"))
    return out
