#!/usr/bin/env python3
"""Strict-parser conformance audit for every published *.json in the delivery kit.

Companion to ``export_safety.py``. Same contract: read-only outside ``--out``,
findings handed to the owning lane, a clean result is never a certification.

The CSV auditor asks "can a spreadsheet reader open this". This one asks the
JSON equivalent: **can a reader who is not Python parse this file at all?**
Python's ``json`` module is more permissive than the JSON specification in ways
that produce files only Python can read:

* ``json.dump`` writes bare ``NaN``, ``Infinity`` and ``-Infinity`` by default.
  ``JSON.parse`` in a browser, Go's ``encoding/json`` and Java's Jackson all
  reject them outright. The file does not partially work; it does not open.
  ``allow_nan=False`` is the producer-side fix.
* ``json.load`` silently keeps the LAST of two identical keys in one object, so
  a duplicated key loses data with no error anywhere.
* A lone surrogate escape produces a str Python accepts and strict UTF-8 does
  not, so the file cannot be re-encoded.
* An integer above 2^53 loses precision in any JavaScript reader, silently.

Python 3 standard library only. No network.
"""

import argparse
import json
import os
import sys
import unicodedata

from export_safety import HIGH, MEDIUM, LOW, INFO, csv_cell, md_cell

FINDING_COLUMNS = ["severity", "code", "lane", "path", "location", "detail", "sample"]
JS_SAFE_INT = 2 ** 53
SELF_FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def safe_text(value):
    """Make a value writable, whatever it came from.

    An auditor has to survive the input it detects. The first run of this tool
    crashed writing its own findings, because the sample it had captured for a
    LONE_SURROGATE finding was itself a lone surrogate and could not be encoded
    as UTF-8. A detector that dies on a detection is not a detector.
    """
    if value is None:
        return None
    return str(value).encode("utf-8", "backslashreplace").decode("utf-8")


def finding(severity, code, lane, path, location, detail, sample=""):
    return {"severity": severity, "code": code, "lane": lane, "path": path,
            "location": safe_text(location), "detail": safe_text(detail),
            "sample": safe_text(sample)[:120]}


def _pairs_hook(duplicates):
    def hook(pairs):
        seen = {}
        for key, _ in pairs:
            if key in seen:
                duplicates.append(key)
            seen[key] = True
        return dict(pairs)
    return hook


def _walk(node, path, emit):
    if isinstance(node, dict):
        for key, value in node.items():
            if unicodedata.normalize("NFC", key) != key:
                emit("UNNORMALIZED_UNICODE", LOW, f"{path}.{key}",
                     "object key is in decomposed form; it will not match its "
                     "precomposed spelling on a lookup", key)
            _walk(value, f"{path}.{key}", emit)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk(value, f"{path}[{index}]", emit)
    elif isinstance(node, bool):
        return
    elif isinstance(node, int):
        if abs(node) > JS_SAFE_INT:
            emit("INT_PRECISION_LOSS", MEDIUM, path,
                 f"{node} exceeds 2^53; a JavaScript reader rounds it silently and "
                 "reports no error", node)
    elif isinstance(node, str):
        if any(0xD800 <= ord(c) <= 0xDFFF for c in node):
            emit("LONE_SURROGATE", HIGH, path,
                 "unpaired surrogate; the value cannot be re-encoded as UTF-8", node)
        if any(ord(c) < 0x20 and c not in "\t\n\r" for c in node):
            emit("CONTROL_CHAR_IN_STRING", MEDIUM, path,
                 "raw control character in a string value", repr(node))
        if unicodedata.normalize("NFC", node) != node:
            emit("UNNORMALIZED_UNICODE", LOW, path,
                 "decomposed form; will not compare equal to its precomposed "
                 "spelling on a join", node)


def scan_json(path, lane, rel_path):
    findings = []

    def emit(code, severity, location, detail, sample=""):
        findings.append(finding(severity, code, lane, rel_path, location, detail, sample))

    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        emit("UNREADABLE", MEDIUM, None, f"cannot open: {exc}")
        return findings

    if not raw.strip():
        # A zero-byte artifact is not a pass. It is a missing output that looks
        # like a present one.
        emit("EMPTY_FILE", MEDIUM, None,
             "file is empty; an absent artifact must not read as a produced one")
        return findings
    if raw.startswith(b"\xef\xbb\xbf"):
        emit("BOM_PRESENT", MEDIUM, None,
             "UTF-8 BOM before the first token; several strict parsers reject it")
        raw = raw[3:]
    if not raw.endswith(b"\n"):
        emit("NO_TRAILING_NEWLINE", INFO, None,
             "no trailing newline; every diff of this file reports a changed last line")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        emit("NOT_UTF8", HIGH, None, f"not valid UTF-8: {exc}")
        return findings

    # Non-strict literals are detected by the parser, not by scanning the text.
    # A regex over the raw bytes flags the WORD "NaN" wherever it appears -- this
    # auditor's own findings file says "bare NaN is not JSON" in its prose, and
    # the regex version dutifully reported the auditor to itself. parse_constant
    # fires only on a real bare token, so it cannot false-positive.
    constants = []
    duplicates = []
    try:
        document = json.loads(
            text,
            object_pairs_hook=_pairs_hook(duplicates),
            parse_constant=lambda name: constants.append(name) or float("nan"),
        )
    except ValueError as exc:
        emit("INVALID_JSON", HIGH, None, f"does not parse: {exc}")
        return findings

    for name in constants:
        emit("NON_STRICT_LITERAL", HIGH, "value",
             f"bare {name} is not JSON; JSON.parse, Go and Jackson reject the whole "
             "file. Producer fix: json.dump(..., allow_nan=False)", name)

    for key in sorted(set(duplicates)):
        emit("DUPLICATE_OBJECT_KEY", HIGH, key,
             f"key {key!r} appears more than once in one object; a parser keeps the "
             "last and the earlier value is lost with no error", key)

    _walk(document, "$", emit)
    return findings


def scan_tree(root, lane_filter=None, skip_lane=None, include_self_fixtures=False,
               lane_prefix=None):
    findings, files = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        if not include_self_fixtures and \
                os.path.abspath(dirpath).startswith(SELF_FIXTURES):
            continue
        for name in sorted(filenames):
            if not name.lower().endswith(".json"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            lane = rel.split(os.sep)[0]
            if lane_filter and lane != lane_filter:
                continue
            if skip_lane and lane == skip_lane:
                continue
            # The repository holds many unrelated projects. Auditing them and
            # reporting the result as a delivery-kit finding would be wrong twice
            # over: out of scope, and handed to an owner who never asked.
            if lane_prefix and not lane.startswith(lane_prefix):
                continue
            findings.extend(scan_json(full, lane, rel))
            files.append(rel)
    findings.sort(key=lambda f: (f["lane"], f["path"], f["code"], f["location"] or ""))
    return findings, files


def write_report(path, findings, files):
    counts = {}
    for item in findings:
        counts[item["code"]] = counts.get(item["code"], 0) + 1
    by_lane = {}
    for item in findings:
        by_lane.setdefault(item["lane"], []).append(item)
    with open(path, "w", encoding="utf-8") as fh:
        w = fh.write
        w("# JSON strict-parser conformance audit\n\n")
        w("Read-only. Asks whether a reader who is not Python can parse each published "
          "JSON artifact at all.\n\n")
        w(f"- Files scanned: **{len(files)}**\n- Findings: **{len(findings)}**\n\n")
        if counts:
            w("| Code | Count |\n|---|---|\n")
            for code, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
                w(f"| `{code}` | {count} |\n")
            w("\n")
        w("Zero findings means no issue detected by these ten checks — never "
          "\"certified\" or \"valid for a given schema\". An unreadable or empty file is "
          "reported, never counted as a pass.\n\n")
        if not findings:
            w("## Findings\n\nNone detected by these checks.\n")
            return
        w("## Findings by lane\n\n")
        for lane in sorted(by_lane):
            w(f"### `{lane}` — {len(by_lane[lane])} finding(s)\n\n")
            w("| Severity | Code | File | Location | Detail |\n|---|---|---|---|---|\n")
            for item in by_lane[lane]:
                w(f"| {item['severity']} | `{item['code']}` | `{md_cell(item['path'])}` | "
                  f"{md_cell(item['location'])} | {md_cell(item['detail'])} |\n")
            w("\n")


def run(root, out_dir, lane_filter=None, skip_lane=None, include_self_fixtures=False,
        lane_prefix=None):
    findings, files = scan_tree(root, lane_filter, skip_lane, include_self_fixtures,
                                lane_prefix)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "json_findings.json"), "w", encoding="utf-8") as fh:
        json.dump({"files_scanned": files, "findings": findings},
                  fh, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        fh.write("\n")
    import csv as _csv
    with open(os.path.join(out_dir, "json_findings.csv"), "w",
              encoding="utf-8", newline="") as fh:
        writer = _csv.writer(fh, lineterminator="\n")
        writer.writerow(FINDING_COLUMNS)
        for item in findings:
            writer.writerow([csv_cell(item.get(n)) for n in FINDING_COLUMNS])
    write_report(os.path.join(out_dir, "json_safety_report.md"), findings, files)
    return findings, files


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["scan"])
    parser.add_argument("--root", default=os.path.dirname(here))
    parser.add_argument("--out", default=os.path.join(here, "examples"))
    parser.add_argument("--lane", default=None)
    parser.add_argument("--skip-lane", default=None)
    parser.add_argument("--include-self-fixtures", action="store_true")
    parser.add_argument("--lane-prefix", default=None,
                        help="only audit lanes whose directory name starts with this")
    parser.add_argument("--fail-on", default=None, choices=[HIGH, MEDIUM, LOW, INFO])
    args = parser.parse_args(argv)

    findings, files = run(args.root, args.out, args.lane, args.skip_lane,
                          args.include_self_fixtures, args.lane_prefix)
    counts = {}
    for item in findings:
        counts[item["code"]] = counts.get(item["code"], 0) + 1
    print(f"files={len(files)} findings={len(findings)}")
    for code, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {count:>5}  {code}")
    if args.fail_on:
        order = [INFO, LOW, MEDIUM, HIGH]
        if any(order.index(f["severity"]) >= order.index(args.fail_on) for f in findings):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
