#!/usr/bin/env python3
"""Offline alert-history assessment. No network, telemetry collection, or paging writes."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
GROUPS = {"ESS", "RIS", "IAM"}


class InputError(ValueError):
    """A supplied record cannot support an unambiguous calculation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InputError(message)


def text(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label}: nonempty text required")
    return value


def timestamp(value: Any, label: str) -> datetime:
    text(value, label)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"{label}: invalid ISO timestamp") from exc
    require(dt.tzinfo is not None and dt.utcoffset() is not None, f"{label}: timezone required")
    return dt.astimezone(timezone.utc)


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise InputError(f"noncanonical JSON value: {exc}") from exc


def loads(data: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise InputError(f"nonfinite JSON number: {value}")

    def finite_float(value: str) -> float:
        result = float(value)
        require(math.isfinite(result), "nonfinite JSON number")
        return result

    try:
        result = json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_constant, parse_float=finite_float)
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON: {exc.msg} at line {exc.lineno}") from exc
    require(isinstance(result, dict), "packet: object required")
    return result


def check_refs(refs: Any, sources: dict[str, Any], label: str, required: bool = True) -> None:
    require(isinstance(refs, list), f"{label}: source_refs list required")
    require(not required or bool(refs), f"{label}: evidence reference required")
    require(all(isinstance(x, str) and x in sources for x in refs), f"{label}: unresolved source reference")
    require(len(refs) == len(set(refs)), f"{label}: duplicate source reference")


def validate(packet: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], int]:
    require(isinstance(packet, dict), "packet: object required")
    require(type(packet.get("schema_version")) is int and packet["schema_version"] == 1, "schema_version must be 1")
    require(type(packet.get("synthetic")) is bool, "synthetic: explicit boolean required")
    for key in ("sources", "incidents", "notifications"):
        require(isinstance(packet.get(key), list), f"{key}: list required")
    sources: dict[str, Any] = {}
    for source in packet["sources"]:
        require(isinstance(source, dict), "source: object required")
        sid = text(source.get("id"), "source.id")
        require(sid not in sources, f"duplicate source ID: {sid}")
        text(source.get("locator"), f"{sid}.locator")
        text(source.get("excerpt"), f"{sid}.excerpt")
        sources[sid] = source
    obs = packet.get("observation")
    require(isinstance(obs, dict), "observation: object required")
    start, end = timestamp(obs.get("start"), "start"), timestamp(obs.get("end"), "end")
    require(start < end, "observation: start must precede end")
    require(obs.get("lifecycle_coverage") in {"complete", "partial"}, "observation: lifecycle_coverage required")
    text(obs.get("coverage_basis"), "observation.coverage_basis")
    check_refs(obs.get("source_refs"), sources, "observation")
    incidents: dict[str, Any] = {}
    for incident in packet["incidents"]:
        require(isinstance(incident, dict), "incident: object required")
        iid = text(incident.get("id"), "incident.id")
        require(iid not in incidents, f"duplicate incident ID: {iid}")
        require(incident.get("group") in GROUPS, f"{iid}: group must be ESS, RIS or IAM")
        text(incident.get("service"), f"{iid}.service")
        check_refs(incident.get("source_refs"), sources, iid)
        detected = timestamp(incident.get("detected_at"), f"{iid}.detected_at")
        require(incident.get("lifecycle_coverage", obs["lifecycle_coverage"]) in {"complete", "partial"}, f"{iid}: coverage")
        times: dict[str, datetime] = {}
        for key in ("ack_at", "resolved_at"):
            require(key in incident, f"{iid}.{key}: explicit timestamp or null required")
            if incident[key] is not None:
                times[key] = timestamp(incident[key], f"{iid}.{key}")
                require(times[key] >= detected, f"{iid}.{key}: precedes detection")
        require("meaningful_response" in incident, f"{iid}: meaningful_response or null required")
        response = incident["meaningful_response"]
        if response is not None:
            require(isinstance(response, dict), f"{iid}: meaningful_response object required")
            times["response"] = timestamp(response.get("at"), f"{iid}.response.at")
            require(times["response"] >= detected, f"{iid}: response precedes detection")
            text(response.get("action"), f"{iid}.response.action")
            check_refs(response.get("source_refs"), sources, f"{iid}.response")
            if "resolved_at" in times:
                require(times["response"] <= times["resolved_at"], f"{iid}: first response follows resolution")
        owner = incident.get("owner_state")
        require(owner in {"owned", "unowned", "unknown"}, f"{iid}: owner_state")
        require(incident.get("owner_role") is None or isinstance(incident.get("owner_role"), str), f"{iid}: owner_role")
        if owner == "owned":
            text(incident.get("owner_role"), f"{iid}.owner_role")
        else:
            require(incident.get("owner_role") is None, f"{iid}: unowned/unknown must not assert an owner")
        check_refs(incident.get("owner_source_refs"), sources, f"{iid}.owner", owner != "unknown")
        state = incident.get("actionability")
        require(state in {"actionable", "nonactionable", "unknown"}, f"{iid}: actionability")
        check_refs(incident.get("actionability_source_refs"), sources, f"{iid}.actionability", state != "unknown")
        runbook = incident.get("runbook")
        require(isinstance(runbook, dict), f"{iid}: runbook object required")
        require(runbook.get("use") in {"useful", "not_useful", "not_used", "unknown"}, f"{iid}: runbook.use")
        if runbook.get("ref") is not None:
            text(runbook["ref"], f"{iid}.runbook.ref")
        if runbook["use"] in {"useful", "not_useful"}:
            text(runbook.get("ref"), f"{iid}.runbook.ref")
        check_refs(runbook.get("source_refs"), sources, f"{iid}.runbook", runbook["use"] != "unknown")
        esc = incident.get("escalation")
        require(isinstance(esc, dict), f"{iid}: escalation object required")
        require(esc.get("required") in {"yes", "no", "unknown"}, f"{iid}: escalation.required")
        check_refs(esc.get("source_refs"), sources, f"{iid}.escalation", esc["required"] != "unknown")
        for key in ("due_at", "at"):
            require(key in esc, f"{iid}: escalation.{key} must be explicit")
            if esc[key] is not None:
                require(timestamp(esc[key], f"{iid}.escalation.{key}") >= detected, f"{iid}: escalation precedes detection")
        if esc["required"] == "no":
            require(esc["due_at"] is None and esc["at"] is None, f"{iid}: escalation contradicts not-required")
        incidents[iid] = incident
    notifications: dict[str, Any] = {}
    duplicates = 0
    for row in packet["notifications"]:
        require(isinstance(row, dict), "notification: object required")
        nid = text(row.get("id"), "notification.id")
        if nid in notifications:
            require(canonical(row) == canonical(notifications[nid]), f"conflicting notification ID: {nid}")
            duplicates += 1
            continue
        require(row.get("group") in GROUPS, f"{nid}: group")
        for key in ("service", "rule", "fingerprint"):
            text(row.get(key), f"{nid}.{key}")
        require(row.get("kind") in {"initial", "repeat", "escalation", "unknown"}, f"{nid}: kind")
        at = timestamp(row.get("at"), f"{nid}.at")
        require("incident_id" in row, f"{nid}: incident_id or null required")
        iid = row["incident_id"]
        if iid is not None:
            require(isinstance(iid, str) and iid in incidents, f"{nid}: unresolved incident_id")
            inc = incidents[iid]
            require((inc["service"], inc["group"]) == (row["service"], row["group"]), f"{nid}: incident scope mismatch")
            require(at >= timestamp(inc["detected_at"], iid), f"{nid}: notification precedes detection")
        seconds = row.get("triage_seconds")
        require("triage_seconds" in row, f"{nid}: triage_seconds or null required")
        require(seconds is None or (type(seconds) in (float, int) and math.isfinite(seconds) and seconds >= 0), f"{nid}: invalid triage_seconds")
        check_refs(row.get("source_refs"), sources, nid)
        notifications[nid] = row
    return sources, incidents, sorted(notifications.values(), key=lambda x: x["id"]), duplicates


def measured(values: list[float], eligible: int) -> dict[str, Any]:
    return {"observed_count": len(values), "eligible_count": eligible,
            "median_seconds": statistics.median(values) if values else None,
            "min_seconds": min(values) if values else None,
            "max_seconds": max(values) if values else None}


def analyze(packet: dict[str, Any]) -> dict[str, Any]:
    sources, incidents, notifications, duplicates = validate(packet)
    obs = packet["observation"]
    start, end = timestamp(obs["start"], "start"), timestamp(obs["end"], "end")
    selected = [n for n in notifications if start <= timestamp(n["at"], n["id"]) < end]
    by_incident: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for notification in selected:
        by_incident[notification["incident_id"]].append(notification)
    rows, recommendations = [], []
    for iid, inc in sorted(incidents.items()):
        detected = timestamp(inc["detected_at"], iid)
        linked = by_incident[iid]
        resolved = timestamp(inc["resolved_at"], iid) if inc["resolved_at"] else None
        if not linked and not (detected < end and (resolved is None or resolved >= start)):
            continue
        if detected >= end:
            continue
        coverage = inc.get("lifecycle_coverage", obs["lifecycle_coverage"])
        response = inc["meaningful_response"]
        at = timestamp(response["at"], iid) if response else None
        # Missing response despite a recorded resolution is a documentation gap,
        # not proof that no one acted before service was restored.
        state = ("observed" if at is not None and at < end else
                 "unknown" if coverage == "partial" or (resolved is not None and resolved < end) else
                 "right_censored")
        ack = timestamp(inc["ack_at"], iid) if inc["ack_at"] else None
        esc = inc["escalation"]
        due = timestamp(esc["due_at"], iid) if esc["due_at"] else None
        escalated = timestamp(esc["at"], iid) if esc["at"] else None
        if esc["required"] == "no":
            escalation_state = "not_required"
        elif esc["required"] == "unknown" or due is None:
            escalation_state = "unknown"
        elif escalated is not None and escalated < end:
            escalation_state = "on_time" if escalated <= due else "late"
        elif due >= end:
            escalation_state = "not_due_in_window"
        else:
            escalation_state = "overdue_as_of_end" if coverage == "complete" else "unknown"
        repeated = [n for n in linked if n["kind"] == "repeat"]
        triage = [n["triage_seconds"] for n in repeated if n["triage_seconds"] is not None]
        known_triage = sum(triage)
        require(math.isfinite(known_triage), f"{iid}: nonfinite triage aggregate")
        evidence = (inc["source_refs"] + inc["owner_source_refs"] + inc["actionability_source_refs"]
                    + inc["runbook"]["source_refs"] + inc["escalation"]["source_refs"]
                    + (response["source_refs"] if response else [])
                    + [ref for n in linked for ref in n["source_refs"]])
        row = {"id": iid, "group": inc["group"], "service": inc["service"],
               "cohort": "new_detection" if detected >= start else "carry_in",
               "notification_ids": [n["id"] for n in linked], "notification_count": len(linked),
               "repeat_count": len(repeated), "escalation_notification_count": sum(n["kind"] == "escalation" for n in linked),
               "known_repeat_triage_seconds": known_triage, "repeat_triage_observed_count": len(triage),
               "owner_state": inc["owner_state"], "owner_role": inc["owner_role"],
               "actionability": inc["actionability"], "runbook_use": inc["runbook"]["use"],
               "response_state": state, "lifecycle_coverage": coverage,
               "response_seconds": (at - detected).total_seconds() if state == "observed" else None,
               "ack_seconds": (ack - detected).total_seconds() if ack is not None and ack < end else None,
               "censor_seconds": (end - detected).total_seconds() if state == "right_censored" else None,
               "escalation_state": escalation_state, "source_refs": sorted(set(evidence))}
        rows.append(row)
        options = []
        if inc["owner_state"] in {"unowned", "unknown"}:
            options.append(("ROUTING", "Confirm an accountable service role and rehearse routing", "Reduce time spent locating someone able to act", "Service owner and operations lead", [2, 6], "Retained routing exercise with recipient, useful action and elapsed time"))
        if repeated:
            options.append(("REPEATS", "Review repeat timing and correlation using the linked incident", "Reduce repeated triage without hiding distinct incidents or necessary escalations", "Service operations role", [2, 8], "Before/after shadow replay retaining separate incidents, escalation and reset behavior"))
        if inc["actionability"] == "nonactionable":
            options.append(("ACTIONABILITY", "Reconcile the alert condition with an explicit useful response", "Reduce interruptions that cannot change an operational decision", "Service owner with practitioner reviewer", [3, 10], "Reviewed user-impact examples and a documented response or nonpaging disposition"))
        if inc["runbook"]["use"] in {"not_useful", "unknown"}:
            options.append(("RUNBOOK", "Run an independent task walkthrough and repair observed guidance gaps", "Reduce investigation delay caused by unusable or unevaluated guidance", "Runbook maintainer and independent practitioner", [2, 6], "Timed walkthrough noting successful steps, missing context and revisions"))
        if escalation_state in {"late", "overdue_as_of_end", "unknown"}:
            options.append(("ESCALATION", "Confirm escalation conditions and rehearse the fallback route", "Reach a useful responder earlier when the initial route stalls", "Operations lead and dependent service owner", [2, 6], "Timestamped fallback exercise against the locally agreed escalation objective"))
        if state != "observed":
            options.append(("RESPONSE_EVIDENCE", "Complete first-useful-action evidence separately from acknowledgement", "Identify actual response delay without mistaking missing records for inactivity", "Incident record steward", [1, 4], "Linked first action with timestamp, purpose and source; coverage basis retained"))
        for code, change, mechanism, role, effort, evidence in options:
            recommendations.append({"id": f"AQ-{iid}-{code}", "incident_id": iid,
                "group": inc["group"], "service": inc["service"], "change": change,
                "expected_mechanism": mechanism, "proposed_owner_role": role,
                "proposed_effort_hours_low_high": effort, "effort_basis": "planning assumption, not measured savings or a commitment",
                "phase": "0-90 days (proposed)", "validation_evidence": evidence,
                "source_refs": row["source_refs"]})
    cohorts = {}
    for group in sorted(GROUPS):
        subset = [r for r in rows if r["group"] == group and r["cohort"] == "new_detection"]
        cohorts[group] = {"recorded_new_incidents": len(subset),
            "response_states": dict(sorted(Counter(r["response_state"] for r in subset).items())),
            "first_meaningful_response": measured([r["response_seconds"] for r in subset if r["response_seconds"] is not None], len(subset)),
            "acknowledgement": measured([r["ack_seconds"] for r in subset if r["ack_seconds"] is not None], len(subset))}
    orphans = [n for n in selected if n["incident_id"] is None]
    all_new = [r for r in rows if r["cohort"] == "new_detection"]
    classified = [r for r in rows if r["actionability"] != "unknown"]
    actionable = sum(r["actionability"] == "actionable" for r in classified)
    normalized = dict(packet, sources=sorted(packet["sources"], key=lambda x: x["id"]),
                      incidents=sorted(packet["incidents"], key=lambda x: x["id"]), notifications=notifications)
    return {"schema_version": 1, "tool_version": VERSION, "synthetic": packet["synthetic"],
        "label": "SYNTHETIC REHEARSAL - NOT UNIVERSITY FINDINGS" if packet["synthetic"] else "SUPPLIED-RECORD ANALYSIS - REQUIRES PROFESSIONAL INTERPRETATION",
        "normalized_evidence_sha256": hashlib.sha256(canonical(normalized).encode()).hexdigest(),
        "observation": obs, "counts": {"input_notification_rows": len(packet["notifications"]),
            "duplicate_export_rows": duplicates, "unique_notifications": len(notifications),
            "notifications_in_window": len(selected), "notifications_outside_window": len(notifications) - len(selected),
            "unlinked_notifications": len(orphans), "recorded_incidents_in_scope": len(rows),
            "carry_in_incidents": sum(r["cohort"] == "carry_in" for r in rows),
            "repeat_notifications": sum(r["repeat_count"] for r in rows),
            "escalation_notifications": sum(r["escalation_notification_count"] for r in rows),
            "unowned_incidents": sum(r["owner_state"] == "unowned" for r in rows),
            "unknown_owner_incidents": sum(r["owner_state"] == "unknown" for r in rows)},
        "first_meaningful_response": measured([r["response_seconds"] for r in all_new if r["response_seconds"] is not None], len(all_new)),
        "recorded_actionability": {"actionable": actionable, "classified_incidents": len(classified),
            "unknown_incidents": len(rows) - len(classified), "fraction": actionable / len(classified) if classified else None,
            "interpretation": "reviewed incident sample only; not alert precision, recall, or an institutional rate"},
        "groups": cohorts, "incidents": rows, "unlinked_notifications": orphans,
        "recommendations": recommendations, "sources": sorted(sources.values(), key=lambda x: x["id"]),
        "limits": ["Half-open observation window [start,end); events at end belong to the next window.",
            "Only explicitly linked incidents are grouped; matching fingerprints never establish identity.",
            "Repeated notifications are not automatically wasted work; escalations remain separate.",
            "Observed-only response medians exclude unresolved/unknown and carry-in records; they can be biased downward.",
            "Useful-response time uses the supplied first documented action; partial histories may conceal earlier actions.",
            "Complete lifecycle export is not a complete census of all service incidents; recall is not estimable.",
            "Actionability and runbook-use labels are supplied interpretations with references, not independently verified facts.",
            "Effort ranges are proposed planning assumptions; no savings, staffing commitment, peer rank or maturity score is inferred."]}


def md(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")


def render(report: dict[str, Any]) -> str:
    out = ["# Alert usefulness and response readiness", "", report["label"], "",
           f"Evidence digest: `{report['normalized_evidence_sha256']}`", "",
           f"Observation: {report['observation']['start']} to {report['observation']['end']} (end excluded).", "",
           "## Counts", "", "| Measure | Count |", "|---|---:|"]
    out += [f"| {md(k)} | {v} |" for k, v in report["counts"].items()]
    out += ["", "## Meaningful response (new detections only)", "",
            "Observed median is not an all-incident recovery metric. Unknown and censored cases remain below.", "",
            "| Group | Eligible | Observed | Median seconds | Response states |", "|---|---:|---:|---:|---|"]
    for group, values in report["groups"].items():
        metric = values["first_meaningful_response"]
        out.append(f"| {group} | {metric['eligible_count']} | {metric['observed_count']} | {metric['median_seconds'] if metric['median_seconds'] is not None else 'UNKNOWN'} | {md(values['response_states'])} |")
    out += ["", "## Incident review", "", "| Incident | Group | Notifications / repeats | Owner | Runbook use | Response | ACK / useful seconds | Escalation | Evidence |", "|---|---|---|---|---|---|---|---|---|"]
    for row in report["incidents"]:
        out.append("| " + " | ".join(md(x) for x in (row["id"], row["group"], f"{row['notification_count']} / {row['repeat_count']}", row["owner_state"], row["runbook_use"], row["response_state"] + " / " + row["cohort"], f"{row['ack_seconds'] if row['ack_seconds'] is not None else 'UNKNOWN'} / {row['response_seconds'] if row['response_seconds'] is not None else 'UNKNOWN'}", row["escalation_state"], ", ".join(row["source_refs"]))) + " |")
    out += ["", "## Unlinked notifications", "", "These are not merged or counted as proven separate incidents."]
    out += [f"- {md(n['id'])}: {md(n['service'])}, {md(n['at'])}; evidence {md(n['source_refs'])}." for n in report["unlinked_notifications"]]
    if not report["unlinked_notifications"]:
        out.append("None in the supplied window.")
    out += ["", "## Proposed improvement register", ""]
    for rec in report["recommendations"]:
        out += [f"### {md(rec['id'])}", "", md(rec["change"]) + ".", "",
                f"Mechanism: {md(rec['expected_mechanism'])}.",
                f"Proposed role: {md(rec['proposed_owner_role'])}; effort {rec['proposed_effort_hours_low_high']} hours ({rec['effort_basis']}).",
                f"Validation: {md(rec['validation_evidence'])}.", f"Evidence: {md(rec['source_refs'])}.", ""]
    out += ["## Evidence locators and retained excerpts", ""]
    for source in report["sources"]:
        out += [f"### {md(source['id'])}", "", f"Locator: {md(source['locator'])}", "", md(source["excerpt"]), ""]
    out += ["## Interpretation limits", ""] + ["- " + x for x in report["limits"]]
    return "\n".join(out) + "\n"


def csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    """Human spreadsheet view. JSON preserves exact strings; CSV quotes formula-like text."""
    def cell(value: Any) -> Any:
        if value is None:
            return "UNKNOWN"
        if isinstance(value, (dict, list)):
            value = canonical(value)
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: cell(row.get(key)) for key in fields})
    return buffer.getvalue()


def export(report: dict[str, Any], output: Path) -> None:
    # A new directory avoids overwriting an earlier assessment or source packet.
    files = {"report.json": json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
             "report.md": render(report),
             "incidents.csv": csv_text(report["incidents"], ["id", "group", "service", "cohort", "notification_count", "repeat_count", "escalation_notification_count", "known_repeat_triage_seconds", "repeat_triage_observed_count", "owner_state", "owner_role", "runbook_use", "response_state", "response_seconds", "ack_seconds", "censor_seconds", "escalation_state", "source_refs"]),
             "recommendations.csv": csv_text(report["recommendations"], ["id", "incident_id", "group", "service", "change", "expected_mechanism", "proposed_owner_role", "proposed_effort_hours_low_high", "effort_basis", "phase", "validation_evidence", "source_refs"])}
    output.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        (output / name).write_text(content, encoding="utf-8")
    manifest = {"tool_version": VERSION, "synthetic": report["synthetic"], "sha256": {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON packet; run synthetic_history.py to generate the example")
    parser.add_argument("--out-dir", required=True, type=Path, help="new output directory")
    args = parser.parse_args(argv)
    try:
        report = analyze(loads(args.input.read_text(encoding="utf-8-sig")))
        export(report, args.out_dir)
    except (InputError, OSError, TypeError, OverflowError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"label": report["label"], "counts": report["counts"], "output": str(args.out_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
