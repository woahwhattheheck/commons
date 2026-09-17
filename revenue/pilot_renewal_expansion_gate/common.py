#!/usr/bin/env python3
"""Evidence-bound pilot delivery -> renewal/expansion review gate.

Stdlib-only. This module never contacts a buyer/provider, sends messages, mutates CRM,
accepts contracts, invoices, moves money, or recognizes revenue. It only compiles and
verifies evidence supplied by a host into a conservative owner-review packet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from datetime import datetime, timezone
from typing import Any

SCHEMA = "pilot-renewal-expansion/v1"
RECEIPT_SCHEMA = "pilot-renewal-expansion-receipt/v1"
TRUTH_CEILING = "PROPOSED_NOT_ACCEPTED"
TERMINAL_STATES = {
    "READY_FOR_RENEWAL_REVIEW",
    "HOLD_ACCEPTANCE",
    "HOLD_PAYMENT",
    "HOLD_WINDOW",
    "HOLD_EVIDENCE",
    "DNR",
}
AUTHORITY = {
    "external_send_authorized": False,
    "contract_or_signature_authorized": False,
    "buyer_acceptance_established": False,
    "renewal_or_expansion_approved": False,
    "invoice_or_payment_authorized": False,
    "cash_or_revenue_recognized": False,
    "deployment_authorized": False,
    "scheduling_authorized": False,
    "crm_mutation_authorized": False,
}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_INPUT_BYTES = 1_000_000
ALLOWED_EVIDENCE_KINDS = {
    "BASELINE_ACCEPTANCE",
    "CHANGE_ORDER_APPROVAL",
    "MILESTONE_ACCEPTANCE",
    "PAYMENT_SETTLED",
    "SUPPORT_FINDING",
    "GAP_STATUS",
    "RENEWAL_WINDOW",
    "DNR",
}
ALLOWED_EVIDENCE_STATUS = {"VERIFIED", "MISSING", "CONFLICTING", "PROVIDED_UNVERIFIED"}


class GateError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_constant(value: str) -> None:
    raise GateError(f"non-finite JSON number prohibited: {value}")


def _pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_loads(data: bytes) -> Any:
    if len(data) > MAX_INPUT_BYTES:
        raise GateError("input exceeds size limit")
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise GateError("input must be UTF-8") from exc
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_dupes, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise GateError(f"invalid JSON: {exc.msg}") from exc


def _read_regular(path: Path) -> bytes:
    st = path.lstat()
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise GateError(f"{path}: regular non-symlink file required")
    if st.st_size > MAX_INPUT_BYTES:
        raise GateError(f"{path}: file too large")
    with path.open("rb") as handle:
        data = handle.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise GateError(f"{path}: file too large")
    return data


def _dt(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{field}: non-empty timestamp required")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise GateError(f"{field}: invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise GateError(f"{field}: timezone required")
    return parsed.astimezone(timezone.utc)


def _z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _exact_keys(obj: dict[str, Any], allowed: set[str], where: str, required: set[str] | None = None) -> None:
    extra = set(obj) - allowed
    if extra:
        raise GateError(f"{where}: unknown field(s): {', '.join(sorted(extra))}")
    required = required or set()
    missing = required - set(obj)
    if missing:
        raise GateError(f"{where}: missing field(s): {', '.join(sorted(missing))}")


def _obj(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GateError(f"{where}: object required")
    return value


def _list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise GateError(f"{where}: list required")
    return value


def _str(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{where}: non-empty string required")
    return value.strip()


def _id(value: Any, where: str) -> str:
    value = _str(value, where)
    if not ID_RE.fullmatch(value):
        raise GateError(f"{where}: invalid identifier")
    return value


def _sha(value: Any, where: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise GateError(f"{where}: lowercase SHA-256 required")
    return value


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise GateError(f"{where}: boolean required")
    return value


def _int(value: Any, where: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise GateError(f"{where}: integer >= {minimum} required")
    return value


def _unique(values: list[str], where: str) -> None:
    if len(values) != len(set(values)):
        raise GateError(f"{where}: duplicate identifier")


def _parse_source(raw: Any, where: str) -> dict[str, Any]:
    obj = _obj(raw, where)
    allowed = {"id", "locator", "sha256", "observed_at"}
    _exact_keys(obj, allowed, where, allowed)
    source_id = _id(obj["id"], f"{where}.id")
    locator = _str(obj["locator"], f"{where}.locator")
    if not (locator.startswith("https://") or locator.startswith("repo://")):
        raise GateError(f"{where}.locator: https:// or repo:// required")
    if any(ch.isspace() for ch in locator):
        raise GateError(f"{where}.locator: whitespace prohibited")
    return {
        "id": source_id,
        "locator": locator,
        "sha256": _sha(obj["sha256"], f"{where}.sha256"),
        "observed_at": _z(_dt(obj["observed_at"], f"{where}.observed_at")),
    }

