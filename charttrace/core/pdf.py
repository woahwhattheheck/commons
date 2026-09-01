"""Small deterministic PDF writer/parser for embedded synthetic text.

This is intentionally not OCR. It extracts only text already embedded in a
PDF and is sufficient for deterministic, page-cited synthetic acceptance
fixtures.
"""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union


class PDFError(ValueError):
    pass


class EncryptedPDFError(PDFError):
    pass


@dataclass(frozen=True, slots=True)
class PDFPage:
    page_number: int
    text: str


_OBJECT_RE = re.compile(rb"(?m)^\s*(\d+)\s+0\s+obj\b(.*?)endobj", re.S)
_PAGE_RE = re.compile(rb"/Type\s*/Page\b")
_CONTENTS_RE = re.compile(rb"/Contents\s+(\[[^\]]*\]|\d+\s+0\s+R)", re.S)
_REFERENCE_RE = re.compile(rb"(\d+)\s+0\s+R")
_STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
_TEXT_BLOCK_RE = re.compile(rb"BT\b(.*?)\bET", re.S)
_SHOW_TEXT_RE = re.compile(
    rb"(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]+>)\s*Tj\b"
    rb"|\[((?:[^\[\]]|\((?:\\.|[^\\)])*\))*)\]\s*TJ\b",
    re.S,
)
_ARRAY_STRING_RE = re.compile(rb"\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]+>")


def _decode_literal(token: bytes) -> str:
    body = token[1:-1]
    decoded = bytearray()
    index = 0
    escapes = {
        ord("n"): b"\n",
        ord("r"): b"\r",
        ord("t"): b"\t",
        ord("b"): b"\b",
        ord("f"): b"\f",
        ord("("): b"(",
        ord(")"): b")",
        ord("\\"): b"\\",
    }
    while index < len(body):
        value = body[index]
        if value != ord("\\"):
            decoded.append(value)
            index += 1
            continue
        index += 1
        if index >= len(body):
            break
        escaped = body[index]
        if escaped in escapes:
            decoded.extend(escapes[escaped])
            index += 1
        elif escaped in (ord("\r"), ord("\n")):
            if escaped == ord("\r") and index + 1 < len(body):
                if body[index + 1] == ord("\n"):
                    index += 1
            index += 1
        elif ord("0") <= escaped <= ord("7"):
            end = index + 1
            while end < min(index + 3, len(body)) and ord("0") <= body[end] <= ord(
                "7"
            ):
                end += 1
            decoded.append(int(body[index:end], 8) & 0xFF)
            index = end
        else:
            decoded.append(escaped)
            index += 1
    if decoded.startswith(b"\xfe\xff"):
        return bytes(decoded[2:]).decode("utf-16-be", errors="replace")
    return bytes(decoded).decode("latin-1", errors="replace")


def _decode_pdf_string(token: bytes) -> str:
    if token.startswith(b"("):
        return _decode_literal(token)
    compact = re.sub(rb"\s+", b"", token[1:-1])
    if len(compact) % 2:
        compact += b"0"
    try:
        decoded = bytes.fromhex(compact.decode("ascii"))
    except ValueError:
        return ""
    if decoded.startswith(b"\xfe\xff"):
        return decoded[2:].decode("utf-16-be", errors="replace")
    return decoded.decode("latin-1", errors="replace")


def _extract_stream_text(stream: bytes) -> str:
    lines: List[str] = []
    for block_match in _TEXT_BLOCK_RE.finditer(stream):
        block = block_match.group(1)
        previous_end = 0
        for match in _SHOW_TEXT_RE.finditer(block):
            separator_commands = block[previous_end : match.start()]
            if lines and re.search(rb"\b(?:T\*|Td|TD)\b", separator_commands):
                if lines[-1] != "\n":
                    lines.append("\n")
            if match.group(1) is not None:
                text = _decode_pdf_string(match.group(1))
            else:
                text = "".join(
                    _decode_pdf_string(item)
                    for item in _ARRAY_STRING_RE.findall(match.group(2))
                )
            if text:
                if lines and lines[-1] not in {"\n", " "}:
                    lines.append("\n")
                lines.append(text)
            previous_end = match.end()
    return "".join(lines).strip()


def extract_embedded_pdf_text(data: bytes) -> Tuple[PDFPage, ...]:
    if not data.startswith(b"%PDF-"):
        raise PDFError("input is not a PDF")
    if re.search(rb"/Encrypt\b", data):
        raise EncryptedPDFError("encrypted PDF text extraction is held")

    objects = {int(match.group(1)): match.group(2) for match in _OBJECT_RE.finditer(data)}
    if not objects:
        raise PDFError("PDF object table is unavailable")
    page_objects = [
        body
        for _, body in sorted(objects.items())
        if _PAGE_RE.search(body) is not None
    ]
    pages: List[PDFPage] = []
    for page_number, page_object in enumerate(page_objects, 1):
        contents = _CONTENTS_RE.search(page_object)
        if contents is None:
            pages.append(PDFPage(page_number, ""))
            continue
        references = [
            int(match.group(1)) for match in _REFERENCE_RE.finditer(contents.group(1))
        ]
        text_parts: List[str] = []
        for reference in references:
            content_object = objects.get(reference, b"")
            stream_match = _STREAM_RE.search(content_object)
            if stream_match is None:
                continue
            stream = stream_match.group(1)
            if re.search(rb"/FlateDecode\b", content_object):
                try:
                    stream = zlib.decompress(stream)
                except zlib.error as exc:
                    raise PDFError("invalid FlateDecode stream") from exc
            extracted = _extract_stream_text(stream)
            if extracted:
                text_parts.append(extracted)
        pages.append(PDFPage(page_number, "\n".join(text_parts)))
    return tuple(pages)


def read_embedded_pdf_text(
    source: Union[str, Path, bytes, bytearray]
) -> Tuple[PDFPage, ...]:
    data = bytes(source) if isinstance(source, (bytes, bytearray)) else Path(source).read_bytes()
    return extract_embedded_pdf_text(data)


def _pdf_text_token(text: str) -> bytes:
    try:
        raw = text.encode("latin-1")
    except UnicodeEncodeError:
        return b"<FEFF" + text.encode("utf-16-be").hex().upper().encode("ascii") + b">"
    escaped = (
        raw.replace(b"\\", b"\\\\")
        .replace(b"(", b"\\(")
        .replace(b")", b"\\)")
        .replace(b"\r", b"\\r")
        .replace(b"\n", b"\\n")
    )
    return b"(" + escaped + b")"


def build_minimal_pdf(pages: Sequence[str]) -> bytes:
    """Build a byte-deterministic, unencrypted PDF with embedded page text."""

    if not pages:
        raise ValueError("a PDF must contain at least one page")
    page_count = len(pages)
    font_object_number = 3 + page_count * 2
    objects: List[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = b" ".join(
        f"{3 + index * 2} 0 R".encode("ascii") for index in range(page_count)
    )
    objects.append(
        b"<< /Type /Pages /Kids ["
        + kids
        + f"] /Count {page_count} >>".encode("ascii")
    )
    for index, page_text in enumerate(pages):
        page_object_number = 3 + index * 2
        content_object_number = page_object_number + 1
        page_object = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            + b"/Resources << /Font << /F1 "
            + f"{font_object_number} 0 R".encode("ascii")
            + b" >> >> /Contents "
            + f"{content_object_number} 0 R".encode("ascii")
            + b" >>"
        )
        commands = [b"BT", b"/F1 10 Tf", b"72 720 Td"]
        for line_number, line in enumerate(page_text.splitlines() or [""]):
            if line_number:
                commands.append(b"0 -14 Td")
            commands.append(_pdf_text_token(line) + b" Tj")
        commands.append(b"ET")
        stream = b"\n".join(commands)
        content_object = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
        objects.extend((page_object, content_object))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{object_number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def write_minimal_pdf(path: Union[str, Path], pages: Sequence[str]) -> Path:
    target = Path(path)
    target.write_bytes(build_minimal_pdf(pages))
    return target
