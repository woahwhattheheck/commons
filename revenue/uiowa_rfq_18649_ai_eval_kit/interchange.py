"""Lossless, reader-safe export/import for the UIOWA-075 evaluation kit.

Why this module exists
----------------------
The kit's whole value is that a second person can read the results without the
producing environment.  That only holds if a value survives the trip out to a
CSV a University or Clark's reader opens in a spreadsheet, and back again,
*unchanged*.  Naive CSV export quietly destroys four things we actually carry:

  1. A cell beginning ``=``/``+``/``-``/``@`` is executed as a formula by Excel,
     LibreOffice and Google Sheets.  That is both a correctness bug (the value
     is gone) and the classic CSV-injection vector.  We neutralize it with the
     spreadsheet literal-text marker AND report it, and the paired reader undoes
     the marker exactly -- neutralized, flagged, reversible.  Silently mangling
     it would be worse than not exporting at all.
  2. NULL (never recorded), "" (recorded and empty) and the literal string "NA"
     are three different facts.  A bare CSV collapses the first two.  We use the
     Postgres COPY convention: NULL is the sentinel ``\\N``; a literal backslash
     at the start of a value is escaped by doubling.  Reversible, and readable
     by any CSV tool.
  3. Dates.  ``03/04/2026`` is 3 April in Iowa City's British-English readers and
     4 March in US readers.  We do not guess.  ISO-8601 in, ISO-8601 out, and an
     ambiguous slash date is a loud rejection naming both readings.
  4. Unicode, embedded quotes/commas, CRLF inside a quoted field, and very long
     source locators.  These are just correctness; they are in the fixtures
     because they are the ones that break in practice.

Python 3 standard library only.  No network.  No third-party packages.

Format boundary (stated honestly, not faked)
--------------------------------------------
This module writes CSV, JSON and Markdown.  It does NOT write .xlsx or .pdf:
both need a dependency this kit refuses to take.  Rather than shipping a stub
that pretends, the CSV is emitted next to a machine-readable column dictionary
(``schema.json``) so a spreadsheet import is correct and repeatable, and the
Markdown report is the document-format deliverable.  See README.md.
"""

import csv
import hashlib
import json
import re
import unicodedata
from datetime import date

NULL_TOKEN = "\\N"

# Leading characters a spreadsheet will treat as the start of a formula, plus
# the control characters that let an attacker smuggle one past a naive filter.
RISKY_LEAD = ("=", "+", "-", "@", "\t", "\r", "\n")

# 3/4/2026 -- unreadable without knowing the producer's locale.  We reject it.
AMBIGUOUS_DATE = re.compile(r"^\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*$")

NUMERIC_KINDS = ("int", "float")


class InterchangeError(ValueError):
    """Raised when a value cannot be carried through a format without guessing."""


class AmbiguousDateError(InterchangeError):
    pass


def normalize_text(value):
    """NFC-normalize so an accented name compares equal however it was typed.

    'José' (combining acute) and 'José' (precomposed) are the same
    name; only one of them survives a naive == against a fixture.
    """
    return unicodedata.normalize("NFC", value)


def encode_cell(value, kind="text"):
    """Return (text, warning_or_None) for one CSV cell.

    Escape order is the exact reverse of decode_cell's, which is what makes the
    round trip exact rather than approximately exact.
    """
    if value is None:
        return NULL_TOKEN, None
    if kind in NUMERIC_KINDS:
        if isinstance(value, bool):
            raise InterchangeError("bool in a numeric column; use kind='bool'")
        return repr(value) if isinstance(value, float) else str(value), None
    if kind == "bool":
        return "true" if value else "false", None
    if kind == "date":
        text = value.isoformat() if isinstance(value, date) else str(value)
        _parse_date(text)  # fail here, at export, not in the reader's spreadsheet
        return text, None

    text = normalize_text(str(value))
    warning = None
    # 1. formula / literal-apostrophe guard
    if text.startswith(RISKY_LEAD):
        warning = "formula-like value neutralized on export"
        text = "'" + text
    elif text.startswith("'"):
        text = "'" + text
    # 2. NULL-sentinel guard
    if text.startswith("\\"):
        text = "\\" + text
    return text, warning


def decode_cell(text, kind="text"):
    """Inverse of encode_cell.  Exact, not lossy."""
    if text == NULL_TOKEN:
        return None
    if kind in NUMERIC_KINDS:
        if text == "":
            raise InterchangeError("empty numeric cell: use \\N for 'not recorded'")
        return int(text) if kind == "int" else float(text)
    if kind == "bool":
        if text not in ("true", "false"):
            raise InterchangeError(f"unreadable bool cell: {text!r}")
        return text == "true"
    if kind == "date":
        return _parse_date(text).isoformat()

    if text.startswith("\\"):
        text = text[1:]
    if text.startswith("'"):
        text = text[1:]
    return normalize_text(text)


def _parse_date(text):
    text = text.strip()
    if AMBIGUOUS_DATE.match(text):
        a, b, y = AMBIGUOUS_DATE.match(text).groups()
        raise AmbiguousDateError(
            f"ambiguous date {text!r}: could be {y}-{int(a):02d}-{int(b):02d} "
            f"(US) or {y}-{int(b):02d}-{int(a):02d} (day-first). "
            "Supply ISO-8601 YYYY-MM-DD; this kit will not guess."
        )
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise InterchangeError(f"not an ISO-8601 date: {text!r}") from exc


def write_csv(path, columns, rows):
    """Write rows to CSV.  Returns the list of export warnings (never silent).

    ``columns`` is a list of (field_name, kind) pairs -- that list IS the column
    dictionary, and it is what read_csv needs to reverse this exactly.
    """
    warnings = []
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow([name for name, _ in columns])
        for index, row in enumerate(rows):
            cells = []
            for name, kind in columns:
                text, warning = encode_cell(row.get(name), kind)
                if warning:
                    warnings.append({"row": index, "field": name, "warning": warning})
                cells.append(text)
            writer.writerow(cells)
    return warnings


def read_csv(path, columns):
    kinds = dict(columns)
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        expected = [name for name, _ in columns]
        if header != expected:
            raise InterchangeError(f"header mismatch: {header!r} != {expected!r}")
        rows = []
        for cells in reader:
            if len(cells) != len(expected):
                raise InterchangeError(
                    f"row has {len(cells)} cells, expected {len(expected)}"
                )
            rows.append(
                {name: decode_cell(cell, kinds[name]) for name, cell in zip(expected, cells)}
            )
    return rows


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def record_hash(record):
    """Stable content hash of one record, after Unicode normalization.

    This is how the kit *proves* a round trip instead of asserting it: hash the
    records before export, hash them after import, compare.
    """
    canonical = json.dumps(
        _normalize_tree(record), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_tree(node):
    if isinstance(node, str):
        return normalize_text(node)
    if isinstance(node, dict):
        return {k: _normalize_tree(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_normalize_tree(v) for v in node]
    return node


def digest_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def md_escape(value):
    """Make a value safe inside a Markdown table cell without losing it."""
    if value is None:
        return "_not recorded_"
    text = normalize_text(str(value))
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    # A newline would end the table row; keep the content, show the break.
    return text.replace("\r\n", " ⏎ ").replace("\n", " ⏎ ").replace("\r", " ⏎ ")


def write_markdown_table(handle, headers, rows):
    handle.write("| " + " | ".join(md_escape(h) for h in headers) + " |\n")
    handle.write("|" + "|".join("---" for _ in headers) + "|\n")
    for row in rows:
        handle.write("| " + " | ".join(md_escape(c) for c in row) + " |\n")
