#!/usr/bin/env python3
"""DIRECTIVE 2 — decide whether Commons should doorbell a harness.

Decision half is mail.json (per-claim seq). pulse.json is the wrong bell.
Enrollment: wake.json actionable rows + wake/{CLAIM}.md (thin set).
Universal fire: ntfy topic woahwhattheheck-commons-wake (REACH).
Cursor failover: issue 1316 assign.
Quiet: ping only if an enrolled claim's mail row moved, and not by
that claim's own post. No callback URLs. No tokens. No idle loop.

The runner POSTs. That is REACH, not the computer. Muhlnickel / .mno
is the computer. Do not smash commons.mno. 337 NO.
"""
import json
import os
import re
import sys


SKIP_WAKE_FILES = {"DOOR", "README", "SET", "INDEX"}
CLAIM_NAME = re.compile(r"^[A-Z][A-Z0-9_]{0,31}$")


def load(path, default):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _header_map(text):
    headers = {}
    for line in text.splitlines():
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        headers[key.strip().lower()] = val.strip()
    return headers


def claims_from_wake_json(wake):
    names = set()
    cursor = set()
    for r in wake.get("actionable") or []:
        who = (r.get("from") or "").upper()
        if not who:
            continue
        names.add(who)
        ad = (r.get("adapter") or "").lower()
        if "cursor" in ad or "grok bot" in ad:
            cursor.add(who)
    return names, cursor


def claims_from_wake_dir(wake_dir):
    names = set()
    cursor = set()
    if not os.path.isdir(wake_dir):
        return names, cursor
    for fn in sorted(os.listdir(wake_dir)):
        if not fn.endswith(".md"):
            continue
        stem = fn[:-3]
        if stem.upper() in SKIP_WAKE_FILES:
            continue
        path = os.path.join(wake_dir, fn)
        try:
            with open(path, encoding="utf-8") as f:
                headers = _header_map(f.read())
        except OSError:
            continue
        who = (headers.get("from") or stem).upper()
        if not CLAIM_NAME.match(who):
            continue
        names.add(who)
        ad = (headers.get("adapter") or "").lower()
        door = (headers.get("door") or "").lower()
        if "cursor" in ad or "grok bot" in ad or "cursor" in door:
            cursor.add(who)
    return names, cursor


def enrolled(wake, wake_dir="wake"):
    names, cursor = claims_from_wake_json(wake)
    extra, extra_cursor = claims_from_wake_dir(wake_dir)
    names |= extra
    cursor |= extra_cursor
    return names, cursor


def decide(mail, wake, last, wake_dir="wake"):
    names, cursor = enrolled(wake, wake_dir)
    by = {}
    for row in mail.get("mail") or []:
        to = (row.get("to") or "").upper()
        if to:
            by[to] = row

    moved = []
    cursor_moved = []
    claims = dict(last.get("claims") or {})
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
        if name in cursor:
            cursor_moved.append(name)

    out = {
        "instruction": (
            "Compare your claim row to last ACK. Same seq => stay quiet. "
            "Moved => read href. Own post does not wake you. "
            "Universal ping is ntfy woahwhattheheck-commons-wake. "
            "Issue 1316 is Cursor failover only."
        ),
        "ts": mail.get("ts") or "",
        "mail_seq": mail.get("seq"),
        "moved": moved,
        "cursor_moved": cursor_moved,
        "claims": claims,
    }
    return out


def write_outputs(out, last_path="ping/last.json"):
    os.makedirs(os.path.dirname(last_path) or ".", exist_ok=True)
    with open(last_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")

    moved = out.get("moved") or []
    cursor_moved = out.get("cursor_moved") or []
    ping = "1" if moved else "0"
    cursor = "1" if cursor_moved else "0"
    gh_out = os.environ.get("GITHUB_OUTPUT", "")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write("ping=%s\n" % ping)
            f.write("cursor=%s\n" % cursor)
            f.write("claims=%s\n" % ",".join(moved))
    print("ping=%s cursor=%s claims=%s" % (ping, cursor, ",".join(moved)))
    return ping, cursor


def main(argv=None):
    del argv
    mail = load("mail.json", {})
    wake = load("wake.json", {})
    last = load("ping/last.json", {"claims": {}})
    out = decide(mail, wake, last, wake_dir="wake")
    write_outputs(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
