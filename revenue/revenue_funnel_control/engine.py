from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "TJL_REVENUE_FUNNEL_V1"
BUNDLE_SCHEMA = "TJL_REVENUE_FUNNEL_BUNDLE_V1"
AUTHORITY = {
    "external_send": False,
    "muse_selection": False,
    "provider_mutation": False,
    "invoice_creation": False,
    "payment_movement": False,
    "receivable_establishment": False,
    "revenue_recognition": False,
}
LANES = {"OUTREACH", "BOUNTY", "COMPETITION", "CONTRACT", "PRODUCT", "OTHER"}
EVENT_KINDS = {
    "QUALIFIED",
    "PROPOSAL_SENT",
    "CLAIM_SUBMITTED",
    "ACCEPTED",
    "MERGED",
    "AWARDED",
    "INVOICE_ISSUED",
    "PAYMENT_RECEIVED",
    "OUTBOUND_SENT",
    "INBOUND_RECEIVED",
    "MUSE_CLEAR",
    "DNR",
    "COLLISION_HOLD",
}
SOURCE_CLASSES = {
    "PROVIDER_RECEIPT",
    "BUYER_MESSAGE",
    "SPONSOR_MESSAGE",
    "GITHUB",
    "SLACK",
    "INTERNAL_RETAINED",
}
OPPORTUNITY_KEYS = {
    "id", "title", "lane", "currency", "reference_amount_cents", "events",
}
EVENT_KEYS = {
    "id", "kind", "observed_at", "source_class", "ref", "sha256", "amount_cents",
}
DOC_KEYS = {"schema", "evaluation_at", "micro_batch_threshold_cents", "opportunities"}


class FunnelError(ValueError):
    pass


def _exact_dict(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise FunnelError(f"{where}: expected exact object")
    if set(value) != keys:
        missing = sorted(keys - set(value))
        extra = sorted(set(value) - keys)
        raise FunnelError(f"{where}: exact keys required; missing={missing}; extra={extra}")
    return value


def _canonical(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise FunnelError(f"not canonical JSON: {exc}") from exc
    return text.encode("utf-8", "strict")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_time(value: Any, where: str) -> datetime:
    if type(value) is not str or not value.endswith("Z") or "." in value:
        raise FunnelError(f"{where}: exact whole-second UTC RFC3339 Z required")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise FunnelError(f"{where}: invalid timestamp") from exc
    return parsed


def _bounded_text(value: Any, where: str, *, maximum: int = 512, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise FunnelError(f"{where}: string required")
    if len(value) > maximum or (not allow_empty and not value):
        raise FunnelError(f"{where}: invalid length")
    if any(ord(ch) < 32 for ch in value):
        raise FunnelError(f"{where}: control characters forbidden")
    return value


def _sha(value: Any, where: str) -> str:
    value = _bounded_text(value, where, maximum=64)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise FunnelError(f"{where}: lowercase sha256 required")
    return value


def _money(value: Any, where: str, *, optional: bool = False) -> int | None:
    if optional and value is None:
        return None
    if type(value) is not int or value < 0 or value > 10**15:
        raise FunnelError(f"{where}: bounded nonnegative integer cents required")
    return value


def _stage_for(kinds: set[str], paid_total: int, reference_amount: int | None) -> str:
    if paid_total:
        if reference_amount is None:
            return "PAYMENT_RECORDED_TARGET_UNKNOWN"
        if paid_total < reference_amount:
            return "PARTIALLY_PAID"
        if paid_total == reference_amount:
            return "PAID"
        return "OVERPAID_RECONCILE"
    if "INVOICE_ISSUED" in kinds or "AWARDED" in kinds:
        return "INVOICED_OR_AWARDED"
    if "ACCEPTED" in kinds or "MERGED" in kinds:
        return "ACCEPTED_OR_MERGED"
    if "PROPOSAL_SENT" in kinds or "CLAIM_SUBMITTED" in kinds:
        return "PROPOSED_OR_CLAIMED"
    if "QUALIFIED" in kinds:
        return "QUALIFIED"
    return "DISCOVERED"


def _latest(events: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    matches = [e for e in events if e["kind"] == kind]
    return matches[-1] if matches else None


def _next_action(stage: str, events: list[dict[str, Any]]) -> str:
    last_dnr = _latest(events, "DNR")
    last_inbound = _latest(events, "INBOUND_RECEIVED")
    last_outbound = _latest(events, "OUTBOUND_SENT")
    last_collision = _latest(events, "COLLISION_HOLD")
    last_muse = _latest(events, "MUSE_CLEAR")

    if last_inbound and (not last_outbound or last_inbound["observed_at"] > last_outbound["observed_at"]):
        return "RESPOND_TO_NEW_INBOUND"
    if last_dnr and (not last_inbound or last_dnr["observed_at"] >= last_inbound["observed_at"]):
        return "INBOUND_ONLY_DNR"
    if last_collision and (not last_muse or last_collision["observed_at"] >= last_muse["observed_at"]):
        return "HOLD_COLLISION"
    if stage in {"PAID"}:
        return "DONE_PAID"
    if stage == "OVERPAID_RECONCILE":
        return "RECONCILE_OVERPAYMENT"
    if stage in {"PARTIALLY_PAID", "PAYMENT_RECORDED_TARGET_UNKNOWN"}:
        return "RECONCILE_PAYMENT_STATE"
    if stage in {"INVOICED_OR_AWARDED", "ACCEPTED_OR_MERGED"}:
        return "COLLECTION_REVIEW"
    if stage == "PROPOSED_OR_CLAIMED":
        return "ADVANCE_ACCEPTANCE"
    if stage == "QUALIFIED":
        if last_muse and (not last_outbound or last_muse["observed_at"] > last_outbound["observed_at"]):
            return "OWNER_OUTBOUND_REVIEW"
        return "MUSE_REQUIRED_BEFORE_OUTBOUND"
    return "QUALIFY"


def _validate_event(
    raw: Any,
    *,
    opportunity_id: str,
    evaluation_at: datetime,
    reference_amount: int | None,
) -> dict[str, Any]:
    e = _exact_dict(raw, EVENT_KEYS, f"{opportunity_id}.event")
    event_id = _bounded_text(e["id"], f"{opportunity_id}.event.id", maximum=120)
    kind = _bounded_text(e["kind"], f"{event_id}.kind", maximum=40)
    if kind not in EVENT_KINDS:
        raise FunnelError(f"{event_id}.kind: unsupported")
    observed = _parse_time(e["observed_at"], f"{event_id}.observed_at")
    if observed > evaluation_at:
        raise FunnelError(f"{event_id}: future evidence")
    source_class = _bounded_text(e["source_class"], f"{event_id}.source_class", maximum=40)
    if source_class not in SOURCE_CLASSES:
        raise FunnelError(f"{event_id}.source_class: unsupported")
    ref = _bounded_text(e["ref"], f"{event_id}.ref", maximum=512)
    sha = _sha(e["sha256"], f"{event_id}.sha256")
    amount = _money(e["amount_cents"], f"{event_id}.amount_cents", optional=True)
    if kind == "PAYMENT_RECEIVED":
        if amount is None or amount <= 0:
            raise FunnelError(f"{event_id}: payment needs positive amount")
        if source_class != "PROVIDER_RECEIPT":
            raise FunnelError(f"{event_id}: payment requires PROVIDER_RECEIPT retained evidence")
    elif amount is not None:
        if kind not in {"AWARDED", "INVOICE_ISSUED", "PROPOSAL_SENT", "CLAIM_SUBMITTED"}:
            raise FunnelError(f"{event_id}: amount not allowed for {kind}")
    if kind in {"DNR", "COLLISION_HOLD", "MUSE_CLEAR", "OUTBOUND_SENT", "INBOUND_RECEIVED"} and amount is not None:
        raise FunnelError(f"{event_id}: control/contact events cannot carry amount")
    return {
        "id": event_id,
        "kind": kind,
        "observed_at": observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_class": source_class,
        "ref": ref,
        "sha256": sha,
        "amount_cents": amount,
    }


def _compile_opportunity(raw: Any, evaluation_at: datetime, threshold: int) -> dict[str, Any]:
    op = _exact_dict(raw, OPPORTUNITY_KEYS, "opportunity")
    op_id = _bounded_text(op["id"], "opportunity.id", maximum=120)
    title = _bounded_text(op["title"], f"{op_id}.title", maximum=240)
    lane = _bounded_text(op["lane"], f"{op_id}.lane", maximum=40)
    if lane not in LANES:
        raise FunnelError(f"{op_id}.lane: unsupported")
    currency = _bounded_text(op["currency"], f"{op_id}.currency", maximum=8)
    if not (3 <= len(currency) <= 8 and currency.upper() == currency and currency.isalpha()):
        raise FunnelError(f"{op_id}.currency: uppercase alphabetic currency/unit required")
    reference_amount = _money(op["reference_amount_cents"], f"{op_id}.reference_amount_cents", optional=True)
    if type(op["events"]) is not list:
        raise FunnelError(f"{op_id}.events: array required")
    events = [_validate_event(e, opportunity_id=op_id, evaluation_at=evaluation_at, reference_amount=reference_amount) for e in op["events"]]
    ids = [e["id"] for e in events]
    if len(ids) != len(set(ids)):
        raise FunnelError(f"{op_id}: duplicate event id")
    event_bindings = [(e["source_class"], e["ref"], e["sha256"]) for e in events]
    if len(event_bindings) != len(set(event_bindings)):
        raise FunnelError(f"{op_id}: duplicate retained evidence binding")
    events.sort(key=lambda e: (e["observed_at"], e["id"]))
    kinds = {e["kind"] for e in events}

    if any(k in kinds for k in {"PROPOSAL_SENT", "CLAIM_SUBMITTED", "ACCEPTED", "MERGED", "AWARDED", "INVOICE_ISSUED", "PAYMENT_RECEIVED"}) and "QUALIFIED" not in kinds:
        raise FunnelError(f"{op_id}: commercial progress requires QUALIFIED evidence")
    if ("ACCEPTED" in kinds or "MERGED" in kinds or "AWARDED" in kinds or "INVOICE_ISSUED" in kinds or "PAYMENT_RECEIVED" in kinds) and not ({"PROPOSAL_SENT", "CLAIM_SUBMITTED"} & kinds):
        raise FunnelError(f"{op_id}: acceptance/settlement path requires proposal or claim evidence")
    if ("AWARDED" in kinds or "INVOICE_ISSUED" in kinds or "PAYMENT_RECEIVED" in kinds) and not ({"ACCEPTED", "MERGED"} & kinds):
        raise FunnelError(f"{op_id}: award/invoice/payment requires accepted or merged evidence")
    if "PAYMENT_RECEIVED" in kinds and not ({"AWARDED", "INVOICE_ISSUED"} & kinds):
        raise FunnelError(f"{op_id}: payment requires award or invoice evidence")

    payment_total = sum(e["amount_cents"] or 0 for e in events if e["kind"] == "PAYMENT_RECEIVED")
    stage = _stage_for(kinds, payment_total, reference_amount)
    action = _next_action(stage, events)

    economic_gap = (
        reference_amount is not None
        and stage in {"ACCEPTED_OR_MERGED", "INVOICED_OR_AWARDED", "PARTIALLY_PAID"}
    )
    small_batch_candidate = bool(
        economic_gap
        and reference_amount is not None
        and reference_amount <= threshold
        and action in {"COLLECTION_REVIEW", "RECONCILE_PAYMENT_STATE"}
    )
    return {
        "id": op_id,
        "title": title,
        "lane": lane,
        "currency": currency,
        "reference_amount_cents": reference_amount,
        "events": events,
        "stage": stage,
        "next_action": action,
        "payment_received_cents": payment_total,
        "economically_unfinished": bool(economic_gap),
        "micro_batch_candidate": small_batch_candidate,
        "evidence_root_sha256": _digest(events),
    }


def compile_portfolio(document: Any) -> dict[str, Any]:
    doc = _exact_dict(document, DOC_KEYS, "document")
    if doc["schema"] != SCHEMA:
        raise FunnelError("document.schema: unsupported")
    evaluation_at = _parse_time(doc["evaluation_at"], "document.evaluation_at")
    threshold = _money(doc["micro_batch_threshold_cents"], "document.micro_batch_threshold_cents")
    if type(doc["opportunities"]) is not list:
        raise FunnelError("document.opportunities: array required")

    opportunities = [_compile_opportunity(op, evaluation_at, threshold) for op in doc["opportunities"]]
    ids = [op["id"] for op in opportunities]
    if len(ids) != len(set(ids)):
        raise FunnelError("duplicate opportunity id")
    opportunities.sort(key=lambda op: op["id"])

    stage_counts: dict[str, int] = {}
    next_action_counts: dict[str, int] = {}
    payment_by_currency: dict[str, int] = {}
    unfinished_count = 0
    micro_batch_count = 0
    for op in opportunities:
        stage_counts[op["stage"]] = stage_counts.get(op["stage"], 0) + 1
        next_action_counts[op["next_action"]] = next_action_counts.get(op["next_action"], 0) + 1
        payment_by_currency[op["currency"]] = payment_by_currency.get(op["currency"], 0) + op["payment_received_cents"]
        unfinished_count += int(op["economically_unfinished"])
        micro_batch_count += int(op["micro_batch_candidate"])

    return {
        "schema": SCHEMA,
        "evaluation_at": evaluation_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "micro_batch_threshold_cents": threshold,
        "truth_boundary": "RETAINED_EVIDENCE_INPUT_NOT_PROVIDER_AUTHENTICATED",
        "authority": dict(AUTHORITY),
        "opportunities": opportunities,
        "summary": {
            "opportunity_count": len(opportunities),
            "stage_counts": dict(sorted(stage_counts.items())),
            "next_action_counts": dict(sorted(next_action_counts.items())),
            "economically_unfinished_count": unfinished_count,
            "micro_batch_candidate_count": micro_batch_count,
            "payment_received_by_currency": dict(sorted(payment_by_currency.items())),
            "advertised_or_reference_amount_is_revenue": False,
            "merged_or_accepted_is_paid": False,
        },
    }


def compile_bundle(document: Any) -> dict[str, Any]:
    packet = compile_portfolio(document)
    normalized_input = json.loads(_canonical(document).decode("utf-8"))
    receipt = {
        "schema": BUNDLE_SCHEMA,
        "input_sha256": _digest(normalized_input),
        "packet_sha256": _digest(packet),
        "authority": dict(AUTHORITY),
    }
    return {
        "schema": BUNDLE_SCHEMA,
        "input": normalized_input,
        "packet": packet,
        "receipt": receipt,
    }


def verify_bundle(bundle: Any) -> bool:
    if type(bundle) is not dict or set(bundle) != {"schema", "input", "packet", "receipt"}:
        return False
    if bundle.get("schema") != BUNDLE_SCHEMA:
        return False
    receipt = bundle.get("receipt")
    if type(receipt) is not dict or set(receipt) != {"schema", "input_sha256", "packet_sha256", "authority"}:
        return False
    if receipt.get("schema") != BUNDLE_SCHEMA or receipt.get("authority") != AUTHORITY:
        return False
    try:
        recomputed = compile_bundle(bundle["input"])
    except FunnelError:
        return False
    return _canonical(recomputed) == _canonical(bundle)


def _load_json_strict(path: Path, *, limit: int = 8_000_000) -> Any:
    st = os.lstat(path)
    if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
        raise FunnelError("input must be a bounded regular file")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise FunnelError("input changed or is not regular")
        raw = os.read(fd, limit + 1)
        after = os.fstat(fd)
        if len(raw) > limit or (before.st_dev, before.st_ino, before.st_size) != (after.st_dev, after.st_ino, after.st_size):
            raise FunnelError("input changed while reading")
    finally:
        os.close(fd)

    def reject_constant(value: str) -> None:
        raise FunnelError(f"non-finite JSON constant: {value}")

    def reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise FunnelError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    try:
        return json.loads(raw.decode("utf-8", "strict"), parse_constant=reject_constant, object_pairs_hook=reject_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FunnelError(f"invalid JSON: {exc}") from exc


def _write_exclusive(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise FunnelError("short write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile/verify retained-evidence revenue funnel portfolios.")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("input")
    compile_p.add_argument("output")
    verify_p = sub.add_parser("verify")
    verify_p.add_argument("bundle")
    args = parser.parse_args(argv)

    try:
        if args.command == "compile":
            document = _load_json_strict(Path(args.input))
            bundle = compile_bundle(document)
            _write_exclusive(Path(args.output), _canonical(bundle) + b"\n")
            print(json.dumps({"valid": True, "packet_sha256": bundle["receipt"]["packet_sha256"]}, sort_keys=True))
            return 0
        bundle = _load_json_strict(Path(args.bundle))
        valid = verify_bundle(bundle)
        print(json.dumps({"valid": valid}, sort_keys=True))
        return 0 if valid else 2
    except (OSError, FunnelError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
