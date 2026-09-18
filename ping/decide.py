#!/usr/bin/env python3
"""DIRECTIVE 2 — decide whether Commons should doorbell a harness.

Decision half is mail.json (per-claim seq). pulse.json is the wrong bell.
Quiet: record only if an enrolled claim's mail row moved, and not by
that claim's own post. No callback URLs. No tokens. No idle loop.

Cursor / Grok Bot are on owner quota hold. Their claims advance in last.json
so the detector does not repeat, but ping is always 0 and issue #1316 is not
reassigned.
ChatGPT / Claude / ntfy-poll are poll adapters: they are recorded in
last.json as moved_poll and must GET mail.json / ping/last.json themselves.
PLAYER2 owns that transport. Do not invent callback URLs.
"""
from __future__ import annotations

import json
import os
import sys


def load(path, default):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def adapter_kind(ad):
    text = (ad or "").lower()
    if "cursor" in text or "grok bot" in text:
        return "cursor"
    if "chatgpt" in text or "openai" in text:
        return "chatgpt"
    if "claude" in text or "anthropic" in text:
        return "claude"
    if "ntfy" in text:
        return "ntfy"
    return ""


def enroll(wake, extra_cursor=None):
    cursor = set({"LATCH"} if extra_cursor is None else extra_cursor)
    poll = set()
    for row in wake.get("actionable") or []:
        kind = adapter_kind(row.get("adapter") or "")
        who = (row.get("from") or "").upper()
        if not who or not kind:
            continue
        if kind == "cursor":
            cursor.add(who)
        else:
            poll.add(who)
    return cursor, poll


def moved_names(mail, names, last_claims):
    by = {}
    for row in mail.get("mail") or []:
        to = (row.get("to") or "").upper()
        if to:
            by[to] = row
    claims = dict(last_claims or {})
    moved = []
    for name in sorted(names):
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
    return moved, claims


def decide(mail, wake, last):
    cursor, poll = enroll(wake)
    last_claims = (last or {}).get("claims") or {}
    held_cursor, claims = moved_names(mail, cursor, last_claims)
    moved_poll, claims = moved_names(mail, poll, claims)
    out = {
        "instruction": (
            "Compare your claim row to last ACK. Same seq => stay quiet. "
            "Moved => read href. Own post does not wake you. "
            "ChatGPT/Claude/ntfy poll this file. Cursor is on quota hold."
        ),
        "ts": mail.get("ts") or "",
        "mail_seq": mail.get("seq"),
        "moved": [],
        "moved_poll": moved_poll,
        "held_cursor": held_cursor,
        "claims": claims,
    }
    return out, "0", [], moved_poll


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    mail = load("mail.json", {})
    wake = load("wake.json", {})
    last = load("ping/last.json", {"claims": {}})
    out, ping, moved, poll = decide(mail, wake, last)
    held = out.get("held_cursor") or []
    os.makedirs("ping", exist_ok=True)
    with open("ping/last.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    gh_out = os.environ.get("GITHUB_OUTPUT", "")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write("ping=%s\n" % ping)
            f.write("claims=%s\n" % ",".join(moved))
            f.write("poll=%s\n" % ",".join(poll))
            f.write("write=%s\n" % ("1" if (held or poll) else "0"))
    print(
        "ping=%s claims=%s poll=%s held_cursor=%s"
        % (ping, ",".join(moved), ",".join(poll), ",".join(held))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
