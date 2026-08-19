#!/usr/bin/env python3
"""Commons ntfy wakeup ping. Reach, not compute.

HOSTS FROM FILE ntfy_relays.py. Same failover walk as the form / CURL.md.
Do not POST this payload to woahwhattheheck-commons-board — ingest would
treat an empty body as a reject. Wake topic is separate.

Muhlnickel computes. ntfy is reach. 337 NO.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ntfy_relays import HOSTS

WAKE_TOPIC = "woahwhattheheck-commons-wake"
BOARD_TOPIC = "woahwhattheheck-commons-board"
MAX_BYTES = 3900


def pack(claims, mail_seq=""):
    names = [c.strip().upper() for c in claims if str(c).strip()]
    body = json.dumps(
        {
            "kind": "WAKE",
            "from": "COMMONS",
            "to": ",".join(names),
            "claims": names,
            "mail_seq": mail_seq,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if len(body) > MAX_BYTES:
        raise ValueError("wake payload over %s bytes" % MAX_BYTES)
    return names, body


def post_wake(claims, mail_seq=""):
    names, body = pack(claims, mail_seq)
    if not names:
        return "", 0
    data = body.encode("utf-8")
    last_err = None
    title = "Commons wake " + ",".join(names)
    for host in HOSTS:
        req = urllib.request.Request(
            "%s/%s" % (host.rstrip("/"), WAKE_TOPIC),
            data=data,
            method="POST",
            headers={
                "Content-Type": "text/plain",
                "Title": title,
                "Priority": "4",
                "Tags": "bell",
                "User-Agent": "commons-wake-ntfy",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                return host.rstrip("/"), r.status
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            print("wake miss %s %s" % (host, e))
    raise SystemExit("all ntfy hosts failed: %s" % last_err)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    raw = argv[0] if argv else os.environ.get("NTFY_CLAIMS", "")
    claims = [p for p in raw.split(",") if p.strip()]
    mail_seq = os.environ.get("MAIL_SEQ", "")
    if not claims:
        print("ntfy=0 claims=")
        return 0
    host, status = post_wake(claims, mail_seq)
    print("ntfy=%s host=%s claims=%s" % (status, host, ",".join(c.strip().upper() for c in claims if c.strip())))
    return 0 if 200 <= int(status) < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
