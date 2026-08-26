#!/usr/bin/env python3
"""Union every ntfy relay onto ntfy.sh without changing post identity.

Bryce 2026-08-19: detect cap, switch providers, no button. Form already walks
hosts; ingest only reads ntfy.sh. Owner and peer posts that land on a failover
host must therefore be replayed under the same post id.

The muhlnickel's host-zero property is already measured. This module only
offloads a peer reconciliation chore. It does not run the muhlnickel.

Do not remint. Preserve the source host as data. Skip if p/{id}.md already
exists or the id is already present on the canonical ntfy host.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from relay_manifest import NTFY_HOSTS, NTFY_TOPIC


HOSTS = list(NTFY_HOSTS)
TOPIC = NTFY_TOPIC
HOME = HOSTS[0]
SINCE = "24h"


def _host(value: object) -> str:
    """Return one stable spelling for host comparisons and receipts."""
    return str(value or "").rstrip("/")


def poll(host: str) -> list[dict]:
    """Poll one relay and retain both transport and declared origin data."""
    source_host = _host(host)
    url = f"{source_host}/{TOPIC}/json?poll=1&since={SINCE}"
    req = urllib.request.Request(
        url, headers={"Accept": "application/x-ndjson", "User-Agent": "commons-ntfy-relays"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"poll fail {source_host} {exc}")
        return []

    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") != "message":
            continue

        message = event.get("message") or ""
        payload = None
        post_id = None
        try:
            candidate = json.loads(message)
            if isinstance(candidate, dict):
                payload = candidate
                candidate_id = candidate.get("id")
                if isinstance(candidate_id, str) and candidate_id:
                    post_id = candidate_id
        except (json.JSONDecodeError, TypeError):
            pass

        declared_origin = payload.get("carrier_origin") if payload else None
        if not isinstance(declared_origin, str) or not declared_origin:
            declared_origin = source_host
        out.append(
            {
                "id": post_id,
                "message": message,
                "payload": payload,
                # host is retained for callers of the original implementation.
                "host": source_host,
                "source_host": source_host,
                "carrier_origin": _host(declared_origin),
                "event_id": event.get("id"),
            }
        )
    print(f"poll ok {source_host} n={len(out)}")
    return out


def _event_key(event: dict) -> tuple[str, str, str, str]:
    """Choose the same representative regardless of poll response order."""
    source_host = _host(event.get("source_host") or event.get("host"))
    carrier_origin = _host(event.get("carrier_origin") or source_host)
    return (
        source_host,
        carrier_origin,
        str(event.get("event_id") or ""),
        str(event.get("message") or ""),
    )


def union_events(events: list[dict]) -> list[dict]:
    """Deterministically union relay events by the caller-supplied post id."""
    grouped: dict[str, list[dict]] = {}
    for event in events:
        post_id = event.get("id")
        if not isinstance(post_id, str) or not post_id:
            continue
        grouped.setdefault(post_id, []).append(event)

    union = []
    for post_id in sorted(grouped):
        rows = sorted(grouped[post_id], key=_event_key)
        chosen = dict(rows[0])
        source_hosts = sorted(
            {_host(row.get("source_host") or row.get("host")) for row in rows}
        )
        source_hosts = [host for host in source_hosts if host]
        carrier_origins = sorted(
            {
                _host(
                    row.get("carrier_origin")
                    or row.get("source_host")
                    or row.get("host")
                )
                for row in rows
            }
        )
        carrier_origins = [origin for origin in carrier_origins if origin]
        chosen["id"] = post_id
        chosen["source_host"] = _host(chosen.get("source_host") or chosen.get("host"))
        chosen["host"] = chosen["source_host"]
        chosen["source_hosts"] = source_hosts
        chosen["carrier_origins"] = carrier_origins
        chosen["carrier_origin"] = (
            carrier_origins[0] if carrier_origins else chosen["source_host"]
        )
        union.append(chosen)
    return union


def relay_message(event: dict) -> str:
    """Add origin receipts while preserving the exact caller-supplied id/body."""
    payload = event.get("payload")
    if not isinstance(payload, dict):
        try:
            payload = json.loads(event.get("message") or "")
        except (json.JSONDecodeError, TypeError):
            payload = {}
    payload = dict(payload) if isinstance(payload, dict) else {}
    post_id = event.get("id")
    if payload.get("id") != post_id:
        # union_events only accepts an id parsed from this payload. Refuse to
        # manufacture or rewrite one if a caller supplies an inconsistent row.
        raise ValueError("relay event id does not match payload id")

    source_host = _host(event.get("source_host") or event.get("host"))
    carrier_origin = _host(event.get("carrier_origin") or source_host)
    source_hosts = sorted({_host(host) for host in event.get("source_hosts", []) if _host(host)})
    carrier_origins = sorted(
        {_host(host) for host in event.get("carrier_origins", []) if _host(host)}
    )
    payload["source_host"] = source_host
    payload["carrier_origin"] = carrier_origin
    if source_hosts:
        payload["source_hosts"] = source_hosts
    if carrier_origins:
        payload["carrier_origins"] = carrier_origins
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def already(post_id: str) -> bool:
    if not post_id:
        return False
    return os.path.exists(os.path.join("p", f"{post_id}.md"))


def replay(message: str) -> bool:
    req = urllib.request.Request(
        f"{_host(HOME)}/{TOPIC}",
        data=message.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain", "User-Agent": "commons-ntfy-relays"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"replay fail {exc}")
        return False


def main() -> int:
    polled = []
    for host in HOSTS:
        # Poll every configured host before deciding what the union contains.
        polled.extend(poll(host))

    replayed = skipped = 0
    home = _host(HOME)
    union = union_events(polled)
    for event in union:
        post_id = event["id"]
        if already(post_id):
            skipped += 1
            continue
        if home in event.get("source_hosts", []):
            skipped += 1
            continue
        message = relay_message(event)
        if replay(message):
            replayed += 1
            print(f"replay {post_id} from {event['source_host']}")
        else:
            # No durable retry ledger is needed: the same remote event remains
            # pollable and the next run retries the same id without reminting.
            print(f"retry {post_id} from {event['source_host']}")
    print(f"done unique={len(union)} replayed={replayed} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
