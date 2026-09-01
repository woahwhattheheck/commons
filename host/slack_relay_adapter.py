#!/usr/bin/env python3
"""Slack destination adapter for local uncredentialed bridges.

Local bridges (measured: Discord direct-root standby) can offer a payload
here when Slack is uncredentialed on that host. This module wires existing
roads; it does not remint them:

- ``ntfy_relays.relay_message`` for the identity-preserving envelope
- ``integrations.grok_slack.bridge.credential_presence`` / ``SECRET_ENV``
- ``integrations.gemini_slack.bridge`` doctor/serve env names (same tokens)

Test mode emits a synthetic end-to-end receipt with zero Slack or ntfy
sends. Credential absence fails closed with an explicit receipt, never a
silent skip. Token values are never copied into receipts, logs, or git.

  python3 host/slack_relay_adapter.py --self-test
  python3 host/slack_relay_adapter.py --mode test --offer offer.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ntfy_relays
from integrations.gemini_slack import bridge as gemini_slack_bridge
from integrations.grok_slack.bridge import SECRET_ENV, credential_presence


SCHEMA = "commons-slack-relay-adapter/v1"
SELF_TEST_SCHEMA = "commons-slack-relay-adapter-self-test/v1"
MODES = ("test", "live")
DEFAULT_CHANNEL = "C0BRGMDQB6G"
DEFAULT_SOURCE_HOST = "local-uncredentialed-bridge"
REUSED = (
    "ntfy_relays.py",
    "integrations/grok_slack/bridge.py",
    "integrations/gemini_slack/bridge.py",
)


class RelayAdapterError(ValueError):
    """The offer is invalid. No Slack or ntfy send is attempted."""


def _now_ts() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _text(value: object, at: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RelayAdapterError(f"{at} must be nonempty text")
    return value.strip()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def gemini_credential_presence(env: dict[str, str] | None = None) -> dict[str, str]:
    """Same present/missing names as ``integrations.gemini_slack.bridge.doctor``."""
    source = env if env is not None else os.environ
    return {
        name: ("present" if source.get(name) else "missing") for name in SECRET_ENV
    }


def inspect_credentials(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Compose grok_slack + gemini_slack presence. Values stay out of the receipt."""
    grok = credential_presence(env)
    gemini = gemini_credential_presence(env)
    missing = any(grok.get(name) == "missing" for name in SECRET_ENV)
    return {
        "credential_presence": dict(grok),
        "credential_sources": {
            "grok_slack": dict(grok),
            "gemini_slack": dict(gemini),
        },
        "credentials_missing": missing,
        "gemini_module": getattr(gemini_slack_bridge, "__name__", "integrations.gemini_slack.bridge"),
    }


def compose_envelope(offer: dict[str, Any]) -> str:
    """Preserve the caller id through the existing ntfy relay envelope. No remint."""
    post_id = _text(offer.get("id"), "offer.id")
    payload = offer.get("payload")
    if payload is None:
        payload = {"id": post_id, "body": str(offer.get("body") or "")}
    if not isinstance(payload, dict):
        raise RelayAdapterError("offer.payload must be an object")
    payload = dict(payload)
    payload.setdefault("id", post_id)
    source_host = str(offer.get("source_host") or DEFAULT_SOURCE_HOST)
    carrier_origin = str(offer.get("carrier_origin") or source_host)
    event = {
        "id": post_id,
        "payload": payload,
        "message": json.dumps(payload, ensure_ascii=False),
        "source_host": source_host,
        "carrier_origin": carrier_origin,
        "source_hosts": [source_host],
        "carrier_origins": [carrier_origin],
    }
    try:
        return ntfy_relays.relay_message(event)
    except ValueError as exc:
        raise RelayAdapterError(f"offer id does not match payload id: {exc}") from exc


def _receipt(
    *,
    ok: bool,
    state: str,
    mode: str,
    offer_id: str,
    observed_at: str,
    creds: dict[str, Any],
    envelope: str,
    channel: str,
    note: str,
    network_calls: int = 0,
    transport_state: str = "",
) -> dict[str, Any]:
    parsed = json.loads(envelope) if envelope else {}
    return {
        "schema": SCHEMA,
        "ok": ok,
        "state": state,
        "mode": mode,
        "offer_id": offer_id,
        "observed_at": observed_at,
        "channel": channel,
        "network_calls": network_calls,
        "real_slack_send": False,
        "silent_skip": False,
        "credential_presence": creds["credential_presence"],
        "credential_sources": creds["credential_sources"],
        "credentials_missing": creds["credentials_missing"],
        "reused": list(REUSED),
        "envelope": parsed,
        "envelope_sha256": _sha256_text(envelope) if envelope else "",
        "transport_state": transport_state,
        "note": note,
    }


def deliver(
    offer: dict[str, Any],
    *,
    mode: str = "live",
    env: dict[str, str] | None = None,
    transport: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Attempt Slack destination delivery. Never silently skip.

    ``mode="test"`` returns a synthetic receipt and never calls a transport.
    ``mode="live"`` with missing Slack credentials fails closed. Live mode
    still refuses a real Slack Web API / Socket Mode session unless a test
    injects ``transport``.
    """
    if mode not in MODES:
        raise RelayAdapterError(f"unknown mode: {mode!r}")
    if not isinstance(offer, dict):
        raise RelayAdapterError("offer must be an object")

    envelope = compose_envelope(offer)
    offer_id = _text(offer.get("id"), "offer.id")
    channel = str(offer.get("channel") or DEFAULT_CHANNEL)
    stamp = observed_at or _now_ts()
    creds = inspect_credentials(env)

    if mode == "test":
        return _receipt(
            ok=True,
            state="SYNTHETIC_DELIVERED",
            mode=mode,
            offer_id=offer_id,
            observed_at=stamp,
            creds=creds,
            envelope=envelope,
            channel=channel,
            note=(
                "Test mode. Synthetic Slack destination receipt. "
                "Zero Slack or ntfy sends. Existing relay/integrations wired, not reminted."
            ),
        )

    if creds["credentials_missing"]:
        return _receipt(
            ok=False,
            state="CREDENTIAL_ABSENT",
            mode=mode,
            offer_id=offer_id,
            observed_at=stamp,
            creds=creds,
            envelope=envelope,
            channel=channel,
            note=(
                "Slack credentials missing on this host. Fail closed. "
                "Zero Slack calls. Not a silent skip. "
                "Local uncredentialed bridges keep the explicit receipt."
            ),
        )

    if transport is None:
        return _receipt(
            ok=False,
            state="TRANSPORT_NOT_INJECTED",
            mode=mode,
            offer_id=offer_id,
            observed_at=stamp,
            creds=creds,
            envelope=envelope,
            channel=channel,
            note=(
                "Credentials present. Refusing to open a live Slack Web API "
                "or Socket Mode session from this adapter. Inject transport in tests only."
            ),
        )

    result = transport({
        "channel": channel,
        "offer_id": offer_id,
        "envelope": json.loads(envelope),
        "mode": mode,
    })
    if not isinstance(result, dict):
        result = {"state": "TRANSPORT_INVALID"}
    return _receipt(
        ok=bool(result.get("ok")),
        state=str(result.get("state") or "INJECTED_TRANSPORT"),
        mode=mode,
        offer_id=offer_id,
        observed_at=stamp,
        creds=creds,
        envelope=envelope,
        channel=channel,
        network_calls=1,
        transport_state=str(result.get("state") or ""),
        note="Injected transport only. Token values are not logged. No Slack client opened here.",
    )


def canonical(receipt: object) -> bytes:
    return (json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def self_test() -> dict[str, Any]:
    offer = {
        "id": "caliper-slack-relay-adapter-self-test-01",
        "body": "synthetic slack destination",
        "source_host": "local-uncredentialed-bridge",
    }
    stamp = "2026-09-01T00:00:00Z"
    first = canonical(deliver(offer, mode="test", env={}, observed_at=stamp))
    second = canonical(deliver(offer, mode="test", env={}, observed_at=stamp))
    if first != second:
        raise AssertionError("synthetic test-mode receipt was not byte-identical")
    synthetic = json.loads(first)
    if synthetic["state"] != "SYNTHETIC_DELIVERED" or synthetic["real_slack_send"] or synthetic["silent_skip"]:
        raise AssertionError("test-mode receipt was not a synthetic fail-visible delivery")
    absent = deliver(offer, mode="live", env={}, observed_at=stamp)
    if absent["state"] != "CREDENTIAL_ABSENT" or absent["ok"] or absent["silent_skip"]:
        raise AssertionError("credential absence did not fail closed with an explicit receipt")
    blob = json.dumps(synthetic) + json.dumps(absent)
    if "xoxb" in blob.lower() or "xapp" in blob.lower():
        raise AssertionError("receipt leaked a Slack token prefix")
    return {"schema": SELF_TEST_SCHEMA, "status": "PASS", "checks": 4}


def _load_offer(path: str) -> dict[str, Any]:
    raw = json.load(sys.stdin) if path == "-" else json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RelayAdapterError("offer JSON must be an object")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, default="test")
    parser.add_argument("--offer", default="-", help="offer JSON path (default: stdin)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = self_test() if args.self_test else deliver(_load_offer(args.offer), mode=args.mode, env=None)
    except (OSError, json.JSONDecodeError, RelayAdapterError, AssertionError) as exc:
        print(f"slack-relay-adapter: {exc}", file=sys.stderr)
        return 2
    blob = canonical(result)
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(blob)
    else:
        sys.stdout.write(blob.decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
