#!/usr/bin/env python3
"""Canonical key compiler for connector-native outbound seam leases.

This module has no provider authority and performs no network calls. It only
computes the deterministic GitHub branch name that a connector-capable worker
must attempt to create atomically before an external outreach mutation.
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
REPLY_SCHEMA = "outbound-connector-reply-lease/v2"
REPLY_BRANCH_PREFIX = "outbound-connector-reply-lease/v2/"
_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._:/+\-]{0,190}$")
_PROVIDER_RE = re.compile(r"^[a-z0-9][a-z0-9._+\-]{0,63}$")


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


def _normalize_domain(value: Any, field: str) -> str:
    if type(value) is not str:
        raise LeaseKeyError(f"{field} must be a string")
    candidate = value.strip().rstrip(".").casefold()
    if not candidate or len(candidate) > 253:
        raise LeaseKeyError(f"{field} must be a non-empty domain <= 253 chars")
    if "://" in candidate or any(ch in candidate for ch in "/@?#"):
        raise LeaseKeyError(f"{field} must be an organization domain, not a URL/address")
    try:
        ascii_domain = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise LeaseKeyError(f"{field} is not a valid IDNA domain") from exc
    labels = ascii_domain.split(".")
    if len(labels) < 2:
        raise LeaseKeyError(f"{field} must contain a registrable-style dotted domain")
    for label in labels:
        if not label or len(label) > 63:
            raise LeaseKeyError(f"{field} contains an invalid domain label")
        if label[0] == "-" or label[-1] == "-":
            raise LeaseKeyError(f"{field} domain labels cannot start/end with '-'")
        if re.fullmatch(r"[a-z0-9-]+", label) is None:
            raise LeaseKeyError(f"{field} contains invalid domain characters")
    return ascii_domain


def _machine_token(value: Any, field: str) -> str:
    if type(value) is not str:
        raise LeaseKeyError(f"{field} must be a string")
    token = value.strip().casefold()
    if not token or len(token) > 191 or _TOKEN_RE.fullmatch(token) is None:
        raise LeaseKeyError(f"{field} must use 1..191 lowercase-token chars [a-z0-9._:/+-]")
    return token


def _provider_token(value: Any, field: str) -> str:
    if type(value) is not str:
        raise LeaseKeyError(f"{field} must be a string")
    token = value.strip().casefold()
    if not token or _PROVIDER_RE.fullmatch(token) is None:
        raise LeaseKeyError(f"{field} must be a short lowercase provider token")
    return token


def _normalize_opportunity(raw: Any) -> dict[str, str]:
    if type(raw) is not dict:
        raise LeaseKeyError("opportunity must be an object")
    kind = raw.get("kind")
    if type(kind) is not str:
        raise LeaseKeyError("opportunity.kind must be a string")
    kind = kind.strip().casefold()
    if kind == "cold":
        if set(raw) != {"kind"}:
            raise LeaseKeyError("cold opportunity requires exact field: kind")
        return {"kind": "cold"}
    if kind == "external":
        if set(raw) != {"kind", "authority", "id"}:
            raise LeaseKeyError("external opportunity requires exact fields: kind,authority,id")
        return {
            "kind": "external",
            "authority": _normalize_domain(raw["authority"], "opportunity.authority"),
            "id": _machine_token(raw["id"], "opportunity.id"),
        }
    if kind == "reply":
        if set(raw) != {"kind", "provider", "event_id"}:
            raise LeaseKeyError("reply opportunity requires exact fields: kind,provider,event_id")
        return {
            "kind": "reply",
            "provider": _provider_token(raw["provider"], "opportunity.provider"),
            "event_id": _machine_token(raw["event_id"], "opportunity.event_id"),
        }
    raise LeaseKeyError("opportunity.kind must be one of: cold, external, reply")


def _compile_seam(seam: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    canonical = json.dumps(
        seam,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    digest = hashlib.sha256(canonical).hexdigest()
    return {**seam, "seam_sha256": digest, "branch": prefix + digest}


def compile_reply_key(provider: Any, event_id: Any) -> dict[str, Any]:
    """Compile one global mutex for one durable inbound provider event.

    Reply identity deliberately excludes buyer/contact/domain classification. The
    provider plus exact durable event ID already names the event that may be
    answered once; adding caller-classified organization data would let parallel
    workers mint distinct locks for the same human message.
    """
    seam = {
        "schema": REPLY_SCHEMA,
        "provider": _provider_token(provider, "provider"),
        "event_id": _machine_token(event_id, "event_id"),
    }
    return _compile_seam(seam, REPLY_BRANCH_PREFIX)


def compile_key(buyer_scope: Any, opportunity: Any) -> dict[str, Any]:
    buyer = _normalize_domain(buyer_scope, "buyer_scope")
    normalized_opportunity = _normalize_opportunity(opportunity)
    if normalized_opportunity["kind"] == "reply":
        return compile_reply_key(
            normalized_opportunity["provider"], normalized_opportunity["event_id"]
        )
    seam = {
        "schema": SCHEMA,
        "buyer_scope": buyer,
        "opportunity": normalized_opportunity,
    }
    return _compile_seam(seam, BRANCH_PREFIX)


def compile_document(raw: Mapping[str, Any]) -> dict[str, Any]:
    if type(raw) is not dict:
        raise LeaseKeyError("input must be an object")
    schema = raw.get("schema")
    if schema == SCHEMA:
        if set(raw) != {"schema", "buyer_scope", "opportunity"}:
            raise LeaseKeyError("v1 input requires exact schema,buyer_scope,opportunity fields")
        return compile_key(raw["buyer_scope"], raw["opportunity"])
    if schema == REPLY_SCHEMA:
        if set(raw) != {"schema", "provider", "event_id"}:
            raise LeaseKeyError("reply-v2 input requires exact schema,provider,event_id fields")
        return compile_reply_key(raw["provider"], raw["event_id"])
    raise LeaseKeyError(f"schema must be {SCHEMA} or {REPLY_SCHEMA}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a connector-native outbound seam branch")
    parser.add_argument("--buyer-scope", help="canonical organization primary domain (cold/external only)")
    parser.add_argument("--cold", action="store_true", help="one organization-level unsolicited outreach seam")
    parser.add_argument("--external-authority", help="domain of authoritative opportunity issuer/source")
    parser.add_argument("--external-id", help="stable external procurement/project/issue ID")
    parser.add_argument("--reply-provider", help="provider token for one inbound reply event")
    parser.add_argument("--reply-event-id", help="durable provider inbound message/event ID")
    parser.add_argument("--json", dest="json_text", help="strict JSON input document")
    args = parser.parse_args(argv)
    try:
        if args.json_text is not None:
            if any((args.buyer_scope, args.cold, args.external_authority, args.external_id, args.reply_provider, args.reply_event_id)):
                raise LeaseKeyError("use either --json or scope flags")
            result = compile_document(_parse_json(args.json_text))
        else:
            external_mode = args.external_authority is not None or args.external_id is not None
            reply_mode = args.reply_provider is not None or args.reply_event_id is not None
            modes = int(args.cold) + int(external_mode) + int(reply_mode)
            if modes != 1:
                raise LeaseKeyError("choose exactly one opportunity mode: --cold, external pair, or reply pair")
            if reply_mode:
                if args.buyer_scope is not None:
                    raise LeaseKeyError("--buyer-scope is forbidden for reply mode; provider event identity is global")
                if args.reply_provider is None or args.reply_event_id is None:
                    raise LeaseKeyError("reply mode requires --reply-provider and --reply-event-id")
                result = compile_reply_key(args.reply_provider, args.reply_event_id)
            else:
                if args.buyer_scope is None:
                    raise LeaseKeyError("--buyer-scope is required for cold/external mode")
                if args.cold:
                    opportunity = {"kind": "cold"}
                else:
                    if args.external_authority is None or args.external_id is None:
                        raise LeaseKeyError("external mode requires --external-authority and --external-id")
                    opportunity = {"kind": "external", "authority": args.external_authority, "id": args.external_id}
                result = compile_key(args.buyer_scope, opportunity)
    except LeaseKeyError as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())