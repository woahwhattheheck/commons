#!/usr/bin/env python3
"""Canonical Muse publication-election v2 entrypoint.

The deterministic election compiler lives in ``_muse_election_v2_core``.  This
public boundary composes it with the fail-closed current-authority envelope.
Raw/caller-provided Slack snapshots are analysis evidence only: they may prove
HOLD or NOT_SELECTED, but cannot mint current SELECTED authority until a real
provider-authenticated adapter exists.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Iterable, Mapping

from tools.outbound_send_guard import _muse_election_v2_core as _core
from tools.outbound_send_guard import muse_current_authority_v2 as current_auth

_AUTHORITY_FIELDS = frozenset(
    {
        "authority_mode",
        "snapshot_authenticated",
        "snapshot_authentication_sha256",
        "valid_until",
        "request_context_sha256",
    }
)
_NEGATIVE_AUTHORITY_FIELDS = current_auth._SELECTION_FIELDS + current_auth._WINNER_FIELDS


def __getattr__(name: str) -> Any:
    """Preserve the existing module API while the core remains internal."""
    return getattr(_core, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_core)))


def _legacy_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(receipt["payload"])
    for name in _AUTHORITY_FIELDS:
        payload.pop(name, None)
    return {"payload": payload, "receipt_sha256": _core._digest(payload)}


def _legacy_prior_receipts(
    prior_receipts: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Project valid sealed v2 receipts back to the deterministic core ledger."""
    projected: list[Mapping[str, Any]] = []
    for prior in prior_receipts:
        if current_auth.verify_untrusted_snapshot_receipt(prior):
            projected.append(_legacy_projection(prior))
        else:
            projected.append(prior)
    return projected


def compile_receipt(
    request: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    prior_receipts: Iterable[Mapping[str, Any]] = (),
    ledger_complete: bool,
) -> dict[str, Any]:
    """Compile raw snapshot evidence with a verifier-owned clock, then seal it.

    There is intentionally no caller-controlled ``observed_at`` input.  The
    current raw-snapshot path is fail-closed: a deterministic-core SELECTED
    result is demoted by ``muse_current_authority_v2`` until an authenticated
    provider adapter is composed in a separate reviewed lane.
    """
    observed = current_auth._utc_now()
    raw = _core.compile_receipt(
        request,
        snapshot,
        observed_at=_core._fmt(observed),
        prior_receipts=_legacy_prior_receipts(prior_receipts),
        ledger_complete=ledger_complete,
    )

    # Negative receipts are coordination outcomes, not winner-authority
    # carriers.  Remove all authority-looking selection/winner metadata before
    # the current-authority envelope verifies them.
    if raw["payload"].get("decision") != "SELECTED":
        for name in _NEGATIVE_AUTHORITY_FIELDS:
            raw["payload"][name] = None
        raw["receipt_sha256"] = _core._digest(raw["payload"])

    return current_auth.seal_untrusted_snapshot_receipt(raw)


def verify_receipt(raw: Mapping[str, Any]) -> bool:
    """Verify both the current-authority envelope and deterministic core."""
    if not current_auth.verify_untrusted_snapshot_receipt(raw):
        return False
    try:
        return _core.verify_receipt(_legacy_projection(raw))
    except (KeyError, TypeError, ValueError):
        return False


def verify_selected_binding(
    request: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> bool:
    """Verify a selected binding.

    The unauthenticated-snapshot authority envelope intentionally rejects
    SELECTED, so this returns false until a separately reviewed authenticated
    adapter provides a positive authority mode.
    """
    if not verify_receipt(receipt):
        return False
    if receipt["payload"].get("decision") != "SELECTED":
        return False
    return _core.verify_selected_binding(request, _legacy_projection(receipt))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare")
    for name in (
        "buyer-scope-sha256",
        "recipient-fingerprint",
        "offer-scope-sha256",
        "intent-sha256",
        "body-sha256",
    ):
        prep.add_argument("--" + name, required=True)
    prep.add_argument("--route-kind", required=True)
    prep.add_argument("--claimant", required=True)
    prep.add_argument("--operation-id", required=True)
    prep.add_argument("--lease-binding", required=True)
    prep.add_argument("--request-id", required=True)
    prep.add_argument("--requested-at", required=True)

    comp = sub.add_parser("compile")
    comp.add_argument("--request", required=True)
    comp.add_argument("--snapshot", required=True)
    comp.add_argument("--prior-ledger")
    comp.add_argument("--ledger-complete", action="store_true")

    verify = sub.add_parser("verify")
    verify.add_argument("--receipt", required=True)
    verify.add_argument("--request")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            lease_binding = _core._read_json(args.lease_binding, "lease binding")
            candidate = {
                "buyer_scope_sha256": args.buyer_scope_sha256,
                "recipient_fingerprint": args.recipient_fingerprint,
                "offer_scope_sha256": args.offer_scope_sha256,
                "route_kind": args.route_kind,
                "intent_sha256": args.intent_sha256,
                "body_sha256": args.body_sha256,
                "claimant": args.claimant,
                "operation_id": args.operation_id,
                "lease_binding": lease_binding,
            }
            _core._write_json(
                _core.prepare_request(
                    candidate,
                    request_id=args.request_id,
                    requested_at=args.requested_at,
                )
            )
            return 0

        if args.command == "compile":
            request = _core._read_json(args.request, "request")
            snapshot = _core._read_json(args.snapshot, "snapshot")
            prior: list[Mapping[str, Any]] = []
            if args.prior_ledger:
                ledger = _core._read_json(args.prior_ledger, "prior ledger")
                if type(ledger) is not list:
                    raise _core.MuseElectionV2Error("prior ledger: array required")
                prior = ledger
            receipt = compile_receipt(
                request,
                snapshot,
                prior_receipts=prior,
                ledger_complete=args.ledger_complete,
            )
            _core._write_json(receipt)
            return {"SELECTED": 0, "NOT_SELECTED": 3, "HOLD": 4}[
                receipt["payload"]["decision"]
            ]

        receipt = _core._read_json(args.receipt, "receipt")
        ok = verify_receipt(receipt)
        if ok and args.request:
            ok = verify_selected_binding(
                _core._read_json(args.request, "request"),
                receipt,
            )
        _core._write_json({"valid": ok})
        return 0 if ok else 2
    except (_core.MuseElectionV2Error, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
