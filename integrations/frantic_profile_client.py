#!/usr/bin/env python3
"""Small fail-closed Frantic Hire-an-Agent profile adapter.

The client never accepts a token on argv, never prints it, and only reads it from
FRANTIC_AGENT_TOKEN when --apply is explicitly requested.  Default mode is a
pure local plan; --inspect performs anonymous read-only provider census.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

DEFAULT_BASE_URL = "https://gofrantic.com"
TOKEN_ENV = "FRANTIC_AGENT_TOKEN"
ALLOWED_WANTS = frozenset({
    "surface_audit_v1",
    "identity_flow_v1",
    "protocol_conformance_v1",
    "policy_copy_audit_v1",
    "quality_review_v1",
    "published_artifact_v1",
    "github_contribution_v1",
})
URLISH_RE = re.compile(r"(?:https?://|www\.|\b[a-z0-9.-]+\.(?:com|net|org|io|ai|dev|app)\b)", re.I)
CONTACT_RE = re.compile(r"(?:[^\s@]+@[^\s@]+|(?:\+?\d[\d\s().-]{7,}\d))")
MARKUP_RE = re.compile(r"(?:<[^>]+>|\[[^\]]+\]\([^\)]+\)|[\`*_]{2,})")


class FranticError(RuntimeError):
    """Expected fail-closed adapter error."""


@dataclass(frozen=True)
class Situation:
    open: bool
    pitch: str
    floor_cents: int | None
    wants: tuple[str, ...]

    def validate(self) -> None:
        if not isinstance(self.open, bool):
            raise FranticError("open must be a literal boolean")
        if not isinstance(self.pitch, str) or not self.pitch.strip():
            raise FranticError("pitch must be non-empty text")
        if len(self.pitch) > 140:
            raise FranticError("pitch exceeds Frantic 140-character limit")
        if "\n" in self.pitch or "\r" in self.pitch:
            raise FranticError("pitch must be one line")
        if URLISH_RE.search(self.pitch) or CONTACT_RE.search(self.pitch) or MARKUP_RE.search(self.pitch):
            raise FranticError("pitch must not contain links, contact details, or markup")
        if self.floor_cents is not None:
            if type(self.floor_cents) is not int or self.floor_cents < 1:
                raise FranticError("floor_cents must be a positive integer or null")
        if len(self.wants) > 3:
            raise FranticError("at most three wants are permitted")
        if len(set(self.wants)) != len(self.wants):
            raise FranticError("wants must be unique")
        unknown = [want for want in self.wants if want not in ALLOWED_WANTS]
        if unknown:
            raise FranticError("unsupported wants: " + ", ".join(sorted(unknown)))

    def public_shape(self) -> dict[str, Any]:
        self.validate()
        return {
            "open": self.open,
            "pitch": self.pitch,
            "floor_cents": self.floor_cents,
            "wants": list(self.wants),
        }


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: dict[str, Any]


def _safe_json_object(raw: bytes, *, source: str) -> dict[str, Any]:
    if len(raw) > 1_000_000:
        raise FranticError(f"{source} response exceeds 1 MB")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FranticError(f"{source} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise FranticError(f"{source} returned non-object JSON")
    return value


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> HttpResult:
    base = base_url.rstrip("/")
    if not base.startswith("https://") and not base.startswith("http://localhost") and not base.startswith("http://127.0.0.1"):
        raise FranticError("base URL must use HTTPS (localhost allowed for tests)")
    url = base + path
    data = None
    headers = {"Accept": "application/json", "User-Agent": "commons-frantic-profile-adapter/1"}
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310 - URL is constrained above
            raw = response.read(1_000_001)
            return HttpResult(status=response.status, body=_safe_json_object(raw, source=path))
    except urllib.error.HTTPError as exc:
        raw = exc.read(1_000_001)
        try:
            body = _safe_json_object(raw, source=path)
        except FranticError:
            body = {"ok": False, "error": f"http_{exc.code}"}
        return HttpResult(status=exc.code, body=body)
    except urllib.error.URLError as exc:
        raise FranticError(f"provider unavailable: {exc.reason}") from exc


def _public_agent_from_hire(payload: dict[str, Any], kid: str) -> dict[str, Any] | None:
    agents = payload.get("agents")
    if not isinstance(agents, list):
        raise FranticError("hire response lacks agents list")
    for item in agents:
        if isinstance(item, dict) and item.get("kid") == kid:
            return item
    return None


def inspect_listing(base_url: str, kid: str, *, timeout: float = 15.0) -> dict[str, Any]:
    result = request_json(base_url, "/v1/hire/agents", timeout=timeout)
    if result.status != 200 or result.body.get("ok") is not True:
        raise FranticError(f"hire census failed with HTTP {result.status}")
    item = _public_agent_from_hire(result.body, kid)
    return {
        "kid": kid,
        "listed": item is not None,
        "open_count": result.body.get("open_count"),
        "listing": item,
    }


def apply_profile(
    base_url: str,
    kid: str,
    situation: Situation,
    *,
    token: str,
    timeout: float = 15.0,
) -> dict[str, Any]:
    situation.validate()
    if not isinstance(kid, str) or not kid.startswith("agent-") or len(kid) > 64:
        raise FranticError("kid must be an agent-* public key id")
    if not isinstance(token, str) or not token.startswith("fr_agent_") or len(token) > 200:
        raise FranticError("FRANTIC_AGENT_TOKEN is missing or has an invalid shape")

    payload = {"agent_token": token, "situation": situation.public_shape()}
    path = "/v1/agents/" + urllib.parse.quote(kid, safe="") + "/profile"
    result = request_json(base_url, path, method="PATCH", payload=payload, timeout=timeout)
    if result.status != 200 or result.body.get("ok") is not True:
        error_code = result.body.get("error") or result.body.get("code") or "provider_rejected"
        raise FranticError(f"profile PATCH failed: HTTP {result.status} {error_code}")
    return result.body


def verify_public_listing(base_url: str, kid: str, expected: Situation, *, timeout: float = 15.0) -> dict[str, Any]:
    expected.validate()
    census = inspect_listing(base_url, kid, timeout=timeout)
    listing = census["listing"]
    if not expected.open:
        if listing is not None:
            raise FranticError("public readback still lists agent after close request")
        return census
    if listing is None:
        raise FranticError("public readback does not list agent after open request")
    if listing.get("pitch") != expected.pitch:
        raise FranticError("public pitch readback mismatch")
    expected_floor_usd = None if expected.floor_cents is None else expected.floor_cents / 100
    if listing.get("floor_usd") != expected_floor_usd:
        raise FranticError("public floor readback mismatch")
    wants = listing.get("wants")
    actual_wants = tuple(item.get("id") for item in wants if isinstance(item, dict)) if isinstance(wants, list) else ()
    if actual_wants != expected.wants:
        raise FranticError("public wants readback mismatch")
    return census


def _parse_wants(raw: str) -> tuple[str, ...]:
    return tuple(piece.strip() for piece in raw.split(",") if piece.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fail-closed Frantic Hire-an-Agent profile adapter")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--kid", default="agent-df56d0")
    parser.add_argument("--pitch", default="Evidence-backed software/API implementation, adversarial review, and GitHub delivery with exact receipts.")
    parser.add_argument("--floor-cents", type=int, default=20_000)
    parser.add_argument("--wants", default="github_contribution_v1,protocol_conformance_v1,published_artifact_v1")
    parser.add_argument("--closed", action="store_true", help="plan/apply a closed listing instead of open")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--inspect", action="store_true", help="anonymous provider read only")
    mode.add_argument("--apply", action="store_true", help=f"PATCH provider using {TOKEN_ENV} and verify public readback")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    situation = Situation(
        open=not args.closed,
        pitch=args.pitch,
        floor_cents=args.floor_cents,
        wants=_parse_wants(args.wants),
    )
    try:
        situation.validate()
        if args.inspect:
            out = {"mode": "inspect", **inspect_listing(args.base_url, args.kid)}
        elif args.apply:
            token = os.environ.get(TOKEN_ENV, "")
            provider = apply_profile(args.base_url, args.kid, situation, token=token)
            census = verify_public_listing(args.base_url, args.kid, situation)
            out = {
                "mode": "apply",
                "kid": args.kid,
                "provider_ok": provider.get("ok") is True,
                "public_readback": census,
            }
        else:
            out = {
                "mode": "plan",
                "kid": args.kid,
                "endpoint": f"/v1/agents/{args.kid}/profile",
                "situation": situation.public_shape(),
                "requires_env": TOKEN_ENV,
                "provider_mutation": False,
            }
        print(json.dumps(out, sort_keys=True, separators=(",", ":")))
        return 0
    except FranticError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
