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
import io
import os
import tempfile
import json
import re
import sys
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator
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


def _read_source(path: Path) -> bytes:
    """Capture bounded bytes once; parsers and metadata use this same snapshot.

    This is not a filesystem transaction: a writer can change a file while it is
    being read. The guarantee is that the hash describes the bytes actually
    supplied to the parser, never a second read of a newer revision.
    """
    try:
        if not path.is_file():
            raise ExtractionError("INPUT_NOT_A_REGULAR_FILE")
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ExtractionError(f"INPUT_READ_FAILED:{type(exc).__name__}") from exc
    if len(raw) > MAX_BYTES:
        raise ExtractionError(f"INPUT_TOO_LARGE:{len(raw)}>{MAX_BYTES}")
    return raw


def _ensure_distinct_output(source: Path, output: Path) -> None:
    """Reject spelling, symlink, and hard-link aliases of the source artifact."""
    try:
        aliases = source.resolve() == output.resolve()
        if not aliases and output.exists():
            aliases = source.samefile(output)
    except OSError as exc:
        raise ExtractionError(f"OUTPUT_IDENTITY_CHECK_FAILED:{type(exc).__name__}") from exc
    if aliases:
        raise ExtractionError("OUTPUT_ALIASES_INPUT")


def _write_output(source: Path, output: Path, payload: str) -> None:
    """Stage a complete report, then replace its directory entry atomically.

    Do not open the destination for truncation: an existing symlink or hard
    link must not mutate its target. A failed staging/replacement leaves the
    previous report intact. Only this function's own temporary file is removed.
    """
    _ensure_distinct_output(source, output)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _ensure_distinct_output(source, output)
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


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


def extract_text(path: Path, *, raw: bytes | None = None) -> tuple[list[Segment], list[str]]:
    raw = _read_source(path) if raw is None else raw
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


def _docx_blocks(
    parent: ET.Element, path: str, warnings: list[str], *, direct: bool = True,
) -> Iterator[tuple[ET.Element, str, bool]]:
    """Walk transparent block wrappers with exact OOXML paths.

    Existing direct-body paragraph/table locators remain unchanged. Wrapped
    content receives an XML-part locator instead of silently shifting those
    legacy counters. Unsupported body content is disclosed, not invented.
    """
    counts: dict[str, int] = {}
    ignored = {"sectPr", "bookmarkStart", "bookmarkEnd", "proofErr", "permStart", "permEnd"}
    for child in parent:
        local = child.tag.rsplit("}", 1)[-1]
        counts[child.tag] = counts.get(child.tag, 0) + 1
        child_path = f"{path}/w:{local}[{counts[child.tag]}]"
        if child.tag in {f"{{{W_NS}}}p", f"{{{W_NS}}}tbl"}:
            yield child, child_path, direct
        elif child.tag == f"{{{W_NS}}}sdt":
            content = child.find("w:sdtContent", NS)
            if content is None:
                warnings.append(f"DOCX_CONTENT_CONTROL_MISSING_CONTENT:{child_path}")
            else:
                yield from _docx_blocks(
                    content, child_path + "/w:sdtContent[1]", warnings, direct=False,
                )
        elif child.tag == f"{{{W_NS}}}customXml":
            yield from _docx_blocks(child, child_path, warnings, direct=False)
        elif child.tag not in {f"{{{W_NS}}}{name}" for name in ignored}:
            warnings.append(f"DOCX_UNSUPPORTED_BODY_ELEMENT:{child.tag} at {child_path}")


def extract_docx(path: Path, *, raw: bytes | None = None) -> tuple[list[Segment], list[str]]:
    raw = _read_source(path) if raw is None else raw
    warnings = [
        "DOCX_PAGE_NUMBERS_NOT_RELIABLE_IN_PACKAGE; using section/paragraph/table locators"
    ]
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
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

    revision_tags = {f"{{{W_NS}}}{tag}" for tag in ("ins", "del", "moveFrom", "moveTo")}
    if any(node.tag in revision_tags for node in root.iter()):
        warnings.append("DOCX_TRACKED_CHANGES_PRESENT; extracted view is not adjudicated")

    for child, xml_path, direct in _docx_blocks(body, "/w:document/w:body", warnings):
        if child.tag == f"{{{W_NS}}}p":
            if direct:
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
                    locator=f"paragraph {paragraph_index}" if direct else f"word/document.xml:{xml_path}",
                    text=text,
                    heading_path=list(stack),
                    warnings=[],
                )
            )
        elif child.tag == f"{{{W_NS}}}tbl":
            if direct:
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
                    locator=f"table {table_index}" if direct else f"word/document.xml:{xml_path}",
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


def extract_pdf(path: Path, *, raw: bytes | None = None) -> tuple[list[Segment], list[str]]:
    raw = _read_source(path) if raw is None else raw
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractionError(
            "PDF_BACKEND_UNAVAILABLE: install pypdf>=6,<7"
        ) from exc

    warnings: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(raw), strict=False)
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
    raw = _read_source(path)
    size = len(raw)

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        document_type = "plain_text"
        segments, warnings = extract_text(path, raw=raw)
    elif suffix == ".docx":
        document_type = "docx"
        segments, warnings = extract_docx(path, raw=raw)
    elif suffix == ".pdf":
        document_type = "pdf"
        segments, warnings = extract_pdf(path, raw=raw)
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
            "sha256": hashlib.sha256(raw).hexdigest(),
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
        if args.output:
            _ensure_distinct_output(args.input, args.output)
        result = extract(args.input)
        payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            _write_output(args.input, args.output, payload)
        else:
            sys.stdout.write(payload)
        return 0 if result["status"] in {"ok", "partial"} else 2
    except (ExtractionError, OSError) as exc:
        error = str(exc) if isinstance(exc, ExtractionError) else f"IO_ERROR:{type(exc).__name__}"
        payload = {
            "schema": SCHEMA,
            "document": {"name": args.input.name},
            "status": "error",
            "error": error,
            "warnings": [],
            "segments": [],
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
