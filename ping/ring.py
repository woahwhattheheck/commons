#!/usr/bin/env python3
"""REACH: POST a wake ping to ntfy. Not a listener. Not the computer.

Topic: woahwhattheheck-commons-wake
Any harness can subscribe: curl -s ntfy.sh/woahwhattheheck-commons-wake/json
Failover hosts match ground/CURL.md. ntfy 200 is mail. 337 NO.
"""
import json
import os
import sys
import urllib.error
import urllib.request


TOPIC = "woahwhattheheck-commons-wake"
HOSTS = (
    "https://ntfy.sh",
    "https://ntfy.envs.net",
    "https://ntfy.adminforge.de",
    "https://ntfy.mzte.de",
)


def ring(claims, extra=None, timeout=12):
    claims = [c for c in claims if c]
    body = {"kind": "WAKE", "claims": claims}
    if extra:
        body.update(extra)
    data = json.dumps(body, separators=(",", ":")).encode()
    title = "WAKE " + ",".join(claims) if claims else "WAKE"
    last_err = None
    for host in HOSTS:
        req = urllib.request.Request(
            host + "/" + TOPIC,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Title": title,
                "Tags": "bell",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return host, int(resp.status)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
            continue
    raise RuntimeError("ntfy wake failed: %s" % last_err)


def claims_from_argv(argv):
    found = [c.strip().upper() for c in argv[1:] if c.strip()]
    if found:
        return found
    env = os.environ.get("CLAIMS") or ""
    return [c.strip().upper() for c in env.split(",") if c.strip()]


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    claims = claims_from_argv(argv)
    host, status = ring(claims)
    print("%s %s" % (status, host))
    return 0 if status == 200 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
