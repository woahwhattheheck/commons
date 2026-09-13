from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from typing import Any

from revenue.multi_framework_evidence_freshness.gate import (
    GateError as BaseGateError,
    compile_packet as compile_base_packet,
    verify_packet as verify_base_packet,
)

SCHEMA = "commons.multi-framework-evidence-freshness-pilot/v1"
DIAGNOSTIC_PRICE_USD_CENTS = 350_000
INTEGRATION_PRICE_USD_CENTS = 1_000_000
MAX_DIAGNOSTIC_EVIDENCE = 500
MAX_INPUT_BYTES = 4_000_000
STATES = ("REUSABLE", "STALE", "SCOPE_MISMATCH", "MISSING_OWNER", "INCOMPLETE")
_FALSE_AUTHORITY = {
    "audit_opinion": False,
    "certification_opinion": False,
    "control_effectiveness_rating": False,
    "evidence_mutation": False,
    "customer_contact": False,
    "provider_mutation": False,
    "payment": False,
    "revenue_recognition": False,
    "free_custom_adapter": False,
}


class PilotError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _utc_text(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise PilotError("trusted_as_of:timezone_required")
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(text: Any) -> datetime:
    if type(text) is not str:
        raise PilotError("evaluated_at:string_required")
    try:
        dt = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PilotError("evaluated_at:canonical_utc_required") from exc
    if dt.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        raise PilotError("evaluated_at:canonical_utc_required")
    return dt


def _exact_dict(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise PilotError(f"{where}:object_required")
    if set(value) != keys:
        raise PilotError(f"{where}:keys")
    return value


def _reason_counts(base_packet: dict[str, Any]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in base_packet["results"]:
        if row["state"] == "REUSABLE":
            continue
        for reason in row["reasons"]:
            counts[reason] = counts.get(reason, 0) + 1
    return [{"reason": key, "count": counts[key]} for key in sorted(counts)]


def _buyer_report(packet: dict[str, Any]) -> str:
    counts = packet["diagnostic"]["counts"]
    lines = [
        "# Multi-Framework Evidence Freshness Diagnostic",
        "",
        f"Assessment: `{packet['diagnostic']['assessment_id']}`",
        f"Evaluated at: `{packet['evaluated_at']}`",
        f"Evidence objects reviewed: **{packet['diagnostic']['evidence_object_count']}**",
        "",
        "## Result",
        "",
    ]
    for state in STATES:
        lines.append(f"- {state}: **{counts[state]}**")
    lines += ["", "## Non-reusable reason counts", ""]
    if packet["diagnostic"]["reason_counts"]:
        for row in packet["diagnostic"]["reason_counts"]:
            lines.append(f"- {row['reason']}: **{row['count']}**")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Fixed diagnostic scope",
        "",
        f"- Diagnostic price: **${DIAGNOSTIC_PRICE_USD_CENTS // 100:,} fixed**",
        f"- Included volume: one sanitized export, up to **{MAX_DIAGNOSTIC_EVIDENCE} evidence objects**",
        "- Deliverable: this summary plus deterministic JSON evidence/receipt package",
        "- Custom source-system adapter: **not included**",
        f"- Optional integration sprint after a paid diagnostic establishes value and adapter scope: **${INTEGRATION_PRICE_USD_CENTS // 100:,}**",
        "",
        "## Truth boundary",
        "",
        "This diagnostic is evidence freshness/reuse QA only. It is not an audit opinion, certification opinion, control-effectiveness conclusion, or assurance recommendation. It does not mutate evidence, contact a customer, mutate a provider, move money, or recognize revenue.",
        "",
    ]
    return "\n".join(lines) + "\n"


def compile_pilot(raw: Any, *, trusted_as_of: datetime | None = None) -> dict[str, Any]:
    if type(raw) is not dict:
        raise PilotError("input:object_required")
    evidence = raw.get("evidence")
    if type(evidence) is not list:
        raise PilotError("input.evidence:list_required")
    if len(evidence) > MAX_DIAGNOSTIC_EVIDENCE:
        raise PilotError("diagnostic:evidence_limit_exceeded")

    as_of = trusted_as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise PilotError("trusted_as_of:timezone_required")
    as_of = as_of.astimezone(timezone.utc).replace(microsecond=0)
    try:
        base = compile_base_packet(raw, trusted_as_of=as_of)
        verify_base_packet(base)
    except BaseGateError as exc:
        raise PilotError(f"base_gate:{exc}") from exc

    packet: dict[str, Any] = {
        "schema": SCHEMA,
        "evaluated_at": _utc_text(as_of),
        "base_binding": {
            "base_schema": base["schema"],
            "input_sha256": base["input_sha256"],
            "projection_sha256": base["projection_sha256"],
            "base_receipt_sha256": base["receipt_sha256"],
            "base_packet_sha256": _sha(base),
        },
        "base_packet": base,
        "diagnostic": {
            "assessment_id": base["assessment_id"],
            "evidence_object_count": len(evidence),
            "counts": {state: base["counts"][state] for state in STATES},
            "reason_counts": _reason_counts(base),
        },
        "offer": {
            "currency": "USD",
            "diagnostic_price_cents": DIAGNOSTIC_PRICE_USD_CENTS,
            "diagnostic_max_evidence_objects": MAX_DIAGNOSTIC_EVIDENCE,
            "diagnostic_input": "ONE_SANITIZED_EXPORT",
            "integration_sprint_price_cents": INTEGRATION_PRICE_USD_CENTS,
            "integration_requires_paid_diagnostic": True,
            "free_custom_adapter": False,
        },
        "authority": dict(_FALSE_AUTHORITY),
    }
    report_body = _buyer_report(packet)
    packet["buyer_report_sha256"] = hashlib.sha256(report_body.encode("utf-8")).hexdigest()
    packet["receipt_sha256"] = _sha(packet)
    return packet


def render_buyer_markdown(packet: dict[str, Any]) -> str:
    verify_pilot(packet)
    return _buyer_report(packet) + f"Receipt: `{packet['receipt_sha256']}`\n"


def verify_pilot(packet: Any) -> bool:
    _exact_dict(
        packet,
        {
            "schema", "evaluated_at", "base_binding", "base_packet", "diagnostic", "offer",
            "authority", "buyer_report_sha256", "receipt_sha256",
        },
        "packet",
    )
    if packet["schema"] != SCHEMA:
        raise PilotError("packet:schema")
    evaluated = _parse_utc(packet["evaluated_at"])
    rebuilt = compile_pilot(packet["base_packet"]["input"], trusted_as_of=evaluated)
    if _canon(rebuilt) != _canon(packet):
        raise PilotError("packet:recompile_mismatch")
    if packet["authority"] != _FALSE_AUTHORITY:
        raise PilotError("packet:authority")
    return True


def _pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PilotError(f"duplicate_json_key:{key}")
        out[key] = value
    return out


def _read_json_regular(path: str) -> Any:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PilotError("input_open_failed") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise PilotError("input_not_regular")
        if st.st_size > MAX_INPUT_BYTES:
            raise PilotError("input_too_large")
        data = b""
        while len(data) <= MAX_INPUT_BYTES:
            chunk = os.read(fd, min(65536, MAX_INPUT_BYTES + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > MAX_INPUT_BYTES:
            raise PilotError("input_too_large")
        end = os.fstat(fd)
        if (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns) != (end.st_dev, end.st_ino, end.st_size, end.st_mtime_ns):
            raise PilotError("input_changed_during_read")
    finally:
        os.close(fd)
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise PilotError("invalid_utf8") from exc
    if text.startswith("\ufeff"):
        raise PilotError("bom_forbidden")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_hook,
            parse_constant=lambda token: (_ for _ in ()).throw(PilotError(f"non_finite:{token}")),
        )
    except json.JSONDecodeError as exc:
        raise PilotError(f"invalid_json:{exc.msg}") from exc


def _write_exclusive(path: str, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 3 and args[0] == "compile":
        raw = _read_json_regular(args[1])
        packet = compile_pilot(raw)
        _write_exclusive(args[2], json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")
        print(f"PILOT_PACKAGE_READY {packet['receipt_sha256']}")
        return 0
    if len(args) == 2 and args[0] == "verify":
        packet = _read_json_regular(args[1])
        verify_pilot(packet)
        print(f"VERIFIED {packet['receipt_sha256']}")
        return 0
    print("usage: pilot.py compile INPUT.json OUTPUT.json | pilot.py verify OUTPUT.json", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
