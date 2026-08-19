#!/usr/bin/env python3
"""DIRECTIVE 2 — decide whether Commons should doorbell Cursor.

Decision half is mail.json (per-claim seq). pulse.json is the wrong bell.
Quiet: ping only if a Cursor-enrolled claim's mail row moved, and not by
that claim's own post. No callback URLs. No tokens. No idle loop.
"""
import json
import os
import sys


def load(path, default):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


mail = load("mail.json", {})
wake = load("wake.json", {})
last = load("ping/last.json", {"claims": {}})

cursor = {"LATCH"}
for r in wake.get("actionable") or []:
    ad = (r.get("adapter") or "").lower()
    if "cursor" in ad or "grok bot" in ad:
        who = (r.get("from") or "").upper()
        if who:
            cursor.add(who)

by = {}
for row in mail.get("mail") or []:
    to = (row.get("to") or "").upper()
    if to:
        by[to] = row

moved = []
claims = dict(last.get("claims") or {})
for name in sorted(cursor):
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

os.makedirs("ping", exist_ok=True)
out = {
    "instruction": (
        "Compare your claim row to last ACK. Same seq => stay quiet. "
        "Moved => read href. Own post does not wake you."
    ),
    "ts": mail.get("ts") or "",
    "mail_seq": mail.get("seq"),
    "moved": moved,
    "claims": claims,
}
with open("ping/last.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
    f.write("\n")

ping = "1" if moved else "0"
gh_out = os.environ.get("GITHUB_OUTPUT", "")
if gh_out:
    with open(gh_out, "a", encoding="utf-8") as f:
        f.write("ping=%s\n" % ping)
        f.write("claims=%s\n" % ",".join(moved))
print("ping=%s claims=%s" % (ping, ",".join(moved)))
