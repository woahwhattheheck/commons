#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, Mapping

POLICY_SCHEMA = "hotel-room-turn-policy/v1"
EVIDENCE_SCHEMA = "hotel-room-turn-evidence/v1"
REPORT_SCHEMA = "hotel-room-turn-report/v1"
PILOT_ID = "hotel-room-turn-evidence-pilot"
PRICE_USD = 2500
DURATION_DAYS = 7
KINDS = ("housekeeping", "maintenance", "manager_release")
STATES = ("CLEAR", "BLOCK")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MACHINE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+\-]{0,127}$")
MAX_INPUT_BYTES = 2 * 1024 * 1024

AUTHORITY = {
    "pms_write": False,
    "guest_data_access": False,
    "dispatch_housekeeping": False,
    "dispatch_maintenance": False,
    "charge_guest": False,
    "recognize_revenue": False,
}


class ContractError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(raw: bytes | str) -> Any:
    if isinstance(raw, bytes):
        if not raw or len(raw) > MAX_INPUT_BYTES:
            raise ContractError(f"input must be 1..{MAX_INPUT_BYTES} bytes")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ContractError("input must be UTF-8") from exc
    elif isinstance(raw, str):
        text = raw
    else:
        raise ContractError("input must be bytes or text")
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ContractError(f"non-finite JSON token: {token}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON: {exc.msg}") from exc


def canon(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError("value is not canonical JSON") from exc


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exact_keys(obj: Mapping[str, Any], expected: set[str], where: str) -> None:
    actual = set(obj)
    if actual != expected:
        raise ContractError(
            f"{where} keys mismatch missing={sorted(expected - actual)} unknown={sorted(actual - expected)}"
        )


def _obj(value: Any, where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError(f"{where} must be object")
    return value


def _arr(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise ContractError(f"{where} must be array")
    return value


def _text(value: Any, where: str, *, max_len: int = 256) -> str:
    if type(value) is not str or not value or len(value) > max_len:
        raise ContractError(f"{where} must be non-empty string <= {max_len}")
    if any(ord(ch) < 0x20 or ch == "\x7f" for ch in value):
        raise ContractError(f"{where} contains control characters")
    return value


def _machine(value: Any, where: str) -> str:
    text = _text(value, where, max_len=128)
    if _MACHINE.fullmatch(text) is None:
        raise ContractError(f"{where} must be machine token")
    return text


def _int(value: Any, where: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ContractError(f"{where} must be integer in [{low},{high}]")
    return value


def _hex64(value: Any, where: str) -> str:
    text = _text(value, where, max_len=64)
    if _HEX64.fullmatch(text) is None:
        raise ContractError(f"{where} must be 64 lowercase hex")
    return text


def _time(value: Any, where: str) -> dt.datetime:
    text = _text(value, where, max_len=64)
    raw = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ContractError(f"{where} must be RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"{where} must include timezone")
    return parsed.astimezone(dt.timezone.utc)


def _fmt_time(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_policy(raw: Any, expected_sha256: str) -> dict[str, Any]:
    expected_sha256 = _hex64(expected_sha256, "expected_policy_sha256")
    obj = _obj(raw, "policy")
    if sha256_bytes(canon(obj)) != expected_sha256:
        raise ContractError("policy sha256 mismatch")
    _exact_keys(
        obj,
        {
            "schema_version",
            "pilot_id",
            "property_id",
            "price_usd",
            "duration_days",
            "max_age_minutes",
            "allowed_managers",
            "rooms",
        },
        "policy",
    )
    if obj["schema_version"] != POLICY_SCHEMA:
        raise ContractError("policy.schema_version drift")
    if obj["pilot_id"] != PILOT_ID:
        raise ContractError("policy.pilot_id drift")
    if _int(obj["price_usd"], "policy.price_usd", 0, 1_000_000) != PRICE_USD:
        raise ContractError("policy.price_usd drift")
    if _int(obj["duration_days"], "policy.duration_days", 1, 30) != DURATION_DAYS:
        raise ContractError("policy.duration_days drift")
    property_id = _machine(obj["property_id"], "policy.property_id")

    ages = _obj(obj["max_age_minutes"], "policy.max_age_minutes")
    _exact_keys(ages, set(KINDS), "policy.max_age_minutes")
    max_age_minutes = {kind: _int(ages[kind], f"policy.max_age_minutes.{kind}", 1, 1440) for kind in KINDS}

    managers_raw = _arr(obj["allowed_managers"], "policy.allowed_managers")
    if not managers_raw:
        raise ContractError("policy.allowed_managers must not be empty")
    managers = sorted({_machine(v, "policy.allowed_managers[]") for v in managers_raw})
    if len(managers) != len(managers_raw):
        raise ContractError("policy.allowed_managers must be unique")

    rooms_raw = _arr(obj["rooms"], "policy.rooms")
    if not rooms_raw:
        raise ContractError("policy.rooms must not be empty")
    rooms: list[dict[str, str]] = []
    seen_room: set[str] = set()
    seen_turn: set[str] = set()
    for idx, item in enumerate(rooms_raw):
        room = _obj(item, f"policy.rooms[{idx}]")
        _exact_keys(room, {"room_id", "turn_id"}, f"policy.rooms[{idx}]")
        room_id = _machine(room["room_id"], f"policy.rooms[{idx}].room_id")
        turn_id = _machine(room["turn_id"], f"policy.rooms[{idx}].turn_id")
        if room_id in seen_room:
            raise ContractError(f"duplicate room_id: {room_id}")
        if turn_id in seen_turn:
            raise ContractError(f"duplicate turn_id: {turn_id}")
        seen_room.add(room_id)
        seen_turn.add(turn_id)
        rooms.append({"room_id": room_id, "turn_id": turn_id})
    rooms.sort(key=lambda x: x["room_id"])

    return {
        "schema_version": POLICY_SCHEMA,
        "pilot_id": PILOT_ID,
        "property_id": property_id,
        "price_usd": PRICE_USD,
        "duration_days": DURATION_DAYS,
        "max_age_minutes": max_age_minutes,
        "allowed_managers": managers,
        "rooms": rooms,
        "policy_sha256": expected_sha256,
    }


def _parse_event(raw: Any, idx: int) -> dict[str, Any]:
    where = f"evidence.events[{idx}]"
    obj = _obj(raw, where)
    _exact_keys(
        obj,
        {
            "event_id",
            "room_id",
            "turn_id",
            "kind",
            "observed_at",
            "state",
            "actor_id",
            "detail_code",
            "source_ref_sha256",
        },
        where,
    )
    kind = _machine(obj["kind"], f"{where}.kind")
    if kind not in KINDS:
        raise ContractError(f"{where}.kind unknown: {kind}")
    state = _text(obj["state"], f"{where}.state", max_len=16)
    if state not in STATES:
        raise ContractError(f"{where}.state unknown: {state}")
    observed = _time(obj["observed_at"], f"{where}.observed_at")
    return {
        "event_id": _machine(obj["event_id"], f"{where}.event_id"),
        "room_id": _machine(obj["room_id"], f"{where}.room_id"),
        "turn_id": _machine(obj["turn_id"], f"{where}.turn_id"),
        "kind": kind,
        "observed_at": _fmt_time(observed),
        "state": state,
        "actor_id": _machine(obj["actor_id"], f"{where}.actor_id"),
        "detail_code": _machine(obj["detail_code"], f"{where}.detail_code"),
        "source_ref_sha256": _hex64(obj["source_ref_sha256"], f"{where}.source_ref_sha256"),
    }


def parse_evidence(raw: Any, policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    obj = _obj(raw, "evidence")
    _exact_keys(obj, {"schema_version", "pilot_id", "property_id", "events"}, "evidence")
    if obj["schema_version"] != EVIDENCE_SCHEMA:
        raise ContractError("evidence.schema_version drift")
    if obj["pilot_id"] != PILOT_ID:
        raise ContractError("evidence.pilot_id drift")
    if obj["property_id"] != policy["property_id"]:
        raise ContractError("evidence.property_id mismatch")
    events_raw = _arr(obj["events"], "evidence.events")

    dedup: dict[str, dict[str, Any]] = {}
    for idx, item in enumerate(events_raw):
        event = _parse_event(item, idx)
        existing = dedup.get(event["event_id"])
        if existing is None:
            dedup[event["event_id"]] = event
        elif existing != event:
            raise ContractError(f"event_id replay content mismatch: {event['event_id']}")
    return sorted(dedup.values(), key=lambda e: (e["room_id"], e["turn_id"], e["kind"], e["observed_at"], e["event_id"]))


def _cell_for_kind(
    *,
    room: Mapping[str, str],
    kind: str,
    events: list[dict[str, Any]],
    policy: Mapping[str, Any],
    now: dt.datetime,
) -> dict[str, Any]:
    same_room = [e for e in events if e["room_id"] == room["room_id"] and e["kind"] == kind]
    current = [e for e in same_room if e["turn_id"] == room["turn_id"]]
    wrong_turn_count = len(same_room) - len(current)
    base = {"kind": kind, "latest_event_ids": [], "state": None, "actor_id": None, "observed_at": None, "age_minutes": None}
    if not current:
        reasons = [f"MISSING_{kind.upper()}"]
        if wrong_turn_count:
            reasons.append(f"WRONG_TURN_{kind.upper()}:{wrong_turn_count}")
        return {**base, "clear": False, "reasons": reasons}

    times = [_time(e["observed_at"], "event.observed_at") for e in current]
    latest_time = max(times)
    latest = [e for e in current if _time(e["observed_at"], "event.observed_at") == latest_time]
    latest.sort(key=lambda e: e["event_id"])
    base["latest_event_ids"] = [e["event_id"] for e in latest]
    base["observed_at"] = _fmt_time(latest_time)

    fingerprints = {(e["state"], e["actor_id"], e["detail_code"], e["source_ref_sha256"]) for e in latest}
    if len(fingerprints) > 1:
        return {**base, "clear": False, "reasons": [f"CONFLICT_{kind.upper()}"]}

    chosen = latest[0]
    base["state"] = chosen["state"]
    base["actor_id"] = chosen["actor_id"]
    age_seconds = (now - latest_time).total_seconds()
    base["age_minutes"] = int(age_seconds // 60) if age_seconds >= 0 else None

    if age_seconds < 0:
        return {**base, "clear": False, "reasons": [f"FUTURE_{kind.upper()}"]}
    if age_seconds > policy["max_age_minutes"][kind] * 60:
        return {**base, "clear": False, "reasons": [f"STALE_{kind.upper()}"]}
    if kind == "manager_release" and chosen["actor_id"] not in set(policy["allowed_managers"]):
        return {**base, "clear": False, "reasons": ["UNAUTHORIZED_MANAGER"]}
    if chosen["state"] != "CLEAR":
        return {**base, "clear": False, "reasons": [f"BLOCK_{kind.upper()}:{chosen['detail_code']}"]}
    return {**base, "clear": True, "reasons": []}


def compile_report(policy_raw: Any, evidence_raw: Any, *, expected_policy_sha256: str, now: dt.datetime) -> dict[str, Any]:
    if type(now) is not dt.datetime or now.tzinfo is None or now.utcoffset() is None:
        raise ContractError("now must be timezone-aware datetime")
    now = now.astimezone(dt.timezone.utc)
    policy = parse_policy(policy_raw, expected_policy_sha256)
    evidence = parse_evidence(evidence_raw, policy)

    known_rooms = {room["room_id"] for room in policy["rooms"]}
    unknown_rooms = sorted({e["room_id"] for e in evidence} - known_rooms)
    if unknown_rooms:
        raise ContractError(f"evidence references unknown rooms: {unknown_rooms}")

    room_results: list[dict[str, Any]] = []
    for room in policy["rooms"]:
        checks = [
            _cell_for_kind(room=room, kind=kind, events=evidence, policy=policy, now=now)
            for kind in KINDS
        ]
        ready = all(check["clear"] for check in checks)
        reasons = sorted({reason for check in checks for reason in check["reasons"]})
        room_results.append(
            {
                "room_id": room["room_id"],
                "turn_id": room["turn_id"],
                "decision": "READY" if ready else "BLOCKED",
                "reasons": reasons,
                "checks": checks,
            }
        )

    ready_count = sum(1 for room in room_results if room["decision"] == "READY")
    unsigned = {
        "schema_version": REPORT_SCHEMA,
        "pilot_id": PILOT_ID,
        "property_id": policy["property_id"],
        "evaluated_at": _fmt_time(now),
        "policy_sha256": policy["policy_sha256"],
        "commercial_terms": {
            "price_usd": PRICE_USD,
            "duration_days": DURATION_DAYS,
            "scope": "offline/de-identified one-property room-turn evidence pilot",
            "status": "OFFER_CONTRACT_NOT_PAYMENT_PROOF",
        },
        "authority": AUTHORITY,
        "event_count_unique": len(evidence),
        "room_count": len(room_results),
        "ready_count": ready_count,
        "blocked_count": len(room_results) - ready_count,
        "rooms": room_results,
    }
    receipt = sha256_bytes(canon(unsigned))
    return {**unsigned, "receipt_sha256": receipt}


def verify_report(report: Any, *, expected_policy_sha256: str, expected_report_sha256: str) -> bool:
    obj = _obj(report, "report")
    if "receipt_sha256" not in obj:
        raise ContractError("report missing receipt_sha256")
    receipt = _hex64(obj["receipt_sha256"], "report.receipt_sha256")
    retained = _hex64(expected_report_sha256, "expected_report_sha256")
    if not hmac.compare_digest(receipt, retained):
        raise ContractError("report retained receipt mismatch")
    if obj.get("schema_version") != REPORT_SCHEMA:
        raise ContractError("report.schema_version drift")
    if obj.get("policy_sha256") != _hex64(expected_policy_sha256, "expected_policy_sha256"):
        raise ContractError("report policy root mismatch")
    unsigned = dict(obj)
    del unsigned["receipt_sha256"]
    expected = sha256_bytes(canon(unsigned))
    if not hmac.compare_digest(receipt, expected):
        raise ContractError("report receipt mismatch")
    return True


def render_markdown(report: Mapping[str, Any], *, expected_policy_sha256: str, expected_report_sha256: str) -> str:
    verify_report(
        report,
        expected_policy_sha256=expected_policy_sha256,
        expected_report_sha256=expected_report_sha256,
    )
    lines = [
        "# Hotel Room-Turn Evidence Pilot — acceptance sheet",
        "",
        f"- Property: `{report['property_id']}`",
        f"- Evaluated: `{report['evaluated_at']}`",
        f"- Fixed pilot price: **${report['commercial_terms']['price_usd']:,}**",
        f"- Pilot duration: **{report['commercial_terms']['duration_days']} days**",
        f"- Room decisions: **{report['ready_count']} READY / {report['blocked_count']} BLOCKED**",
        f"- Receipt: `{report['receipt_sha256']}`",
        "",
        "| Room | Turn | Decision | Reasons |",
        "|---|---|---|---|",
    ]
    for room in report["rooms"]:
        reasons = ", ".join(room["reasons"]) if room["reasons"] else "—"
        lines.append(f"| {room['room_id']} | {room['turn_id']} | **{room['decision']}** | {reasons} |")
    lines.extend(
        [
            "",
            "## Acceptance boundary",
            "",
            "A room is READY only when fresh housekeeping, maintenance, and named-manager release evidence all bind the same turnover generation and are internally consistent. Missing, stale, conflicting, future, wrong-turn, unauthorized-manager, or explicit block evidence leaves the room BLOCKED.",
            "",
            "This pilot is offline and de-identified. It does not write to a PMS, access guest data, dispatch staff, charge guests, or prove payment/revenue.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_file(path: Path) -> Any:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ContractError(f"cannot open ordinary input file: {path}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ContractError(f"input must be ordinary file: {path}")
        if st.st_size < 1 or st.st_size > MAX_INPUT_BYTES:
            raise ContractError(f"input size out of range: {path}")
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            raw = handle.read(MAX_INPUT_BYTES + 1)
        if len(raw) < 1 or len(raw) > MAX_INPUT_BYTES:
            raise ContractError(f"input size out of range after read: {path}")
        return loads_strict(raw)
    finally:
        if fd >= 0:
            os.close(fd)


def _write_exclusive(path: Path, data: bytes) -> None:
    if not path.parent.exists() or not path.parent.is_dir():
        raise ContractError(f"output parent missing: {path.parent}")
    if path.exists() or path.is_symlink():
        raise ContractError(f"refusing existing output path: {path}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a bounded hotel room-turn readiness receipt")
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile")
    p_compile.add_argument("--policy", required=True)
    p_compile.add_argument("--evidence", required=True)
    p_compile.add_argument("--expected-policy-sha256", required=True)
    p_compile.add_argument("--out", required=True)

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--report", required=True)
    p_verify.add_argument("--expected-policy-sha256", required=True)
    p_verify.add_argument("--expected-report-sha256", required=True)

    p_render = sub.add_parser("render")
    p_render.add_argument("--report", required=True)
    p_render.add_argument("--expected-policy-sha256", required=True)
    p_render.add_argument("--expected-report-sha256", required=True)
    p_render.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            report = compile_report(
                _load_file(Path(args.policy)),
                _load_file(Path(args.evidence)),
                expected_policy_sha256=args.expected_policy_sha256,
                now=_utc_now(),
            )
            _write_exclusive(Path(args.out), canon(report))
            print(report["receipt_sha256"])
            return 0
        if args.command == "verify":
            report = _load_file(Path(args.report))
            verify_report(
                report,
                expected_policy_sha256=args.expected_policy_sha256,
                expected_report_sha256=args.expected_report_sha256,
            )
            print(report["receipt_sha256"])
            return 0
        if args.command == "render":
            report = _load_file(Path(args.report))
            verify_report(
                report,
                expected_policy_sha256=args.expected_policy_sha256,
                expected_report_sha256=args.expected_report_sha256,
            )
            _write_exclusive(
                Path(args.out),
                render_markdown(
                    report,
                    expected_policy_sha256=args.expected_policy_sha256,
                    expected_report_sha256=args.expected_report_sha256,
                ).encode("utf-8"),
            )
            print(report["receipt_sha256"])
            return 0
    except (ContractError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
