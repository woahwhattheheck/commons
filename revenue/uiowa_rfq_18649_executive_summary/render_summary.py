#!/usr/bin/env python3
"""Render a leadership briefing from the existing UIOWA-093 trace bundle.

Source statements remain verbatim. Structural trace checks do not authenticate
evidence or make the resulting draft an accepted institutional assessment.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from revenue.uiowa_rfq_18649_traceability_rehearsal import validate_trace

DEFAULT_BUNDLE = ROOT / "revenue/uiowa_rfq_18649_traceability_rehearsal"
SOURCES = ("evidence.csv", "findings.csv", "recommendations.csv", "trace-map.csv",
           "executive-summary.md", "final-report.md")
FIELDS = {
    "evidence.csv": ("evidence_id", "service", "source_type", "source_name", "locator", "observation", "evidence_state"),
    "findings.csv": ("finding_id", "service", "type", "title", "statement", "evidence_ids", "confidence", "limitation"),
    "recommendations.csv": ("recommendation_id", "title", "linked_findings", "action", "expected_outcome", "effort", "dependency"),
    "trace-map.csv": ("statement_id", "report_location", "statement_summary", "recommendation_ids", "finding_ids", "evidence_ids"),
}
NOTICE = ("DRAFT — supplied-record leadership briefing. Structural references were checked; "
          "source authenticity, professional conclusions and institutional acceptance are not established. "
          "The bundled public example is fictional.")


def source_inventory(root: Path) -> dict:
    result = {}
    for name in SOURCES:
        raw = (root / name).read_bytes()
        result[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                        "git_blob_sha1": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}
    return result


def records(root: Path, name: str) -> list[dict]:
    rows = []
    with (root / name).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, strict=True)
        missing = set(FIELDS[name]) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{name}: required briefing columns missing: {sorted(missing)}")
        previous_line = reader.line_num
        for row in reader:
            rows.append({"record": row, "source": {"file": name, "line_start": previous_line + 1,
                                                   "line_end": reader.line_num}})
            previous_line = reader.line_num
    return sorted(rows, key=lambda r: r["record"][FIELDS[name][0]])


def build(root: Path) -> dict:
    root = root.resolve(strict=True)
    before = source_inventory(root)
    validation = validate_trace.validate(root)
    if validation["status"] != "PASS":
        details = "; ".join(f"{i['file']}:{i['row']} {i['code']} {i['detail']}" for i in validation["issues"])
        raise ValueError(f"source trace bundle is {validation['status']}: {details}")
    tables = {name: records(root, name) for name in FIELDS}
    if source_inventory(root) != before:
        raise ValueError("source bundle changed while the briefing was being assembled")
    canonical = json.dumps(before, sort_keys=True, separators=(",", ":")).encode()
    return {"schema": "uiowa-executive-summary/v1", "status": "DRAFT", "notice": NOTICE,
            "source_bundle_sha256": hashlib.sha256(canonical).hexdigest(),
            "source_files": before, "source_validation": validation,
            "findings": tables["findings.csv"], "recommendations": tables["recommendations.csv"],
            "evidence": tables["evidence.csv"], "statement_trace": tables["trace-map.csv"],
            "planning_state": {"priority_and_schedule": "NOT_SUPPLIED",
                               "accountable_owners": "NOT_SUPPLIED",
                               "cash_savings": "NOT_ESTIMATED",
                               "measured_outcome_results": "NOT_SUPPLIED"}}


def text(value: str) -> str:
    value = html.escape(value or "NOT SUPPLIED", quote=True)
    for char, entity in (("\\", "&#92;"), ("|", "&#124;"), ("`", "&#96;"),
                         ("*", "&#42;"), ("_", "&#95;"), ("[", "&#91;"), ("]", "&#93;")):
        value = value.replace(char, entity)
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def refs(value: str, family: str) -> str:
    return ", ".join(f"[{text(ident)}](#{family}-{ident})" for ident in sorted(validate_trace.split_ids(value))) or "None supplied"


def markdown(report: dict) -> str:
    lines = ["# Leadership review briefing", "", NOTICE, "",
             f"Source bundle: `{report['source_bundle_sha256']}`.", "",
             "## Strengths, gaps and uncertainty", "",
             "The following finding text, classifications and confidence labels come from the source register. "
             "Confidence is supplied metadata, not recalculated here. Each limitation travels with its statement.", ""]
    for item in report["findings"]:
        row = item["record"]
        ident = row["finding_id"]
        lines += [f'<a id="finding-{ident}"></a>', "", f"### {text(ident)} — {text(row['title'])}", "",
                  f"{text(row['service'])}; supplied classification: **{text(row['type'])}**; "
                  f"supplied confidence: {text(row['confidence'])}.", "",
                  text(row["statement"]), "", f"**Limitation:** {text(row['limitation'])}", "",
                  "Sources: " + refs(row["evidence_ids"], "evidence") + ".", ""]
    lines += ["## Decisions and practical sequencing", "",
              "These are proposed actions copied from the recommendation register. "
              "Display order follows identifiers, not priority or an approved schedule. "
              "Confirm dependencies, accountable owners and sequencing before adopting a plan.", ""]
    findings = {i["record"]["finding_id"]: i["record"] for i in report["findings"]}
    for item in report["recommendations"]:
        row = item["record"]
        ident = row["recommendation_id"]
        evidence = set()
        for fid in validate_trace.split_ids(row["linked_findings"]):
            evidence.update(validate_trace.split_ids(findings[fid]["evidence_ids"]))
        lines += [f'<a id="recommendation-{ident}"></a>', "", f"### {text(ident)} — {text(row['title'])}", "",
                  f"**Proposed action:** {text(row['action'])}", "",
                  f"**Dependency:** {text(row['dependency'])}", "",
                  f"**Expected outcome, not a measurement:** {text(row['expected_outcome'])}", "",
                  f"**Supplied implementation-effort label:** {text(row['effort'])}. "
                  "This is not a dollar estimate or cash savings.", "",
                  "**Owner, priority, schedule and measured result:** NOT SUPPLIED.", "",
                  "Finding basis: " + refs(row["linked_findings"], "finding") + ". "
                  "Source chain: " + refs(";".join(sorted(evidence)), "evidence") + ".", ""]
    lines += ["## Resource assumptions and outcome follow-up", "",
              "Effort labels and dependencies above are the supplied planning inputs. "
              "No staffing quantity, budget, cash saving, baseline, target, measurement window or realized "
              "benefit is inferred. Record those decisions separately with their source and version. "
              "An expected benefit must not be reported as an observed result.", "",
              "## Statement-to-source navigation", "",
              "Original statement identities and locations are retained below. "
              "Finding and recommendation links point into this portable briefing.", "",
              "| Statement | Original location | Registered statement | Findings | Recommendations | Evidence |",
              "|---|---|---|---|---|---|"]
    for item in report["statement_trace"]:
        row = item["record"]
        lines.append("| " + " | ".join([text(row["statement_id"]), text(row["report_location"]),
                     text(row["statement_summary"]), refs(row["finding_ids"], "finding"),
                     refs(row["recommendation_ids"], "recommendation"), refs(row["evidence_ids"], "evidence")]) + " |")
    lines += ["", "## Evidence locators and retained observations", ""]
    for item in report["evidence"]:
        row = item["record"]
        ident = row["evidence_id"]
        source = item["source"]
        lines += [f'<a id="evidence-{ident}"></a>', "", f"### {text(ident)} — {text(row['source_name'])}", "",
                  f"{text(row['service'])}; {text(row['source_type'])}; supplied state: {text(row['evidence_state'])}.", "",
                  f"**Original locator:** {text(row['locator'])}", "", text(row["observation"]), "",
                  f"Register locator: {text(source['file'])}, lines {source['line_start']}–{source['line_end']}.", ""]
    lines += ["## Exact source versions", "",
              "These hashes identify the input files used to render this draft, not the authenticity "
              "of underlying source documents. Structural PASS is not substantive approval.", "",
              "| Source file | Bytes | Git blob | SHA-256 |", "|---|---:|---|---|"]
    for name, identity in sorted(report["source_files"].items()):
        lines.append(f"| {text(name)} | {identity['bytes']} | {identity['git_blob_sha1']} | {identity['sha256']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", nargs="?", type=Path, default=DEFAULT_BUNDLE,
                        help="Existing UIOWA-093 trace bundle directory")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    try:
        report = build(args.bundle)
        rendered = markdown(report) if args.format == "markdown" else json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        print(rendered, end="")
        return 0
    except (OSError, ValueError, csv.Error, KeyError, TypeError) as exc:
        print(f"executive-summary error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
