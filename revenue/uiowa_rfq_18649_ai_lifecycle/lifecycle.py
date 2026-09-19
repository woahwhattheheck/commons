"""Offline, vendor-neutral AI lifecycle investigation and comparison kit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .contract import InvalidRecord, SCHEMA, check, timestamp
else:  # Support the documented direct-file CLI as well as package imports.
    from contract import InvalidRecord, SCHEMA, check, timestamp


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def indexed(rows: list[dict], name: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        if row["id"] in result:
            raise InvalidRecord(f"duplicate {name} id: {row['id']}")
        result[row["id"]] = row
    return result


def referenced(index: dict, key: str, where: str) -> dict:
    if key not in index:
        raise InvalidRecord(f"{where}: missing reference {key!r}")
    return index[key]


def artifact_state(a: dict) -> str:
    if a["content"] is not None and a["sha256"] is not None:
        return "bytes_verified"
    if a["sha256"] is not None:
        return "digest_declared_only"
    return "digest_unknown"


def validate(data: dict) -> tuple[dict, dict, dict, dict]:
    check(data)
    artifacts = indexed(data["artifacts"], "artifact")
    versions = indexed(data["versions"], "version")
    runs = indexed(data["runs"], "run")
    comparisons = indexed(data["comparisons"], "comparison")
    indexed(data["incidents"], "incident")
    as_of = timestamp(data["as_of"])

    def artifact(key: str, kind: str, where: str, by: str | None = None) -> dict:
        row = referenced(artifacts, key, where)
        if row["kind"] != kind:
            raise InvalidRecord(f"{where}: {key!r} must be {kind}")
        if by and timestamp(row["captured_at"]) > timestamp(by):
            raise InvalidRecord(f"{where}: artifact captured after its recorded use")
        return row

    for a in artifacts.values():
        if timestamp(a["captured_at"]) > as_of:
            raise InvalidRecord(f"{a['id']}: captured after as_of")
        if a["content"] is not None and a["sha256"] is not None and digest(a["content"]) != a["sha256"]:
            raise InvalidRecord(f"{a['id']}: content/digest mismatch")
    for v in versions.values():
        if timestamp(v["effective_at"]) > as_of:
            raise InvalidRecord(f"{v['id']}: effective after as_of")
        if len(set(v["source_ids"])) != len(v["source_ids"]):
            raise InvalidRecord(f"{v['id']}: duplicate source reference")
        for key, kind in [(v["prompt_id"], "prompt"), (v["config_id"], "configuration")]:
            artifact(key, kind, v["id"], v["effective_at"])
        for key in v["source_ids"]:
            artifact(key, "knowledge", v["id"], v["effective_at"])
        if v["parent_id"] is not None:
            parent = referenced(versions, v["parent_id"], v["id"])
            if parent["workflow_id"] != v["workflow_id"] or timestamp(parent["effective_at"]) >= timestamp(v["effective_at"]):
                raise InvalidRecord(f"{v['id']}: parent must be an earlier version of the same workflow")
    for r in runs.values():
        version = referenced(versions, r["version_id"], r["id"])
        if not timestamp(version["effective_at"]) <= timestamp(r["observed_at"]) <= as_of:
            raise InvalidRecord(f"{r['id']}: run outside version/as_of chronology")
        for field, kind in [("dataset_id", "dataset"), ("rubric_id", "rubric"), ("protocol_id", "protocol")]:
            artifact(r[field], kind, r["id"], r["observed_at"])
        indexed(r["cases"], f"case in {r['id']}")
        for case in r["cases"]:
            if case["output_id"] is not None:
                artifact(case["output_id"], "output", r["id"], r["observed_at"])
    for c in comparisons.values():
        before = referenced(runs, c["baseline_run_id"], c["id"])
        after = referenced(runs, c["candidate_run_id"], c["id"])
        if before["id"] == after["id"]:
            raise InvalidRecord(f"{c['id']}: comparison requires distinct runs")
        if versions[before["version_id"]]["workflow_id"] != versions[after["version_id"]]["workflow_id"]:
            raise InvalidRecord(f"{c['id']}: cross-workflow comparison")
        if timestamp(after["observed_at"]) < timestamp(before["observed_at"]):
            raise InvalidRecord(f"{c['id']}: candidate predates baseline")
    for i in data["incidents"]:
        run = referenced(runs, i["run_id"], i["id"])
        version = versions[run["version_id"]]
        referenced(indexed(run["cases"], "case"), i["case_id"], i["id"])
        if not timestamp(run["observed_at"]) <= timestamp(i["opened_at"]) <= as_of:
            raise InvalidRecord(f"{i['id']}: invalid opening chronology")
        if i["resolved_at"] is not None:
            if not timestamp(i["opened_at"]) <= timestamp(i["resolved_at"]) <= as_of or not i["resolution"]:
                raise InvalidRecord(f"{i['id']}: invalid resolution chronology or missing account")
        for key in i["investigation_ids"]:
            artifact(key, "investigation", i["id"], i["resolved_at"])
        correction = i["corrective_version_id"]
        if correction is not None:
            changed = referenced(versions, correction, i["id"])
            if changed["workflow_id"] != version["workflow_id"] or timestamp(changed["effective_at"]) < timestamp(i["opened_at"]):
                raise InvalidRecord(f"{i['id']}: corrective version precedes investigation or changes workflow")
            if i["resolved_at"] and timestamp(changed["effective_at"]) > timestamp(i["resolved_at"]):
                raise InvalidRecord(f"{i['id']}: corrective version follows reported resolution")
        followup = i["followup_comparison_id"]
        if followup is not None:
            pair = referenced(comparisons, followup, i["id"])
            candidate = runs[pair["candidate_run_id"]]
            baseline = runs[pair["baseline_run_id"]]
            if correction is None or candidate["version_id"] != correction or baseline["version_id"] != version["id"]:
                raise InvalidRecord(f"{i['id']}: follow-up does not link affected and corrective versions")
            if i["resolved_at"] and timestamp(candidate["observed_at"]) > timestamp(i["resolved_at"]):
                raise InvalidRecord(f"{i['id']}: follow-up follows reported resolution")
    return artifacts, versions, runs, comparisons


def metric(run: dict, field: str) -> dict:
    known = [c for c in run["cases"] if c[field] is not None]
    scale = 100 if field == "passed" else 1
    value = math.fsum(c[field] / len(known) for c in known) * scale if known else None
    return {"value": value, "measured": len(known), "unknown": len(run["cases"]) - len(known),
            "case_ids": sorted(c["id"] for c in known)}


def changes(old: dict, new: dict, artifacts: dict) -> list[str]:
    result = []
    for field in ("model", "support_owner", "lifecycle"):
        if old[field] != new[field]:
            result.append(field)
    for field in ("prompt_id", "config_id"):
        a, b = artifacts[old[field]], artifacts[new[field]]
        if a["sha256"] is None or b["sha256"] is None:
            result.append(field + ":digest_unknown")
        elif a["sha256"] != b["sha256"]:
            result.append(field)
    before = sorted((key, artifacts[key]["sha256"]) for key in old["source_ids"])
    after = sorted((key, artifacts[key]["sha256"]) for key in new["source_ids"])
    if before != after:
        result.append("source_ids")
    return result


def analyze(data: dict) -> dict:
    artifacts, versions, runs, comparisons = validate(data)
    report: dict[str, Any] = {"schema_version": 1, "data_status": data["data_status"], "as_of": data["as_of"],
        "replay_state": "not_executed", "interpretation": "Descriptive record comparison, not causal attribution, statistical significance, University findings, or proof of a live model replay.",
        "artifacts": [{"id": a["id"], "kind": a["kind"], "version": a["version"], "locator": a["locator"],
                       "sha256": a["sha256"], "state": artifact_state(a)} for a in data["artifacts"]],
        "versions": [], "runs": [], "comparisons": [], "incidents": []}
    for v in sorted(versions.values(), key=lambda x: (timestamp(x["effective_at"]), x["id"])):
        ids = [v["prompt_id"], v["config_id"], *v["source_ids"]]
        gaps = [key + ":" + artifact_state(artifacts[key]) for key in ids if artifact_state(artifacts[key]) != "bytes_verified"]
        if v["model"]["revision"] is None:
            gaps.append("model_revision_unknown")
        if not v["support_owner"]:
            gaps.append("support_owner_unknown")
        if not v["source_ids"]:
            gaps.append("source_context_not_recorded")
        parent = versions.get(v["parent_id"])
        report["versions"].append({**v, "input_material_state": "incomplete" if gaps else "retained_inputs",
            "gaps": gaps, "changed_fields": changes(parent, v, artifacts) if parent else []})
    for run in runs.values():
        refs = [run["dataset_id"], run["rubric_id"], run["protocol_id"]]
        refs += [c["output_id"] for c in run["cases"] if c["output_id"] is not None]
        missing = [c["id"] for c in run["cases"] if c["output_id"] is None]
        unverified = [key for key in refs if artifact_state(artifacts[key]) != "bytes_verified"]
        report["runs"].append({"id": run["id"], "version_id": run["version_id"], "kind": run["kind"],
            "observed_at": run["observed_at"], "cohort": run["cohort"], "case_count": len(run["cases"]),
            "notes": run["notes"], "missing_outputs": missing, "unverified_artifacts": unverified,
            "metrics": {field: metric(run, field) for field in ("passed", "repair_seconds", "latency_ms")}})
    for pair in comparisons.values():
        old, new = runs[pair["baseline_run_id"]], runs[pair["candidate_run_id"]]
        reasons, states = [], []
        for field in ("kind", "cohort", "evaluator_revision"):
            if old[field] != new[field]:
                reasons.append(field + "_differs")
        for field in ("dataset_id", "rubric_id", "protocol_id"):
            a, b = artifacts[old[field]], artifacts[new[field]]
            states += [artifact_state(a), artifact_state(b)]
            if a["sha256"] is None or b["sha256"] is None:
                reasons.append(field + "_digest_unknown")
            elif a["sha256"] != b["sha256"]:
                reasons.append(field + "_digest_differs")
        if {c["id"] for c in old["cases"]} != {c["id"] for c in new["cases"]}:
            reasons.append("case_population_differs")
        metrics = {}
        for field, unit in [("passed", "percentage_points"), ("repair_seconds", "seconds_per_measured_case"), ("latency_ms", "milliseconds_per_measured_case")]:
            a, b = metric(old, field), metric(new, field)
            why = list(reasons)
            if not a["measured"] or not b["measured"]:
                why.append("no_measured_cases")
            elif a["case_ids"] != b["case_ids"]:
                why.append("measurement_coverage_differs")
            metrics[field] = {"baseline": a, "candidate": b, "delta_unit": unit,
                "delta": None if why else b["value"] - a["value"], "comparable": not why, "reasons": why}
        n = sum(m["comparable"] for m in metrics.values())
        report["comparisons"].append({**pair, "state": "comparable" if n == 3 else "partial" if n else "not_comparable",
            "context_basis": "bytes_verified" if all(s == "bytes_verified" for s in states) else "declared_or_unknown_digests",
            "changed_fields": changes(versions[old["version_id"]], versions[new["version_id"]], artifacts), "metrics": metrics})
    for incident in data["incidents"]:
        report["incidents"].append({**incident, "affected_version_id": runs[incident["run_id"]]["version_id"],
            "state": "reported_resolved" if incident["resolved_at"] else "open",
            "evidence_state": "bytes_verified" if incident["investigation_ids"] and all(artifact_state(artifacts[k]) == "bytes_verified" for k in incident["investigation_ids"]) else "incomplete"})
    return report


def safe_text(value: Any) -> str:
    return html.escape(str(value)).replace("|", "&#124;").replace("`", "&#96;").replace("\n", "<br>").replace("\r", "")


def markdown(report: dict) -> str:
    lines = ["# AI lifecycle investigation", "", f"**Data: {report['data_status'].upper()}** | As of {safe_text(report['as_of'])}",
        "", report["interpretation"], "", "Model replay: **NOT EXECUTED**. Retained inputs are not a promise of deterministic provider behavior.",
        "", "## Version timeline", "", "| Version / effective time | Model revision | Support owner | Changes / rationale | Material / ownership gaps |", "|---|---|---|---|---|"]
    for v in report["versions"]:
        lines.append("| " + " | ".join(safe_text(x) for x in [v["id"] + " / " + v["effective_at"], v["model"]["revision"] or "UNKNOWN", v["support_owner"] or "UNKNOWN", (", ".join(v["changed_fields"]) or "baseline") + ": " + v["change_reason"], "; ".join(v["gaps"]) or "none recorded"]) + " |")
    lines += ["", "## Descriptive comparisons", "", "Deltas are candidate minus baseline. Denominators count measured cases; null is unknown, never zero.",
              "", "| Pair / metric | Baseline | Candidate | Delta | Interpretation |", "|---|---:|---:|---:|---|"]
    for c in report["comparisons"]:
        for name, m in c["metrics"].items():
            values = [c["id"] + " / " + name,
                f"{m['baseline']['value']} (n={m['baseline']['measured']}, unknown={m['baseline']['unknown']})",
                f"{m['candidate']['value']} (n={m['candidate']['measured']}, unknown={m['candidate']['unknown']})",
                "UNKNOWN" if m["delta"] is None else f"{m['delta']:+.4g} {m['delta_unit']}",
                "; ".join(m["reasons"]) or "matched recorded context; " + c["context_basis"]]
            lines.append("| " + " | ".join(safe_text(x) for x in values) + " |")
    lines += ["", "## Investigation links", ""]
    for i in report["incidents"]:
        lines.append(f"- {safe_text(i['id'])}: {safe_text(i['run_id'])}/{safe_text(i['case_id'])} → {safe_text(i['corrective_version_id'])}; {i['state']}; evidence {i['evidence_state']}; follow-up {safe_text(i['followup_comparison_id'])}.")
    lines += ["", "## Operator follow-through", "", "Inspect review.json for exact artifacts, hashes, support ownership, observation denominators, missing outputs, and comparison reasons. Verify availability of the recorded model revision separately before attempting any future rerun. Preserve unresolved questions; this report does not assign institutional maturity ratings.", ""]
    return "\n".join(lines)


def export(report: dict, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (target / "review.md").write_text(markdown(report), encoding="utf-8")
    events = [(v["effective_at"], "version", v["id"], v["workflow_id"], v["support_owner"], v["change_reason"]) for v in report["versions"]]
    for i in report["incidents"]:
        events.append((i["opened_at"], "incident_open", i["id"], i["affected_version_id"], i["owner"], i["symptom"]))
        if i["resolved_at"]:
            events.append((i["resolved_at"], "incident_reported_resolved", i["id"], i["corrective_version_id"], i["owner"], i["resolution"]))
    def cell(value: Any) -> str:
        text = "" if value is None else str(value)
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
    with (target / "timeline.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "event", "id", "context_id", "owner", "description", "data_status"])
        for event in sorted(events, key=lambda e: (timestamp(e[0]), e[1], e[2])):
            writer.writerow([cell(x) for x in (*event, report["data_status"])])


def load(path: Path) -> dict:
    def pairs(items: list[tuple]) -> dict:
        result = {}
        for key, value in items:
            if key in result:
                raise InvalidRecord(f"duplicate JSON property: {key}")
            result[key] = value
        return result
    def nonfinite(value: str) -> None:
        raise InvalidRecord(f"non-finite JSON value: {value}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, nargs="?")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--schema", action="store_true")
    args = parser.parse_args(argv)
    if args.schema:
        print(json.dumps(SCHEMA, ensure_ascii=False, indent=2))
        return 0
    if args.record is None or args.out is None:
        parser.error("record and --out are required unless --schema is used")
    try:
        report = analyze(load(args.record))
        export(report, args.out)
    except (InvalidRecord, OSError, json.JSONDecodeError, UnicodeError, OverflowError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(f"OK {len(report['versions'])} versions, {len(report['runs'])} runs, {len(report['comparisons'])} comparisons; data={report['data_status']}; replay=not_executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
