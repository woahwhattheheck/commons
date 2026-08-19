#!/usr/bin/env python3
"""Pull every ntfy relay onto ntfy.sh so ingest_ntfy (which only reads ntfy.sh) sees failover mail.

Bryce 2026-08-19: detect cap, switch providers, no button. Form already walks hosts.
Ingest did not. Owner + other players landed on envs.net and vanished (rmw818).
Do not remint. Same id, same body. Skip if p/{id}.md already exists.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

HOSTS = [
    "https://ntfy.sh",
    "https://ntfy.envs.net",
    "https://ntfy.adminforge.de",
    "https://ntfy.mzte.de",
]
TOPIC = "woahwhattheheck-commons-board"
HOME = "https://ntfy.sh"
SINCE = "24h"


def poll(host: str) -> list[dict]:
    url = f"{host}/{TOPIC}/json?poll=1&since={SINCE}"
    req = urllib.request.Request(
        url, headers={"Accept": "application/x-ndjson", "User-Agent": "commons-ntfy-relays"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"poll fail {host} {e}")
        return []
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("event") != "message":
            continue
        msg = ev.get("message") or ""
        pid = None
        try:
            payload = json.loads(msg)
            if isinstance(payload, dict):
                pid = payload.get("id")
        except json.JSONDecodeError:
            pass
        out.append({"id": pid, "message": msg, "host": host, "event_id": ev.get("id")})
    print(f"poll ok {host} n={len(out)}")
    return out


def already(pid: str) -> bool:
    if not pid:
        return False
    return os.path.exists(os.path.join("p", f"{pid}.md"))


def replay(msg: str) -> bool:
    req = urllib.request.Request(
        f"{HOME}/{TOPIC}",
        data=msg.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain", "User-Agent": "commons-ntfy-relays"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"replay fail {e}")
        return False


def main() -> int:
    seen = set()
    replayed = skipped = 0
    for host in HOSTS:
        for ev in poll(host):
            pid = ev.get("id")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            if already(pid):
                skipped += 1
                continue
            if host.rstrip("/") == HOME:
                skipped += 1
                continue
            if replay(ev["message"]):
                replayed += 1
                print(f"replay {pid} from {host}")
            else:
                print(f"drop {pid} from {host}")
    print(f"done unique={len(seen)} replayed={replayed} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
