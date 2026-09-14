#!/usr/bin/env python3
"""Fail-closed admission for one canonical outbound opportunity/reply seam.

This module intentionally does not claim organization-wide mutual exclusion.
The connector seam serializes one closed-schema opportunity/reply identity. A
production send may additionally require an independently authoritative
organization scope plus an organization-wide atomic pressure/mutex layer.

A legacy ``revenue/outbound_mutex`` document is never accepted here. That helper
hashes caller free text (opportunity/channel/destination) and can split one
commercial opportunity across aliases. It remains historical/reference CAS
material, not canonical opportunity/reply seam authority.
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

STATE = "CANONICAL_OPPORTUNITY_SEAM_PREREQUISITE"


class SeamAuthorityError(ValueError):
    """Raised when a candidate cannot carry canonical opportunity-seam authority."""


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
    """Validate one exact connector opportunity/reply seam.

    The input must be byte-semantically equivalent to ``compile_key`` output:
    no price/recipient/route/draft aliases, no caller-selected branch, and no
    legacy free-form lease document.

    A successful receipt is deliberately incomplete for production mutation:
    ``key.py`` normalizes syntax but does not prove organization alias identity,
    and distinct cold/external/reply opportunities intentionally compile to
    distinct branches. Callers must not represent this receipt as an
    organization-wide or sole production mutex.
    """
    if not _is_plain_dict(value):
        raise SeamAuthorityError("candidate must be a plain JSON object")
    if _looks_like_legacy_mutex(value):
        raise SeamAuthorityError(
            "legacy revenue/outbound_mutex leases are non-authoritative for canonical opportunity seams"
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
        "organization_scope_authority_required": True,
        "organization_wide_mutex_required": True,
        "production_mutex_complete": False,
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
        description="Validate one canonical connector opportunity/reply seam; never production-ready alone"
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
