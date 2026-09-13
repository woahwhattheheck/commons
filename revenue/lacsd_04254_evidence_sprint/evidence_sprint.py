"""Evaluate candidate AI/ML sewer-collection decision evidence against the fixed synthetic portfolio."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping, Sequence

from evidence_core import (
    CANDIDATE_SCHEMA,
    EVENT_SCHEMA,
    RECEIPT_SCHEMA,
    ValidationError,
    _hex64,
    _strict_keys,
    _validate_candidate,
    build_portfolio,
    canonical_json,
    canonical_sha256,
)

MAX_JSON_BYTES = 1_048_576


def evaluate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    portfolio = build_portfolio()
    normalized = _validate_candidate(candidate, portfolio)
    events_by_scenario: dict[str, list[dict[str, Any]]] = {row["scenario_id"]: [] for row in portfolio["scenarios"]}
    for event in normalized["events"]:
        events_by_scenario[event["scenario_id"]].append(event)

    rows: list[dict[str, Any]] = []
    alert_expected_count = 0
    alert_detected_count = 0
    non_alert_count = 0
    non_alert_with_effect = 0
    timely_count = 0
    duplicate_effect_count = 0
    lineage_events = 0
    lineage_pass_events = 0
    recovery_expected = 0
    recovery_pass = 0

    for scenario in portfolio["scenarios"]:
        sid = scenario["scenario_id"]
        expected = scenario["expected_disposition"]
        events = events_by_scenario[sid]
        dispositions = [event["disposition"] for event in events]
        effects = sorted({event["effect_id"] for event in events if event["effect_id"] is not None})
        lineage_ok = all(event["input_sha256"] == scenario["stream_sha256"] for event in events) if events else False
        lineage_events += len(events)
        lineage_pass_events += sum(event["input_sha256"] == scenario["stream_sha256"] for event in events)

        if expected == "ALERT":
            alert_expected_count += 1
            detected = len(effects) >= 1 and "ALERT" in dispositions
            if detected:
                alert_detected_count += 1
            duplicate_effect_count += max(0, len(effects) - 1)
            alert_times = [event["observed_at_s"] for event in events if event["disposition"] == "ALERT"]
            first_alert = min(alert_times) if alert_times else None
            deadline = scenario["onset_s"] + scenario["max_alert_latency_s"]
            timely = first_alert is not None and scenario["onset_s"] <= first_alert <= deadline
            if timely:
                timely_count += 1
            expected_match = detected and all(d == "ALERT" for d in dispositions) and len(effects) == 1
        else:
            non_alert_count += 1
            detected = False
            first_alert = None
            timely = None
            if effects or "ALERT" in dispositions:
                non_alert_with_effect += 1
            expected_match = bool(events) and not effects and all(d == expected for d in dispositions)

        recovery_ok: bool | None = None
        if scenario["interruption_end_s"] is not None:
            recovery_expected += 1
            recovery_ok = any(event["disposition"] == "ALERT" and event["observed_at_s"] >= scenario["interruption_end_s"] for event in events) and len(effects) == 1
            if recovery_ok:
                recovery_pass += 1

        rows.append({"scenario_id": sid, "fault_class": scenario["fault_class"], "expected_disposition": expected, "event_count": len(events), "distinct_effect_count": len(effects), "lineage_ok": lineage_ok, "first_alert_s": first_alert, "timely": timely, "recovery_ok": recovery_ok, "expected_match": expected_match})

    covered = sum(bool(events_by_scenario[row["scenario_id"]]) for row in portfolio["scenarios"])
    scenario_matches = sum(row["expected_match"] for row in rows)
    detection_rate = alert_detected_count / alert_expected_count if alert_expected_count else 1.0
    false_urgent_rate = non_alert_with_effect / non_alert_count if non_alert_count else 0.0
    timeliness_rate = timely_count / alert_expected_count if alert_expected_count else 1.0
    lineage_rate = lineage_pass_events / lineage_events if lineage_events else 0.0
    recovery_rate = recovery_pass / recovery_expected if recovery_expected else 1.0

    gates = {
        "all_scenarios_covered": covered == len(portfolio["scenarios"]),
        "exact_expected_dispositions": scenario_matches == len(portfolio["scenarios"]),
        "alert_detection_rate_1_0": detection_rate == 1.0,
        "false_urgent_alert_rate_0_0": false_urgent_rate == 0.0,
        "timeliness_rate_1_0": timeliness_rate == 1.0,
        "duplicate_effect_count_0": duplicate_effect_count == 0,
        "lineage_pass_rate_1_0": lineage_rate == 1.0,
        "recovery_rate_1_0": recovery_rate == 1.0,
    }
    claims = [
        {"claim_id": "synthetic.coverage", "test": "all fixed scenarios have at least one candidate evidence event", "passed": gates["all_scenarios_covered"], "evidence": {"covered_scenarios": covered, "scenario_count": len(portfolio["scenarios"])}},
        {"claim_id": "synthetic.expected-dispositions", "test": "all scenario outputs match the fixed expected synthetic disposition", "passed": gates["exact_expected_dispositions"], "evidence": {"exact_match_rate": scenario_matches / len(portfolio["scenarios"])}},
        {"claim_id": "synthetic.alert-detection", "test": "every fixed ALERT scenario produces at least one alert effect", "passed": gates["alert_detection_rate_1_0"], "evidence": {"alert_detection_rate": detection_rate}},
        {"claim_id": "synthetic.no-false-urgent", "test": "non-ALERT scenarios produce zero urgent effect IDs", "passed": gates["false_urgent_alert_rate_0_0"], "evidence": {"false_urgent_alert_rate": false_urgent_rate}},
        {"claim_id": "synthetic.timeliness", "test": "first alert occurs within each fixed scenario latency bound", "passed": gates["timeliness_rate_1_0"], "evidence": {"timeliness_pass_rate": timeliness_rate}},
        {"claim_id": "synthetic.exactly-once-work-intent", "test": "retries/replays never mint a second distinct effect/work-intent ID for one actionable scenario", "passed": gates["duplicate_effect_count_0"], "evidence": {"duplicate_effect_count": duplicate_effect_count}},
        {"claim_id": "synthetic.lineage", "test": "every candidate event binds the exact fixed scenario-stream SHA-256", "passed": gates["lineage_pass_rate_1_0"], "evidence": {"lineage_pass_rate": lineage_rate}},
        {"claim_id": "synthetic.interruption-recovery", "test": "the interrupted scenario emits exactly one alert effect after transport recovery", "passed": gates["recovery_rate_1_0"], "evidence": {"recovery_pass_rate": recovery_rate}},
    ]
    status = "READY_FOR_BUYER_REVIEW" if all(gates.values()) else "HOLD"
    return {
        "portfolio_sha256": portfolio["portfolio_sha256"],
        "candidate_sha256": canonical_sha256(normalized),
        "candidate_id": normalized["candidate_id"],
        "model_id": normalized["model_id"],
        "model_version": normalized["model_version"],
        "candidate_build_sha256": normalized["candidate_build_sha256"],
        "scenario_count": len(portfolio["scenarios"]),
        "covered_scenarios": covered,
        "exact_match_rate": scenario_matches / len(portfolio["scenarios"]),
        "alert_detection_rate": detection_rate,
        "false_urgent_alert_rate": false_urgent_rate,
        "timeliness_pass_rate": timeliness_rate,
        "duplicate_effect_count": duplicate_effect_count,
        "lineage_pass_rate": lineage_rate,
        "recovery_pass_rate": recovery_rate,
        "gates": gates,
        "claims": claims,
        "scenario_results": rows,
        "status": status,
        "authority": {"field_performance_claimed": False, "production_control_authorized": False, "maintenance_dispatch_authorized": False, "buyer_acceptance_claimed": False, "payment_or_revenue_claimed": False},
        "note": "Synthetic software/evidence mechanics only; not field or buyer performance.",
    }


def compile_receipt(candidate: Mapping[str, Any]) -> dict[str, Any]:
    evaluation = evaluate_candidate(candidate)
    receipt = {"schema": RECEIPT_SCHEMA, "evaluation": evaluation, "evaluation_sha256": canonical_sha256(evaluation)}
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt


def verify_receipt(receipt: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise ValidationError("receipt must be an object")
    _strict_keys(receipt, {"schema", "evaluation", "evaluation_sha256", "receipt_sha256"}, label="receipt")
    if receipt["schema"] != RECEIPT_SCHEMA:
        raise ValidationError("unsupported receipt schema")
    _hex64(receipt["evaluation_sha256"], label="evaluation_sha256")
    _hex64(receipt["receipt_sha256"], label="receipt_sha256")
    expected = compile_receipt(candidate)
    if canonical_json(receipt) != canonical_json(expected):
        raise ValidationError("receipt does not exactly match a fresh evaluation of candidate + fixed portfolio")
    return dict(receipt)


def reference_candidate() -> dict[str, Any]:
    portfolio = build_portfolio()
    candidate_id = "reference-synthetic-candidate"
    model_id = "demo-only"
    model_version = "v1"
    candidate_build_sha256 = canonical_sha256({"candidate_id": candidate_id, "model_id": model_id, "model_version": model_version, "artifact": "synthetic-reference-build"})
    events: list[dict[str, Any]] = []
    for scenario in portfolio["scenarios"]:
        expected = scenario["expected_disposition"]
        if expected == "ALERT":
            observed = scenario["interruption_end_s"] if scenario["interruption_end_s"] is not None else scenario["onset_s"]
            packet = min(scenario["packets"], key=lambda p: (abs(p["observed_at_s"] - observed), p["observed_at_s"]))
            effect_id = f"effect-{scenario['scenario_id']}"
        else:
            packet = scenario["packets"][-1]
            observed = packet["observed_at_s"]
            effect_id = None
        events.append({"schema": EVENT_SCHEMA, "event_id": f"event-{scenario['scenario_id']}", "candidate_id": candidate_id, "model_id": model_id, "model_version": model_version, "candidate_build_sha256": candidate_build_sha256, "scenario_id": scenario["scenario_id"], "source_packet_id": packet["packet_id"], "observed_at_s": observed, "disposition": expected, "effect_id": effect_id, "input_sha256": scenario["stream_sha256"]})
    return {"schema": CANDIDATE_SCHEMA, "candidate_id": candidate_id, "model_id": model_id, "model_version": model_version, "candidate_build_sha256": candidate_build_sha256, "portfolio_sha256": portfolio["portfolio_sha256"], "events": events}


def _file_generation(st: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _load_strict_json(path: Path) -> Any:
    """Read one bounded ordinary-file generation and strict-parse its UTF-8 JSON."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(os.fspath(path), flags)
    except OSError as exc:
        raise ValidationError(f"cannot open JSON input as retained final component: {exc.strerror or exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValidationError("JSON input must be an ordinary regular file")
        if before.st_size < 0 or before.st_size > MAX_JSON_BYTES:
            raise ValidationError(f"JSON input exceeds {MAX_JSON_BYTES} byte limit")
        chunks: list[bytes] = []
        remaining = before.st_size + 1
        while remaining > 0:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(fd)
        if _file_generation(after) != _file_generation(before):
            raise ValidationError("JSON input generation changed while being read")
        if len(data) != before.st_size:
            raise ValidationError("JSON input length changed while being read")
        if len(data) > MAX_JSON_BYTES:
            raise ValidationError(f"JSON input exceeds {MAX_JSON_BYTES} byte limit")
    except OSError as exc:
        raise ValidationError(f"failed while reading JSON input: {exc.strerror or exc}") from exc
    finally:
        os.close(fd)
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValidationError("JSON input must be strict UTF-8") from exc

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=pairs_hook, parse_constant=lambda value: (_ for _ in ()).throw(ValidationError(f"non-finite JSON constant: {value}")))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {exc}") from exc


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("portfolio", help="print the fixed synthetic portfolio")
    sub.add_parser("demo", help="print a passing demonstration candidate and receipt")
    evaluate_parser = sub.add_parser("evaluate", help="evaluate candidate JSON")
    evaluate_parser.add_argument("candidate", type=Path)
    verify_parser = sub.add_parser("verify", help="verify receipt against candidate JSON")
    verify_parser.add_argument("candidate", type=Path)
    verify_parser.add_argument("receipt", type=Path)
    args = parser.parse_args(argv)
    if args.command == "portfolio":
        print(json.dumps(build_portfolio(), sort_keys=True, indent=2))
    elif args.command == "demo":
        candidate = reference_candidate()
        print(json.dumps({"candidate": candidate, "receipt": compile_receipt(candidate)}, sort_keys=True, indent=2))
    elif args.command == "evaluate":
        print(json.dumps(compile_receipt(_load_strict_json(args.candidate)), sort_keys=True, indent=2))
    else:
        candidate = _load_strict_json(args.candidate)
        receipt = _load_strict_json(args.receipt)
        print(json.dumps(verify_receipt(receipt, candidate), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
