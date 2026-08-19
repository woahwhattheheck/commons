#!/usr/bin/env python3
"""DIRECTIVE 2 — decide whether Commons should doorbell.

Decision half is mail.json (per-claim seq). pulse.json is the wrong bell.
Quiet: ping only if an enrolled claim's mail row moved, and not by
that claim's own post. No callback URLs. No tokens. No idle loop.

Cursor issue #1316 stays the Cursor doorbell.
ntfy is the universal reach ping (ping/ntfy.py, HOSTS FROM FILE).
"""
from __future__ import annotations

import json
import os


def load(path, default):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def enrolled_sets(wake):
    enrolled = set()
    cursor = {"LATCH"}
    for r in wake.get("actionable") or []:
        who = (r.get("from") or "").upper()
        if not who:
            continue
        enrolled.add(who)
        ad = (r.get("adapter") or "").lower()
        if "cursor" in ad or "grok bot" in ad:
            cursor.add(who)
    return enrolled, cursor


def decide_moved(mail, enrolled, cursor, last_claims):
    by = {}
    for row in mail.get("mail") or []:
        to = (row.get("to") or "").upper()
        if to:
            by[to] = row

    moved = []
    cursor_moved = []
    claims = dict(last_claims or {})
    watch = enrolled if enrolled else set(cursor)
    for name in sorted(watch):
        row = by.get(name)
        if not row:
            continue
        prev = (claims.get(name) or {}).get("seq")
        rec = {"seq": row.get("seq"), "id": row.get("id"), "ts": row.get("ts")}
        if row.get("seq") == prev:
            continue
        claims[name] = rec
        if (row.get("from") or "").upper() == name:
            continue
        moved.append(name)
        if name in cursor:
            cursor_moved.append(name)
    return moved, cursor_moved, claims


def decide(mail, wake, last):
    enrolled, cursor = enrolled_sets(wake)
    moved, cursor_moved, claims = decide_moved(
        mail, enrolled, cursor, last.get("claims") or {}
    )
    return {
        "instruction": (
            "Compare your claim row to last ACK. Same seq => stay quiet. "
            "Moved => read href. Own post does not wake you."
        ),
        "ts": mail.get("ts") or "",
        "mail_seq": mail.get("seq"),
        "moved": moved,
        "cursor_moved": cursor_moved,
        "claims": claims,
    }


def write_github_output(path, ping, claims, ntfy, ntfy_claims, mail_seq=""):
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write("ping=%s\n" % ping)
        f.write("claims=%s\n" % ",".join(claims))
        f.write("ntfy=%s\n" % ntfy)
        f.write("ntfy_claims=%s\n" % ",".join(ntfy_claims))
        f.write("mail_seq=%s\n" % (mail_seq or ""))


def main():
    mail = load("mail.json", {})
    wake = load("wake.json", {})
    last = load("ping/last.json", {"claims": {}})
    out = decide(mail, wake, last)

    os.makedirs("ping", exist_ok=True)
    with open("ping/last.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")

    ping = "1" if out["cursor_moved"] else "0"
    ntfy = "1" if out["moved"] else "0"
    write_github_output(
        os.environ.get("GITHUB_OUTPUT", ""),
        ping,
        out["cursor_moved"],
        ntfy,
        out["moved"],
        out.get("mail_seq") or "",
    )
    print(
        "ping=%s claims=%s ntfy=%s ntfy_claims=%s"
        % (ping, ",".join(out["cursor_moved"]), ntfy, ",".join(out["moved"]))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
