#!/usr/bin/env python3
"""Deterministic decision-program compiler/evaluator for ARM26BX06-NV012 evidence.

This is a non-operational demonstration kernel. It does not contact providers,
submit proposals, or make final decisions. All inputs are owner-supplied JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "commons.decision-program/v1"
DECISION_STATES = {"PENDING_HUMAN", "HUMAN_ACCEPTED", "HUMAN_REJECTED"}
BIAS_STATES = {"PASS", "FAIL", "NOT_RUN"}
RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
OPS = {"<=", ">=", "=="}

class ValidationError(ValueError):
    pass


def _is_int(value: Any) -> bool:
    return type(value) is int


def _strict_object(value: Any, where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValidationError(f"{where} must be an object")
    return value


def _strict_list(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise ValidationError(f"{where} must be an array")
    return value


def _string(value: Any, where: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{where} must be a non-empty string")
    return value


def _keys(obj: dict[str, Any], required: set[str], optional: set[str], where: str) -> None:
    got = set(obj)
    missing = sorted(required - got)
    extra = sorted(got - required - optional)
    if missing or extra:
        raise ValidationError(f"{where} keys mismatch missing={missing} extra={extra}")


def canonical_bytes(value: Any) -> bytes:
    """Canonical JSON with booleans/ints/strings only; rejects floats/non-finite values."""
    def check(node: Any, where: str = "$") -> None:
        if node is None or type(node) in (str, bool, int):
            return
        if type(node) is float:
            raise ValidationError(f"{where}: floats are forbidden; use integer scaled units")
        if type(node) is list:
            for i, item in enumerate(node):
                check(item, f"{where}[{i}]")
            return
        if type(node) is dict:
            for key, item in node.items():
                if type(key) is not str:
                    raise ValidationError(f"{where}: object keys must be strings")
                check(item, f"{where}.{key}")
            return
        raise ValidationError(f"{where}: unsupported JSON type {type(node).__name__}")
    check(value)
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _unique_ids(rows: list[Any], where: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(rows):
        row = _strict_object(raw, f"{where}[{i}]")
        rid = _string(row.get("id"), f"{where}[{i}].id")
        if rid in seen:
            raise ValidationError(f"duplicate id {rid!r} in {where}")
        seen.add(rid)
        out.append(row)
    return out


def validate_program(raw: Any) -> dict[str, Any]:
    p = deepcopy(_strict_object(raw, "$"))
    _keys(
        p,
        {
            "schema_version", "program_id", "title", "generation", "supersedes_digest",
            "as_of", "human_authority", "objectives", "options", "constraints",
            "assumptions", "risks", "bias_checks", "evidence"
        },
        {"notes"},
        "$",
    )
    if p["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("unsupported schema_version")
    _string(p["program_id"], "$.program_id")
    _string(p["title"], "$.title")
    _string(p["as_of"], "$.as_of")
    if not _is_int(p["generation"]) or p["generation"] < 1:
        raise ValidationError("$.generation must be integer >= 1")
    if p["generation"] == 1:
        if p["supersedes_digest"] is not None:
            raise ValidationError("generation 1 must not supersede a prior digest")
    else:
        if type(p["supersedes_digest"]) is not str or len(p["supersedes_digest"]) != 64:
            raise ValidationError("generation >1 requires a 64-char supersedes_digest")

    auth = _strict_object(p["human_authority"], "$.human_authority")
    _keys(auth, {"required", "decision_state"}, {"decision_note"}, "$.human_authority")
    if auth["required"] is not True:
        raise ValidationError("human authority must remain required")
    if auth["decision_state"] not in DECISION_STATES:
        raise ValidationError("invalid human decision_state")

    objectives = _unique_ids(_strict_list(p["objectives"], "$.objectives"), "$.objectives")
    if not objectives:
        raise ValidationError("at least one objective is required")
    objective_ids: set[str] = set()
    total_weight = 0
    for i, row in enumerate(objectives):
        _keys(row, {"id", "label", "weight_bp"}, set(), f"$.objectives[{i}]")
        _string(row["label"], f"$.objectives[{i}].label")
        w = row["weight_bp"]
        if not _is_int(w) or w <= 0:
            raise ValidationError("objective weight_bp must be a positive integer")
        total_weight += w
        objective_ids.add(row["id"])
    if total_weight != 10000:
        raise ValidationError(f"objective weights must sum to 10000 bp, got {total_weight}")

    options = _unique_ids(_strict_list(p["options"], "$.options"), "$.options")
    if len(options) < 2:
        raise ValidationError("at least two options are required")
    option_ids: set[str] = set()
    for i, row in enumerate(options):
        _keys(row, {"id", "label", "scores", "metrics"}, set(), f"$.options[{i}]")
        _string(row["label"], f"$.options[{i}].label")
        scores = _strict_object(row["scores"], f"$.options[{i}].scores")
        if set(scores) != objective_ids:
            raise ValidationError(f"option {row['id']} scores must cover each objective exactly")
        for oid, score in scores.items():
            if not _is_int(score) or not 0 <= score <= 10000:
                raise ValidationError(f"option {row['id']} score {oid} must be integer 0..10000")
        metrics = _strict_object(row["metrics"], f"$.options[{i}].metrics")
        for key, value in metrics.items():
            _string(key, f"$.options[{i}].metrics key")
            if not _is_int(value):
                raise ValidationError("metrics must be integer scaled units")
        option_ids.add(row["id"])

    constraints = _unique_ids(_strict_list(p["constraints"], "$.constraints"), "$.constraints")
    for i, row in enumerate(constraints):
        _keys(row, {"id", "metric", "op", "value", "rationale"}, set(), f"$.constraints[{i}]")
        _string(row["metric"], f"$.constraints[{i}].metric")
        _string(row["rationale"], f"$.constraints[{i}].rationale")
        if row["op"] not in OPS or not _is_int(row["value"]):
            raise ValidationError("constraint op/value invalid")

    assumptions = _unique_ids(_strict_list(p["assumptions"], "$.assumptions"), "$.assumptions")
    if not assumptions:
        raise ValidationError("at least one assumption is required")
    for i, row in enumerate(assumptions):
        _keys(row, {"id", "statement", "status", "evidence_ids"}, set(), f"$.assumptions[{i}]")
        _string(row["statement"], f"$.assumptions[{i}].statement")
        if row["status"] not in {"SUPPORTED", "UNRESOLVED", "REJECTED"}:
            raise ValidationError("invalid assumption status")
        _strict_list(row["evidence_ids"], f"$.assumptions[{i}].evidence_ids")

    risks = _unique_ids(_strict_list(p["risks"], "$.risks"), "$.risks")
    if not risks:
        raise ValidationError("at least one risk is required")
    for i, row in enumerate(risks):
        _keys(row, {"id", "statement", "level", "mitigation"}, set(), f"$.risks[{i}]")
        _string(row["statement"], f"$.risks[{i}].statement")
        _string(row["mitigation"], f"$.risks[{i}].mitigation")
        if row["level"] not in RISK_LEVELS:
            raise ValidationError("invalid risk level")

    bias = _unique_ids(_strict_list(p["bias_checks"], "$.bias_checks"), "$.bias_checks")
    if not bias:
        raise ValidationError("at least one bias check is required")
    for i, row in enumerate(bias):
        _keys(row, {"id", "question", "status", "finding"}, set(), f"$.bias_checks[{i}]")
        _string(row["question"], f"$.bias_checks[{i}].question")
        _string(row["finding"], f"$.bias_checks[{i}].finding")
        if row["status"] not in BIAS_STATES:
            raise ValidationError("invalid bias status")

    evidence = _unique_ids(_strict_list(p["evidence"], "$.evidence"), "$.evidence")
    if not evidence:
        raise ValidationError("at least one evidence item is required")
    evidence_ids = set()
    for i, row in enumerate(evidence):
        _keys(row, {"id", "kind", "source_ref", "observed_at", "digest_sha256"}, set(), f"$.evidence[{i}]")
        _string(row["kind"], f"$.evidence[{i}].kind")
        _string(row["source_ref"], f"$.evidence[{i}].source_ref")
        _string(row["observed_at"], f"$.evidence[{i}].observed_at")
        if type(row["digest_sha256"]) is not str or len(row["digest_sha256"]) != 64:
            raise ValidationError("evidence digest_sha256 must be 64 hex chars")
        try:
            int(row["digest_sha256"], 16)
        except ValueError as exc:
            raise ValidationError("evidence digest_sha256 must be hex") from exc
        evidence_ids.add(row["id"])
    for i, row in enumerate(assumptions):
        for eid in row["evidence_ids"]:
            if eid not in evidence_ids:
                raise ValidationError(f"assumption {row['id']} references unknown evidence {eid}")

    canonical_bytes(p)
    return p


def _constraint_pass(metric: int, op: str, expected: int) -> bool:
    if op == "<=":
        return metric <= expected
    if op == ">=":
        return metric >= expected
    if op == "==":
        return metric == expected
    raise AssertionError(op)


def evaluate(raw: Any) -> dict[str, Any]:
    p = validate_program(raw)
    objectives = {row["id"]: row for row in p["objectives"]}
    option_rows: list[dict[str, Any]] = []
    for option in p["options"]:
        failures: list[str] = []
        for constraint in p["constraints"]:
            metric = option["metrics"].get(constraint["metric"])
            if metric is None or not _constraint_pass(metric, constraint["op"], constraint["value"]):
                failures.append(constraint["id"])
        weighted = sum(option["scores"][oid] * objectives[oid]["weight_bp"] for oid in objectives)
        option_rows.append({
            "option_id": option["id"],
            "eligible": not failures,
            "failed_constraints": sorted(failures),
            "weighted_score": weighted,
        })
    eligible = [row for row in option_rows if row["eligible"]]
    eligible.sort(key=lambda r: (-r["weighted_score"], r["option_id"]))
    machine_preference = eligible[0]["option_id"] if eligible else None
    runner = eligible[1] if len(eligible) > 1 else None
    winner = eligible[0] if eligible else None

    what_flips: dict[str, Any]
    if winner is None:
        what_flips = {"kind": "NO_ELIGIBLE_OPTION", "delta_weighted_score": None}
    elif runner is None:
        what_flips = {"kind": "CONSTRAINT_ONLY", "delta_weighted_score": None}
    else:
        gap = winner["weighted_score"] - runner["weighted_score"]
        what_flips = {
            "kind": "RUNNER_UP_SCORE_SWING",
            "runner_up_option_id": runner["option_id"],
            "delta_weighted_score": gap + 1,
            "explanation": "Runner-up must gain this many weighted-score units relative to the machine preference to become first.",
        }

    blockers = []
    if any(a["status"] == "UNRESOLVED" for a in p["assumptions"]):
        blockers.append("UNRESOLVED_ASSUMPTION")
    if any(r["level"] in {"HIGH", "CRITICAL"} for r in p["risks"]):
        blockers.append("HIGH_OR_CRITICAL_RISK")
    if any(b["status"] != "PASS" for b in p["bias_checks"]):
        blockers.append("BIAS_CHECK_NOT_PASS")
    if not eligible:
        blockers.append("NO_ELIGIBLE_OPTION")

    if blockers:
        readiness = "HOLD"
    else:
        readiness = "READY_FOR_HUMAN_REVIEW"
    result = {
        "schema_version": "commons.decision-evaluation/v1",
        "program_id": p["program_id"],
        "generation": p["generation"],
        "program_digest": digest(p),
        "readiness": readiness,
        "blockers": sorted(set(blockers)),
        "machine_preference": machine_preference,
        "human_decision_required": True,
        "final_decision": None,
        "option_results": sorted(option_rows, key=lambda r: r["option_id"]),
        "what_flips_decision": what_flips,
    }
    result["evaluation_digest"] = digest(result)
    return result


def verify_refresh(previous: Any, current: Any) -> dict[str, Any]:
    prev = validate_program(previous)
    cur = validate_program(current)
    if cur["program_id"] != prev["program_id"]:
        raise ValidationError("refresh program_id mismatch")
    if cur["generation"] != prev["generation"] + 1:
        raise ValidationError("refresh generation must increment exactly once")
    prev_digest = digest(prev)
    if cur["supersedes_digest"] != prev_digest:
        raise ValidationError("refresh does not bind exact prior generation")
    prev_evidence = {r["id"]: r for r in prev["evidence"]}
    cur_evidence = {r["id"]: r for r in cur["evidence"]}
    changed = sorted(eid for eid in set(prev_evidence) | set(cur_evidence) if prev_evidence.get(eid) != cur_evidence.get(eid))
    return {
        "schema_version": "commons.decision-refresh-verification/v1",
        "program_id": cur["program_id"],
        "from_generation": prev["generation"],
        "to_generation": cur["generation"],
        "prior_digest": prev_digest,
        "current_digest": digest(cur),
        "changed_evidence_ids": changed,
        "human_re_review_required": True,
    }


def _read_json(path: Path) -> Any:
    def no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in pairs:
            if k in out:
                raise ValidationError(f"duplicate JSON key {k!r}")
            out[k] = v
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_dupes, parse_float=lambda _: (_ for _ in ()).throw(ValidationError("floats forbidden")), parse_constant=lambda _: (_ for _ in ()).throw(ValidationError("non-finite numbers forbidden")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("evaluate")
    ev.add_argument("program", type=Path)
    rf = sub.add_parser("verify-refresh")
    rf.add_argument("previous", type=Path)
    rf.add_argument("current", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "evaluate":
            output = evaluate(_read_json(args.program))
        else:
            output = verify_refresh(_read_json(args.previous), _read_json(args.current))
        sys.stdout.buffer.write(canonical_bytes(output))
        return 0
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
