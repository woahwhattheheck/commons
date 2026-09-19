#!/usr/bin/env python3
"""UIOWA-085: offline, non-authoritative relative-day roadmap preparation.

Standard library only. No network, calendar, model service, scoring or procurement.
Ranges are planning assumptions, not probabilities or commitments. Source records
and their provenance are retained in every JSON report. See README for semantics.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import sys
from typing import Any

PHASES = ("0-90", "90-180", "180+")
STARTS = (0, 90, 180)


class InputError(ValueError):
    """An input cannot be interpreted without silently changing its meaning."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise InputError(message)


def integer(value: Any, where: str) -> int:
    require(type(value) is int and value >= 0, f"{where}: expected nonnegative integer")
    return value


def text(value: Any, where: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{where}: expected nonblank text")
    return value


def span(value: Any, where: str) -> dict[str, int] | None:
    if value is None:
        return None
    require(isinstance(value, dict) and set(value) == {"low", "high"}, f"{where}: use low/high or null")
    lo, hi = integer(value["low"], where + ".low"), integer(value["high"], where + ".high")
    require(lo <= hi, f"{where}: low exceeds high")
    return {"low": lo, "high": hi}


def string_list(value: Any, where: str, nonempty: bool = False) -> list[str]:
    require(isinstance(value, list), f"{where}: expected list")
    for item in value:
        text(item, where)
    require(len(value) == len(set(value)), f"{where}: duplicate value")
    require(bool(value) or not nonempty, f"{where}: expected at least one value")
    return value


def records(value: Any, where: str) -> dict[str, dict[str, Any]]:
    require(isinstance(value, list), f"{where}: expected list")
    result = {}
    for record in value:
        require(isinstance(record, dict), f"{where}: expected object records")
        key = text(record.get("id"), where + ".id")
        require(key not in result, f"{where}: duplicate id {key}")
        result[key] = record
    return result


def strict_json(raw: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise InputError(f"nonfinite JSON value: {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def phase(day: int) -> str:
    return PHASES[0 if day < 90 else 1 if day < 180 else 2]


def phase_range(lo: int, hi: int | None) -> list[str]:
    return list(PHASES[PHASES.index(phase(lo)):]) if hi is None else list(
        PHASES[PHASES.index(phase(lo)):PHASES.index(phase(hi)) + 1]
    )


def validate(data: Any) -> tuple[dict, dict, list[str]]:
    require(isinstance(data, dict), "input: expected object")
    require(type(data.get("schema_version")) is int and data["schema_version"] == 1,
            "schema_version: expected integer 1")
    text(data.get("scenario_id"), "scenario_id")
    require(data.get("data_kind") in ("synthetic", "engagement_draft"), "data_kind: synthetic or engagement_draft")
    text(data.get("planning_basis"), "planning_basis")
    findings = records(data.get("findings"), "findings")
    recs = records(data.get("recommendations"), "recommendations")
    for fid, finding in findings.items():
        text(finding.get("summary"), fid + ".summary")
        string_list(finding.get("source_refs"), fid + ".source_refs", nonempty=True)
    for rid, rec in recs.items():
        for key in ("title", "group", "owner_role", "outcome", "acceptance_evidence"):
            text(rec.get(key), rid + "." + key)
        refs = string_list(rec.get("finding_ids"), rid + ".finding_ids", nonempty=True)
        require(set(refs) <= findings.keys(), f"{rid}: dangling finding reference")
        deps = string_list(rec.get("depends_on"), rid + ".depends_on")
        require(set(deps) <= recs.keys(), f"{rid}: dangling prerequisite")
        integer(rec.get("not_before_day"), rid + ".not_before_day")
        for key in ("duration_days", "effort_hours"):
            require(key in rec, f"{rid}.{key}: use explicit null for unknown")
            span(rec[key], rid + "." + key)
        require(rec.get("effort_phase") in (*PHASES, None), f"{rid}: invalid effort_phase")
        require(rec.get("preferred_phase") in (*PHASES, None), f"{rid}: invalid preferred_phase")
        string_list(rec.get("assumptions"), rid + ".assumptions")
        hypothesis = rec.get("maturity_hypothesis")
        require(isinstance(hypothesis, dict), f"{rid}: expected maturity_hypothesis")
        for key in ("baseline", "target"):
            require(key in hypothesis, f"{rid}.maturity_hypothesis.{key}: use null for unknown")
            value = hypothesis[key]
            require(value is None or type(value) is int and 1 <= value <= 5,
                    f"{rid}.maturity_hypothesis.{key}: integer 1..5 or null")
        text(hypothesis.get("rationale"), rid + ".maturity_hypothesis.rationale")
        text(hypothesis.get("evidence_needed"), rid + ".maturity_hypothesis.evidence_needed")
    capacities = data.get("role_capacity")
    require(isinstance(capacities, list), "role_capacity: expected list")
    seen = set()
    for item in capacities:
        require(isinstance(item, dict), "role_capacity: expected object")
        role = text(item.get("owner_role"), "role_capacity.owner_role")
        require(item.get("phase") in PHASES, "role_capacity: invalid phase")
        key = (role, item["phase"])
        require(key not in seen, f"role_capacity: duplicate {key}")
        seen.add(key)
        require("hours" in item, "role_capacity.hours: use explicit null for unknown")
        span(item["hours"], "role_capacity.hours")
        text(item.get("basis"), "role_capacity.basis")
    # Stable Kahn order; no recursion limit on long recommendation chains.
    pending = {key: set(rec["depends_on"]) for key, rec in recs.items()}
    order = []
    while pending:
        ready = sorted(key for key, deps in pending.items() if not deps)
        require(bool(ready), "prerequisite cycle involves: " + ", ".join(sorted(pending)))
        order.extend(ready)
        for key in ready:
            del pending[key]
        for deps in pending.values():
            deps.difference_update(ready)
    return findings, recs, order


def budget_status(demand: dict, capacity: dict | None) -> str:
    if capacity is not None and demand["low"] > capacity["high"]:
        return "EXCEEDS_ASSUMPTIONS"
    if capacity is None or demand["high"] is None:
        return "UNKNOWN"
    if demand["high"] <= capacity["low"]:
        return "WITHIN_ASSUMPTIONS"
    return "RANGE_OVERLAP"


def build(data: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(data)
    findings, recs, order = validate(data)
    rows, ancestors = {}, {}
    for rid in order:
        rec = recs[rid]
        deps = [rows[key] for key in rec["depends_on"]]
        lo = max([rec["not_before_day"]] + [d["finish_day"]["low"] for d in deps])
        unknown_parent = any(d["finish_day"]["high"] is None for d in deps)
        hi = None if unknown_parent else max([rec["not_before_day"]] + [d["finish_day"]["high"] for d in deps])
        duration = rec["duration_days"]
        finish_lo = lo + (duration["low"] if duration is not None else 0)
        finish_hi = None if hi is None or duration is None else hi + duration["high"]
        flags = []
        if duration is None:
            flags.append("UNKNOWN_DURATION")
        if unknown_parent:
            flags.append("UNKNOWN_PREREQUISITE_FINISH")
        preferred = rec.get("preferred_phase")
        possible = phase_range(lo, hi)
        if preferred is not None and preferred not in possible:
            flags.append("PREFERRED_PHASE_OUTSIDE_EARLIEST_RANGE")
        elif preferred is not None and len(possible) > 1:
            flags.append("PREFERRED_PHASE_RANGE_RISK")
        effort_phase = rec.get("effort_phase")
        if effort_phase is None:
            flags.append("UNALLOCATED_EFFORT")
        elif PHASES.index(effort_phase) < PHASES.index(phase(lo)):
            flags.append("EFFORT_BEFORE_EARLIEST_START")
        hypothesis = rec["maturity_hypothesis"]
        baseline, target = hypothesis["baseline"], hypothesis["target"]
        if baseline is None or target is None:
            hypothesis_state = "UNKNOWN_BASELINE_OR_TARGET"
        elif target - baseline not in (1, 2):
            hypothesis_state = "REVIEW_PROGRESSION_SCOPE"
        else:
            hypothesis_state = "ONE_TO_TWO_LEVEL_HYPOTHESIS_NOT_VALIDATED"
        ancestors[rid] = set(rec["depends_on"])
        for dep in rec["depends_on"]:
            ancestors[rid].update(ancestors[dep])
        rows[rid] = {
            "id": rid, "title": rec["title"], "group": rec["group"], "owner_role": rec["owner_role"],
            "finding_ids": sorted(rec["finding_ids"]), "source_refs": sorted({
                ref for fid in rec["finding_ids"] for ref in findings[fid]["source_refs"]}),
            "depends_on": sorted(rec["depends_on"]), "dependency_layer": 0 if not deps else 1 + max(d["dependency_layer"] for d in deps),
            "start_day": {"low": lo, "high": hi}, "finish_day": {"low": finish_lo, "high": finish_hi},
            "possible_start_phases": possible,
            "possible_execution_phases": phase_range(lo, None if finish_hi is None else max(lo, finish_hi - 1)),
            "timing_incomplete": hi is None or finish_hi is None,
            "preferred_phase": preferred, "effort_phase": effort_phase, "effort_hours": rec["effort_hours"],
            "outcome": rec["outcome"], "acceptance_evidence": rec["acceptance_evidence"],
            "maturity_hypothesis": hypothesis, "hypothesis_state": hypothesis_state,
            "assumptions": rec["assumptions"], "flags": flags,
        }
    capacity_map = {(c["owner_role"], c["phase"]): c for c in data["role_capacity"]}
    buckets: dict[tuple[str, str], list[dict]] = {}
    for row in rows.values():
        buckets.setdefault((row["owner_role"], row["effort_phase"] or "UNALLOCATED"), []).append(row)
    resources = []
    for key in sorted(set(buckets) | set(capacity_map)):
        items = buckets.get(key, [])
        demand = {"low": sum(r["effort_hours"]["low"] for r in items if r["effort_hours"] is not None),
                  "high": None if any(r["effort_hours"] is None for r in items) else sum(r["effort_hours"]["high"] for r in items)}
        capacity = capacity_map.get(key, {}).get("hours")
        unallocated = sorted(r["id"] for r in rows.values() if r["owner_role"] == key[0] and r["effort_phase"] is None)
        status = budget_status(demand, capacity)
        if unallocated and status != "EXCEEDS_ASSUMPTIONS":
            status = "UNKNOWN"
        resources.append({"owner_role": key[0], "phase": key[1], "recommendation_ids": sorted(r["id"] for r in items),
                          "demand_hours": demand, "capacity_hours": capacity, "status": status,
                          "unallocated_recommendation_ids": unallocated,
                          "basis": capacity_map.get(key, {}).get("basis", "No capacity estimate supplied")})
    keys = sorted(rows)
    parallel = [[left, right] for pos, left in enumerate(keys) for right in keys[pos + 1:]
                if left not in ancestors[right] and right not in ancestors[left]]
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {"schema_version": 1, "scenario_id": data["scenario_id"], "data_kind": data["data_kind"],
            "status": "DRAFT_PLANNING_NOT_A_COMMITMENT", "source_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "phase_semantics": "Relative calendar days: [0,90), [90,180), [180,infinity). No calendar events are created.",
            "planning_limit": "Dependency-only earliest bounds; role-hour totals are a separate review, not a resource-leveled schedule. Unknown bounds are not zero estimates. Phase ranges are possibilities, not probabilities.",
            "recommendations": [rows[key] for key in order], "role_capacity_review": resources,
            "dependency_independent_pairs": parallel,
            "parallel_limit": "No prerequisite path connects these pairs; shared roles, timing and other constraints may still prevent concurrent work.",
            "source_input": copy.deepcopy(data)}


def bounds(value: dict | None) -> str:
    if value is None:
        return "UNKNOWN"
    return f'{value["low"]}..{value["high"] if value["high"] is not None else "UNKNOWN"}'


def cell(value: Any) -> str:
    return html.escape(str(value), quote=True).replace("|", "&#124;").replace("\r\n", "\n").replace("\n", "<br>")


def render_markdown(report: dict) -> str:
    lines = [f'# Phased roadmap — {cell(report["scenario_id"])}', "",
             f'**{report["data_kind"].upper()} / {report["status"]}**', "",
             report["phase_semantics"], "", report["planning_limit"], "",
             "| Recommendation | Group / owner role | Earliest start / finish bounds | 0–90 | 90–180 | 180+ | Prerequisites |",
             "|---|---|---|---|---|---|---|"]
    for row in report["recommendations"]:
        phases = ["May start" if p in row["possible_start_phases"] else "May continue" if p in row["possible_execution_phases"] else "—" for p in PHASES]
        lines.append("| " + " | ".join([cell(row["id"] + ": " + row["title"]), cell(row["group"] + " / " + row["owner_role"]),
                                      cell(bounds(row["start_day"]) + " / " + bounds(row["finish_day"])), *phases,
                                      cell(", ".join(row["depends_on"]) or "None")]) + " |")
    lines += ["", "Unknown upper bounds are labeled UNKNOWN; multiple phase cells describe uncertainty, not duplicate work.", "", "## Recommendation evidence and outcomes", ""]
    for row in report["recommendations"]:
        h = row["maturity_hypothesis"]
        lines += [f'### {cell(row["id"])} — {cell(row["title"])}',
                  f'Finding IDs: {cell(", ".join(row["finding_ids"]))}. Sources: {cell("; ".join(row["source_refs"]))}.',
                  f'Outcome: {cell(row["outcome"])}', f'Acceptance evidence: {cell(row["acceptance_evidence"])}',
                  f'Maturity hypothesis: {cell(h["baseline"] if h["baseline"] is not None else "UNKNOWN")} → {cell(h["target"] if h["target"] is not None else "UNKNOWN")} ({row["hypothesis_state"]}).',
                  f'Rationale: {cell(h["rationale"])} Evidence still needed: {cell(h["evidence_needed"])}',
                  f'Assumptions: {cell("; ".join(row["assumptions"]) or "None supplied")}',
                  f'Review flags: {cell(", ".join(row["flags"]) or "None under supplied inputs")}', ""]
    lines += ["## Role-hour capacity review", "", "| Role | Effort phase | Required hours | Available hours | Status | Unallocated work |", "|---|---|---|---|---|---|"]
    for item in report["role_capacity_review"]:
        lines.append("| " + " | ".join(map(cell, [item["owner_role"], item["phase"], bounds(item["demand_hours"]),
                                                    bounds(item["capacity_hours"]), item["status"], ", ".join(item["unallocated_recommendation_ids"]) or "None"])) + " |")
    lines += ["", "Effort phase is an explicit allocation assumption, not inferred from start day. Resource pressure does not silently move the dependency-only dates.", "", "## Potential parallel work", report["parallel_limit"], ""]
    lines += [f'- {cell(a)} / {cell(b)}' for a, b in report["dependency_independent_pairs"]]
    lines += ["", f'Canonical source-input SHA-256: `{report["source_sha256"]}`', ""]
    return "\n".join(lines)


def render_html(report: dict) -> str:
    # Plain HTML with no scripts, network resources or executable source locators.
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>Phased roadmap planning</title>',
             '<style>body{font:16px/1.5 system-ui,sans-serif;margin:2rem;max-width:1200px}table{border-collapse:collapse;width:100%}th,td{border:1px solid;padding:.5rem;text-align:left;vertical-align:top}caption{text-align:left;font-weight:bold;padding:.5rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}article{border-top:2px solid;margin-top:2rem}a{overflow-wrap:anywhere}@media print{body{margin:.5cm}thead{display:table-header-group}tr{break-inside:avoid}}</style>',
             f'<h1>Phased roadmap — {cell(report["scenario_id"])}</h1>',
             f'<p><strong>{cell(report["data_kind"].upper())} / {cell(report["status"])}</strong></p>',
             f'<p>{cell(report["phase_semantics"])}</p><p>{cell(report["planning_limit"])}</p>',
             '<table><caption>Possible phase placement; ranges are not repeated work</caption><thead><tr><th scope="col">Recommendation / role</th><th scope="col">0–90</th><th scope="col">90–180</th><th scope="col">180+</th><th scope="col">Prerequisites and bounds</th></tr></thead><tbody>']
    for index, row in enumerate(report["recommendations"]):
        parts.append(f'<tr><th scope="row"><a href="#item-{index}">{cell(row["id"])}: {cell(row["title"])}</a><br>{cell(row["group"])} / {cell(row["owner_role"])}</th>')
        for p in PHASES:
            meaning = "May start" if p in row["possible_start_phases"] else "May continue" if p in row["possible_execution_phases"] else "—"
            parts.append(f'<td>{meaning}</td>')
        parts.append(f'<td>{cell(", ".join(row["depends_on"]) or "None")}<br>Start {cell(bounds(row["start_day"]))}; finish {cell(bounds(row["finish_day"]))}</td></tr>')
    parts.append('</tbody></table><p>Unknown bounds remain UNKNOWN. Read role-hour constraints and evidence before treating any possible phase as achievable.</p>')
    for index, row in enumerate(report["recommendations"]):
        parts += [f'<article id="item-{index}"><h2>{cell(row["id"])}: {cell(row["title"])}</h2>',
                  f'<p>Outcome: {cell(row["outcome"])}</p><p>Acceptance evidence: {cell(row["acceptance_evidence"])}</p>',
                  f'<p>Findings: {cell(", ".join(row["finding_ids"]))}<br>Sources: {cell("; ".join(row["source_refs"]))}</p>',
                  f'<p>Review flags: {cell(", ".join(row["flags"]) or "None under supplied inputs")}</p></article>']
    parts += ['<h2>Full planning notes, maturity hypotheses and resource review</h2>',
              '<pre>' + html.escape(render_markdown(report)) + '</pre>', '</html>']
    return "\n".join(parts) + "\n"


def render_csv(report: dict) -> str:
    out = io.StringIO(newline="")
    columns = ["id", "title", "group", "owner_role", "finding_ids", "source_refs", "depends_on", "start_low", "start_high", "finish_low", "finish_high", "possible_start_phases", "effort_phase", "effort_low", "effort_high", "outcome", "acceptance_evidence", "flags", "data_kind", "source_sha256"]
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in report["recommendations"]:
        rec = {key: row[key] for key in ("id", "title", "group", "owner_role", "outcome", "acceptance_evidence")}
        for key in ("finding_ids", "source_refs", "depends_on", "possible_start_phases", "flags"):
            rec[key] = json.dumps(row[key], ensure_ascii=False)
        for stem, key in (("start", "start_day"), ("finish", "finish_day"), ("effort", "effort_hours")):
            for bound in ("low", "high"):
                value = None if row[key] is None else row[key][bound]
                rec[stem + "_" + bound] = "UNKNOWN" if value is None else value
        rec["effort_phase"] = row["effort_phase"] or "UNALLOCATED"
        rec.update(data_kind=report["data_kind"], source_sha256=report["source_sha256"])
        # Spreadsheet applications may evaluate leading formula text even when quoted.
        # Human-editable CSV adds an apostrophe; lossless machine interchange is JSON.
        writer.writerow({key: "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value for key, value in rec.items()})
    return out.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data = strict_json(args.input.read_text(encoding="utf-8"))
        report = build(data)
        outputs = {"roadmap.json": json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                   "roadmap.csv": render_csv(report), "roadmap.md": render_markdown(report), "roadmap.html": render_html(report)}
        for name in outputs:
            require((args.out_dir / name).resolve() != args.input.resolve(), "output would overwrite source input")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for name, content in outputs.items():
            (args.out_dir / name).write_text(content, encoding="utf-8")
        print(f'{report["data_kind"]}: {len(report["recommendations"])} recommendations; {len(report["role_capacity_review"])} capacity rows; {report["source_sha256"]}')
        return 0
    except (InputError, ValueError, OSError, TypeError, KeyError) as exc:
        print(f"roadmap input/output error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
