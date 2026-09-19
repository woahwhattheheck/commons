#!/usr/bin/env python3
"""Offline recovery-record assessor. Never connects to or changes a service.

The states describe the supplied records, not the truth of a production system.
Python 3.10+, standard library only. See CONTRACT.md and FACILITATOR.md.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BOUNDARY = ("Assessment of supplied records only; no execution, operational authorization, "
            "University finding, certification, or inferred maturity score.")
COMMON = ("failure_recognition", "decision_ownership", "recovery_communications")
BASE = {
    "rollback": ("previous_state_available", "rollback_rehearsal", "dependency_compatibility", "side_effect_handling"),
    "forward_repair": ("repair_validated", "deployment_rehearsal", "dependency_compatibility", "side_effect_handling"),
    "restore": ("restore_point_available", "restore_rehearsal", "dependency_compatibility", "reconciliation_rehearsal"),
}
DATA = {
    "rollback": ("old_version_compatible", "new_writes_preserved", "migration_reversal_rehearsal"),
    "forward_repair": ("migration_compatibility", "new_writes_preserved"),
    "restore": ("new_writes_preserved",),
}
DOMAINS = ("service", "version", "dependencies", "monitoring")
ALL_CHECKS = set(COMMON) | {c for seq in (*BASE.values(), *DATA.values()) for c in seq}
ALL_CHECKS |= {"verification_" + d for d in (*DOMAINS, "data_integrity", "data_loss")}
STAGES = ("impact_at", "detected_at", "decided_at", "action_started_at", "action_completed_at")


class InputError(ValueError):
    """Malformed or internally inconsistent input, not a finding about a team."""


def require(ok: bool, path: str, message: str) -> None:
    if not ok:
        raise InputError(f"{path}: {message}")


def obj(value: Any, path: str, keys: str) -> dict:
    require(isinstance(value, dict), path, "expected an object")
    expected = set(keys.split())
    require(set(value) == expected, path,
            f"fields differ; missing={sorted(expected - set(value))}, extra={sorted(set(value) - expected)}")
    return value


def text(value: Any, path: str, nullable: bool = False) -> None:
    require((nullable and value is None) or (isinstance(value, str) and bool(value.strip())),
            path, "expected nonblank text" + (" or null" if nullable else ""))


def number(value: Any, path: str, nullable: bool = False) -> None:
    require((nullable and value is None) or
            (type(value) in (int, float) and math.isfinite(value) and value >= 0),
            path, "expected a finite nonnegative number" + (" or null" if nullable else ""))


def stamp(value: Any, path: str) -> datetime | None:
    if value is None:
        return None
    text(value, path)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"{path}: expected ISO 8601 timestamp") from exc
    require(dt.tzinfo is not None and dt.utcoffset() is not None, path, "timezone is required")
    return dt.astimezone(timezone.utc)


def rows(value: Any, path: str) -> list:
    require(isinstance(value, list), path, "expected an array")
    return value


def validate(packet: Any) -> dict:
    """Validate the complete v1 contract without modifying the caller's data."""
    p = obj(packet, "$", "schema_version scenario_id title group service classification as_of evidence_max_age_days change targets timeline decision options evidence recovery")
    require(type(p["schema_version"]) is int and p["schema_version"] == 1, "schema_version", "must be integer 1")
    for key in ("scenario_id", "title", "group", "service"):
        text(p[key], key)
    require(p["classification"] in ("synthetic", "supplied"), "classification", "use synthetic or supplied")
    as_of = stamp(p["as_of"], "as_of")
    require(as_of is not None, "as_of", "cannot be null")
    number(p["evidence_max_age_days"], "evidence_max_age_days")
    require(p["evidence_max_age_days"] <= 36500, "evidence_max_age_days", "maximum is 36500 days")
    change = obj(p["change"], "change", "kind from_version to_version deployed_at")
    require(change["kind"] in ("configuration", "data_migration"), "change.kind", "unsupported change kind")
    for key in ("from_version", "to_version"):
        text(change[key], "change." + key)
    previous = stamp(change["deployed_at"], "change.deployed_at")
    if previous:
        require(previous <= as_of, "change.deployed_at", "cannot follow as_of")
    target = obj(p["targets"], "targets", "recovery_minutes data_loss_minutes observation_minutes")
    for key, value in target.items():
        number(value, "targets." + key, nullable=key != "observation_minutes")
    timeline = obj(p["timeline"], "timeline", " ".join(STAGES))
    for key in STAGES:
        current = stamp(timeline[key], "timeline." + key)
        if current:
            require(current <= as_of, "timeline." + key, "cannot follow as_of")
            require(previous is None or current >= previous, "timeline." + key, "timestamps are out of order")
            previous = current
    decision = obj(p["decision"], "decision", "selected_option_id owner_role rationale")
    for key, value in decision.items():
        text(value, "decision." + key, nullable=True)
    option_ids: set[str] = set()
    for i, option in enumerate(rows(p["options"], "options")):
        q = f"options[{i}]"
        obj(option, q, "id strategy target_version estimated_action_minutes estimated_data_loss_minutes rationale")
        for key in ("id", "target_version", "rationale"):
            text(option[key], q + "." + key)
        require(option["strategy"] in BASE, q + ".strategy", "unsupported strategy")
        require(option["id"] not in option_ids, q + ".id", "duplicate option ID")
        option_ids.add(option["id"])
        bounds = option["estimated_action_minutes"]
        if bounds is not None:
            rows(bounds, q + ".estimated_action_minutes")
            require(len(bounds) == 2, q, "time estimate must be [lower, upper] or null")
            for bound in bounds:
                number(bound, q + ".estimated_action_minutes")
            require(bounds[0] <= bounds[1], q, "time estimate lower exceeds upper")
        number(option["estimated_data_loss_minutes"], q + ".estimated_data_loss_minutes", True)
    require(decision["selected_option_id"] is None or decision["selected_option_id"] in option_ids,
            "decision.selected_option_id", "unknown option")
    evidence_ids: set[str] = set()
    for i, item in enumerate(rows(p["evidence"], "evidence")):
        q = f"evidence[{i}]"
        obj(item, q, "id check option_id kind outcome service release_version target_version observed_at locator summary run_id environment representative")
        for key in ("id", "check", "service", "release_version", "locator", "summary"):
            text(item[key], q + "." + key)
        for key in ("option_id", "target_version", "run_id", "environment"):
            text(item[key], q + "." + key, True)
        require(item["id"] not in evidence_ids, q + ".id", "duplicate evidence ID")
        evidence_ids.add(item["id"])
        require(item["check"] in ALL_CHECKS, q + ".check", "unknown check")
        require(item["option_id"] is None or item["option_id"] in option_ids, q + ".option_id", "unknown option")
        require(item["kind"] in ("document", "interview", "demonstration"), q + ".kind", "unknown evidence kind")
        require(item["outcome"] in ("supports", "contradicts", "unknown"), q + ".outcome", "unknown outcome")
        require(item["representative"] is None or type(item["representative"]) is bool,
                q + ".representative", "expected true, false, or null")
        when = stamp(item["observed_at"], q + ".observed_at")
        require(when is None or when <= as_of, q + ".observed_at", "cannot follow as_of")
    recovery = obj(p["recovery"], "recovery", "checks observation_minutes data_loss_minutes")
    for key in ("observation_minutes", "data_loss_minutes"):
        number(recovery[key], "recovery." + key, True)
    check_ids: set[str] = set()
    for i, check in enumerate(rows(recovery["checks"], "recovery.checks")):
        q = f"recovery.checks[{i}]"
        obj(check, q, "id domain result observed_at evidence_ids note")
        for key in ("id", "note"):
            text(check[key], q + "." + key)
        require(check["id"] not in check_ids, q + ".id", "duplicate verification ID")
        check_ids.add(check["id"])
        require(check["domain"] in (*DOMAINS, "data_integrity", "data_loss"), q + ".domain", "unknown domain")
        require(check["result"] in ("pass", "fail", "unknown"), q + ".result", "unknown result")
        refs = rows(check["evidence_ids"], q + ".evidence_ids")
        for ref in refs:
            text(ref, q + ".evidence_ids")
            require(ref in evidence_ids, q + ".evidence_ids", f"unknown evidence {ref}")
        require(len(refs) == len(set(refs)), q + ".evidence_ids", "duplicate evidence reference")
        when = stamp(check["observed_at"], q + ".observed_at")
        require(when is None or when <= as_of, q + ".observed_at", "cannot follow as_of")
    return p


def needed(packet: dict, option: dict) -> tuple[str, ...]:
    checks = BASE[option["strategy"]]
    return checks + (DATA[option["strategy"]] if packet["change"]["kind"] == "data_migration" else ())


def exclusions(p: dict, item: dict, option: dict | None) -> list[str]:
    reasons = []
    when, as_of = stamp(item["observed_at"], "observed_at"), stamp(p["as_of"], "as_of")
    if when is None:
        reasons.append("undated")
    elif as_of - when > timedelta(days=p["evidence_max_age_days"]):
        reasons.append("stale")
    if item["service"] != p["service"]:
        reasons.append("different_service")
    if item["release_version"] != p["change"]["to_version"]:
        reasons.append("different_release")
    if item["target_version"] != (option["target_version"] if option else None):
        reasons.append("different_target")
    if item["kind"] == "demonstration":
        if not item["run_id"] or not item["environment"]:
            reasons.append("missing_run_context")
        if item["representative"] is not True:
            reasons.append("representativeness_not_established")
    return reasons


def assess_check(p: dict, name: str, option: dict | None = None) -> dict:
    oid = option["id"] if option else None
    candidates = [e for e in p["evidence"] if e["check"] == name and e["option_id"] == oid]
    excluded = [{"id": e["id"], "reasons": exclusions(p, e, option)} for e in candidates if exclusions(p, e, option)]
    eligible = [e for e in candidates if not exclusions(p, e, option)]
    positive = [e for e in eligible if e["outcome"] == "supports"]
    negative = [e for e in eligible if e["outcome"] == "contradicts"]
    state = "unknown"
    if negative:
        state = "conflicting" if positive else "contradicted"
    elif any(e["kind"] == "demonstration" for e in positive):
        state = "demonstrated"
    elif any(e["kind"] == "document" for e in positive):
        state = "documented_only"
    elif positive:
        state = "reported_only"
    return {"check": name, "state": state, "eligible_ids": [e["id"] for e in eligible], "excluded": excluded}


def minutes(start: str | None, end: str | None) -> float | None:
    a, b = stamp(start, "start"), stamp(end, "end")
    return round((b - a).total_seconds() / 60, 6) if a and b and b >= a else None


def compare(value: float | None, target: float | None) -> str:
    return "unknown" if value is None or target is None else ("within" if value <= target else "exceeds")


def inspect_recovery(p: dict, selected: dict | None) -> dict:
    domains = DOMAINS + (("data_integrity",) if p["change"]["kind"] == "data_migration" else ())
    index = {e["id"]: e for e in p["evidence"]}
    completed = stamp(p["timeline"]["action_completed_at"], "action_completed_at")
    evaluated = []
    for check in p["recovery"]["checks"]:
        when = stamp(check["observed_at"], "observed_at")
        reasons = []
        if not selected or not completed or not when or when < completed:
            reasons.append("missing_or_pre_action_verification_context")
        relevant = []
        for ref in check["evidence_ids"]:
            e = index[ref]
            ew = stamp(e["observed_at"], "observed_at")
            if (selected and e["option_id"] == selected["id"] and
                e["check"] == "verification_" + check["domain"] and not exclusions(p, e, selected) and
                e["kind"] == "demonstration" and ew and when and completed and completed <= ew <= when):
                relevant.append(e)
        expected = "supports" if check["result"] == "pass" else "contradicts"
        matches = [e for e in relevant if e["outcome"] == expected]
        if not matches:
            reasons.append("no_matching_demonstration")
        if any(e["outcome"] == "contradicts" for e in relevant) and check["result"] == "pass":
            reasons.append("contradictory_verification_evidence")
        state = ("demonstrated_pass" if check["result"] == "pass" else "demonstrated_failure") if not reasons and check["result"] != "unknown" else "unverified"
        evaluated.append({**check, "state": state, "reasons": reasons})
    domain_states = {}
    for domain in (*domains, "data_loss"):
        checks = [c for c in evaluated if c["domain"] == domain]
        if any(c["state"] == "demonstrated_failure" for c in checks):
            state = "demonstrated_failure"
        elif any(c["result"] == "fail" for c in checks):
            state = "reported_failure_unverified"
        elif checks and all(c["state"] == "demonstrated_pass" for c in checks):
            state = "demonstrated_pass"
        else:
            state = "unknown"
        domain_states[domain] = state
    monitor_times = [c["observed_at"] for c in evaluated if c["domain"] == "monitoring" and c["state"] == "demonstrated_pass"]
    elapsed_window = max((minutes(p["timeline"]["action_completed_at"], t) for t in monitor_times), default=None)
    observation = p["recovery"]["observation_minutes"]
    window_ok = (observation is not None and elapsed_window is not None and
                 p["targets"]["observation_minutes"] <= observation <= elapsed_window)
    if any(domain_states[d] in ("demonstrated_failure", "reported_failure_unverified") for d in domains):
        state = "verification_failure_recorded"
    elif all(domain_states[d] == "demonstrated_pass" for d in domains) and window_ok:
        state = "recovery_demonstrated_in_records"
    elif not evaluated and not completed:
        state = "not_observed"
    else:
        state = "recovery_not_fully_verified"
    verified_at = max((c["observed_at"] for c in evaluated if c["domain"] in domains), key=lambda x: stamp(x, "observed_at")) if state == "recovery_demonstrated_in_records" else None
    total = minutes(p["timeline"]["impact_at"], verified_at)
    loss = p["recovery"]["data_loss_minutes"] if domain_states["data_loss"] == "demonstrated_pass" else None
    return {"state": state, "domain_states": domain_states, "checks": evaluated,
            "observation_window_satisfied": window_ok, "reported_observation_minutes": observation,
            "maximum_observable_minutes": elapsed_window, "verified_at": verified_at,
            "impact_to_verified_minutes": total, "recovery_target": compare(total, p["targets"]["recovery_minutes"]),
            "evidenced_data_loss_minutes": loss, "data_loss_target": compare(loss, p["targets"]["data_loss_minutes"])}


def assess(packet: Any) -> dict:
    p = validate(packet)
    options = []
    followups = []
    common = [assess_check(p, check) for check in COMMON]
    elapsed = minutes(p["timeline"]["impact_at"], p["timeline"]["decided_at"])
    for option in p["options"]:
        checks = [assess_check(p, name, option) for name in needed(p, option)]
        states = {c["state"] for c in checks}
        state = "demonstrated_in_records"
        for candidate in ("conflicting", "contradicted", "unknown", "reported_only", "documented_only"):
            if candidate in states:
                state = candidate
                break
        bounds = option["estimated_action_minutes"]
        projected = [round(elapsed + b, 6) for b in bounds] if bounds is not None and elapsed is not None else None
        options.append({**option, "evidence_state": state, "checks": checks,
                        "projected_impact_minutes": projected,
                        "time_target_using_upper_bound": compare(projected[1] if projected else None, p["targets"]["recovery_minutes"]),
                        "estimated_data_loss_target": compare(option["estimated_data_loss_minutes"], p["targets"]["data_loss_minutes"])})
        for check in checks:
            if check["state"] != "demonstrated":
                followups.append({"scope": option["id"], "check": check["check"], "state": check["state"],
                                  "question": "Reconcile or obtain representative, version-matched execution evidence for " + check["check"].replace("_", " ") + ". Retain contrary records.",
                                  "evidence_ids": check["eligible_ids"], "excluded": check["excluded"]})
    for check in common:
        if check["state"] != "demonstrated":
            followups.append({"scope": "common", **check, "question": "Show how " + check["check"].replace("_", " ") + " operated in this release or a representative exercise."})
    selected = next((o for o in p["options"] if o["id"] == p["decision"]["selected_option_id"]), None)
    recovery = inspect_recovery(p, selected)
    decision_issues = ["missing_" + k for k, v in p["decision"].items() if v is None]
    if p["timeline"]["decided_at"] is None:
        decision_issues.append("missing_decision_timestamp")
    if recovery["state"] != "recovery_demonstrated_in_records":
        followups.append({"scope": "recovery", "state": recovery["state"],
                          "question": "Supply post-action service, version, dependency, monitoring and applicable data-integrity demonstrations; record the observation window and unresolved failures."})
    canonical = json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return {"schema_version": 1, "scenario_id": p["scenario_id"], "title": p["title"], "group": p["group"],
            "service": p["service"], "classification": p["classification"], "boundary": BOUNDARY,
            "basis": {"canonical_input_sha256": hashlib.sha256(canonical).hexdigest(), "as_of": p["as_of"],
                      "evidence_max_age_days": p["evidence_max_age_days"], "evidence": p["evidence"]},
            "common_practices": common, "options": options, "decision": {**p["decision"], "record_issues": decision_issues},
            "metrics_minutes": {"impact_to_detection": minutes(p["timeline"]["impact_at"], p["timeline"]["detected_at"]),
                                "detection_to_decision": minutes(p["timeline"]["detected_at"], p["timeline"]["decided_at"]),
                                "action_duration": minutes(p["timeline"]["action_started_at"], p["timeline"]["action_completed_at"])},
            "recovery": recovery, "followups": followups}


def safe(value: Any) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>\-])", r"\\\1", html.escape(str(value), quote=True).replace("\n", " ").replace("\r", " "))


def markdown(report: dict) -> str:
    lines = [f"# Recovery assessment: {safe(report['scenario_id'])}", "",
             f"**{safe(report['classification'].upper())} — {safe(report['title'])}**", "",
             report["boundary"], "", f"Basis SHA-256: `{report['basis']['canonical_input_sha256']}`",
             f"As of: {safe(report['basis']['as_of'])}", "", "## Common practices", ""]
    for check in report["common_practices"]:
        lines.append(f"- {safe(check['check'])}: **{safe(check['state'])}**; evidence {safe(check['eligible_ids'])}")
    lines += ["", "## Recovery alternatives", "", "Evidence state and objective fit are independent. No strategy is selected by this tool.", ""]
    for option in report["options"]:
        lines += [f"### {safe(option['id'])}: {safe(option['strategy'])}", "",
                  f"Evidence: **{safe(option['evidence_state'])}**. Target version: {safe(option['target_version'])}.",
                  f"Projected impact minutes: {safe(option['projected_impact_minutes'])}; time objective: {safe(option['time_target_using_upper_bound'])}; estimated data-loss objective: {safe(option['estimated_data_loss_target'])}.",
                  f"Recorded rationale: {safe(option['rationale'])}", ""]
        for c in option["checks"]:
            lines.append(f"- {safe(c['check'])}: {safe(c['state'])}; evidence {safe(c['eligible_ids'])}; excluded {safe(c['excluded'])}")
    recovery = report["recovery"]
    lines += ["", "## Recorded decision", "", safe(report["decision"]), "", "## Observed recovery", "",
              f"**{safe(recovery['state'])}**", "", safe(recovery["domain_states"]), "",
              f"Observation window satisfied: {recovery['observation_window_satisfied']}. Impact-to-verified minutes: {safe(recovery['impact_to_verified_minutes'])}.",
              f"Recovery objective: {safe(recovery['recovery_target'])}; evidenced data-loss objective: {safe(recovery['data_loss_target'])}.", ""]
    for c in recovery["checks"]:
        lines.append(f"- {safe(c['id'])}: {safe(c['state'])}; reasons {safe(c['reasons'])}; evidence {safe(c['evidence_ids'])}")
    lines += ["", "## Follow-up questions", ""]
    for f in report["followups"]:
        lines.append(f"- {safe(f['scope'])}: {safe(f['question'])}")
    lines += ["", "## Evidence register (metadata; locators are not fetched)", ""]
    for e in report["basis"]["evidence"]:
        lines.append(f"- **{safe(e['id'])}** — {safe(e['kind'])}/{safe(e['outcome'])}; {safe(e['observed_at'])}; {safe(e['locator'])}; {safe(e['summary'])}")
    return "\n".join(lines) + "\n"


def load(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict:
        out = {}
        for key, value in items:
            require(key not in out, "$", "duplicate JSON member " + key)
            out[key] = value
        return out

    def reject(value: str) -> None:
        raise InputError("$: nonstandard numeric constant " + value)

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=reject)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        report = assess(load(args.packet))
        print(markdown(report) if args.format == "markdown" else json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), end="\n" if args.format == "json" else "")
    except (InputError, OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
