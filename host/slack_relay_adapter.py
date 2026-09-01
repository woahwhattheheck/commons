#!/usr/bin/env python3
"""Slack destination adapter for local bridges that have no Slack credentials.

Composes the existing relay / integration pattern. Does not remint:

- ``ntfy_relays.py`` (origin-preserving payload, refuse inconsistent ids)
- ``integrations/grok_slack`` (``SECRET_ENV``, ``credential_presence``, table)
- ``integrations/gemini_slack`` (same ``SLACK_BOT_TOKEN`` / ``SLACK_APP_TOKEN``)

Test mode returns a synthetic receipt end-to-end with zero network and zero
real Slack sends. Live mode with missing credentials fails closed with an
explicit receipt. That is never a silent skip (``host/slack_mirror.py`` DARK
exit-0 is a different lane and is not reused here).

This module does not call Slack HTTP, does not open Socket Mode,
and never writes tokens. A live send happens only through an injected
transport, which tests replace with a recorder.
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
from integrations.grok_slack.bridge import (
    DEFAULT_CHANNEL,
    SECRET_ENV,
    credential_presence,
)

RECEIPT_SCHEMA = "commons-slack-relay-receipt/v1"
ADAPTER_PATH = "host/slack_relay_adapter.py"
WIRED_PATHS = (
    "ntfy_relays.py",
    "integrations/grok_slack/bridge.py",
    "integrations/gemini_slack/bridge.py",
)
MODES = ("test", "live")
SYNTHETIC_STATE = "SYNTHETIC_DELIVERED"
ABSENT_STATE = "RUNTIME_UNCONFIGURED"
UNINJECTED_STATE = "LIVE_TRANSPORT_UNINJECTED"
INVALID_EVENT_STATE = "INVALID_EVENT"
INVALID_MODE_STATE = "INVALID_MODE"
TRANSPORT_REJECTED_STATE = "TRANSPORT_REJECTED"
TRANSPORT_ERROR_STATE = "TRANSPORT_ERROR"
GEMINI_SECRET_ENV = SECRET_ENV
SELF_TEST_EVENT = {
    "id": "caliper-slack-relay-adapter-01",
    "text": "synthetic Slack destination ping",
    "source_host": "local-uncredentialed",
    "carrier_origin": "local-uncredentialed",
    "channel": DEFAULT_CHANNEL,
}


class SlackRelayAdapterError(ValueError):
    """The event cannot be delivered; callers still receive a receipt."""


Transport = Callable[[dict[str, Any]], dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _synthetic_ts(event_id: str) -> str:
    digest = hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:10]
    return f"synthetic.{digest}"


def _presence(env: dict[str, str] | None) -> dict[str, str]:
    """Reuse grok_slack presence, treating blank/whitespace tokens as missing."""
    presence = credential_presence(env)
    source = env if env is not None else os.environ
    for name in SECRET_ENV:
        if not str(source.get(name) or "").strip():
            presence[name] = "missing"
    return presence


def _missing_credentials(presence: dict[str, str]) -> list[str]:
    return [name for name in SECRET_ENV if presence.get(name) != "present"]


def _origin(event: dict[str, Any]) -> tuple[str, str]:
    source_host = ntfy_relays._host(
        event.get("source_host") or event.get("host") or "local-uncredentialed"
    )
    carrier_origin = ntfy_relays._host(event.get("carrier_origin") or source_host)
    return source_host, carrier_origin


def _compose_text(event: dict[str, Any], event_id: str, source_host: str, carrier_origin: str) -> str:
    text = event.get("text")
    if isinstance(text, str) and text.strip():
        return text
    payload = event.get("payload")
    if not isinstance(payload, dict) and event.get("message"):
        try:
            candidate = json.loads(event.get("message") or "")
        except (json.JSONDecodeError, TypeError):
            candidate = None
        if isinstance(candidate, dict):
            payload = candidate
    if not isinstance(payload, dict):
        raise SlackRelayAdapterError("event has no text or relay payload")
    row = {
        "id": event_id,
        "payload": payload,
        "message": event.get("message") or "",
        "source_host": source_host,
        "host": source_host,
        "carrier_origin": carrier_origin,
        "source_hosts": event.get("source_hosts") or [source_host],
        "carrier_origins": event.get("carrier_origins") or [carrier_origin],
    }
    try:
        return ntfy_relays.relay_message(row)
    except ValueError as exc:
        raise SlackRelayAdapterError(str(exc)) from exc


def normalize_event(event: object) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise SlackRelayAdapterError("event must be an object")
    event_id = event.get("id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise SlackRelayAdapterError("event id must be nonempty text")
    event_id = event_id.strip()
    source_host, carrier_origin = _origin(event)
    channel = str(event.get("channel") or DEFAULT_CHANNEL).strip() or DEFAULT_CHANNEL
    thread_ts = str(event.get("thread_ts") or "").strip()
    text = _compose_text(event, event_id, source_host, carrier_origin)
    return {
        "id": event_id,
        "text": text,
        "source_host": source_host,
        "carrier_origin": carrier_origin,
        "channel": channel,
        "thread_ts": thread_ts,
    }


def _receipt(
    *,
    normalized: dict[str, Any] | None,
    mode: str,
    presence: dict[str, str],
    state: str,
    ok: bool,
    reason: str,
    fail_closed: bool,
    network_calls: int,
    slack_ts: str,
    observed_at: str,
    transport_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "schema": RECEIPT_SCHEMA,
        "adapter": ADAPTER_PATH,
        "wired": list(WIRED_PATHS),
        "mode": mode,
        "ok": ok,
        "state": state,
        "reason": reason,
        "fail_closed": fail_closed,
        "silent_skip": False,
        "id": (normalized or {}).get("id") or "",
        "channel": (normalized or {}).get("channel") or DEFAULT_CHANNEL,
        "thread_ts": (normalized or {}).get("thread_ts") or "",
        "source_host": (normalized or {}).get("source_host") or "",
        "carrier_origin": (normalized or {}).get("carrier_origin") or "",
        "credential_presence": dict(presence),
        "credential_env": list(SECRET_ENV),
        "gemini_slack_env": list(GEMINI_SECRET_ENV),
        "network_calls": network_calls,
        "real_send": False,
        "slack_ts": slack_ts,
        "observed_at": observed_at,
        "missing_credentials": _missing_credentials(presence),
    }
    if transport_result is not None:
        row["transport_ok"] = bool(transport_result.get("ok"))
    return row


def deliver(
    event: object,
    *,
    mode: str = "test",
    env: dict[str, str] | None = None,
    transport: Transport | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Deliver one Slack destination event. Always returns an explicit receipt."""
    observed_at = now or _utc_now()
    presence = _presence(env)
    requested_mode = str(mode or "").strip().lower()
    if requested_mode not in MODES:
        return _receipt(
            normalized=None,
            mode=requested_mode,
            presence=presence,
            state=INVALID_MODE_STATE,
            ok=False,
            reason="mode must be test or live; fail closed; not a silent skip",
            fail_closed=True,
            network_calls=0,
            slack_ts="",
            observed_at=observed_at,
        )
    try:
        normalized = normalize_event(event)
    except SlackRelayAdapterError as exc:
        return _receipt(
            normalized=None,
            mode=requested_mode,
            presence=presence,
            state=INVALID_EVENT_STATE,
            ok=False,
            reason=f"{exc}; fail closed; not a silent skip",
            fail_closed=True,
            network_calls=0,
            slack_ts="",
            observed_at=observed_at,
        )

    if requested_mode == "test":
        return _receipt(
            normalized=normalized,
            mode="test",
            presence=presence,
            state=SYNTHETIC_STATE,
            ok=True,
            reason="test mode: synthetic Slack destination receipt; zero real sends",
            fail_closed=False,
            network_calls=0,
            slack_ts=_synthetic_ts(normalized["id"]),
            observed_at=observed_at,
        )

    missing = _missing_credentials(presence)
    if missing:
        return _receipt(
            normalized=normalized,
            mode="live",
            presence=presence,
            state=ABSENT_STATE,
            ok=False,
            reason=(
                "Slack credentials missing ("
                + ", ".join(missing)
                + "). Fail closed. Zero Slack calls. Not a silent skip."
            ),
            fail_closed=True,
            network_calls=0,
            slack_ts="",
            observed_at=observed_at,
        )

    if transport is None:
        return _receipt(
            normalized=normalized,
            mode="live",
            presence=presence,
            state=UNINJECTED_STATE,
            ok=False,
            reason=(
                "credentials present but no transport injected; refusing chat.postMessage "
                "and Socket Mode. Fail closed. Not a silent skip."
            ),
            fail_closed=True,
            network_calls=0,
            slack_ts="",
            observed_at=observed_at,
        )

    payload = {
        "id": normalized["id"],
        "channel": normalized["channel"],
        "text": normalized["text"],
        "thread_ts": normalized["thread_ts"],
    }
    try:
        result = transport(payload)
    except Exception as exc:
        return _receipt(
            normalized=normalized,
            mode="live",
            presence=presence,
            state=TRANSPORT_ERROR_STATE,
            ok=False,
            reason=f"injected transport raised {type(exc).__name__}: {exc}. Fail closed. Not a silent skip.",
            fail_closed=True,
            network_calls=1,
            slack_ts="",
            observed_at=observed_at,
        )
    if not isinstance(result, dict) or not result.get("ok"):
        return _receipt(
            normalized=normalized,
            mode="live",
            presence=presence,
            state=TRANSPORT_REJECTED_STATE,
            ok=False,
            reason="injected transport rejected the payload; fail closed; not a silent skip",
            fail_closed=True,
            network_calls=1,
            slack_ts="",
            observed_at=observed_at,
            transport_result=result if isinstance(result, dict) else None,
        )
    slack_ts = str(result.get("ts") or result.get("slack_ts") or "")
    receipt = _receipt(
        normalized=normalized,
        mode="live",
        presence=presence,
        state="INJECTED_DELIVERED",
        ok=True,
        reason="injected transport only; adapter did not open Slack HTTP",
        fail_closed=False,
        network_calls=1,
        slack_ts=slack_ts,
        observed_at=observed_at,
        transport_result=result,
    )
    receipt["real_send"] = False
    return receipt


def self_test() -> dict[str, Any]:
    """Prove synthetic success and credential-absence fail-closed with empty env."""
    synthetic = deliver(SELF_TEST_EVENT, mode="test", env={}, now="2026-09-01T00:00:00Z")
    absent = deliver(SELF_TEST_EVENT, mode="live", env={}, now="2026-09-01T00:00:00Z")
    ok = (
        synthetic.get("ok") is True
        and synthetic.get("state") == SYNTHETIC_STATE
        and synthetic.get("real_send") is False
        and synthetic.get("network_calls") == 0
        and synthetic.get("silent_skip") is False
        and absent.get("ok") is False
        and absent.get("state") == ABSENT_STATE
        and absent.get("fail_closed") is True
        and absent.get("silent_skip") is False
        and absent.get("real_send") is False
        and absent.get("network_calls") == 0
    )
    return {"ok": ok, "synthetic": synthetic, "credential_absent": absent}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Slack destination adapter (synthetic by default)")
    parser.add_argument("--mode", choices=MODES, default="test")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--input", help="JSON event file; default is the synthetic fixture")
    args = parser.parse_args(argv)
    if args.self_test:
        report = self_test()
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report["ok"] else 1
    if args.input:
        event = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        event = SELF_TEST_EVENT
    receipt = deliver(event, mode=args.mode, env={})
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    if receipt.get("ok"):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
