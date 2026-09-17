"""Decision, receipt, verification and CLI for the post-delivery gate."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime as _stdlib_datetime, timezone as _stdlib_timezone
from pathlib import Path
from typing import Any

from .common import (
    RECEIPT_SCHEMA, READY, HOLD_ACCEPTANCE, HOLD_PAYMENT, HOLD_WINDOW, HOLD_EVIDENCE, DNR, STATES, GateError, _ts, _dt, digest, authority_flags, canonical_json, load_json
)
from .model import _normalize


def _commercial_generation(normalized: dict[str, Any]) -> int:
    approved = [x["generation"] for x in normalized["change_orders"] if x["status"] == "APPROVED"]
    return max([normalized["baseline"]["generation"], *approved])


def _expected_total(normalized: dict[str, Any], *, _error=GateError) -> int:
    total = normalized["baseline"]["accepted_total_cents"]
    for row in normalized["change_orders"]:
        if row["status"] == "APPROVED":
            total += row["delta_cents"]
    if total < 0:
        raise _error("commercial lineage: approved total cannot be negative")
    return total


def _decision(
    normalized: dict[str, Any],
    now: str,
    *,
    _commercial_generation_fn=_commercial_generation,
    _expected_total_fn=_expected_total,
    _dt_fn=_dt,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    route = normalized["route_control"]
    if route["state"] == "DNR":
        return DNR, ["ROUTE_DNR"]

    baseline = normalized["baseline"]
    if baseline["status"] != "ACCEPTED":
        return HOLD_ACCEPTANCE, ["BASELINE_NOT_ACCEPTED"]

    pending_changes = [x["change_order_id"] for x in normalized["change_orders"] if x["status"] == "PENDING"]
    if pending_changes:
        return HOLD_EVIDENCE, [f"PENDING_CHANGE_ORDER:{x}" for x in pending_changes]

    commercial_generation = _commercial_generation_fn(normalized)
    bad_milestones = []
    for row in normalized["milestones"]:
        if row["commercial_generation"] != commercial_generation:
            bad_milestones.append(f"MILESTONE_GENERATION_MISMATCH:{row['milestone_id']}")
        elif row["status"] != "BUYER_HUMAN_ACCEPTED" or row["accepted_at"] is None:
            bad_milestones.append(f"MILESTONE_NOT_BUYER_HUMAN_ACCEPTED:{row['milestone_id']}")
    if bad_milestones:
        return HOLD_ACCEPTANCE, bad_milestones

    expected = _expected_total_fn(normalized)
    payment = normalized["payment"]
    payment_bad = (
        payment["commercial_generation"] != commercial_generation
        or payment["state"] != "SETTLED"
        or payment["evidence_class"] not in {"PROVIDER_SETTLEMENT", "BANK_SETTLEMENT"}
        or payment["disputed"]
        or payment["refunded_cents"] != 0
        or payment["settled_cents"] < expected
    )
    if payment_bad:
        return HOLD_PAYMENT, ["PAYMENT_NOT_FINAL_EXACT_COMMERCIAL_LINEAGE"]

    now_dt = _dt_fn(now)
    window = normalized["renewal_window"]
    if now_dt < _dt_fn(window["opens_at"]):
        return HOLD_WINDOW, ["RENEWAL_WINDOW_NOT_OPEN"]
    if now_dt > _dt_fn(window["closes_at"]):
        return HOLD_WINDOW, ["RENEWAL_WINDOW_CLOSED"]

    evidence_reasons = []
    for row in normalized["support_findings"]:
        if row["status"] == "OPEN" and row["severity"] in {"HIGH", "BLOCKING"}:
            evidence_reasons.append(f"OPEN_SUPPORT_FINDING:{row['finding_id']}")
    for row in normalized["security_data_gaps"]:
        if row["blocking"] and row["status"] == "OPEN":
            evidence_reasons.append(f"OPEN_BLOCKING_SECURITY_DATA_GAP:{row['gap_id']}")
    for row in normalized["expansion_hypotheses"]:
        if row["commercial_state"] != "PROPOSED_NOT_ACCEPTED":
            evidence_reasons.append(f"HYPOTHESIS_STATE_NOT_PROPOSED_NOT_ACCEPTED:{row['hypothesis_id']}")
        if any(row[key] for key in (
            "buyer_interest_claimed", "roi_claimed", "savings_claimed", "usage_claimed",
            "urgency_claimed", "expansion_approved_claimed"
        )):
            evidence_reasons.append(f"HYPOTHESIS_UNSUPPORTED_CLAIM:{row['hypothesis_id']}")
    if evidence_reasons:
        return HOLD_EVIDENCE, sorted(evidence_reasons)

    return READY, []


def _compile(
    packet: dict[str, Any],
    now: str,
    *,
    _ts_fn=_ts,
    _normalize_fn=_normalize,
    _decision_fn=_decision,
    _commercial_generation_fn=_commercial_generation,
    _expected_total_fn=_expected_total,
    _digest_fn=digest,
    _authority_flags_fn=authority_flags,
    _receipt_schema=RECEIPT_SCHEMA,
) -> dict[str, Any]:
    now = _ts_fn(now, "trusted_now")
    normalized = _normalize_fn(packet, now)
    state, reasons = _decision_fn(normalized, now)
    commercial_generation = _commercial_generation_fn(normalized)
    result = {
        "schema": _receipt_schema,
        "case_id": normalized["case_id"],
        "evaluated_at": now,
        "state": state,
        "reasons": reasons,
        "commercial_generation": commercial_generation,
        "effective_total_cents": _expected_total_fn(normalized),
        "currency": normalized["baseline"]["currency"],
        "input_digest": _digest_fn(normalized),
        "commercial_lineage_digest": _digest_fn({
            "baseline": normalized["baseline"],
            "change_orders": normalized["change_orders"],
        }),
        "baseline_id": normalized["baseline"]["baseline_id"],
        "accepted_milestone_ids": [
            x["milestone_id"] for x in normalized["milestones"]
            if x["status"] == "BUYER_HUMAN_ACCEPTED"
        ],
        "proposed_expansion_hypothesis_ids": [x["hypothesis_id"] for x in normalized["expansion_hypotheses"]],
        "route": {
            "route_id": normalized["route_control"]["route_id"],
            "collision_key": normalized["route_control"]["collision_key"],
            "muse_key": normalized["route_control"]["muse_key"],
            "state": normalized["route_control"]["state"],
        },
        "truth": {
            "expansion_hypotheses_remain": "PROPOSED_NOT_ACCEPTED",
            "buyer_signal_required_for_this_state": False,
            "ready_means": "OWNER_REVIEW_ONLY",
        },
        "authority": _authority_flags_fn(),
    }
    result["receipt_digest"] = _digest_fn(result)
    return result


def _semantic_projection(receipt: dict[str, Any]) -> dict[str, Any]:
    projected = dict(receipt)
    projected.pop("evaluated_at", None)
    projected.pop("receipt_digest", None)
    return projected


def _build_current_api(
    *,
    _datetime_cls=_stdlib_datetime,
    _timezone_obj=_stdlib_timezone,
    _compiler=_compile,
    _canonical=canonical_json,
    _digest_fn=digest,
    _projection=_semantic_projection,
    _dt_fn=_dt,
    _receipt_schema=RECEIPT_SCHEMA,
    _states=frozenset(STATES),
    _gate_error=GateError,
    _hold_evidence=HOLD_EVIDENCE,
):
    """Build current APIs around an import-generation-owned stdlib UTC clock.

    Ordinary reassignment/insertion of module globals cannot replace the clock or
    compiler captured by these closures. Direct closure/function surgery remains
    outside this cooperative in-process boundary.
    """

    def _clock_text() -> str:
        return _datetime_cls.now(_timezone_obj.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def compile_current(packet: dict[str, Any]) -> dict[str, Any]:
        return _compiler(packet, _clock_text())

    def verify_receipt(packet: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
        """Authenticate exact historical semantics, then re-evaluate at current UTC."""
        if not isinstance(receipt, dict):
            raise _gate_error("receipt: object required")
        supplied = dict(receipt)
        claimed = supplied.get("receipt_digest")
        unsigned = dict(supplied)
        unsigned.pop("receipt_digest", None)
        if not isinstance(claimed, str) or claimed != _digest_fn(unsigned):
            raise _gate_error("receipt: digest mismatch")
        if supplied.get("schema") != _receipt_schema or supplied.get("state") not in _states:
            raise _gate_error("receipt: unsupported schema/state")
        evaluated_at = supplied.get("evaluated_at")
        if not isinstance(evaluated_at, str):
            raise _gate_error("receipt: evaluated_at required")

        try:
            historical = _compiler(packet, evaluated_at)
        except _gate_error as exc:
            raise _gate_error(f"receipt: historical recompile failed: {exc}") from exc
        if _canonical(historical) != _canonical(receipt):
            raise _gate_error("receipt: semantic mismatch")

        current_now = _clock_text()
        if _dt_fn(evaluated_at) > _dt_fn(current_now):
            raise _gate_error("receipt: evaluated_at is in the future")
        try:
            current = _compiler(packet, current_now)
        except _gate_error as exc:
            return {
                "integrity_valid": True,
                "prior_state": historical["state"],
                "current_state": _hold_evidence,
                "current_reasons": [f"CURRENT_REEVALUATION_FAILED:{exc}"],
                "current_receipt_digest": None,
                "still_current": False,
            }
        return {
            "integrity_valid": True,
            "prior_state": historical["state"],
            "current_state": current["state"],
            "current_reasons": current["reasons"],
            "current_receipt_digest": current["receipt_digest"],
            "still_current": _canonical(_projection(historical)) == _canonical(_projection(current)),
        }

    return compile_current, verify_receipt


compile_current, verify_receipt = _build_current_api()
del _build_current_api
del _stdlib_datetime
del _stdlib_timezone


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise GateError(f"{path}: regular file required")
    return load_json(path.read_bytes(), str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_compile = sub.add_parser("compile")
    p_compile.add_argument("packet")
    p_compile.add_argument("--output")
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("packet")
    p_verify.add_argument("receipt")
    args = parser.parse_args(argv)
    try:
        packet = _read(Path(args.packet))
        if args.cmd == "compile":
            receipt = compile_current(packet)
            raw = canonical_json(receipt)
            if args.output:
                out = Path(args.output)
                if out.exists() or out.is_symlink():
                    raise GateError("output: refusing overwrite")
                out.write_bytes(raw)
            else:
                print(raw.decode("utf-8"), end="")
            return 0 if receipt["state"] == READY else 2
        result = verify_receipt(packet, _read(Path(args.receipt)))
        print(canonical_json(result).decode("utf-8"), end="")
        return 0 if result["still_current"] else 2
    except (GateError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
