from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from statistics import median_low
from typing import Any, Mapping

from .common import (
    FAMILIES,
    INPUT_SCHEMA,
    MAX_ARMS,
    MAX_ASSIGNMENT_AGE_SECONDS,
    MAX_OPPORTUNITIES,
    PACKET_SCHEMA,
    READY,
    RECEIPT_SCHEMA,
    STAGES,
    STAGE_INDEX,
    UPSTREAM_READY,
    LabError,
    authority_ceiling,
    canonical_json,
    exact_keys,
    parse_time,
    require_id,
    require_int,
    require_slug,
    sha256,
    validate_json_scalars,
    validate_source,
)


def _compile_upstream(funnel: Any, *, as_of: str) -> dict[str, Any]:
    """Compile through the landed commercial-funnel implementation.

    The import is intentionally local: this package can be inspected in isolation,
    while repository/runtime execution always binds to the real upstream compiler.
    """
    try:
        from revenue.commercial_funnel import FunnelError, compile_funnel
    except ImportError as exc:  # pragma: no cover - repository always carries it
        raise LabError("revenue.commercial_funnel is required") from exc
    try:
        return compile_funnel(funnel, as_of=as_of)
    except FunnelError as exc:
        raise LabError(f"upstream commercial funnel refused input: {exc}") from exc


def _normalize_arm(raw: Any, field: str) -> dict[str, str]:
    arm = exact_keys(
        raw,
        required=("id", "segment", "offer_id", "offer_version", "proof_package", "route_class"),
        field=field,
    )
    return {
        "id": require_id(arm["id"], f"{field}.id"),
        "segment": require_slug(arm["segment"], f"{field}.segment"),
        "offer_id": require_id(arm["offer_id"], f"{field}.offer_id"),
        "offer_version": require_id(arm["offer_version"], f"{field}.offer_version"),
        "proof_package": require_slug(arm["proof_package"], f"{field}.proof_package"),
        "route_class": require_slug(arm["route_class"], f"{field}.route_class"),
    }


def _normalize_plan(raw: Any, *, evaluated: datetime) -> dict[str, Any]:
    plan = exact_keys(
        raw,
        required=(
            "id",
            "revision",
            "family",
            "declared_at",
            "source",
            "opportunity_ids",
            "arms",
            "minimum_sample_per_arm",
            "thresholds",
        ),
        field="plan",
    )
    family = plan["family"]
    if family not in FAMILIES:
        raise LabError("plan.family invalid")
    declared_at = parse_time(plan["declared_at"], "plan.declared_at")
    if declared_at > evaluated:
        raise LabError("plan.declared_at is in the future")
    if int((evaluated - declared_at).total_seconds()) > MAX_ASSIGNMENT_AGE_SECONDS:
        raise LabError("plan.declared_at is outside the current experiment window")

    opp_raw = plan["opportunity_ids"]
    if not isinstance(opp_raw, list) or not opp_raw or len(opp_raw) > MAX_OPPORTUNITIES:
        raise LabError(f"plan.opportunity_ids must contain 1..{MAX_OPPORTUNITIES} ids")
    opportunity_ids: list[str] = []
    seen_opps: set[str] = set()
    for i, value in enumerate(opp_raw):
        opp_id = require_id(value, f"plan.opportunity_ids[{i}]")
        if opp_id in seen_opps:
            raise LabError(f"duplicate plan opportunity id: {opp_id}")
        seen_opps.add(opp_id)
        opportunity_ids.append(opp_id)
    opportunity_ids.sort()

    arms_raw = plan["arms"]
    if not isinstance(arms_raw, list) or len(arms_raw) < 2 or len(arms_raw) > MAX_ARMS:
        raise LabError(f"plan.arms must contain 2..{MAX_ARMS} arms")
    arms: list[dict[str, str]] = []
    seen_arms: set[str] = set()
    for i, raw_arm in enumerate(arms_raw):
        arm = _normalize_arm(raw_arm, f"plan.arms[{i}]")
        if arm["id"] in seen_arms:
            raise LabError(f"duplicate arm id: {arm['id']}")
        seen_arms.add(arm["id"])
        arms.append(arm)
    arms.sort(key=lambda item: item["id"])

    thresholds = exact_keys(
        plan["thresholds"],
        required=("expand_reply_bps", "expand_acceptance_bps", "pause_reply_bps"),
        field="plan.thresholds",
    )
    normalized_thresholds = {
        "expand_reply_bps": require_int(thresholds["expand_reply_bps"], "plan.thresholds.expand_reply_bps", minimum=0, maximum=10_000),
        "expand_acceptance_bps": require_int(thresholds["expand_acceptance_bps"], "plan.thresholds.expand_acceptance_bps", minimum=0, maximum=10_000),
        "pause_reply_bps": require_int(thresholds["pause_reply_bps"], "plan.thresholds.pause_reply_bps", minimum=0, maximum=10_000),
    }
    if normalized_thresholds["pause_reply_bps"] > normalized_thresholds["expand_reply_bps"]:
        raise LabError("pause_reply_bps cannot exceed expand_reply_bps")

    return {
        "id": require_id(plan["id"], "plan.id"),
        "revision": require_id(plan["revision"], "plan.revision"),
        "family": family,
        "declared_at": plan["declared_at"],
        "source": validate_source(plan["source"], "plan.source"),
        "opportunity_ids": opportunity_ids,
        "arms": arms,
        "minimum_sample_per_arm": require_int(plan["minimum_sample_per_arm"], "plan.minimum_sample_per_arm", minimum=1, maximum=MAX_OPPORTUNITIES),
        "thresholds": normalized_thresholds,
    }


def _normalize_assignments(raw: Any, *, plan: Mapping[str, Any], evaluated: datetime) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw or len(raw) > MAX_OPPORTUNITIES:
        raise LabError(f"assignments must contain 1..{MAX_OPPORTUNITIES} rows")
    target_ids = set(plan["opportunity_ids"])
    arm_ids = {arm["id"] for arm in plan["arms"]}
    declared = parse_time(plan["declared_at"], "plan.declared_at")
    assignments: list[dict[str, Any]] = []
    seen_assignment_ids: set[str] = set()
    seen_opps: set[str] = set()
    for i, raw_assignment in enumerate(raw):
        field = f"assignments[{i}]"
        assignment = exact_keys(
            raw_assignment,
            required=("id", "opportunity_id", "arm_id", "assigned_at", "evidence"),
            field=field,
        )
        assignment_id = require_id(assignment["id"], f"{field}.id")
        opportunity_id = require_id(assignment["opportunity_id"], f"{field}.opportunity_id")
        arm_id = require_id(assignment["arm_id"], f"{field}.arm_id")
        if assignment_id in seen_assignment_ids:
            raise LabError(f"duplicate assignment id: {assignment_id}")
        if opportunity_id in seen_opps:
            raise LabError(f"opportunity assigned more than once: {opportunity_id}")
        if opportunity_id not in target_ids:
            raise LabError(f"assignment references opportunity outside frozen cohort: {opportunity_id}")
        if arm_id not in arm_ids:
            raise LabError(f"assignment references unknown arm: {arm_id}")
        assigned = parse_time(assignment["assigned_at"], f"{field}.assigned_at")
        if assigned < declared:
            raise LabError(f"assignment predates experiment declaration: {opportunity_id}")
        if assigned > evaluated:
            raise LabError(f"assignment is in the future: {opportunity_id}")
        if int((evaluated - assigned).total_seconds()) > MAX_ASSIGNMENT_AGE_SECONDS:
            raise LabError(f"assignment is outside current experiment window: {opportunity_id}")
        seen_assignment_ids.add(assignment_id)
        seen_opps.add(opportunity_id)
        assignments.append(
            {
                "id": assignment_id,
                "opportunity_id": opportunity_id,
                "arm_id": arm_id,
                "assigned_at": assignment["assigned_at"],
                "evidence": validate_source(assignment["evidence"], f"{field}.evidence"),
            }
        )
    missing = target_ids - seen_opps
    if missing:
        raise LabError(f"frozen cohort missing assignments: {sorted(missing)}")
    assignments.sort(key=lambda item: (item["opportunity_id"], item["id"]))
    return assignments


def _validate_bindings(
    *,
    plan: Mapping[str, Any],
    assignments: list[dict[str, Any]],
    upstream_opportunities: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    opportunity_map: dict[str, dict[str, Any]] = {}
    for opp in upstream_opportunities:
        if not isinstance(opp, dict) or not isinstance(opp.get("id"), str):
            raise LabError("upstream funnel opportunity shape invalid")
        if opp["id"] in opportunity_map:
            raise LabError(f"upstream funnel duplicate opportunity: {opp['id']}")
        opportunity_map[opp["id"]] = opp
    missing = set(plan["opportunity_ids"]) - set(opportunity_map)
    if missing:
        raise LabError(f"frozen experiment opportunity missing from upstream funnel: {sorted(missing)}")

    arm_map = {arm["id"]: arm for arm in plan["arms"]}
    assignment_map = {assignment["opportunity_id"]: assignment for assignment in assignments}
    for opportunity_id in plan["opportunity_ids"]:
        opp = opportunity_map[opportunity_id]
        assignment = assignment_map[opportunity_id]
        arm = arm_map[assignment["arm_id"]]
        if opp.get("family") != plan["family"]:
            raise LabError(f"opportunity family does not match frozen experiment family: {opportunity_id}")
        offer = opp.get("offer")
        if not isinstance(offer, dict) or offer.get("id") != arm["offer_id"] or offer.get("version") != arm["offer_version"]:
            raise LabError(f"arm offer identity does not match upstream funnel: {opportunity_id}")
        events = opp.get("events")
        if not isinstance(events, list):
            raise LabError(f"upstream events invalid: {opportunity_id}")
        if events:
            earliest = min(parse_time(event.get("observed_at"), f"upstream.{opportunity_id}.event.observed_at") for event in events)
            assigned = parse_time(assignment["assigned_at"], f"assignment.{opportunity_id}.assigned_at")
            if assigned >= earliest:
                raise LabError(f"post-outcome assignment refused: {opportunity_id}")
    return opportunity_map, assignment_map


def _basis_points(numerator: int, denominator: int) -> int | None:
    if denominator == 0:
        return None
    return (numerator * 10_000) // denominator


def _add_money(target: dict[str, int], values: Any, field: str) -> None:
    if not isinstance(values, dict):
        raise LabError(f"{field} invalid")
    for currency, amount in values.items():
        if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha() or currency != currency.upper():
            raise LabError(f"{field} currency invalid")
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise LabError(f"{field} amount invalid")
        target[currency] += amount


def _arm_metrics(arm: Mapping[str, Any], assigned: list[dict[str, Any]], opportunities: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    ready: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    for assignment in assigned:
        opp = opportunities[assignment["opportunity_id"]]
        (ready if opp.get("state") == UPSTREAM_READY else held).append(opp)

    stage_counts = {stage: 0 for stage in STAGES}
    time_to_stage: dict[str, list[int]] = {"REPLY": [], "ACCEPTANCE": [], "CASH": []}
    gross: dict[str, int] = defaultdict(int)
    reversals: dict[str, int] = defaultdict(int)
    net: dict[str, int] = defaultdict(int)
    for opp in ready:
        strongest = opp.get("strongest_evidenced_stage")
        if strongest is not None:
            if strongest not in STAGE_INDEX:
                raise LabError(f"upstream strongest stage invalid: {opp.get('id')}")
            for stage in STAGES[: STAGE_INDEX[strongest] + 1]:
                stage_counts[stage] += 1
        stage_times = opp.get("stage_times")
        if not isinstance(stage_times, dict):
            raise LabError(f"upstream stage_times invalid: {opp.get('id')}")
        if "TRAFFIC" in stage_times:
            start = parse_time(stage_times["TRAFFIC"], f"upstream.{opp.get('id')}.stage_times.TRAFFIC")
            for stage in time_to_stage:
                if stage in stage_times:
                    finish = parse_time(stage_times[stage], f"upstream.{opp.get('id')}.stage_times.{stage}")
                    seconds = int((finish - start).total_seconds())
                    if seconds < 0:
                        raise LabError(f"upstream negative time-to-stage: {opp.get('id')}")
                    time_to_stage[stage].append(seconds)
        _add_money(gross, opp.get("gross_cash_by_currency", {}), f"upstream.{opp.get('id')}.gross_cash_by_currency")
        _add_money(reversals, opp.get("cash_reversals_by_currency", {}), f"upstream.{opp.get('id')}.cash_reversals_by_currency")
        _add_money(net, opp.get("net_cash_by_currency", {}), f"upstream.{opp.get('id')}.net_cash_by_currency")

    eligible_count = len(ready)
    reach_bps = {stage: _basis_points(stage_counts[stage], eligible_count) for stage in STAGES}
    transition_bps: dict[str, int | None] = {}
    for i, stage in enumerate(STAGES[:-1]):
        next_stage = STAGES[i + 1]
        transition_bps[f"{stage}_TO_{next_stage}"] = _basis_points(stage_counts[next_stage], stage_counts[stage])
    medians = {stage: (median_low(values) if values else None) for stage, values in time_to_stage.items()}

    return {
        "arm": dict(arm),
        "assigned_count": len(assigned),
        "eligible_count": eligible_count,
        "held_count": len(held),
        "held_opportunity_ids": sorted(str(opp.get("id")) for opp in held),
        "stage_counts": stage_counts,
        "stage_reach_bps": reach_bps,
        "transition_bps": transition_bps,
        "median_seconds_from_traffic": medians,
        "gross_cash_by_currency": dict(sorted(gross.items())),
        "cash_reversals_by_currency": dict(sorted(reversals.items())),
        "net_cash_by_currency": dict(sorted(net.items())),
    }


def _recommend(metrics: Mapping[str, Any], *, minimum_sample: int, thresholds: Mapping[str, int]) -> dict[str, Any]:
    reasons: list[str] = []
    if metrics["held_count"]:
        reasons.append("UPSTREAM_HOLD_PRESENT")
    if metrics["eligible_count"] < minimum_sample:
        reasons.append("MINIMUM_SAMPLE_NOT_MET")
    if reasons:
        return {"state": "INSUFFICIENT_EVIDENCE", "reasons": sorted(reasons)}

    reply_bps = metrics["stage_reach_bps"]["REPLY"]
    acceptance_bps = metrics["stage_reach_bps"]["ACCEPTANCE"]
    if reply_bps is None or acceptance_bps is None:
        return {"state": "INSUFFICIENT_EVIDENCE", "reasons": ["MISSING_RATE_DENOMINATOR"]}
    if reply_bps < thresholds["pause_reply_bps"]:
        return {
            "state": "PAUSE_REVIEW",
            "reasons": [f"REPLY_REACH_BELOW_PAUSE_THRESHOLD:{reply_bps}<{thresholds['pause_reply_bps']}"],
        }
    if reply_bps >= thresholds["expand_reply_bps"] and acceptance_bps >= thresholds["expand_acceptance_bps"]:
        return {
            "state": "EXPAND_CANDIDATE",
            "reasons": [
                f"REPLY_REACH_AT_OR_ABOVE_EXPAND_THRESHOLD:{reply_bps}>={thresholds['expand_reply_bps']}",
                f"ACCEPTANCE_REACH_AT_OR_ABOVE_EXPAND_THRESHOLD:{acceptance_bps}>={thresholds['expand_acceptance_bps']}",
            ],
        }
    return {"state": "KEEP_TESTING", "reasons": ["PREDECLARED_EXPAND_AND_PAUSE_RULES_NOT_TRIGGERED"]}


def _money_delta(left: Mapping[str, int], right: Mapping[str, int]) -> dict[str, int]:
    return {currency: left.get(currency, 0) - right.get(currency, 0) for currency in sorted(set(left) | set(right))}


def _comparisons(arms: list[dict[str, Any]], minimum_sample: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for left, right in combinations(arms, 2):
        left_rates = left["stage_reach_bps"]
        right_rates = right["stage_reach_bps"]
        rate_delta: dict[str, int | None] = {}
        for stage in ("REPLY", "ACCEPTANCE", "CASH"):
            lval, rval = left_rates[stage], right_rates[stage]
            rate_delta[stage] = None if lval is None or rval is None else lval - rval
        sufficient = (
            left["eligible_count"] >= minimum_sample
            and right["eligible_count"] >= minimum_sample
            and left["held_count"] == 0
            and right["held_count"] == 0
        )
        out.append(
            {
                "left_arm_id": left["arm"]["id"],
                "right_arm_id": right["arm"]["id"],
                "comparison_state": "DESCRIPTIVE_SAMPLE_READY" if sufficient else "DESCRIPTIVE_SAMPLE_INCOMPLETE",
                "stage_reach_bps_delta_left_minus_right": rate_delta,
                "net_cash_delta_left_minus_right_by_currency": _money_delta(left["net_cash_by_currency"], right["net_cash_by_currency"]),
                "interpretation": "OBSERVATIONAL_NOT_CAUSAL",
            }
        )
    return out


def _csv_bytes(arms: list[dict[str, Any]]) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(
        [
            "arm_id",
            "segment",
            "offer_id",
            "offer_version",
            "proof_package",
            "route_class",
            "assigned_count",
            "eligible_count",
            "held_count",
            "reply_reach_bps",
            "acceptance_reach_bps",
            "cash_reach_bps",
            "recommendation",
            "recommendation_reasons",
        ]
    )
    for item in arms:
        arm = item["arm"]
        writer.writerow(
            [
                arm["id"],
                arm["segment"],
                arm["offer_id"],
                arm["offer_version"],
                arm["proof_package"],
                arm["route_class"],
                item["assigned_count"],
                item["eligible_count"],
                item["held_count"],
                "" if item["stage_reach_bps"]["REPLY"] is None else item["stage_reach_bps"]["REPLY"],
                "" if item["stage_reach_bps"]["ACCEPTANCE"] is None else item["stage_reach_bps"]["ACCEPTANCE"],
                "" if item["stage_reach_bps"]["CASH"] is None else item["stage_reach_bps"]["CASH"],
                item["recommendation"]["state"],
                "|".join(item["recommendation"]["reasons"]),
            ]
        )
    return out.getvalue().encode("utf-8")


def _markdown_bytes(packet: Mapping[str, Any]) -> bytes:
    lines = [
        "# Commercial experiment evidence packet",
        "",
        f"- State: **{packet['state']}**",
        f"- Evaluated at: `{packet['evaluated_at']}`",
        f"- Experiment: `{packet['experiment']['id']}` revision `{packet['experiment']['revision']}`",
        f"- Family: `{packet['experiment']['family']}`",
        f"- Upstream funnel state: `{packet['upstream_funnel']['state']}`",
        "",
        "## Arm outcomes",
        "",
        "| Arm | Segment | Offer | Route | Eligible / Assigned | Reply bps | Acceptance bps | Cash bps | Recommendation |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in packet["arms"]:
        arm = item["arm"]
        rates = item["stage_reach_bps"]
        def show(value: int | None) -> str:
            return "NA" if value is None else str(value)
        lines.append(
            f"| {arm['id']} | {arm['segment']} | {arm['offer_id']}@{arm['offer_version']} | {arm['route_class']} | "
            f"{item['eligible_count']} / {item['assigned_count']} | {show(rates['REPLY'])} | {show(rates['ACCEPTANCE'])} | "
            f"{show(rates['CASH'])} | {item['recommendation']['state']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "Arm comparisons are descriptive observations over a predeclared cohort. They are not causal proof.",
            "This packet does not authorize buyer contact, send/resend, proposal submission, contracting, pricing",
            "commitments, provider/payment actions, fulfillment, cash-availability claims, accounting/tax treatment,",
            "or revenue recognition. Existing DNR, suppression, consent and collision controls remain authoritative.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def compile_experiment(value: Any, *, as_of: str) -> dict[str, Any]:
    validate_json_scalars(value)
    root = exact_keys(value, required=("schema", "plan", "assignments", "funnel"), field="$")
    if root["schema"] != INPUT_SCHEMA:
        raise LabError("unsupported input schema")
    evaluated = parse_time(as_of, "as_of")
    plan = _normalize_plan(root["plan"], evaluated=evaluated)
    assignments = _normalize_assignments(root["assignments"], plan=plan, evaluated=evaluated)
    upstream = _compile_upstream(root["funnel"], as_of=as_of)
    if not isinstance(upstream, dict) or not isinstance(upstream.get("packet"), dict) or not isinstance(upstream.get("receipt"), dict):
        raise LabError("upstream commercial funnel compiler returned invalid shape")
    upstream_packet = upstream["packet"]
    upstream_receipt = upstream["receipt"]
    upstream_opportunities = upstream_packet.get("opportunities")
    if not isinstance(upstream_opportunities, list):
        raise LabError("upstream funnel packet missing opportunities")
    opportunity_map, assignment_map = _validate_bindings(
        plan=plan,
        assignments=assignments,
        upstream_opportunities=upstream_opportunities,
    )

    assignments_by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for assignment in assignments:
        assignments_by_arm[assignment["arm_id"]].append(assignment)
    arm_results: list[dict[str, Any]] = []
    for arm in plan["arms"]:
        metrics = _arm_metrics(arm, assignments_by_arm.get(arm["id"], []), opportunity_map)
        metrics["recommendation"] = _recommend(
            metrics,
            minimum_sample=plan["minimum_sample_per_arm"],
            thresholds=plan["thresholds"],
        )
        arm_results.append(metrics)
    arm_results.sort(key=lambda item: item["arm"]["id"])

    exclusions = []
    for opp_id in plan["opportunity_ids"]:
        opp = opportunity_map[opp_id]
        if opp.get("state") != UPSTREAM_READY:
            exclusions.append(
                {
                    "opportunity_id": opp_id,
                    "arm_id": assignment_map[opp_id]["arm_id"],
                    "reason": "UPSTREAM_FUNNEL_HOLD",
                    "upstream_hold_reasons": sorted(opp.get("hold_reasons", [])),
                }
            )

    upstream_input_digest = upstream_receipt.get("input_sha256")
    upstream_packet_digest = upstream_receipt.get("packet_sha256")
    if not isinstance(upstream_input_digest, str) or not isinstance(upstream_packet_digest, str):
        raise LabError("upstream receipt missing digests")
    semantic_identity = {
        "schema": INPUT_SCHEMA,
        "plan": plan,
        "assignments": assignments,
        "upstream_funnel_input_sha256": upstream_input_digest,
    }
    input_digest = sha256(canonical_json(semantic_identity))
    authority = authority_ceiling()
    packet_base = {
        "schema": PACKET_SCHEMA,
        "state": READY,
        "evaluated_at": as_of,
        "input_sha256": input_digest,
        "experiment": plan,
        "assignments": assignments,
        "upstream_funnel": {
            "state": upstream_packet.get("state"),
            "input_sha256": upstream_input_digest,
            "packet_sha256": upstream_packet_digest,
            "source_authenticity_asserted_by_lab": False,
        },
        "arms": arm_results,
        "comparisons": _comparisons(arm_results, plan["minimum_sample_per_arm"]),
        "excluded_opportunities": exclusions,
        "authority": authority,
    }
    report_json = canonical_json(packet_base)
    report_csv = _csv_bytes(arm_results)
    report_markdown = _markdown_bytes(packet_base)
    outputs = {
        "report_json_sha256": sha256(report_json),
        "report_csv_sha256": sha256(report_csv),
        "report_markdown_sha256": sha256(report_markdown),
    }
    packet = dict(packet_base)
    packet["outputs"] = outputs
    packet_sha = sha256(canonical_json(packet))
    receipt_base = {
        "schema": RECEIPT_SCHEMA,
        "state": READY,
        "evaluated_at": as_of,
        "input_sha256": input_digest,
        "upstream_funnel_input_sha256": upstream_input_digest,
        "upstream_funnel_packet_sha256": upstream_packet_digest,
        "packet_sha256": packet_sha,
        "outputs": outputs,
        "authority": authority,
    }
    receipt = dict(receipt_base)
    receipt["receipt_sha256"] = sha256(canonical_json(receipt_base))
    return {
        "packet": packet,
        "receipt": receipt,
        "json": report_json,
        "csv": report_csv,
        "markdown": report_markdown,
    }


def verify_compilation(value: Any, *, as_of: str, packet: Any, receipt: Any) -> bool:
    try:
        expected = compile_experiment(value, as_of=as_of)
        if not isinstance(packet, dict) or not isinstance(receipt, dict):
            return False
        if canonical_json(packet) != canonical_json(expected["packet"]):
            return False
        if canonical_json(receipt) != canonical_json(expected["receipt"]):
            return False
        without_digest = {key: val for key, val in receipt.items() if key != "receipt_sha256"}
        return receipt.get("receipt_sha256") == sha256(canonical_json(without_digest))
    except (LabError, TypeError, ValueError, OverflowError):
        return False


def verify_artifacts(
    value: Any,
    *,
    as_of: str,
    packet: Any,
    receipt: Any,
    report_json: bytes,
    report_csv: bytes,
    report_markdown: bytes,
) -> bool:
    try:
        expected = compile_experiment(value, as_of=as_of)
        return (
            verify_compilation(value, as_of=as_of, packet=packet, receipt=receipt)
            and report_json == expected["json"]
            and report_csv == expected["csv"]
            and report_markdown == expected["markdown"]
            and receipt.get("outputs", {}).get("report_json_sha256") == sha256(report_json)
            and receipt.get("outputs", {}).get("report_csv_sha256") == sha256(report_csv)
            and receipt.get("outputs", {}).get("report_markdown_sha256") == sha256(report_markdown)
        )
    except (LabError, TypeError, ValueError, OverflowError):
        return False
