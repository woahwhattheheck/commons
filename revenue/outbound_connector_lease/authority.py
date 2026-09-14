#!/usr/bin/env python3
"""Fail-closed production admission for outbound mutual-exclusion seams.

The repository historically contains multiple outbound lease helpers.  Only the
closed-schema connector lease is a production mutual-exclusion prerequisite for
external sends.  This module deliberately does *not* authorize a provider send;
it validates that a caller is holding the one canonical seam identity that the
fleet must attempt to acquire atomically.

A legacy ``revenue/outbound_mutex`` document is never accepted here.  That
post-merge helper hashes caller free text (opportunity/channel/destination) and
can therefore split one commercial opportunity across aliases.  It remains
useful as local/reference CAS material, but not as production send clearance.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Mapping, Sequence

from revenue.outbound_connector_lease.key import (
    BRANCH_PREFIX,
    SCHEMA,
    LeaseKeyError,
    _parse_json,
    compile_key,
)

STATE = "CANONICAL_MUTEX_PREREQUISITE"
LEGACY_STATE = "HOLD_LEGACY_MUTEX_NONAUTHORITATIVE"


class SeamAuthorityError(ValueError):
    """Raised when a candidate cannot carry production mutex authority."""


def _is_plain_dict(value: Any) -> bool:
    return type(value) is dict


def _looks_like_legacy_mutex(value: Mapping[str, Any]) -> bool:
    """Recognize the #14266 free-form lease shape without trusting its fields."""
    keys = set(value)
    signature = {
        "version",
        "key",
        "opportunity",
        "channel",
        "destination_sha256",
        "holder",
        "state",
        "acquired_at",
        "expires_at",
        "provider_snapshot",
    }
    return signature.issubset(keys)


def admit_compiled_seam(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one exact compiled connector seam and return a non-send receipt.

    The input must be byte-semantically equivalent to ``compile_key`` output:
    no aliases, no extra recipient/price/route/draft fields, no caller-selected
    branch, and no legacy free-form lease document.
    """
    if not _is_plain_dict(value):
        raise SeamAuthorityError("candidate must be a plain JSON object")
    if _looks_like_legacy_mutex(value):
        raise SeamAuthorityError(
            "legacy revenue/outbound_mutex leases are non-authoritative for production sends"
        )

    required = {"schema", "buyer_scope", "opportunity", "seam_sha256", "branch"}
    if set(value) != required:
        raise SeamAuthorityError(
            "compiled seam requires exact schema,buyer_scope,opportunity,seam_sha256,branch fields"
        )
    if value.get("schema") != SCHEMA:
        raise SeamAuthorityError(f"schema must be {SCHEMA}")

    try:
        expected = compile_key(value["buyer_scope"], value["opportunity"])
    except LeaseKeyError as exc:
        raise SeamAuthorityError(str(exc)) from exc

    if dict(value) != expected:
        raise SeamAuthorityError("compiled seam does not match canonical recomputation")
    if not expected["branch"].startswith(BRANCH_PREFIX):
        raise SeamAuthorityError("canonical branch prefix mismatch")

    return {
        "state": STATE,
        "schema": SCHEMA,
        "buyer_scope": expected["buyer_scope"],
        "opportunity": expected["opportunity"],
        "seam_sha256": expected["seam_sha256"],
        "branch": expected["branch"],
        "atomic_branch_create_required": True,
        "provider_reread_required": True,
        "legacy_mutex_accepted": False,
        "external_send_authorized": False,
    }


def admit_json(raw: str) -> dict[str, Any]:
    try:
        parsed = _parse_json(raw)
    except LeaseKeyError as exc:
        raise SeamAuthorityError(str(exc)) from exc
    return admit_compiled_seam(parsed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Admit only the canonical connector-native outbound seam"
    )
    parser.add_argument("--json", required=True, help="compiled seam JSON from key.py")
    args = parser.parse_args(argv)
    try:
        receipt = admit_json(args.json)
    except SeamAuthorityError as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
