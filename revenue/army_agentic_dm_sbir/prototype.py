from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

EVALUATOR_VERSION = "army-agentic-dm-prototype/v1"
ACTIVE = "ACTIVE"
REVOKED = "REVOKED"


class DecisionHold(ValueError):
    """Raised internally for a fail-closed decision-program hold."""


def _dt(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DecisionHold("timestamps_must_be_utc_z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DecisionHold("invalid_timestamp") from exc


def canonical_json(value: Any) -> str:
    """Canonical JSON for the supported decision schema.

    Floats are rejected because cross-runtime float formatting is not an
    authority boundary. The prototype uses integer basis points instead.
    """
    def walk(node: Any) -> None:
        if node is None or isinstance(node, (str, bool, int)):
            return
        if isinstance(node, float):
            raise DecisionHold("floats_forbidden_use_integer_basis_points")
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if isinstance(node, dict):
            if not all(isinstance(k, str) for k in node):
                raise DecisionHold("object_keys_must_be_strings")
            for item in node.values():
                walk(item)
            return
        raise DecisionHold(f"unsupported_json_type:{type(node).__name__}")

    walk(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Evaluation:
    status: str
    input_sha256: str
    receipt_sha256: str
    result: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "input_sha256": self.input_sha256,
            "receipt_sha256": self.receipt_sha256,
            "result": self.result,
        }


def _hold(program: dict[str, Any], reasons: list[str]) -> Evaluation:
    input_sha = digest(program)
    result = {
        "evaluator_version": EVALUATOR_VERSION,
        "reasons": sorted(set(reasons)),
    }
    envelope = {"status": "HOLD", "input_sha256": input_sha, "result": result}
    return Evaluation("HOLD", input_sha, digest(envelope), result)


def evaluate(program: dict[str, Any]) -> Evaluation:
    """Evaluate one immutable DecisionEpisode generation.

    The agent may propose `program`, but this function alone determines whether
    it is decision-ready. It never mutates the caller's object.
    """
    if not isinstance(program, dict):
        raise DecisionHold("program_must_be_object")

    input_sha = digest(program)
    reasons: list[str] = []

    as_of_raw = program.get("as_of")
    try:
        as_of = _dt(as_of_raw)
    except DecisionHold as exc:
        return _hold(program, [str(exc)])

    if not isinstance(program.get("episode_id"), str) or not program["episode_id"]:
        reasons.append("missing_episode_id")
    generation = program.get("generation")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        reasons.append("invalid_generation")

    objectives = program.get("objectives")
    if not isinstance(objectives, list) or not objectives or not all(isinstance(x, str) and x for x in objectives):
        reasons.append("objectives_required")

    assumptions = program.get("assumptions")
    if not isinstance(assumptions, list) or not assumptions:
        reasons.append("assumptions_required")
    else:
        for item in assumptions:
            if not isinstance(item, dict) or item.get("status") != "ACCEPTED":
                reasons.append("assumption_not_accepted")

    risks = program.get("risks")
    if not isinstance(risks, list) or not risks:
        reasons.append("risks_required")
    else:
        for item in risks:
            if not isinstance(item, dict) or item.get("disposition") not in {"ACCEPT", "MITIGATE", "AVOID", "TRANSFER"}:
                reasons.append("risk_disposition_required")

    bias_checks = program.get("bias_checks")
    if not isinstance(bias_checks, list) or not bias_checks:
        reasons.append("bias_checks_required")
    else:
        for item in bias_checks:
            if not isinstance(item, dict) or item.get("status") != "PASS":
                reasons.append("bias_check_not_passed")

    evidence = program.get("evidence")
    evidence_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(evidence, list) or not evidence:
        reasons.append("evidence_required")
    else:
        for item in evidence:
            if not isinstance(item, dict):
                reasons.append("invalid_evidence_record")
                continue
            eid = item.get("id")
            if not isinstance(eid, str) or not eid:
                reasons.append("evidence_id_required")
                continue
            if eid in evidence_by_id:
                reasons.append(f"duplicate_evidence:{eid}")
                continue
            evidence_by_id[eid] = item
            if item.get("status") != ACTIVE:
                reasons.append(f"evidence_not_active:{eid}")
            try:
                observed = _dt(item.get("observed_at"))
                valid_until = _dt(item.get("valid_until"))
                if observed > as_of:
                    reasons.append(f"evidence_from_future:{eid}")
                if valid_until < as_of:
                    reasons.append(f"evidence_stale:{eid}")
            except DecisionHold:
                reasons.append(f"evidence_timestamp_invalid:{eid}")
            payload = item.get("payload")
            claimed = item.get("payload_sha256")
            try:
                actual = digest(payload)
            except DecisionHold:
                reasons.append(f"evidence_payload_invalid:{eid}")
            else:
                if claimed != actual:
                    reasons.append(f"evidence_digest_mismatch:{eid}")
            if not isinstance(item.get("source"), str) or not item["source"]:
                reasons.append(f"evidence_source_required:{eid}")

    criteria = program.get("criteria")
    criteria_by_id: dict[str, dict[str, Any]] = {}
    weight_sum = 0
    if not isinstance(criteria, list) or not criteria:
        reasons.append("criteria_required")
    else:
        for criterion in criteria:
            if not isinstance(criterion, dict):
                reasons.append("invalid_criterion")
                continue
            cid = criterion.get("id")
            if not isinstance(cid, str) or not cid:
                reasons.append("criterion_id_required")
                continue
            if cid in criteria_by_id:
                reasons.append(f"duplicate_criterion:{cid}")
                continue
            criteria_by_id[cid] = criterion
            weight = criterion.get("weight_bps")
            if not isinstance(weight, int) or isinstance(weight, bool) or not 1 <= weight <= 10000:
                reasons.append(f"invalid_weight:{cid}")
            else:
                weight_sum += weight
            refs = criterion.get("evidence_ids")
            if not isinstance(refs, list) or not refs:
                reasons.append(f"criterion_evidence_required:{cid}")
            else:
                for eid in refs:
                    if eid not in evidence_by_id:
                        reasons.append(f"criterion_missing_evidence:{cid}:{eid}")
        if weight_sum != 10000:
            reasons.append(f"weights_must_sum_10000:{weight_sum}")

    options = program.get("options")
    option_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(options, list) or len(options) < 2:
        reasons.append("at_least_two_options_required")
    else:
        for option in options:
            if not isinstance(option, dict):
                reasons.append("invalid_option")
                continue
            oid = option.get("id")
            if not isinstance(oid, str) or not oid:
                reasons.append("option_id_required")
                continue
            if oid in option_by_id:
                reasons.append(f"duplicate_option:{oid}")
                continue
            option_by_id[oid] = option
            scores = option.get("criterion_scores")
            if not isinstance(scores, dict):
                reasons.append(f"option_scores_required:{oid}")
                continue
            for cid in criteria_by_id:
                score = scores.get(cid)
                if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 10000:
                    reasons.append(f"invalid_or_missing_score:{oid}:{cid}")
            extra = set(scores) - set(criteria_by_id)
            for cid in sorted(extra):
                reasons.append(f"unknown_score_criterion:{oid}:{cid}")

    if reasons:
        return _hold(program, reasons)

    totals: dict[str, int] = {}
    contributions: dict[str, dict[str, int]] = {}
    for oid, option in option_by_id.items():
        contributions[oid] = {}
        total = 0
        for cid, criterion in criteria_by_id.items():
            contribution = option["criterion_scores"][cid] * criterion["weight_bps"]
            contributions[oid][cid] = contribution
            total += contribution
        totals[oid] = total

    ranking = sorted(totals, key=lambda oid: (-totals[oid], oid))
    winner = ranking[0]
    runner_up = ranking[1]
    margin = totals[winner] - totals[runner_up]

    what_flips: list[dict[str, Any]] = []
    if margin == 0:
        what_flips.append({"kind": "tie_break", "threshold_weighted_units": 1})
    else:
        for cid, criterion in criteria_by_id.items():
            weight = criterion["weight_bps"]
            score_delta = (margin + weight) // weight
            w_score = option_by_id[winner]["criterion_scores"][cid]
            r_score = option_by_id[runner_up]["criterion_scores"][cid]
            if w_score - score_delta >= 0:
                what_flips.append({
                    "kind": "winner_score_decrease",
                    "criterion_id": cid,
                    "option_id": winner,
                    "score_delta_bps": score_delta,
                    "from": w_score,
                    "to_at_most": w_score - score_delta,
                })
            if r_score + score_delta <= 10000:
                what_flips.append({
                    "kind": "runner_up_score_increase",
                    "criterion_id": cid,
                    "option_id": runner_up,
                    "score_delta_bps": score_delta,
                    "from": r_score,
                    "to_at_least": r_score + score_delta,
                })

    result = {
        "evaluator_version": EVALUATOR_VERSION,
        "episode_id": program["episode_id"],
        "generation": program["generation"],
        "as_of": as_of.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ranking": [{"option_id": oid, "weighted_total": totals[oid]} for oid in ranking],
        "winner": winner,
        "runner_up": runner_up,
        "margin_weighted_units": margin,
        "what_flips": what_flips,
        "evidence_generation_sha256": digest([
            {
                "id": eid,
                "payload_sha256": evidence_by_id[eid]["payload_sha256"],
                "status": evidence_by_id[eid]["status"],
                "observed_at": evidence_by_id[eid]["observed_at"],
                "valid_until": evidence_by_id[eid]["valid_until"],
            }
            for eid in sorted(evidence_by_id)
        ]),
    }
    envelope = {"status": "DECISION_READY", "input_sha256": input_sha, "result": result}
    return Evaluation("DECISION_READY", input_sha, digest(envelope), result)
