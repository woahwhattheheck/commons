#!/usr/bin/env python3
"""Build an offline comparison view from the existing uiowa-synthesis/v1 records.

This presents supplied annotations. It does not calculate maturity, causal themes,
prevalence, independent observations, or factual verification of the input.
"""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
import csv
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import re
import sys

GROUPS = ("ESS", "RIS", "IAM")
DIMENSIONS = ("software", "security", "deployment", "ai")
ROLES = ("support_ids", "dissent_ids", "limitation_ids", "mechanism_source_ids")
MAX_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 5000
MAX_TEXT = 20000
TEXT_FIELDS = ("finding_id", "group", "dimension", "practice_key", "state", "basis",
               "service_id", "statement", "context", "window_start", "window_end", "topology")
OPTIONAL_FIELDS = ("dependency_id", "mechanism_id", "mechanism_basis", "rationale")
SOURCE_FIELDS = ("source_id", "source_ref", "locator", "version", "excerpt", "evidence_kind")
COLUMNS = ("dataset_id", "data_status", "input_sha256", "dimension", "practice_key",
           "window_start", "window_end", "group", "finding_id", "state", "basis",
           "service_id", "statement", "context", "topology", "dependency_id",
           "mechanism_id", "mechanism_basis", "rationale", "support_evidence_json",
           "dissent_evidence_json", "limitation_evidence_json", "mechanism_evidence_json")


class ComparisonError(ValueError):
    """Input or output cannot be represented without hiding a structural problem."""


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ComparisonError(f"Duplicate JSON member: {key!r}")
        result[key] = value
    return result


def _constant(value):
    raise ComparisonError(f"Non-finite JSON value: {value}")


def text(record, field, *, optional=False):
    value = record.get(field)
    if optional and value is None:
        return None
    if not isinstance(value, str) or len(value) > MAX_TEXT:
        raise ComparisonError(f"{field} must be text of at most {MAX_TEXT} characters")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ComparisonError(f"{field} contains invalid Unicode") from exc
    if field not in {"context", "statement", "excerpt", "rationale"} and not value.strip():
        raise ComparisonError(f"{field} must not be empty")
    return value


def parse(raw: bytes) -> dict:
    if not raw or len(raw) > MAX_BYTES:
        raise ComparisonError(f"Input must contain 1..{MAX_BYTES} bytes")
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs,
                           parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ComparisonError(f"Invalid JSON input: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != "uiowa-synthesis/v1":
        raise ComparisonError("Expected existing schema uiowa-synthesis/v1")
    text(value, "dataset_id")
    text(value, "data_status")
    for field in ("sources", "findings"):
        if not isinstance(value.get(field), list) or len(value[field]) > MAX_RECORDS:
            raise ComparisonError(f"{field} must be an array with at most {MAX_RECORDS} records")
    return value


def project(raw: bytes) -> dict:
    native = parse(raw)
    sources = {}
    for item in native["sources"]:
        if not isinstance(item, dict):
            raise ComparisonError("Every source must be an object")
        source = {key: text(item, key) for key in SOURCE_FIELDS}
        for key in ("origin_id", "sha256"):
            source[key] = text(item, key, optional=True)
        if source["source_id"] in sources:
            raise ComparisonError(f"Duplicate source ID: {source['source_id']}")
        sources[source["source_id"]] = source
    grouped = defaultdict(list)
    seen = set()
    for item in native["findings"]:
        if not isinstance(item, dict):
            raise ComparisonError("Every finding must be an object")
        finding = {key: text(item, key) for key in TEXT_FIELDS}
        finding.update({key: text(item, key, optional=True) for key in OPTIONAL_FIELDS})
        if finding["finding_id"] in seen:
            raise ComparisonError(f"Duplicate finding ID: {finding['finding_id']}")
        seen.add(finding["finding_id"])
        for key, allowed in (("group", GROUPS), ("dimension", DIMENSIONS),
                             ("state", ("gap", "strength", "unknown", "not_applicable")),
                             ("basis", ("observed", "reported", "unknown")),
                             ("topology", ("shared", "local", "unknown"))):
            if finding[key] not in allowed:
                raise ComparisonError(f"Unsupported {key}: {finding[key]!r}")
        try:
            window = [date.fromisoformat(finding[key]) for key in ("window_start", "window_end")]
            if any(day.isoformat() != finding[key] for day, key in zip(window, ("window_start", "window_end"))) or window[0] > window[1]:
                raise ValueError("Dates must be ordered YYYY-MM-DD")
        except ValueError as exc:
            raise ComparisonError(f"Invalid observation window: {finding['finding_id']}") from exc
        if finding["state"] in {"unknown", "not_applicable"} and not (finding["rationale"] or "").strip():
            raise ComparisonError("Unknown and not-applicable records need their supplied rationale")
        if finding["topology"] == "shared" and not finding["dependency_id"]:
            raise ComparisonError("Shared topology needs its supplied dependency ID")
        for role in ROLES:
            refs = item.get(role, [])
            if not isinstance(refs, list) or len(refs) > MAX_RECORDS:
                raise ComparisonError(f"{role} must be a bounded array")
            if any(not isinstance(ref, str) or ref not in sources for ref in refs):
                raise ComparisonError(f"Unresolved evidence reference in {finding['finding_id']}: {role}")
            finding[role] = refs
        key = tuple(finding[key] for key in ("dimension", "practice_key", "window_start", "window_end"))
        grouped[key].append(finding)
    rows = []
    for key, findings in sorted(grouped.items()):
        findings.sort(key=lambda finding: (GROUPS.index(finding["group"]), finding["finding_id"]))
        rows.append({"row_id": digest(compact(key).encode()), "dimension": key[0],
                     "practice_key": key[1], "window_start": key[2], "window_end": key[3],
                     "findings": findings})
    return {"schema": "uiowa-comparison-view/v1", "dataset_id": native["dataset_id"],
            "data_status": native["data_status"], "input_sha256": digest(raw),
            "original_base64": base64.b64encode(raw).decode("ascii"),
            "sources": sources, "rows": rows, "columns": COLUMNS}


def export_rows(model, rows=None, groups=GROUPS):
    for row in model["rows"] if rows is None else rows:
        for group in groups:
            findings = [finding for finding in row["findings"] if finding["group"] == group]
            for finding in findings or [{"state": "NOT_SUPPLIED", "rationale": "No record supplied; not a finding of absence."}]:
                cells = {**{key: model[key] for key in ("dataset_id", "data_status")},
                         "input_sha256": model["input_sha256"],
                         **{key: row[key] for key in ("dimension", "practice_key", "window_start", "window_end")},
                         "group": group}
                cells.update({key: finding.get(key) or "" for key in (*TEXT_FIELDS, *OPTIONAL_FIELDS)
                              if key not in {"group", "dimension", "practice_key", "window_start", "window_end"}})
                for role, column in zip(ROLES, COLUMNS[-4:]):
                    cells[column] = compact([model["sources"][source] for source in finding.get(role, [])])
                yield [cells.get(column, "") for column in COLUMNS]


def csv_cell(value):
    value = str(value)
    return "'" + value if value and (value[0] in "\t\r\n" or re.match(r"^\s*[=+@-]", value)) else value


def to_csv(model) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows([csv_cell(cell) for cell in row] for row in export_rows(model))
    return output.getvalue().encode("utf-8")


def html(model):
    root = Path(__file__).parent
    # Escape all HTML-significant codepoints before embedding untrusted data in
    # the inert JSON script. Dynamic nodes are subsequently made with textContent.
    payload = compact(model)
    for character, replacement in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                                    ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        payload = payload.replace(character, replacement)
    template = (root / "template.html").read_text(encoding="utf-8")
    assets = {"STYLE": (root / "view.css").read_text(encoding="utf-8"),
              "SCRIPT": (root / "view.js").read_text(encoding="utf-8"), "DATA": payload}
    return re.sub(r"@@(STYLE|SCRIPT|DATA)@@", lambda match: assets[match[1]], template).encode("utf-8")


def build(source: Path, output: Path) -> dict:
    with source.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    model = project(raw)
    artifacts = {"comparison.html": html(model), "summary.csv": to_csv(model), "assessment.json": raw}
    manifest = {"schema": "uiowa-comparison-build/v1", "dataset_id": model["dataset_id"],
                "data_status": model["data_status"], "input_sha256": digest(raw),
                "comparison_rows": len(model["rows"]),
                "finding_records": sum(len(row["findings"]) for row in model["rows"]),
                "source_records": len(model["sources"]),
                "artifacts": {name: digest(data) for name, data in artifacts.items()},
                "interpretation": "Supplied annotations, not verified University findings or maturity ratings."}
    # Compute every artifact before claiming a new output directory. Never reuse,
    # delete, or overwrite an existing path, even if that directory is empty.
    output.mkdir(parents=False, exist_ok=False)
    for name, data in artifacts.items():
        with (output / name).open("xb") as stream:
            stream.write(data)
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assessment", type=Path)
    parser.add_argument("--out", required=True, type=Path, help="New output directory; parent must exist")
    args = parser.parse_args(argv)
    try:
        manifest = build(args.assessment, args.out)
    except (OSError, ComparisonError) as exc:
        print(f"COMPARISON_NOT_BUILT: {exc}", file=sys.stderr)
        return 2
    print(compact(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
