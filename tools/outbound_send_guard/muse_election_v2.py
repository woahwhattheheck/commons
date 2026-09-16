#!/usr/bin/env python3
"""Canonical Muse election v2 with requester-control dominance.

The canonical v2 implementation is preserved byte-for-byte in the sibling
``_muse_election_v2_core`` module.  This carrier adds one strict requester-control
wire without widening positive authority: a control is valid only when it is an
exact full-line event, is authored by the exact request-event author, is bound to
the exact request/publication/candidate triple, and occurs after that request.
A valid control is terminal for that request id. Reopening requires a newly
prepared request with a fresh request id; silence or a later Muse SELECTED line
cannot reopen a controlled request.
"""
from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

if __package__:
    from . import _muse_election_v2_core as _core
else:  # Preserve direct ``python tools/.../muse_election_v2.py`` execution.
    _core_path = Path(__file__).with_name("_muse_election_v2_core.py")
    _spec = importlib.util.spec_from_file_location("_muse_election_v2_core", _core_path)
    if _spec is None or _spec.loader is None:
        raise RuntimeError("cannot load canonical Muse election v2 core")
    _core = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = _core
    _spec.loader.exec_module(_core)

# Preserve the canonical module surface, including the private helpers used by
# the existing exact-head tests.  Only compile_receipt/main are replaced below.
for _name in dir(_core):
    if _name in {"compile_receipt", "main"}:
        continue
    if _name.startswith("__") and _name.endswith("__"):
        continue
    globals()[_name] = getattr(_core, _name)

__doc__ = _core.__doc__

REQUESTER_CONTROL_ACTIONS = frozenset({"HOLD", "WITHDRAW", "CANCEL", "DO_NOT_SEND"})
REQUESTER_CONTROL_REOPEN_POLICY = "FRESH_REQUEST_ID_REQUIRED"
_REQUESTER_CONTROL_RE = re.compile(
    r"^REQUESTER_CONTROL (HOLD|WITHDRAW|CANCEL|DO_NOT_SEND) "
    r"([A-Za-z0-9][A-Za-z0-9._:-]{7,159}) "
    r"([0-9a-f]{64}) ([0-9a-f]{64})$"
)
_BASE_COMPILE_RECEIPT = _core.compile_receipt
_CLEAR_ON_CONTROL = (
    "selection_message_ts",
    "selected_at",
    "selection_binding_sha256",
    "winner_request_id",
    "winner_candidate_sha256",
    "winner_message_ts",
)


def requester_control_message(
    action: str,
    request_id: str,
    publication_key_sha256: str,
    candidate_sha256: str,
) -> str:
    """Return the only requester-control wire accepted by v2.

    Free-form prose, quoted examples, and bare words such as ``WITHDRAW`` or
    ``DO NOT SEND`` are deliberately not authority-bearing.  Reopening a valid
    control requires a fresh request id produced by ``prepare_request``.
    """
    if action not in REQUESTER_CONTROL_ACTIONS:
        raise MuseElectionV2Error("requester control action invalid")
    rid = _request_id(request_id, "requester_control.request_id")
    pub = _hex64(publication_key_sha256, "requester_control.publication_key")
    cand = _hex64(candidate_sha256, "requester_control.candidate_sha256")
    return f"REQUESTER_CONTROL {action} {rid} {pub} {cand}"


def _parse_requester_control(text: str) -> tuple[str, str, str, str] | None:
    if type(text) is not str:
        return None
    match = _REQUESTER_CONTROL_RE.fullmatch(text)
    if match is None:
        return None
    action, rid, pub, cand = match.groups()
    return action, rid, pub, cand


def _active_requester_controls(
    req: Mapping[str, Any],
    snap: Mapping[str, Any],
    request_message: str,
) -> list[tuple[dict[str, str], tuple[str, str, str, str]]]:
    """Find exact, same-author, post-request controls for this exact request."""
    request_matches = [msg for msg in snap["messages"] if msg["text"] == request_message]
    if len(request_matches) != 1:
        return []
    request_event = request_matches[0]
    request_author = request_event["author_user_id"]
    request_ts = _slack_dt(request_event["message_ts"], "request_message_ts")
    expected = (req["request_id"], req["publication_key"], req["candidate_sha256"])
    active: list[tuple[dict[str, str], tuple[str, str, str, str]]] = []
    for msg in snap["messages"]:
        parsed = _parse_requester_control(msg["text"])
        if parsed is None:
            continue
        action, rid, pub, cand = parsed
        if msg["author_user_id"] != request_author:
            continue
        if (rid, pub, cand) != expected:
            continue
        control_ts = _slack_dt(msg["message_ts"], "requester_control.message_ts")
        if control_ts <= request_ts:
            continue
        active.append((msg, (action, rid, pub, cand)))
    return sorted(
        active,
        key=lambda item: _slack_epoch(item[0]["message_ts"], "requester_control.message_ts"),
    )


def compile_receipt(
    request: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    observed_at: str,
    prior_receipts: Iterable[Mapping[str, Any]] = (),
    ledger_complete: bool,
) -> dict[str, Any]:
    """Compile canonical v2 evidence with terminal requester-control dominance."""
    req, _, request_message = _core._validate_request(request)
    snap = _core.normalize_snapshot(snapshot)
    controls = _active_requester_controls(req, snap, request_message)
    receipt = _BASE_COMPILE_RECEIPT(
        request,
        snapshot,
        observed_at=observed_at,
        prior_receipts=prior_receipts,
        ledger_complete=ledger_complete,
    )
    if not controls:
        return receipt

    payload = copy.deepcopy(receipt["payload"])
    payload["decision"] = "HOLD"
    reasons = list(payload.get("reasons", ()))
    for msg, parsed in controls:
        reasons.append(f"REQUESTER_CONTROL_ACTIVE:{parsed[0]}:{msg['message_ts']}")
    payload["reasons"] = sorted(set(reasons))
    for field in _CLEAR_ON_CONTROL:
        payload[field] = None
    controlled = {"payload": payload, "receipt_sha256": _core._digest(payload)}
    if not _core.verify_receipt(controlled):
        raise MuseElectionV2Error("requester-controlled receipt violates v2 receipt contract")
    return controlled


# Ensure the preserved canonical CLI calls the requester-control-aware compiler.
_core.compile_receipt = compile_receipt


def main(argv: list[str] | None = None) -> int:
    return _core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
