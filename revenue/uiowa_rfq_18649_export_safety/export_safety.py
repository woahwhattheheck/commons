#!/usr/bin/env python3
"""Cross-lane CSV export-safety audit for the UIOWA RFQ 18649 delivery kit.

Why this exists
---------------
Nearly every lane in this engagement exports a CSV, and the RFQ's standard for
all of them is the same: the file has to be **usable by a Clark's or University
reader who does not have the producing environment**. That is not a property any
single lane can assert about itself — it is a property of the bytes on disk. So
this is a read-only auditor over every published `*.csv` in the delivery kit.

**It reports. It never edits another seat's lane.** A finding is handed to the
lane that owns the file, with the exact path, row, column and cell so the owner
can decide. No file outside this directory is opened for writing.

The nine checks, and why each one is a real reader problem
-----------------------------------------------------------
* ``FORMULA_INJECTION`` — a cell beginning ``=``/``+``/``@`` (or a control char)
  is executed as a formula by Excel, LibreOffice and Sheets. The value is lost
  and it is the classic CSV-injection vector. A cell already neutralized with a
  leading apostrophe is **correct** and is reported as ``NEUTRALIZED_OK``, not
  as a finding — this auditor shows what right looks like as well as what wrong
  looks like.
* ``DUPLICATE_HEADER`` — two columns with the same name. Re-import into a
  dataframe or a spreadsheet silently keeps one and drops the other.
* ``RAGGED_ROW`` — a row whose cell count differs from the header's. Every
  column after the break is off by one.
* ``LEADING_COMMENT_LINE`` — a ``#`` provenance notice above the header. The
  text is useful and is not treated as a defect, but a spreadsheet import reads
  the real header as data and the columns arrive unnamed.
* ``NULL_SEMANTICS_AMBIGUOUS`` — a column that mixes empty cells with a literal
  null-ish token (``NA``, ``null``, ``unknown``, ``-``…). The reader cannot tell
  "never recorded" from "recorded as empty" from "not applicable", and those are
  three different facts in an assessment.
* ``AMBIGUOUS_DATE`` — ``03/04/2026`` is 3 April to one reader and 4 March to
  another. Both readings are valid, so the value is not recoverable.
* ``NON_ISO_DATE`` — ``13/04/2026`` is unambiguous but still non-portable.
* ``UNNORMALIZED_UNICODE`` — a decomposed accent means the same name will not
  compare equal to its precomposed spelling on a join.
* ``OVERLONG_CELL`` — long enough that some readers truncate it silently.

What a clean result does NOT mean
----------------------------------
Zero findings means "no issue detected by these nine checks", never "certified",
"compliant" or "safe". A file that cannot be read is ``UNREADABLE`` and counts
as UNKNOWN — never as a pass.

Python 3 standard library only. No network. Read-only outside its own output.
"""

import argparse
import csv
import json
import os
import re
import sys
import unicodedata

HIGH, MEDIUM, LOW, INFO = "HIGH", "MEDIUM", "LOW", "INFO"

NULLISH = {"na", "n/a", "null", "none", "nil", "unknown", "-", "--", "tbd", "n\\a"}
SLASH_DATE = re.compile(r"^\s*(\d{1,2})[/.](\d{1,2})[/.](\d{4})\s*$")
CONTROL_LEAD = ("\t", "\r", "\n")
OVERLONG = 2000

FINDING_COLUMNS = ["severity", "code", "lane", "path", "row", "column_index",
                   "column_name", "detail", "sample"]


def is_number(text):
    try:
        float(text.replace(",", ""))
        return True
    except ValueError:
        return False


def looks_like_formula(cell):
    """True only when a spreadsheet would actually evaluate it.

    Two exclusions, both learned from this auditor's own first run against the
    real delivery kit, where they produced false positives:

    * ``-5`` and ``+3.2`` are numbers, not attacks.
    * A bare ``-`` or ``--`` is a not-applicable placeholder. Excel shows it as
      text; it is not a formula. Ten of this auditor's first eleven injection
      findings were lone dashes in a placeholder column.

    A report full of false positives is a report nobody reads, which is worse
    than no report -- so the bar is "would a spreadsheet evaluate this", not
    "does it start with a suspicious character".
    """
    if not cell:
        return False
    if cell[0] in ("=", "@") or cell[0] in CONTROL_LEAD:
        return True
    if cell[0] in ("+", "-"):
        if is_number(cell):
            return False
        if set(cell.strip()) <= {"+", "-"}:      # placeholder, not an expression
            return False
        return True
    return False


def finding(severity, code, lane, path, row, col_index, col_name, detail, sample=""):
    return {"severity": severity, "code": code, "lane": lane, "path": path,
            "row": row, "column_index": col_index, "column_name": col_name,
            "detail": detail, "sample": sample[:120]}


def scan_csv(path, lane, rel_path):
    """Return (findings, stats) for one file. Never raises on bad input."""
    findings, stats = [], {"rows": 0, "cells": 0, "neutralized": 0}
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        return [finding(MEDIUM, "UNREADABLE", lane, rel_path, None, None, None,
                        f"cannot open: {exc}")], stats

    if raw.startswith(b"\xef\xbb\xbf"):
        findings.append(finding(
            MEDIUM, "ENCODING_RISK", lane, rel_path, 0, 0, None,
            "file begins with a UTF-8 BOM; some readers show it inside the first "
            "column name, which breaks a header match"))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return findings + [finding(
            MEDIUM, "ENCODING_RISK", lane, rel_path, None, None, None,
            f"not valid UTF-8: {exc}")], stats

    try:
        rows = list(csv.reader(text.splitlines(keepends=True)))
    except csv.Error as exc:
        return findings + [finding(
            MEDIUM, "UNREADABLE", lane, rel_path, None, None, None,
            f"csv parse failed: {exc}")], stats

    if not rows:
        return findings, stats

    # Several lanes put a provenance or scope notice on line 1 as a `#` comment.
    # That is useful text and this auditor does NOT treat it as a defect in the
    # data -- but taking it as the header is what produced 185 bogus RAGGED_ROW
    # findings on this auditor's first real run. Skip the comment lines, find the
    # real header, and report the portability issue once per file instead of
    # once per row.
    header_index = 0
    while header_index < len(rows) and rows[header_index] and \
            rows[header_index][0].lstrip().startswith("#"):
        header_index += 1
    if header_index >= len(rows):
        return findings, stats
    if header_index:
        findings.append(finding(
            LOW, "LEADING_COMMENT_LINE", lane, rel_path, 0, 0, None,
            f"{header_index} comment line(s) before the header; a spreadsheet import "
            "shows them as a one-cell row and then reads the real header as data, so "
            "the columns arrive unnamed. Consider a sidecar notice file, or accept it "
            "and say so in the lane's README",
            rows[0][0] if rows[0] else ""))

    rows = rows[header_index:]
    header = rows[0]
    seen = {}
    for index, name in enumerate(header):
        if name in seen:
            findings.append(finding(
                HIGH, "DUPLICATE_HEADER", lane, rel_path, 0, index, name,
                f"column name {name!r} also appears at index {seen[name]}; a "
                "re-import keeps one and silently drops the other"))
        seen[name] = index

    # A file that uses an explicit null sentinel (the Postgres COPY convention
    # \N) HAS said which cells were never recorded, so empty-vs-"NA" in it is a
    # documentation question, not an ambiguity. Detect that before judging.
    declares_sentinel = any(cell == "\\N" for row in rows[1:] for cell in row)
    columns = {index: [] for index in range(len(header))}
    for row_no, row in enumerate(rows[1:], start=1):
        stats["rows"] += 1
        if len(row) != len(header):
            findings.append(finding(
                HIGH, "RAGGED_ROW", lane, rel_path, row_no, None, None,
                f"{len(row)} cells against a {len(header)}-column header; every "
                "column after the break is misaligned"))
        for index, cell in enumerate(row):
            stats["cells"] += 1
            name = header[index] if index < len(header) else f"<col {index}>"
            if index in columns:
                columns[index].append(cell)

            if cell.startswith("'") and looks_like_formula(cell[1:]):
                stats["neutralized"] += 1
                continue
            if looks_like_formula(cell):
                findings.append(finding(
                    HIGH, "FORMULA_INJECTION", lane, rel_path, row_no, index, name,
                    "a spreadsheet will evaluate this cell instead of showing it; "
                    "prefix a literal apostrophe on export", cell))

            if len(cell) > OVERLONG:
                findings.append(finding(
                    INFO, "OVERLONG_CELL", lane, rel_path, row_no, index, name,
                    f"{len(cell)} characters; some readers truncate silently", cell))

            if unicodedata.normalize("NFC", cell) != cell:
                findings.append(finding(
                    LOW, "UNNORMALIZED_UNICODE", lane, rel_path, row_no, index, name,
                    "decomposed form; will not compare equal to its precomposed "
                    "spelling on a join", cell))

            match = SLASH_DATE.match(cell)
            if match:
                a, b, year = match.groups()
                if int(a) <= 12 and int(b) <= 12:
                    findings.append(finding(
                        MEDIUM, "AMBIGUOUS_DATE", lane, rel_path, row_no, index, name,
                        f"could be {year}-{int(a):02d}-{int(b):02d} or "
                        f"{year}-{int(b):02d}-{int(a):02d}; not recoverable without "
                        "knowing the producer's locale", cell))
                else:
                    findings.append(finding(
                        LOW, "NON_ISO_DATE", lane, rel_path, row_no, index, name,
                        "unambiguous but non-portable; ISO-8601 travels", cell))

    for index, cells in columns.items():
        empties = sum(1 for c in cells if c == "")
        tokens = {}
        for c in cells:
            key = c.strip().casefold()
            if key in NULLISH:
                tokens[c.strip()] = tokens.get(c.strip(), 0) + 1
        if empties and tokens:
            spelled = ", ".join(f"{k!r}x{v}" for k, v in sorted(tokens.items()))
            name = header[index] if index < len(header) else None
            if declares_sentinel:
                findings.append(finding(
                    INFO, "NULL_SEMANTICS_DECLARED", lane, rel_path, None, index, name,
                    f"{empties} empty cell(s) alongside {spelled}, in a file that uses "
                    "the \\N null sentinel. The three states ARE distinguishable, but "
                    "only to a reader who knows the convention: ship a column "
                    "dictionary beside the file"))
            else:
                findings.append(finding(
                    MEDIUM, "NULL_SEMANTICS_AMBIGUOUS", lane, rel_path, None, index, name,
                    f"{empties} empty cell(s) alongside {spelled}, and no declared null "
                    "sentinel; a reader cannot tell 'never recorded' from 'recorded as "
                    "empty' from 'not applicable', and those are three different facts"))

    return findings, stats


SELF_FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def scan_tree(root, lane_filter=None, skip_lane=None, include_self_fixtures=False):
    findings, files, stats = [], [], {"rows": 0, "cells": 0, "neutralized": 0}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        # This auditor's own fixtures are DELIBERATELY broken -- they are its
        # self-test corpus. Counting them as delivery-kit findings would report
        # an injection risk in the kit that is really a test asset, which is the
        # same cry-wolf failure the rest of this tool exists to avoid. Found by
        # running the tool from its landed repo path, where --root .. reaches
        # them. Use --include-self-fixtures to audit them on purpose.
        if not include_self_fixtures and \
                os.path.abspath(dirpath).startswith(SELF_FIXTURES):
            continue
        for name in sorted(filenames):
            if not name.lower().endswith(".csv"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            lane = rel.split(os.sep)[0]
            if lane_filter and lane != lane_filter:
                continue
            if skip_lane and lane == skip_lane:
                continue
            file_findings, file_stats = scan_csv(full, lane, rel)
            findings.extend(file_findings)
            files.append(rel)
            for key in stats:
                stats[key] += file_stats[key]
    findings.sort(key=lambda f: (f["lane"], f["path"], f["code"],
                                 f["row"] if f["row"] is not None else -1,
                                 f["column_index"] if f["column_index"] is not None else -1))
    return findings, files, stats


# ------------------------------------------------------------------ writing --

def csv_cell(value):
    """The auditor's own output obeys the rule the auditor enforces.

    Its findings quote offending cells, several of which begin with ``=``. Writing
    those bare would make the report itself an injection vector -- an auditor that
    fails its own check has no standing.
    """
    if value is None:
        return "\\N"
    text = unicodedata.normalize("NFC", str(value))
    if looks_like_formula(text) or text.startswith("'"):
        text = "'" + text
    if text.startswith("\\"):
        text = "\\" + text
    return text


def md_cell(value):
    if value is None:
        return "—"
    text = unicodedata.normalize("NFC", str(value)).replace("\\", "\\\\").replace("|", "\\|")
    return text.replace("\r\n", " ⏎ ").replace("\n", " ⏎ ").replace("\r", " ⏎ ")


def write_findings_csv(path, findings):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(FINDING_COLUMNS)
        for item in findings:
            writer.writerow([csv_cell(item.get(name)) for name in FINDING_COLUMNS])


def write_report(path, findings, files, stats, root):
    by_lane = {}
    for item in findings:
        by_lane.setdefault(item["lane"], []).append(item)
    counts = {}
    for item in findings:
        counts[item["code"]] = counts.get(item["code"], 0) + 1

    with open(path, "w", encoding="utf-8") as fh:
        w = fh.write
        w("# CSV export-safety audit — UIOWA RFQ 18649 delivery kit\n\n")
        w("Read-only audit of every published `*.csv` in the delivery kit, against the "
          "one standard they all share: **the file has to be usable by a Clark's or "
          "University reader who does not have the producing environment.**\n\n")
        w("**This report edits nothing.** Findings are handed to the lane that owns the "
          "file, with the exact path, row and column.\n\n")
        w(f"- Files scanned: **{len(files)}** across **{len({f.split(os.sep)[0] for f in files})}** lane(s)\n")
        w(f"- Data rows: **{stats['rows']}** · cells: **{stats['cells']}**\n")
        w(f"- Cells already neutralized against formula injection: **{stats['neutralized']}**\n")
        w(f"- Findings: **{len(findings)}**\n\n")
        if counts:
            w("| Code | Count |\n|---|---|\n")
            for code, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
                w(f"| `{code}` | {count} |\n")
            w("\n")

        w("## What a clean result does not mean\n\n")
        w("Zero findings means **no issue detected by these eight checks** — never "
          "\"certified\", \"compliant\" or \"safe\". A file that could not be read is "
          "reported as `UNREADABLE` and counts as UNKNOWN, never as a pass. These checks "
          "look at bytes, not at whether the numbers in the file are right.\n\n")

        if not findings:
            w("## Findings\n\nNone detected by these checks.\n")
            return

        w("## Findings by lane\n\n")
        for lane in sorted(by_lane):
            items = by_lane[lane]
            w(f"### `{lane}` — {len(items)} finding(s)\n\n")
            w("| Severity | Code | File | Row | Column | Detail |\n|---|---|---|---|---|---|\n")
            for item in items:
                where = os.path.relpath(item["path"], lane) if item["path"] != lane else item["path"]
                w(f"| {item['severity']} | `{item['code']}` | `{md_cell(where)}` | "
                  f"{md_cell(item['row'])} | {md_cell(item['column_name'])} | "
                  f"{md_cell(item['detail'])} |\n")
            w("\n")


def run(root, out_dir, lane_filter=None, skip_lane=None, include_self_fixtures=False):
    findings, files, stats = scan_tree(root, lane_filter, skip_lane, include_self_fixtures)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "findings.json"), "w", encoding="utf-8") as fh:
        json.dump({"root": os.path.basename(os.path.abspath(root)),
                   "files_scanned": files, "stats": stats, "findings": findings},
                  fh, ensure_ascii=False, sort_keys=True, indent=2)
        fh.write("\n")
    write_findings_csv(os.path.join(out_dir, "findings.csv"), findings)
    write_report(os.path.join(out_dir, "export_safety_report.md"),
                 findings, files, stats, root)
    return findings, files, stats


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["scan"])
    parser.add_argument("--root", default=os.path.dirname(here),
                        help="directory to walk (default: the sibling lanes)")
    parser.add_argument("--out", default=os.path.join(here, "examples"))
    parser.add_argument("--lane", default=None, help="audit one lane only")
    parser.add_argument("--skip-lane", default=None)
    parser.add_argument("--include-self-fixtures", action="store_true",
                        help="also audit this tool's own deliberately-broken fixtures")
    parser.add_argument("--fail-on", default=None, choices=[HIGH, MEDIUM, LOW, INFO],
                        help="exit 1 if any finding is at or above this severity")
    args = parser.parse_args(argv)

    findings, files, stats = run(args.root, args.out, args.lane, args.skip_lane,
                                 args.include_self_fixtures)
    counts = {}
    for item in findings:
        counts[item["code"]] = counts.get(item["code"], 0) + 1
    lanes = len({f.split(os.sep)[0] for f in files})
    print(f"files={len(files)} lanes={lanes} rows={stats['rows']} cells={stats['cells']} "
          f"neutralized={stats['neutralized']} findings={len(findings)}")
    for code, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {count:>5}  {code}")
    if args.fail_on:
        order = [INFO, LOW, MEDIUM, HIGH]
        bar = order.index(args.fail_on)
        if any(order.index(f["severity"]) >= bar for f in findings):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
