#!/usr/bin/env python3
"""Offline AI lifecycle evidence inspection. No providers, model execution or scoring of staff."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
EVALUATOR = "exact-json-v1"


class EvidenceError(ValueError):
    """Malformed evidence cannot be interpreted reliably."""


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise EvidenceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise EvidenceError(f"non-finite JSON number: {value}")


def load_json(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"invalid JSON: {exc.msg}") from exc


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stamp(value: Any) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})", value):
        raise EvidenceError("timestamps must use ISO date/time with seconds and a UTC offset")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid timestamp: {value!r}") from exc
    if result.utcoffset() is None:
        raise EvidenceError("timestamps must carry a UTC offset")
    return result


def shape(row: Any, fields: str, where: str) -> None:
    if not isinstance(row, dict) or set(row) != set(fields.split()):
        raise EvidenceError(f"{where}: expected exactly {fields}")


def text(value: Any, where: str, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{where}: expected nonblank text")


def indexed(rows: Any, fields: str, where: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise EvidenceError(f"{where}: expected an array")
    result = {}
    for row in rows:
        shape(row, fields, where)
        text(row["id"], where + ".id")
        if row["id"] in result:
            raise EvidenceError(f"{where}: duplicate id {row['id']}")
        result[row["id"]] = row
    return result


def ref(value: Any, registry: dict, where: str, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or value not in registry:
        raise EvidenceError(f"{where}: unresolved reference {value!r}")


def refs(values: Any, registry: dict, where: str) -> None:
    if not isinstance(values, list):
        raise EvidenceError(f"{where}: expected an array")
    for value in values:
        ref(value, registry, where)
    if len(set(values)) != len(values):
        raise EvidenceError(f"{where}: duplicate references")


def validate(bundle: Any) -> tuple[dict, dict, dict, dict, dict]:
    shape(bundle, "schema_version synthetic artifacts cases releases runs events", "bundle")
    if type(bundle["schema_version"]) is not int or bundle["schema_version"] != SCHEMA_VERSION:
        raise EvidenceError("unsupported schema_version")
    if type(bundle["synthetic"]) is not bool:
        raise EvidenceError("synthetic must be a boolean")
    artifacts = indexed(bundle["artifacts"], "id sha256 content locator", "artifacts")
    cases = indexed(bundle["cases"], "id input_artifact_id expected_artifact_id source_artifact_ids", "cases")
    releases = indexed(bundle["releases"], "id workflow_id group created_at parent_id model prompt_artifact_id config_artifact_id code_artifact_id environment_artifact_id dataset_case_ids evaluator_id owner_role support_role input_source_ids change_reason investigation_artifact_ids", "releases")
    runs = indexed(bundle["runs"], "id release_id case_id kind occurred_at input_artifact_id output_artifact_id outcome latency_ms incident_id", "runs")
    events = indexed(bundle["events"], "id release_id occurred_at kind artifact_ids summary", "events")
    if not releases:
        raise EvidenceError("at least one release is required")
    for item in artifacts.values():
        digest = item["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise EvidenceError("artifact sha256 must be 64 lowercase hexadecimal characters")
        if item["content"] is not None and not isinstance(item["content"], str):
            raise EvidenceError("artifact content must be text or null")
        text(item["locator"], "artifact.locator")
    for item in cases.values():
        for key in ("input_artifact_id", "expected_artifact_id"):
            ref(item[key], artifacts, "case." + key)
        refs(item["source_artifact_ids"], artifacts, "case.sources")
    for item in releases.values():
        created = stamp(item["created_at"])
        for key in ("workflow_id", "evaluator_id", "change_reason"):
            text(item[key], "release." + key)
        for key in ("owner_role", "support_role"):
            text(item[key], "release." + key, nullable=True)
        if item["group"] not in ("ESS", "RIS", "IAM"):
            raise EvidenceError("release.group must be ESS, RIS or IAM")
        shape(item["model"], "name revision artifact_id", "release.model")
        text(item["model"]["name"], "model.name")
        text(item["model"]["revision"], "model.revision", nullable=True)
        ref(item["model"]["artifact_id"], artifacts, "model.artifact_id", nullable=True)
        for key in ("prompt_artifact_id", "config_artifact_id", "code_artifact_id", "environment_artifact_id"):
            ref(item[key], artifacts, "release." + key)
        refs(item["input_source_ids"], artifacts, "release.sources")
        refs(item["investigation_artifact_ids"], artifacts, "release.investigations")
        refs(item["dataset_case_ids"], cases, "release.dataset")
        ref(item["parent_id"], releases, "release.parent", nullable=True)
        if item["parent_id"] is not None:
            parent = releases[item["parent_id"]]
            if (parent["workflow_id"], parent["group"]) != (item["workflow_id"], item["group"]):
                raise EvidenceError("parent must belong to the same workflow and group")
            if stamp(parent["created_at"]) >= created:
                raise EvidenceError("parent must precede release; cycles are not valid history")
    seen = set()
    for item in runs.values():
        ref(item["release_id"], releases, "run.release")
        release = releases[item["release_id"]]
        ref(item["case_id"], cases, "run.case")
        if item["case_id"] not in release["dataset_case_ids"]:
            raise EvidenceError("run case must be in the release's declared dataset")
        ref(item["input_artifact_id"], artifacts, "run.input")
        ref(item["output_artifact_id"], artifacts, "run.output", nullable=True)
        if stamp(item["occurred_at"]) < stamp(release["created_at"]):
            raise EvidenceError("run cannot precede release")
        if item["kind"] not in ("evaluation", "runtime") or item["outcome"] not in ("success", "error", "unknown"):
            raise EvidenceError("invalid run kind or outcome")
        text(item["incident_id"], "run.incident_id", nullable=True)
        latency = item["latency_ms"]
        if latency is not None and (type(latency) not in (int, float) or not 0 <= latency < float("inf")):
            raise EvidenceError("latency_ms must be finite, nonnegative or null")
        if item["kind"] == "evaluation":
            key = (item["release_id"], item["case_id"])
            if key in seen:
                raise EvidenceError("duplicate evaluation: use a separate release/cohort rather than cherry-pick a run")
            seen.add(key)
    for item in events.values():
        ref(item["release_id"], releases, "event.release")
        if stamp(item["occurred_at"]) < stamp(releases[item["release_id"]]["created_at"]):
            raise EvidenceError("event cannot precede release")
        if item["kind"] not in ("change", "deploy", "observation", "investigation", "rollback", "retire"):
            raise EvidenceError("invalid event kind")
        refs(item["artifact_ids"], artifacts, "event.artifacts")
        text(item["summary"], "event.summary")
    return artifacts, cases, releases, runs, events


def inspect(bundle: dict) -> dict:
    artifacts, cases, releases, runs, events = validate(bundle)
    integrity = {key: ("UNAVAILABLE" if item["content"] is None else "VERIFIED" if sha256(item["content"]) == item["sha256"] else "MISMATCH") for key, item in artifacts.items()}

    def signature(key: str) -> str:
        return artifacts[key]["sha256"]

    def inputs(release: dict) -> list[str]:
        return [release[k] for k in ("prompt_artifact_id", "config_artifact_id", "code_artifact_id", "environment_artifact_id")] + release["input_source_ids"]

    def components(release: dict) -> dict:
        model = dict(release["model"])
        model["artifact_id"] = signature(model["artifact_id"]) if model["artifact_id"] else None
        return {"model": model, "prompt": signature(release["prompt_artifact_id"]), "configuration": signature(release["config_artifact_id"]), "code": signature(release["code_artifact_id"]), "environment": signature(release["environment_artifact_id"]), "sources": sorted(signature(x) for x in release["input_source_ids"]), "dataset": sorted((cid, signature(cases[cid]["input_artifact_id"]), signature(cases[cid]["expected_artifact_id"]), sorted(signature(x) for x in cases[cid]["source_artifact_ids"])) for cid in release["dataset_case_ids"]), "evaluator": release["evaluator_id"]}

    results = []
    evaluations: dict[str, dict[str, dict]] = {}
    for release in sorted(releases.values(), key=lambda r: (stamp(r["created_at"]), r["id"])):
        rid = release["id"]
        eval_runs = {r["case_id"]: r for r in runs.values() if r["release_id"] == rid and r["kind"] == "evaluation"}
        rows = {}
        for cid in sorted(release["dataset_case_ids"]):
            case, run = cases[cid], eval_runs.get(cid)
            row = {"case_id": cid, "run_id": run["id"] if run else None, "status": "UNSCORED", "reason": None}
            required = inputs(release) + [case["input_artifact_id"], case["expected_artifact_id"]] + case["source_artifact_ids"]
            if run is None:
                row["reason"] = "RUN_NOT_RECORDED"
            elif run["outcome"] != "success":
                row["reason"] = "OUTCOME_" + run["outcome"].upper()
            elif run["input_artifact_id"] != case["input_artifact_id"]:
                row["reason"] = "INPUT_BINDING_MISMATCH"
            elif not set(case["source_artifact_ids"]).issubset(release["input_source_ids"]):
                row["reason"] = "SOURCE_NOT_IN_RELEASE"
            elif run["output_artifact_id"] is None:
                row["reason"] = "OUTPUT_NOT_RETAINED"
            elif any(integrity[x] != "VERIFIED" for x in required + [run["output_artifact_id"]]):
                row["reason"] = "ARTIFACT_NOT_VERIFIED"
            elif release["evaluator_id"] != EVALUATOR:
                row["reason"] = "EVALUATOR_NOT_IMPLEMENTED"
            else:
                try:
                    expected = load_json(artifacts[case["expected_artifact_id"]]["content"])
                    observed = load_json(artifacts[run["output_artifact_id"]]["content"])
                    row["status"] = "PASS" if canonical(expected) == canonical(observed) else "FAIL"
                except (EvidenceError, ValueError):
                    row["reason"] = "OUTPUT_OR_EXPECTATION_NOT_STRICT_JSON"
            rows[cid] = row
        evaluations[rid] = rows
        scored = sum(r["status"] != "UNSCORED" for r in rows.values())
        passed = sum(r["status"] == "PASS" for r in rows.values())
        runtime = [r for r in runs.values() if r["release_id"] == rid and r["kind"] == "runtime"]
        counts = Counter(r["outcome"] for r in runtime)
        missing = [x for x in sorted(set(inputs(release))) if integrity[x] != "VERIFIED"]
        gaps = [f"{key.upper()}_NOT_RECORDED" for key in ("owner_role", "support_role") if release[key] is None]
        if release["model"]["revision"] is None:
            gaps.append("MODEL_REVISION_NOT_RECORDED")
        gaps += [f"ARTIFACT_{integrity[x]}:{x}" for x in missing]
        model_artifact = release["model"]["artifact_id"]
        if model_artifact and integrity[model_artifact] != "VERIFIED":
            gaps.append(f"MODEL_ARTIFACT_{integrity[model_artifact]}")
        results.append({"release_id": rid, "workflow_id": release["workflow_id"], "group": release["group"], "assessment_area": "ai-readiness", "created_at": release["created_at"], "manifest_sha256": sha256(canonical(release)), "owner_role": release["owner_role"], "support_role": release["support_role"], "lineage_gaps": gaps, "model_artifact_retention": integrity.get(release["model"]["artifact_id"], "NOT_SUPPLIED"), "rerun_status": "NOT_PERFORMED", "evaluation": {"declared_cases": len(rows), "scored_cases": scored, "passed_cases": passed, "unscored_cases": len(rows) - scored, "pass_rate_scored": passed / scored if scored else None, "coverage": scored / len(rows) if rows else None, "cases": list(rows.values())}, "runtime": {"recorded_runs": len(runtime), "success": counts["success"], "error": counts["error"], "unknown": counts["unknown"], "latency_observations": sum(r["latency_ms"] is not None for r in runtime), "incident_ids": sorted({r["incident_id"] for r in runtime if r["incident_id"]})}, "investigation_evidence": [{"artifact_id": x, "locator": artifacts[x]["locator"], "integrity": integrity[x]} for x in release["investigation_artifact_ids"]]})
    transitions = []
    for result in results:
        release = releases[result["release_id"]]
        if release["parent_id"] is None:
            continue
        parent = releases[release["parent_id"]]
        before, after = components(parent), components(release)
        changed = sorted(key for key in before if before[key] != after[key])
        left, right = evaluations[parent["id"]], evaluations[release["id"]]
        common = sorted(cid for cid in left.keys() & right.keys() if left[cid]["status"] != "UNSCORED" and right[cid]["status"] != "UNSCORED")
        blockers = sorted(set(changed) & {"sources", "dataset", "evaluator"})
        if blockers:
            state = "NOT_COMPARABLE"
        elif not common:
            state = "NO_PAIRED_EVIDENCE"
        elif len(common) != len(left) or len(common) != len(right):
            state = "PARTIAL_COHORT"
        else:
            state = "COMPARABLE"
        # Do not export a numeric improvement claim for changed evaluation conditions.
        delta = None if blockers or not common else (sum(right[c]["status"] == "PASS" for c in common) - sum(left[c]["status"] == "PASS" for c in common)) / len(common)
        transitions.append({"from_release": parent["id"], "to_release": release["id"], "changed_components": changed, "comparison_status": state, "comparison_blockers": blockers, "paired_case_ids": common, "paired_pass_rate_delta": delta, "interpretation": "Association in retained synthetic outputs, not causal attribution or a model rerun." if bundle["synthetic"] else "Association in retained outputs; source authenticity and causal attribution are not established.", "change_reason": release["change_reason"], "investigation_artifact_ids": release["investigation_artifact_ids"]})
    timeline = [{**event, "evidence": [{"artifact_id": x, "locator": artifacts[x]["locator"], "integrity": integrity[x]} for x in event["artifact_ids"]]} for event in sorted(events.values(), key=lambda e: (stamp(e["occurred_at"]), e["id"]))]
    return {"schema_version": SCHEMA_VERSION, "synthetic": bundle["synthetic"], "evidence_kind": "SYNTHETIC_RETAINED_OUTPUT_RESCORING" if bundle["synthetic"] else "UNVERIFIED_SOURCE_RETAINED_OUTPUT_RESCORING", "bundle_sha256": sha256(canonical(bundle)), "limitations": ["This recomputes exact-JSON fixture scores; it does not invoke or rerun any model.", "Hashes establish byte consistency, not source authenticity, immutable provider behavior, approval, or assessment maturity.", "Runtime records are supplied observations; missing telemetry is not success. No latency or productivity benchmark is inferred.", "Coverage and pass rate remain separate. Changed source, dataset or evaluator conditions suppress numeric improvement comparisons."], "artifact_integrity": integrity, "releases": results, "transitions": transitions, "timeline": timeline}


def cell(value: Any) -> str:
    """Escape supplied text for a Markdown table, without interpreting markup."""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("`", "&#96;").replace("\r", " ").replace("\n", " ")


def markdown(report: dict) -> str:
    lines = ["# AI workflow lifecycle inspection", "", "**SYNTHETIC — NOT UNIVERSITY FINDINGS**" if report["synthetic"] else "**SOURCE AUTHENTICITY NOT VERIFIED**", "", f"Bundle SHA-256: `{report['bundle_sha256']}`", "", *["- " + x for x in report["limitations"]], "", "## Release evidence", "", "|Release|Group|Scored / declared|Passed|Coverage|Lineage gaps|Model rerun|", "|---|---|---|---|---|---|---|"]
    for r in report["releases"]:
        e = r["evaluation"]
        coverage = "UNKNOWN" if e["coverage"] is None else f"{e['coverage']:.0%}"
        values = (r["release_id"], r["group"], f"{e['scored_cases']} / {e['declared_cases']}", e["passed_cases"], coverage, "; ".join(r["lineage_gaps"]) or "none recorded", r["rerun_status"])
        lines.append("|" + "|".join(cell(v) for v in values) + "|")
    lines += ["", "## Version comparisons", "", "|From → to|Changed components|Comparison|Paired cases|Paired pass-rate delta|", "|---|---|---|---|---|"]
    for t in report["transitions"]:
        delta = t["paired_pass_rate_delta"]
        values = (t["from_release"] + " → " + t["to_release"], ", ".join(t["changed_components"]), t["comparison_status"], len(t["paired_case_ids"]), "NOT ESTIMATED" if delta is None else f"{delta:+.1%}")
        lines.append("|" + "|".join(cell(v) for v in values) + "|")
    lines += ["", "## Case-to-run trace", "", "|Release|Case|Run|Result|Reason|", "|---|---|---|---|---|"]
    for r in report["releases"]:
        for e in r["evaluation"]["cases"]:
            lines.append("|" + "|".join(cell(v if v is not None else "—") for v in (r["release_id"], e["case_id"], e["run_id"], e["status"], e["reason"])) + "|")
    lines += ["", "## Investigation timeline", "", "|Time|Release|Event|Evidence / integrity|Summary|", "|---|---|---|---|---|"]
    for event in report["timeline"]:
        evidence = "; ".join(f"{x['artifact_id']} @ {x['locator']} [{x['integrity']}]" for x in event["evidence"]) or "NOT SUPPLIED"
        lines.append("|" + "|".join(cell(v) for v in (event["occurred_at"], event["release_id"], event["kind"], evidence, event["summary"])) + "|")
    return "\n".join(lines) + "\n"


def export(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "lifecycle-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "lifecycle-report.md").write_text(markdown(report), encoding="utf-8")
    with (output / "case-trace.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["release_id", "case_id", "run_id", "status", "reason"])
        for release in report["releases"]:
            for row in release["evaluation"]["cases"]:
                values = [release["release_id"], row["case_id"], row["run_id"], row["status"], row["reason"]]
                # JSON is the lossless exchange. CSV is display-safe for spreadsheet import.
                writer.writerow(["" if v is None else "'" + v if v.lstrip().startswith(("=", "+", "-", "@")) or v.startswith(("\t", "\r", "\n")) else v for v in values])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect(load_json(args.bundle.read_text(encoding="utf-8")))
        export(report, args.out)
    except (OSError, EvidenceError, ValueError) as exc:
        parser.exit(2, f"lifecycle: {exc}\n")
    print(f"releases={len(report['releases'])} transitions={len(report['transitions'])} evidence={report['evidence_kind']} rerun=NOT_PERFORMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
