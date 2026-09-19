"""Typed JSON-Pointer interchange for synthetic assessment envelopes.

Whole existing JSON envelopes are retained. This module does not translate
or elevate assessment or authority fields.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ABSENT = "absent"
EMPTY = "empty"
NULL = "null"
PRESENT = "present"

SCALAR_TYPES = ("string", "integer", "float", "bool", "null")


class TransportError(ValueError):
    pass


def _classify(value: Any) -> tuple[str, str, str]:
    if value is None:
        return "null", "", NULL
    if isinstance(value, bool):
        return "bool", "true" if value else "false", PRESENT
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer", str(value), PRESENT
    if isinstance(value, float):
        return "float", repr(value), PRESENT
    if isinstance(value, str):
        return "string", value, EMPTY if value == "" else PRESENT
    raise TransportError(f"unsupported scalar: {type(value).__name__}")


def _escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def to_rows(document: Any, prefix: str = "") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def walk(node: Any, pointer: str) -> None:
        if isinstance(node, dict):
            if not node:
                rows.append({"pointer": pointer or "/", "type": "object", "value": "", "presence": EMPTY})
                return
            for key, child in node.items():
                walk(child, f"{pointer}/{_escape_pointer_token(str(key))}")
            return
        if isinstance(node, list):
            if not node:
                rows.append({"pointer": pointer or "/", "type": "array", "value": "", "presence": EMPTY})
                return
            for i, child in enumerate(node):
                walk(child, f"{pointer}/{i}")
            return
        typ, value, presence = _classify(node)
        rows.append({"pointer": pointer or "/", "type": typ, "value": value, "presence": presence})

    walk(document, prefix)
    return rows


def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _parse_scalar(typ: str, value: str, presence: str) -> Any:
    if presence == NULL or typ == "null":
        return None
    if typ == "bool":
        if value not in ("true", "false"):
            raise TransportError(f"bad bool: {value!r}")
        return value == "true"
    if typ == "integer":
        return int(value)
    if typ == "float":
        return float(value)
    if typ == "string":
        return value
    raise TransportError(f"unknown scalar type {typ}")


def from_rows(rows: list[dict[str, str]]) -> Any:
    if not rows:
        raise TransportError("no rows")
    root: Any = None
    initialized = False

    for row in rows:
        pointer = row.get("pointer") or "/"
        typ = row.get("type") or "string"
        value = row.get("value", "")
        presence = row.get("presence") or PRESENT
        if not pointer.startswith("/"):
            raise TransportError(f"pointer must start with /: {pointer}")
        tokens = [] if pointer == "/" else [_unescape(t) for t in pointer[1:].split("/")]
        if typ in ("object", "array") and presence == EMPTY and not tokens:
            return {} if typ == "object" else []
        if not tokens:
            return _parse_scalar(typ, value, presence)

        if not initialized:
            root = [] if tokens[0].isdigit() else {}
            initialized = True

        cursor = root
        for i, token in enumerate(tokens):
            last = i == len(tokens) - 1
            nxt = tokens[i + 1] if not last else None
            next_index = bool(nxt is not None and nxt.isdigit())
            if last:
                payload: Any
                if typ == "object":
                    payload = {}
                elif typ == "array":
                    payload = []
                else:
                    payload = _parse_scalar(typ, value, presence)
                if isinstance(cursor, list):
                    idx = int(token)
                    while len(cursor) <= idx:
                        cursor.append(None)
                    cursor[idx] = payload
                elif isinstance(cursor, dict):
                    cursor[token] = payload
                else:
                    raise TransportError("cannot assign into scalar")
            else:
                if isinstance(cursor, list):
                    idx = int(token)
                    while len(cursor) <= idx:
                        cursor.append(None)
                    if cursor[idx] is None:
                        cursor[idx] = [] if next_index else {}
                    cursor = cursor[idx]
                elif isinstance(cursor, dict):
                    if token not in cursor or cursor[token] is None:
                        cursor[token] = [] if next_index else {}
                    cursor = cursor[token]
                else:
                    raise TransportError("cannot descend into scalar")
    return root


def write_csv(document: Any, path: str | Path) -> Path:
    path = Path(path)
    rows = to_rows(document)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["pointer", "type", "value", "presence"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def read_csv(path: str | Path) -> Any:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise TransportError("csv missing header")
    required = {"pointer", "type", "value", "presence"}
    if set(reader.fieldnames) < required:
        raise TransportError("csv missing required columns")
    rows = list(reader)
    return from_rows(rows)


def write_xlsx(document: Any, path: str | Path) -> Path:
    path = Path(path)
    rows = to_rows(document)
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ssrel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    def cell(ref: str, text: str) -> ET.Element:
        c = ET.Element("c", r=ref, t="inlineStr")
        is_el = ET.SubElement(c, "is")
        t_el = ET.SubElement(is_el, "t")
        t_el.text = text
        return c

    sheet = ET.Element("worksheet", xmlns=ns)
    sheet_data = ET.SubElement(sheet, "sheetData")
    headers = ["pointer", "type", "value", "presence"]
    header_row = ET.SubElement(sheet_data, "row", r="1")
    for i, h in enumerate(headers):
        header_row.append(cell(f"{chr(65+i)}1", h))
    for ridx, row in enumerate(rows, start=2):
        xml_row = ET.SubElement(sheet_data, "row", r=str(ridx))
        for i, h in enumerate(headers):
            xml_row.append(cell(f"{chr(65+i)}{ridx}", row[h]))
    sheet_xml = ET.tostring(sheet, encoding="utf-8", xml_declaration=True)

    workbook = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        f"<workbook xmlns=\"{ns}\" xmlns:r=\"{ssrel}\">"
        "<sheets><sheet name=\"transport\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
        "</workbook>"
    ).encode("utf-8")
    rels = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>"
        "</Relationships>"
    ).encode("utf-8")
    wb_rels = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/>"
        "</Relationships>"
    ).encode("utf-8")
    ctypes = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
        "<Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>"
        "</Types>"
    ).encode("utf-8")

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ctypes)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return path


def read_xlsx(path: str | Path) -> Any:
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        sheet_name = next((n for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml")), None)
        if not sheet_name:
            raise TransportError("xlsx missing worksheet")
        root = ET.fromstring(zf.read(sheet_name))
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values: list[list[str]] = []
    for row in root.findall(".//m:sheetData/m:row", ns):
        cells = []
        for c in row.findall("m:c", ns):
            t = c.find("m:is/m:t", ns)
            cells.append("" if t is None or t.text is None else t.text)
        if cells:
            values.append(cells)
    if not values:
        raise TransportError("xlsx empty")
    header, *body = values
    if header[:4] != ["pointer", "type", "value", "presence"]:
        raise TransportError("xlsx unexpected header")
    rows = [
        {"pointer": r[0], "type": r[1], "value": r[2] if len(r) > 2 else "", "presence": r[3] if len(r) > 3 else PRESENT}
        for r in body
    ]
    return from_rows(rows)


def project_docx(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    warnings: list[str] = []
    texts: list[str] = []
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise TransportError(f"docx unreadable: {exc}") from exc
    root = ET.fromstring(xml)
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for p in root.iter(f"{w}p"):
        parts = [t.text or "" for t in p.iter(f"{w}t")]
        line = "".join(parts)
        if line:
            texts.append(line)
    warnings.append("DOCX projection is paragraph text only; layout and page numbers are unknown.")
    return {
        "schema": "uiowa.interchange.docx-projection.v1",
        "source": path.name,
        "status": "partial" if texts else "unreadable",
        "warnings": warnings,
        "paragraphs": texts,
        "authority": "none",
        "assessment": "not_elevated",
    }


def project_pdf(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    warnings = [
        "PDF projection does not perform OCR.",
        "Without a PDF parser dependency this reader reports bytes only and marks text as unknown.",
    ]
    data = path.read_bytes()
    return {
        "schema": "uiowa.interchange.pdf-projection.v1",
        "source": path.name,
        "status": "unknown_text",
        "bytes": len(data),
        "warnings": warnings,
        "text": "",
        "authority": "none",
        "assessment": "not_elevated",
    }


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(document: Any, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
