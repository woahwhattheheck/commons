#!/usr/bin/env python3
"""Fail-closed currentness facade for the UArk RFP09112026 qualifier.

The deterministic compiler in ``_qualifier_core.py`` remains the historical /
integrity surface. CURRENT compilation and verification are built over a separate,
private core generation loaded during trusted module initialization. Supported
CURRENT APIs accept no caller time selector and retain no semantic dependency on
the public ``_core`` module or its mutable aliases.

Current verification snapshots one exact built-in JSON generation before any
semantic work. Owner-facing Markdown is CURRENT by default; the separately named
historical renderer is visibly labeled historical/integrity-only.

Arbitrary interpreter takeover (closure-cell/code-object surgery, frame mutation,
or code execution before trusted import) is outside this library boundary.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_CORE_PATH = Path(__file__).with_name("_qualifier_core.py")
_SPEC = importlib.util.spec_from_file_location(
    "uark_rfp09112026_qualifier_core", _CORE_PATH
)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import contract
    raise ImportError(f"cannot load UArk qualifier core from {_CORE_PATH}")
_core = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_core)

# Historical/library compatibility surface. CURRENT semantics below do not resolve
# through this public module or through aliases copied from it.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

ADDENDUM_RECHECK_BOUNDARY_UTC = "2026-10-06T05:00:00Z"
_FUTURE_SKEW = timedelta(minutes=5)


def _make_process_utc_now():
    """Capture process clock primitives once, outside mutable module globals."""
    from datetime import datetime as _clock_datetime
    from datetime import timezone as _clock_timezone

    builtin_now = _clock_datetime.now
    utc = _clock_timezone.utc

    def process_utc_now() -> datetime:
        value = builtin_now(utc)
        return value.astimezone(utc).replace(microsecond=0)

    return process_utc_now


_PROCESS_UTC_NOW = _make_process_utc_now()
del _make_process_utc_now


def _normalize_aware_utc(
    value: datetime,
    _datetime_type=datetime,
    _utc=timezone.utc,
) -> datetime:
    if not isinstance(value, _datetime_type):
        raise InputError("time value must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise InputError("time value must be timezone-aware")
    return value.astimezone(_utc).replace(microsecond=0)


def _utc_text(value: datetime, _normalize=_normalize_aware_utc) -> str:
    return _normalize(value).isoformat().replace("+00:00", "Z")


def _refresh_receipts(
    packet: dict[str, Any],
    _sha256_obj=sha256_obj,
) -> dict[str, Any]:
    decision = packet["decision"]
    decision.pop("decision_receipt_sha256", None)
    decision["decision_receipt_sha256"] = _sha256_obj(decision)
    packet.pop("packet_receipt_sha256", None)
    packet["packet_receipt_sha256"] = _sha256_obj(packet)
    return packet


def _apply_currentness(
    packet: dict[str, Any],
    _parse_dt=_dt,
    _refresh=_refresh_receipts,
    _boundary=ADDENDUM_RECHECK_BOUNDARY_UTC,
) -> dict[str, Any]:
    """Historical replay rule; CURRENT has an independent private copy."""
    evaluated = _parse_dt(packet["evaluated_at_utc"])
    source_checked = _parse_dt(packet["source_generation"]["hogbid_checked_at_utc"])
    recheck_boundary = _parse_dt(_boundary)
    blockers: list[str] = []

    if evaluated < source_checked:
        blockers.append("EVALUATION_PRECEDES_SOURCE_CAPTURE")
    if (
        evaluated >= recheck_boundary
        and source_checked < recheck_boundary
        and packet["source_generation"]["addenda_state"] == "NONE_LISTED"
    ):
        blockers.append("POST_ADDENDUM_SOURCE_RECHECK_REQUIRED")

    if not blockers:
        return packet

    decision = packet["decision"]
    existing = list(decision["blockers"])
    for blocker in blockers:
        if blocker not in existing:
            existing.append(blocker)
    decision["blockers"] = existing
    if decision["status"] != "NO_BID":
        decision["status"] = "HOLD"
    decision["submission_ready"] = False
    return _refresh(packet)


def compile_qualification(
    intake: Any,
    _core_compile=_core.compile_qualification,
    _apply=_apply_currentness,
) -> dict[str, Any]:
    """Historical/integrity compile using intake ``evaluated_at_utc`` as data."""
    return _apply(_core_compile(intake))


def verify_packet(
    packet: Any,
    _deepcopy=copy.deepcopy,
    _sha256_obj=sha256_obj,
    _compile=compile_qualification,
) -> bool:
    """Verify receipt integrity and deterministic historical semantics."""
    required = {
        "schema", "operation", "owner", "model", "evaluated_at_utc", "buyer",
        "rfp_number", "question_deadline_utc", "proposal_deadline_utc",
        "last_planned_addendum_date", "internal_workshare_target_usd",
        "price_boundary", "source_generation", "candidate", "decision",
        "packet_receipt_sha256",
    }
    if not isinstance(packet, dict) or set(packet) != required:
        raise InputError("packet schema mismatch")
    receipt = packet["packet_receipt_sha256"]
    if not isinstance(receipt, str) or not SHA_RE.fullmatch(receipt):
        raise InputError("packet receipt invalid")
    unsigned = _deepcopy(packet)
    unsigned.pop("packet_receipt_sha256")
    if _sha256_obj(unsigned) != receipt:
        raise InputError("packet receipt mismatch")
    intake = {
        "schema": SCHEMA,
        "evaluated_at_utc": packet["evaluated_at_utc"],
        "source_generation": packet["source_generation"],
        "candidate": packet["candidate"],
    }
    expected = _compile(intake)
    if packet != expected:
        raise InputError("packet semantic verification failed")
    return True


def _snapshot_exact_json(value: Any, _input_error=InputError) -> Any:
    """Copy one exact built-in JSON generation; reject observable container hooks."""
    def capture(node: Any) -> Any:
        if node is None or type(node) in (str, int, bool):
            return node
        if type(node) is list:
            return [capture(item) for item in node]
        if type(node) is dict:
            out: dict[str, Any] = {}
            try:
                items = list(node.items())
            except RuntimeError as exc:
                raise _input_error("input changed during generation capture") from exc
            for key, item in items:
                if type(key) is not str:
                    raise _input_error("JSON object keys must be exact strings")
                out[key] = capture(item)
            return out
        raise _input_error(
            f"unsupported non-exact JSON value type: {type(node).__name__}"
        )

    return capture(value)


def _make_private_current_semantics(
    core_path: Path,
    process_now,
    utc_text,
    input_error,
    future_skew,
    boundary_text: str,
    snapshot_exact,
):
    """Construct CURRENT against a private core namespace never published here."""
    private_spec = importlib.util.spec_from_file_location(
        "_uark_current_semantics_private", core_path
    )
    if private_spec is None or private_spec.loader is None:  # pragma: no cover
        raise ImportError(f"cannot load private UArk semantics from {core_path}")
    private_core = importlib.util.module_from_spec(private_spec)
    private_spec.loader.exec_module(private_core)

    p_compile = private_core.compile_qualification
    p_error = private_core.InputError
    p_dt = private_core._dt
    p_sha = private_core.sha256_obj
    p_deepcopy = private_core.copy.deepcopy
    p_sha_re = private_core.SHA_RE
    schema = private_core.SCHEMA
    recheck_boundary = p_dt(boundary_text)

    def translate(call, *args):
        try:
            return call(*args)
        except p_error as exc:
            raise input_error(str(exc)) from exc

    def apply_private_currentness(packet: dict[str, Any]) -> dict[str, Any]:
        evaluated = p_dt(packet["evaluated_at_utc"])
        source_checked = p_dt(packet["source_generation"]["hogbid_checked_at_utc"])
        blockers: list[str] = []
        if evaluated < source_checked:
            blockers.append("EVALUATION_PRECEDES_SOURCE_CAPTURE")
        if (
            evaluated >= recheck_boundary
            and source_checked < recheck_boundary
            and packet["source_generation"]["addenda_state"] == "NONE_LISTED"
        ):
            blockers.append("POST_ADDENDUM_SOURCE_RECHECK_REQUIRED")
        if not blockers:
            return packet
        decision = packet["decision"]
        existing = list(decision["blockers"])
        for blocker in blockers:
            if blocker not in existing:
                existing.append(blocker)
        decision["blockers"] = existing
        if decision["status"] != "NO_BID":
            decision["status"] = "HOLD"
        decision["submission_ready"] = False
        decision.pop("decision_receipt_sha256", None)
        decision["decision_receipt_sha256"] = p_sha(decision)
        packet.pop("packet_receipt_sha256", None)
        packet["packet_receipt_sha256"] = p_sha(packet)
        return packet

    def compile_at(stamped: dict[str, Any]) -> dict[str, Any]:
        return apply_private_currentness(translate(p_compile, stamped))

    def verify_historical_private(packet: dict[str, Any]) -> bool:
        required = {
            "schema", "operation", "owner", "model", "evaluated_at_utc", "buyer",
            "rfp_number", "question_deadline_utc", "proposal_deadline_utc",
            "last_planned_addendum_date", "internal_workshare_target_usd",
            "price_boundary", "source_generation", "candidate", "decision",
            "packet_receipt_sha256",
        }
        if set(packet) != required:
            raise input_error("packet schema mismatch")
        receipt = packet["packet_receipt_sha256"]
        if type(receipt) is not str or not p_sha_re.fullmatch(receipt):
            raise input_error("packet receipt invalid")
        unsigned = p_deepcopy(packet)
        unsigned.pop("packet_receipt_sha256")
        if p_sha(unsigned) != receipt:
            raise input_error("packet receipt mismatch")
        intake = {
            "schema": schema,
            "evaluated_at_utc": packet["evaluated_at_utc"],
            "source_generation": packet["source_generation"],
            "candidate": packet["candidate"],
        }
        expected = compile_at(intake)
        if packet != expected:
            raise input_error("packet semantic verification failed")
        return True

    def decision_body(decision: dict[str, Any]) -> dict[str, Any]:
        body = p_deepcopy(decision)
        body.pop("decision_receipt_sha256", None)
        return body

    def compile_production(intake: Any) -> dict[str, Any]:
        """Compile one exact intake generation using process-owned current UTC."""
        stamped = snapshot_exact(intake)
        if type(stamped) is not dict:
            raise input_error("intake must be an object")
        stamped["evaluated_at_utc"] = utc_text(process_now())
        return compile_at(stamped)

    def verify_packet_current(packet: Any) -> bool:
        """Verify one retained packet generation, then evaluate it at process UTC."""
        retained = snapshot_exact(packet)
        if type(retained) is not dict:
            raise input_error("packet must be an object")
        verify_historical_private(retained)
        trusted = process_now()
        evaluated = p_dt(retained["evaluated_at_utc"])
        if evaluated > trusted + future_skew:
            raise input_error("packet evaluation time is ahead of trusted current time")
        current_intake = {
            "schema": schema,
            "evaluated_at_utc": utc_text(trusted),
            "source_generation": retained["source_generation"],
            "candidate": retained["candidate"],
        }
        current = compile_at(current_intake)
        if decision_body(retained["decision"]) != decision_body(current["decision"]):
            raise input_error("packet decision is no longer current")
        return True

    return compile_production, verify_packet_current


compile_production, verify_packet_current = _make_private_current_semantics(
    _CORE_PATH,
    _PROCESS_UTC_NOW,
    _utc_text,
    InputError,
    _FUTURE_SKEW,
    ADDENDUM_RECHECK_BOUNDARY_UTC,
    _snapshot_exact_json,
)
del _make_private_current_semantics
del _PROCESS_UTC_NOW


def _make_renderers(verify_current, verify_historical, snapshot_exact):
    def body(retained: dict[str, Any], heading: str, banner: str) -> str:
        decision = retained["decision"]
        blockers = "\n".join(f"- {item}" for item in decision["blockers"]) or "- none"
        risks = "\n".join(f"- {item}" for item in decision["risks"]) or "- none"
        return (
            heading + "\n\n" + banner + "\n\n"
            f"**Route:** `{decision['route_requested']}`  \n"
            f"**Status:** `{decision['status']}`  \n"
            f"**Submission ready:** `{str(decision['submission_ready']).lower()}`  \n"
            f"**Internal workshare target:** `${retained['internal_workshare_target_usd']:,}`"
            f" — `{retained['price_boundary']}`\n\n"
            "## Blockers\n" + blockers + "\n\n"
            "## Risks / packet gaps\n" + risks + "\n\n"
            "## Authority boundary\n"
            "This result authorizes no buyer or partner contact, no portal action, no "
            "signature, no price commitment, no certification/assessment representation, "
            "no FCI/CUI handling, no contract acceptance, and no award/revenue claim. "
            "Any email requires a fresh collision/provider-history fence and explicit "
            "Muse single-writer selection.\n\n"
            f"Receipt: `{retained['packet_receipt_sha256']}`\n"
        )

    def render_markdown(packet: Any) -> str:
        retained = snapshot_exact(packet)
        verify_current(retained)
        return body(
            retained,
            "# UArk RFP09112026 CURRENT qualification",
            "**CURRENT AUTHORITY CHECK PASSED at render time.**",
        )

    def render_markdown_historical(packet: Any) -> str:
        retained = snapshot_exact(packet)
        verify_historical(retained)
        return body(
            retained,
            "# UArk RFP09112026 historical qualification snapshot",
            "**HISTORICAL / INTEGRITY ONLY — NOT CURRENT AUTHORITY.**",
        )

    return render_markdown, render_markdown_historical


render_markdown, render_markdown_historical = _make_renderers(
    verify_packet_current,
    verify_packet,
    _snapshot_exact_json,
)
del _make_renderers


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "compile":
            packet = compile_production(read_json_file(args.input_json))
            json_text = canonical_json(packet) + "\n"
            markdown_text = render_markdown(packet)
            if args.json_out:
                _write_exclusive(args.json_out, json_text)
            else:
                sys.stdout.write(json_text)
            if args.markdown_out:
                _write_exclusive(args.markdown_out, markdown_text)
            return 0
        if args.command == "verify":
            verify_packet_current(read_json_file(args.packet_json))
            print("VERIFIED")
            return 0
        raise InputError("unknown command")
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
