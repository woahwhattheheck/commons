"""Lossless offline CSV comment staging; never makes review decisions.

UIOWA-124. Python standard library only. Comment IDs are scoped by source_id;
record text is exact, references are exact, and conflicting reimports are retained.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

SCHEMA = "uiowa-review-import/v1"
REQUIRED = ("comment_id", "reviewer_role", "comment_text", "finding_id", "report_version")
OPTIONAL = ("finding_namespace", "comment_kind", "proposed_edit")


class ImportFormatError(ValueError):
    """The source cannot be interpreted without guessing its structure."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_csv(raw: bytes, source_id: str, source_name: str) -> dict:
    """Parse UTF-8/BOM CSV, retaining logical records and physical line spans.

    Structural failures abort the whole import. Semantic row problems are retained
    as diagnostics by stage_comments. No CSV dialect or encoding is guessed.
    """
    if not isinstance(raw, bytes):
        raise ImportFormatError("CSV input must be bytes")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ImportFormatError("source_id must be an explicit nonempty string")
    if not isinstance(source_name, str) or not source_name:
        raise ImportFormatError("source_name must be an explicit nonempty string")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportFormatError(f"invalid UTF-8 at byte {exc.start}") from exc
    if "\x00" in text:
        raise ImportFormatError("NUL byte in CSV; binary/spreadsheet files need CSV export first")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ImportFormatError("CSV requires a header") from exc
    if not header or any(not x or x != x.strip() for x in header):
        raise ImportFormatError("header names must be nonempty without surrounding whitespace")
    if len(header) != len(set(header)):
        raise ImportFormatError("duplicate CSV column names")
    missing = sorted(set(REQUIRED) - set(header))
    if missing:
        raise ImportFormatError("missing columns: " + ", ".join(missing))
    rows = []
    previous_end = reader.line_num
    try:
        for number, cells in enumerate(reader, start=1):
            start, end = previous_end + 1, reader.line_num
            previous_end = end
            if len(cells) != len(header):
                raise ImportFormatError(
                    f"record {number}, lines {start}-{end}: "
                    f"expected {len(header)} columns, got {len(cells)}")
            rows.append({"record_number": number, "line_start": start,
                         "line_end": end, "values": dict(zip(header, cells))})
    except csv.Error as exc:
        raise ImportFormatError(f"malformed CSV near physical line {reader.line_num}: {exc}") from exc
    return {"schema": SCHEMA, "source": {"source_id": source_id,
            "source_name": source_name, "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_length": len(raw), "encoding": "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8",
            "columns": header}, "rows": rows}


def validate_catalog(catalog: dict) -> list[dict]:
    """A catalog must explicitly identify each finding's namespace and revision.

    Entries are not deduplicated: duplicate candidates are an ambiguity to resolve.
    Additional fields (locators, upstream IDs) survive into the resolved target.
    """
    if not isinstance(catalog, dict) or not isinstance(catalog.get("findings"), list):
        raise ImportFormatError("catalog requires a findings array")
    for index, target in enumerate(catalog["findings"]):
        if not isinstance(target, dict) or any(
            not isinstance(target.get(k), str) or not target[k].strip()
            for k in ("finding_id", "namespace", "report_version")
        ):
            raise ImportFormatError(f"catalog finding {index}: missing explicit identity/revision")
    return catalog["findings"]


def empty_state() -> dict:
    return {"schema": SCHEMA, "comments": []}


def _state_index(state: dict) -> dict[tuple[str, str], dict]:
    if not isinstance(state, dict) or state.get("schema") != SCHEMA or not isinstance(state.get("comments"), list):
        raise ImportFormatError("invalid prior import state schema")
    indexed = {}
    for item in state["comments"]:
        try:
            key = item["source_id"], item["comment_id"]
            if key in indexed or any(not isinstance(v, str) or not v.strip() for v in key):
                raise ValueError("duplicate/invalid comment identity")
            variants = item["variants"]
            if not isinstance(variants, list) or not variants:
                raise ValueError("empty variants")
            seen = set()
            for variant in variants:
                values = variant["values"]
                if not isinstance(values, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in values.items()):
                    raise ValueError("invalid source values")
                if any(k not in values for k in REQUIRED) or values["comment_id"] != key[1]:
                    raise ValueError("identity/required field mismatch")
                fingerprint = digest(values)
                if variant["fingerprint"] != fingerprint or fingerprint in seen:
                    raise ValueError("invalid/duplicate variant fingerprint")
                seen.add(fingerprint)
                if not isinstance(variant["occurrences"], list) or not variant["occurrences"]:
                    raise ValueError("missing source occurrences")
                for occurrence in variant["occurrences"]:
                    if not isinstance(occurrence, dict) or occurrence.get("source_id") != key[0]:
                        raise ValueError("source occurrence identity mismatch")
                    if any(type(occurrence.get(k)) is not int or occurrence[k] < 1
                           for k in ("record_number", "line_start", "line_end")):
                        raise ValueError("invalid source record/line locator")
                    if occurrence["line_start"] > occurrence["line_end"]:
                        raise ValueError("reversed source line locator")
                    source_hash = occurrence.get("sha256", "")
                    if not isinstance(source_hash, str) or len(source_hash) != 64 or any(
                            c not in "0123456789abcdef" for c in source_hash):
                        raise ValueError("invalid source digest")
            indexed[key] = item
        except (KeyError, TypeError, ValueError) as exc:
            raise ImportFormatError(f"invalid prior import state: {exc}") from exc
    return indexed


def _resolve(values: dict, targets: list[dict]) -> tuple[dict | None, list[dict]]:
    diagnostics = []
    for field in REQUIRED:
        if not values[field].strip():
            diagnostics.append({"code": "MISSING_VALUE", "field": field})
    for field in ("comment_id", "finding_id", "report_version", "finding_namespace"):
        value = values.get(field, "")
        if value and value != value.strip():
            diagnostics.append({"code": "REFERENCE_WHITESPACE", "field": field,
                                "value": value, "suggestion": "correct the source explicitly; no trimming was applied"})
    if diagnostics:
        return None, diagnostics
    same_id = [t for t in targets if t["finding_id"] == values["finding_id"]]
    ns = values.get("finding_namespace", "")
    if ns:
        same_id = [t for t in same_id if t["namespace"] == ns]
    if not same_id:
        return None, [{"code": "UNKNOWN_FINDING", "finding_id": values["finding_id"], "namespace": ns}]
    matching = [t for t in same_id if t["report_version"] == values["report_version"]]
    if not matching:
        return None, [{"code": "VERSION_MISMATCH", "requested": values["report_version"],
                       "available": sorted(set(t["report_version"] for t in same_id))}]
    if len(matching) != 1:
        return None, [{"code": "AMBIGUOUS_FINDING", "candidates": deepcopy(matching)}]
    return deepcopy(matching[0]), []


def stage_comments(raw: bytes, source_id: str, source_name: str,
                   catalog: dict, prior: dict | None = None) -> dict:
    """Return immutable replay state + ready comments + explicit unresolved rows.

    Same source/comment/values is idempotent, even if the row moved. Changes become
    a retained variant and withdraw that identity from *this staged ready set*.
    This is not a retroactive undo of a tracker action; no tracker is mutated here.
    """
    parsed = parse_csv(raw, source_id, source_name)
    targets = validate_catalog(catalog)
    state = deepcopy(prior) if prior is not None else empty_state()
    indexed = _state_index(state)
    row_problems = []
    for row in parsed["rows"]:
        values = row["values"]
        occurrence = {**parsed["source"], **{k: row[k] for k in ("record_number", "line_start", "line_end")}}
        if not values["comment_id"].strip():
            row_problems.append({"status": "UNRESOLVED", "values": deepcopy(values),
                                 "occurrence": occurrence,
                                 "diagnostics": [{"code": "MISSING_VALUE", "field": "comment_id"}]})
            continue
        key = source_id, values["comment_id"]
        fingerprint = digest(values)
        item = indexed.setdefault(key, {"source_id": source_id, "comment_id": key[1], "variants": []})
        variant = next((v for v in item["variants"] if v["fingerprint"] == fingerprint), None)
        if variant is None:
            variant = {"fingerprint": fingerprint, "values": deepcopy(values), "occurrences": []}
            item["variants"].append(variant)
        if occurrence not in variant["occurrences"]:
            variant["occurrences"].append(occurrence)
    ready, unresolved = [], []
    state["comments"] = [indexed[k] for k in sorted(indexed)]
    for item in state["comments"]:
        item["variants"].sort(key=lambda v: v["fingerprint"])
        for v in item["variants"]:
            v["occurrences"].sort(key=lambda o: canonical(o))
        common = {"source_id": item["source_id"], "comment_id": item["comment_id"],
                  "import_key": digest([item["source_id"], item["comment_id"]])}
        if len(item["variants"]) != 1:
            unresolved.append({**common, "status": "UNRESOLVED", "variants": deepcopy(item["variants"]),
                               "diagnostics": [{"code": "COMMENT_CONTENT_CONFLICT", "variant_count": len(item["variants"])}]})
            continue
        variant = item["variants"][0]
        target, problems = _resolve(variant["values"], targets)
        record = {**common, **deepcopy(variant), "status": "UNRESOLVED" if problems else "READY",
                  "target": target, "diagnostics": problems}
        (unresolved if problems else ready).append(record)
    return {"schema": SCHEMA, "source": parsed["source"], "catalog_sha256": digest(catalog),
            "state": state, "ready": ready, "unresolved": unresolved,
            "unkeyed_rows": row_problems,
            "summary": {"input_records": len(parsed["rows"]), "unique_comments": len(state["comments"]),
                        "ready": len(ready), "unresolved": len(unresolved), "unkeyed_rows": len(row_problems)}}


def render_report(result: dict) -> str:
    """Readable diagnostic report. JSON retains original text without escaping."""
    out = ["# Reviewer-comment import", "", "Import readiness is not a review decision or acceptance.", "",
           f"Source: {result['source']['source_name']}", f"Source SHA-256: {result['source']['sha256']}", "",
           "```json", json.dumps(result["summary"], indent=2), "```", ""]
    for record in result["ready"] + result["unresolved"]:
        out += [f"## {record['comment_id']} — {record['status']}", ""]
        for v in record.get("variants", [record]):
            out += ["### Original comment", ""]
            # HTML escaping prevents raw HTML execution; blockquote retains visible lines.
            import html
            out += ["> " + html.escape(line) for line in v["values"]["comment_text"].splitlines()]
            out += ["", "Source occurrences: " + "; ".join(
                f"record {o['record_number']}, physical lines {o['line_start']}-{o['line_end']}"
                for o in v["occurrences"]), ""]
        out += ["Diagnostics: " + (", ".join(d["code"] for d in record["diagnostics"]) or "none"), ""]
    for row in result["unkeyed_rows"]:
        out += [f"## Unkeyed source record {row['occurrence']['record_number']}", "",
                "MISSING_VALUE: comment_id. Full source content retained in JSON.", ""]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--prior", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="New JSON result file; never overwrites")
    parser.add_argument("--report", type=Path, help="Optional new Markdown diagnostic report")
    args = parser.parse_args()
    try:
        prior = json.loads(args.prior.read_text(encoding="utf-8")) if args.prior else None
        if prior is not None and "state" in prior:
            prior = prior["state"]
        result = stage_comments(args.csv.read_bytes(), args.source_id, args.csv.name,
                                json.loads(args.catalog.read_text(encoding="utf-8")), prior)
        # Reserve destinations before writing to avoid touching an existing artifact.
        if args.report and args.out.resolve() == args.report.resolve():
            raise ImportFormatError("JSON and Markdown require different output paths")
        if args.out.exists() or (args.report and args.report.exists()):
            raise ImportFormatError("output already exists; choose new output filenames")
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        if args.report:
            with args.report.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(render_report(result))
    except (OSError, ImportFormatError, json.JSONDecodeError) as exc:
        parser.exit(2, f"import error: {exc}\n")
    print(json.dumps(result["summary"], sort_keys=True))
    return 1 if result["unresolved"] or result["unkeyed_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
