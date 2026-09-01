"""Deterministic PDF-1.4 writer for synthetic ChartTrace fixtures.

Stdlib only. This writer exists so the oracle can emit exact, hashable
page-bearing originals without a third-party PDF library.
"""

from __future__ import annotations


def escape_pdf_literal(text: str) -> bytes:
    cleaned = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )
    return cleaned.encode("latin-1", errors="replace")


def _content_stream(text: str) -> bytes:
    literal = escape_pdf_literal(text)
    return b"BT /F1 9 Tf 36 750 Td (" + literal + b") Tj ET\n"


def build_pdf(page_texts: tuple[str, ...]) -> bytes:
    """Build a one-font, one-line-per-page PDF. Page count is len(page_texts)."""

    if not page_texts:
        raise ValueError("PDF requires at least one page")
    page_count = len(page_texts)
    font_id = 3 + (2 * page_count)
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    }
    kid_refs = " ".join(f"{3 + index} 0 R" for index in range(page_count))
    objects[2] = f"<< /Type /Pages /Count {page_count} /Kids [{kid_refs}] >>".encode("ascii")
    for index, text in enumerate(page_texts):
        page_id = 3 + index
        content_id = 3 + page_count + index
        stream = _content_stream(text)
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        ).encode("ascii")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"endstream"
        )

    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for obj_id in range(1, font_id + 1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{obj_id} 0 obj\n".encode("ascii") + objects[obj_id] + b"\nendobj\n")
    xref_at = sum(len(part) for part in parts)
    xref = [f"xref\n0 {font_id + 1}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for obj_id in range(1, font_id + 1):
        xref.append(f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer\n<< /Size {font_id + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode("ascii")
    return b"".join(parts + xref + [trailer])


def pdf_page_count(content: bytes) -> int:
    marker = b"/Type /Pages /Count "
    start = content.find(marker)
    if start < 0:
        raise ValueError("PDF is missing a Pages count")
    start += len(marker)
    end = content.find(b" ", start)
    return int(content[start:end])
