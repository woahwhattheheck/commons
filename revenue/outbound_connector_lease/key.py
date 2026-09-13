#!/usr/bin/env python3
"""Canonical key compiler for connector-native outbound seam leases.

This module has no provider authority and performs no network calls.  It only
computes the deterministic GitHub branch name that a connector-capable worker
must attempt to create atomically before a net-new external outreach mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Any, Mapping, Sequence

SCHEMA = "outbound-connector-lease/v1"
BRANCH_PREFIX = "outbound-connector-lease/v1/"
COLD_SCOPE = "cold"
_OPPORTUNITY_RE = re.compile(r"^[a-z0-9][a-z0-9._:/+\-]{0,190}$")


class LeaseKeyError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise LeaseKeyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _parse_json(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                LeaseKeyError(f"non-finite JSON number: {token}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise LeaseKeyError("invalid JSON") from exc
    if type(value) is not dict:
        raise LeaseKeyError("input must be a JSON object")
    return value


def _normalize_domain(value: Any) -> str:
    if type(value) is not str:
        raise LeaseKeyError("buyer_scope must be a string")
    candidate = value.strip().rstrip(".").casefold()
    if not candidate or len(candidate) > 253:
        raise LeaseKeyError("buyer_scope must be a non-empty domain <= 253 chars")
    if "://" in candidate or any(ch in candidate for ch in "/@?#"):
        raise LeaseKeyError("buyer_scope must be an organization domain, not a URL/address")
    try:
        ascii_domain = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise LeaseKeyError("buyer_scope is not a valid IDNA domain") from exc
    labels = ascii_domain.split(".")
    if len(labels) < 2:
        raise LeaseKeyError("buyer_scope must contain a registrable-style dotted domain")
    for label in labels:
        if not label or len(label) > 63:
            raise LeaseKeyError("buyer_scope contains an invalid domain label")
        if label[0] == "-" or label[-1] == "-":
            raise LeaseKeyError("buyer_scope domain labels cannot start/end with '-'")
        if re.fullmatch(r"[a-z0-9-]+", label) is None:
            raise LeaseKeyError("buyer_scope contains invalid domain characters")
    return ascii_domain


def _normalize_opportunity(value: Any) -> str:
    if type(value) is not str:
        raise LeaseKeyError("opportunity_scope must be a string")
    token = value.strip().casefold()
    if not token or len(token) > 191 or _OPPORTUNITY_RE.fullmatch(token) is None:
        raise LeaseKeyError(
            "opportunity_scope must be 1..191 lowercase-token characters "
            "[a-z0-9._:/+-]"
        )
    return token


def compile_key(buyer_scope: Any, opportunity_scope: Any) -> dict[str, str]:
    buyer = _normalize_domain(buyer_scope)
    opportunity = _normalize_opportunity(opportunity_scope)
    seam = {
        "schema": SCHEMA,
        "buyer_scope": buyer,
        "opportunity_scope": opportunity,
    }
    canonical = json.dumps(
        seam,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    digest = hashlib.sha256(canonical).hexdigest()
    return {
        **seam,
        "seam_sha256": digest,
        "branch": BRANCH_PREFIX + digest,
    }


def compile_document(raw: Mapping[str, Any]) -> dict[str, str]:
    if type(raw) is not dict or set(raw) != {"schema", "buyer_scope", "opportunity_scope"}:
        raise LeaseKeyError("input requires exact schema,buyer_scope,opportunity_scope fields")
    if raw["schema"] != SCHEMA:
        raise LeaseKeyError(f"schema must be {SCHEMA}")
    return compile_key(raw["buyer_scope"], raw["opportunity_scope"])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a connector-native outbound seam branch")
    parser.add_argument("--buyer-scope", help="canonical organization primary domain")
    parser.add_argument("--opportunity-scope", help="stable opportunity id/token; use 'cold' for generic cold outreach")
    parser.add_argument("--json", dest="json_text", help="strict JSON input document")
    args = parser.parse_args(argv)
    try:
        if args.json_text is not None:
            if args.buyer_scope is not None or args.opportunity_scope is not None:
                raise LeaseKeyError("use either --json or the two scope flags")
            result = compile_document(_parse_json(args.json_text))
        else:
            if args.buyer_scope is None or args.opportunity_scope is None:
                raise LeaseKeyError("both --buyer-scope and --opportunity-scope are required")
            result = compile_key(args.buyer_scope, args.opportunity_scope)
    except LeaseKeyError as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
