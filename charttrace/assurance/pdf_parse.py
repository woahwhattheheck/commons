"""Independent PDF-1.4 text extractor for ChartTrace synthetic fixtures.

This parser does not import the oracle. It only reads bytes produced by
``charttrace.fixtures.pdf_synth`` and recovers page literals.
"""

from __future__ import annotations

import re


_STREAM = re.compile(rb"stream\n(.*?)\nendstream", re.DOTALL)
_TJ = re.compile(rb"Td \((.*)\) Tj", re.DOTALL)


def unescape_pdf_literal(raw: bytes) -> str:
    out = bytearray()
    index = 0
    while index < len(raw):
        if raw[index] == 0x5C and index + 1 < len(raw):
            out.append(raw[index + 1])
            index += 2
            continue
        out.append(raw[index])
        index += 1
    return out.decode("latin-1", errors="replace")


def extract_page_texts(content: bytes) -> tuple[str, ...]:
    """Return page strings in object order. Empty PDFs raise."""

    if not content.startswith(b"%PDF-"):
        raise ValueError("not a PDF")
    pages: list[str] = []
    for block in _STREAM.findall(content):
        match = _TJ.search(block)
        if match is None:
            continue
        pages.append(unescape_pdf_literal(match.group(1)))
    if not pages:
        raise ValueError("PDF contained no recoverable text pages")
    return tuple(pages)


def pdf_page_count(content: bytes) -> int:
    marker = b"/Type /Pages /Count "
    start = content.find(marker)
    if start < 0:
        raise ValueError("PDF is missing a Pages count")
    start += len(marker)
    end = content.find(b" ", start)
    return int(content[start:end])
