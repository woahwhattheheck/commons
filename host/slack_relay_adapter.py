#!/usr/bin/env python3
"""Synthetic/read-only Slack destination adapter for uncredentialed local bridges.

Composes the existing relay / integration pattern. Does not remint:

- ``ntfy_relays.py`` (origin-preserving payload, refuse inconsistent ids)
- ``integrations/grok_slack`` (``SECRET_ENV``, ``credential_presence``, table)
- ``integrations/gemini_slack`` (same ``SLACK_BOT_TOKEN`` / ``SLACK_APP_TOKEN``)

Every valid event returns a synthetic receipt. Credential presence is an
observational overlay only: missing or present Slack tokens never admit,
deny, or fail-close the adapter. Transport callables and urllib are never
used. This is not ``host/slack_mirror.py`` DARK skip.
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
INVALID_EVENT_STATE = "INVALID_EVENT"
INVALID_MODE_STATE = "INVALID_MODE"
GEMINI_SECRET_ENV = SECRET_ENV
GEMINI_BRIDGE_NAME = gemini_slack_bridge.__name__
SELF_TEST_EVENT = {
    "id": "caliper-slack-relay-adapter-01",
    "text": "synthetic Slack destination ping",
    "source_host": "local-uncredentialed",
    "carrier_origin": "local-uncredentialed",
    "channel": DEFAULT_CHANNEL,
}


class SlackRelayAdapterError(ValueError):
    """The event cannot be composed; callers still receive a receipt."""


Transport = Callable[[dict[str, Any]], dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _synthetic_ts(event_id: str) -> str:
    digest = hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:10]
    return f"synthetic.{digest}"


def _presence(env: dict[str, str] | None) -> dict[str, str]:
    """Reuse grok_slack presence as overlay. Blank/whitespace counts as missing."""
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
    observed_at: str,
) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "adapter": ADAPTER_PATH,
        "wired": list(WIRED_PATHS),
        "mode": mode,
        "ok": ok,
        "state": state,
        "reason": reason,
        "read_only": True,
        "synthetic": True,
        "admission_gate": False,
        "credential_gate": False,
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
        "gemini_slack_module": GEMINI_BRIDGE_NAME,
        "network_calls": 0,
        "real_send": False,
        "slack_ts": _synthetic_ts((normalized or {}).get("id") or "") if ok else "",
        "observed_at": observed_at,
        "missing_credentials": _missing_credentials(presence),
    }


def deliver(
    event: object,
    *,
    mode: str = "test",
    env: dict[str, str] | None = None,
    transport: Transport | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Compose one synthetic/read-only Slack destination receipt.

    ``transport`` is accepted for call-site compatibility and is never invoked.
    Credential presence is recorded and never used as an admission gate.
    """
    del transport
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
            reason="mode must be test or live; both are synthetic/read-only; not an admission gate",
            fail_closed=True,
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
            reason=f"{exc}; malformed event; not an admission gate",
            fail_closed=True,
            observed_at=observed_at,
        )
    return _receipt(
        normalized=normalized,
        mode=requested_mode,
        presence=presence,
        state=SYNTHETIC_STATE,
        ok=True,
        reason=(
            "synthetic/read-only Slack destination receipt; zero real sends; "
            "credential presence is overlay, not an admission gate"
        ),
        fail_closed=False,
        observed_at=observed_at,
    )


def self_test() -> dict[str, Any]:
    """Prove synthetic success with empty env in both test and live labels."""
    synthetic = deliver(SELF_TEST_EVENT, mode="test", env={}, now="2026-09-01T00:00:00Z")
    live_uncredentialed = deliver(
        SELF_TEST_EVENT, mode="live", env={}, now="2026-09-01T00:00:00Z"
    )
    ok = (
        synthetic.get("ok") is True
        and synthetic.get("state") == SYNTHETIC_STATE
        and synthetic.get("real_send") is False
        and synthetic.get("network_calls") == 0
        and synthetic.get("silent_skip") is False
        and synthetic.get("admission_gate") is False
        and synthetic.get("read_only") is True
        and live_uncredentialed.get("ok") is True
        and live_uncredentialed.get("state") == SYNTHETIC_STATE
        and live_uncredentialed.get("fail_closed") is False
        and live_uncredentialed.get("admission_gate") is False
        and live_uncredentialed.get("credential_gate") is False
        and live_uncredentialed.get("read_only") is True
        and live_uncredentialed.get("real_send") is False
        and live_uncredentialed.get("network_calls") == 0
    )
    return {"ok": ok, "synthetic": synthetic, "live_uncredentialed": live_uncredentialed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Slack destination adapter (synthetic/read-only)"
    )
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
