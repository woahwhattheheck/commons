#!/usr/bin/env python3
"""Locator-preserving document extraction for RFQ assessment evidence.

Supported formats:
- PDF: page locators via pypdf
- DOCX: section-heading + paragraph/table locators via OOXML
- TXT/MD: section-heading + line-range locators

The adapter intentionally does not invent page numbers for DOCX/TXT documents.
When text extraction is unavailable or incomplete, it reports explicit warnings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

SCHEMA = "uiowa.document-extraction.v1"
MAX_BYTES = 50 * 1024 * 1024
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


class ExtractionError(Exception):
    pass


@dataclass
class Segment:
    segment_id: str
    kind: str
    locator: str
    text: str
    heading_path: list[str]
    warnings: list[str]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _heading_level_from_markdown(line: str) -> int | None:
    m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    return len(m.group(1)) if m else None


def _heading_path_update(stack: list[str], level: int, title: str) -> list[str]:
    level = max(1, min(level, 9))
    if len(stack) >= level:
        stack = stack[: level - 1]
    while len(stack) < level - 1:
        stack.append("(untitled)")
    stack.append(title.strip())
    return stack


def extract_text(path: Path) -> tuple[list[Segment], list[str]]:
    raw = path.read_bytes()
    warnings: list[str] = []
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
        warnings.append("TEXT_DECODE_REPLACEMENTS_USED")

    lines = text.splitlines()
    segments: list[Segment] = []
    stack: list[str] = []
    buffer: list[str] = []
    start_line = 1

    def flush(end_line: int) -> None:
        nonlocal buffer, start_line
        if not buffer:
            return
        body = "\n".join(buffer).strip()
        if body:
            segments.append(
                Segment(
                    segment_id=f"text-{len(segments)+1:04d}",
                    kind="text",
                    locator=f"lines {start_line}-{end_line}",
                    text=body,
                    heading_path=list(stack),
                    warnings=[],
                )
            )
        buffer = []

    for idx, line in enumerate(lines, start=1):
        level = _heading_level_from_markdown(line)
        if level:
            flush(idx - 1)
            title = re.sub(r"^#{1,6}\s+", "", line).strip()
            stack = _heading_path_update(stack, level, title)
            segments.append(
                Segment(
                    segment_id=f"heading-{len(segments)+1:04d}",
                    kind="heading",
                    locator=f"line {idx}",
                    text=title,
                    heading_path=list(stack),
                    warnings=[],
                )
            )
            start_line = idx + 1
        else:
            if not buffer:
                start_line = idx
            buffer.append(line)
    flush(len(lines))
    if not segments and text.strip():
        segments.append(
            Segment(
                segment_id="text-0001",
                kind="text",
                locator=f"lines 1-{max(1, len(lines))}",
                text=text.strip(),
                heading_path=[],
                warnings=[],
            )
        )
    return segments, warnings


def _docx_paragraph_text(p: ET.Element) -> str:
    parts: list[str] = []
    for node in p.iter():
        if node.tag == f"{{{W_NS}}}t":
            parts.append(node.text or "")
        elif node.tag == f"{{{W_NS}}}tab":
            parts.append("\t")
        elif node.tag in {f"{{{W_NS}}}br", f"{{{W_NS}}}cr"}:
            parts.append("\n")
    return "".join(parts).strip()


def _docx_style_id(p: ET.Element) -> str | None:
    ppr = p.find("w:pPr", NS)
    if ppr is None:
        return None
    style = ppr.find("w:pStyle", NS)
    if style is None:
        return None
    return style.get(f"{{{W_NS}}}val")


def _docx_heading_level(style_id: str | None) -> int | None:
    if not style_id:
        return None
    m = re.search(r"heading\s*([1-9])", style_id, flags=re.I)
    if not m:
        m = re.search(r"Heading([1-9])", style_id)
    return int(m.group(1)) if m else None


def extract_docx(path: Path) -> tuple[list[Segment], list[str]]:
    warnings = [
        "DOCX_PAGE_NUMBERS_NOT_RELIABLE_IN_PACKAGE; using section/paragraph/table locators"
    ]
    try:
        with zipfile.ZipFile(path) as zf:
            try:
                xml_bytes = zf.read("word/document.xml")
            except KeyError as exc:
                raise ExtractionError("DOCX_MISSING_word/document.xml") from exc
    except zipfile.BadZipFile as exc:
        raise ExtractionError("DOCX_INVALID_ZIP_CONTAINER") from exc

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ExtractionError("DOCX_DOCUMENT_XML_PARSE_ERROR") from exc

    body = root.find("w:body", NS)
    if body is None:
        raise ExtractionError("DOCX_MISSING_BODY")

    segments: list[Segment] = []
    stack: list[str] = []
    paragraph_index = 0
    table_index = 0

    for child in body:
        if child.tag == f"{{{W_NS}}}p":
            paragraph_index += 1
            text = _docx_paragraph_text(child)
            if not text:
                continue
            level = _docx_heading_level(_docx_style_id(child))
            if level:
                stack = _heading_path_update(stack, level, text)
                kind = "heading"
            else:
                kind = "paragraph"
            segments.append(
                Segment(
                    segment_id=f"docx-{len(segments)+1:04d}",
                    kind=kind,
                    locator=f"paragraph {paragraph_index}",
                    text=text,
                    heading_path=list(stack),
                    warnings=[],
                )
            )
        elif child.tag == f"{{{W_NS}}}tbl":
            table_index += 1
            rows: list[str] = []
            for tr in child.findall("w:tr", NS):
                cells: list[str] = []
                for tc in tr.findall("w:tc", NS):
                    cell_parts = [_docx_paragraph_text(p) for p in tc.findall(".//w:p", NS)]
                    cells.append(" ".join(p for p in cell_parts if p).strip())
                rows.append(" | ".join(cells))
            text = "\n".join(rows).strip()
            segments.append(
                Segment(
                    segment_id=f"docx-{len(segments)+1:04d}",
                    kind="table",
                    locator=f"table {table_index}",
                    text=text,
                    heading_path=list(stack),
                    warnings=["TABLE_LINEARIZED_ROW_MAJOR_WITH_PIPE_SEPARATORS"],
                )
            )

    if not segments:
        warnings.append("DOCX_NO_EXTRACTABLE_TEXT")
    return segments, warnings


def _split_pdf_page_text(text: str) -> list[str]:
    """Keep a page as a citation unit, but preserve logical blocks when possible."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text or "") if b.strip()]
    if not blocks and (text or "").strip():
        blocks = [(text or "").strip()]
    return blocks


def extract_pdf(path: Path) -> tuple[list[Segment], list[str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractionError(
            "PDF_BACKEND_UNAVAILABLE: install pypdf>=6,<7"
        ) from exc

    warnings: list[str] = []
    try:
        reader = PdfReader(str(path), strict=False)
    except Exception as exc:
        raise ExtractionError(f"PDF_OPEN_FAILED: {type(exc).__name__}") from exc

    if getattr(reader, "is_encrypted", False):
        try:
            status = reader.decrypt("")
        except Exception:
            status = 0
        if not status:
            raise ExtractionError("PDF_ENCRYPTED_PASSWORD_REQUIRED")

    segments: list[Segment] = []
    empty_pages = 0
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            empty_pages += 1
            segments.append(
                Segment(
                    segment_id=f"pdf-{len(segments)+1:04d}",
                    kind="unreadable",
                    locator=f"page {page_no}",
                    text="",
                    heading_path=[],
                    warnings=[f"PAGE_TEXT_EXTRACTION_FAILED:{type(exc).__name__}"],
                )
            )
            continue
        blocks = _split_pdf_page_text(text)
        if not blocks:
            empty_pages += 1
            segments.append(
                Segment(
                    segment_id=f"pdf-{len(segments)+1:04d}",
                    kind="unreadable",
                    locator=f"page {page_no}",
                    text="",
                    heading_path=[],
                    warnings=[
                        "PAGE_NO_EXTRACTABLE_TEXT; possible image-only, scanned, or unsupported layout"
                    ],
                )
            )
            continue
        for block_index, block in enumerate(blocks, start=1):
            segments.append(
                Segment(
                    segment_id=f"pdf-{len(segments)+1:04d}",
                    kind="page_text",
                    locator=f"page {page_no}, block {block_index}",
                    text=block,
                    heading_path=[],
                    warnings=[],
                )
            )

    if empty_pages:
        warnings.append(f"PDF_PAGES_WITHOUT_EXTRACTABLE_TEXT={empty_pages}/{len(reader.pages)}")
    if reader.pages and empty_pages == len(reader.pages):
        warnings.append("PDF_TEXT_EXTRACTION_EMPTY_FOR_ALL_PAGES; OCR_REQUIRED_FOR_IMAGE_ONLY_CONTENT")
    return segments, warnings


def extract(path: Path) -> dict:
    path = path.resolve()
    if not path.is_file():
        raise ExtractionError("INPUT_NOT_A_REGULAR_FILE")
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise ExtractionError(f"INPUT_TOO_LARGE:{size}>{MAX_BYTES}")

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        document_type = "plain_text"
        segments, warnings = extract_text(path)
    elif suffix == ".docx":
        document_type = "docx"
        segments, warnings = extract_docx(path)
    elif suffix == ".pdf":
        document_type = "pdf"
        segments, warnings = extract_pdf(path)
    else:
        raise ExtractionError(f"UNSUPPORTED_EXTENSION:{suffix or '(none)'}")

    extracted_nonempty = sum(1 for s in segments if s.text.strip())
    status = "ok"
    if warnings or extracted_nonempty < len(segments):
        status = "partial"
    if not extracted_nonempty:
        status = "unreadable"

    return {
        "schema": SCHEMA,
        "document": {
            "name": path.name,
            "type": document_type,
            "bytes": size,
            "sha256": sha256_file(path),
        },
        "status": status,
        "warnings": warnings,
        "segments": [asdict(s) for s in segments],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = extract(args.input)
        payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        else:
            sys.stdout.write(payload)
        return 0 if result["status"] in {"ok", "partial"} else 2
    except ExtractionError as exc:
        payload = {
            "schema": SCHEMA,
            "document": {"name": args.input.name},
            "status": "error",
            "error": str(exc),
            "warnings": [],
            "segments": [],
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
