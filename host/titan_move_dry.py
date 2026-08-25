#!/usr/bin/env python3
"""host/titan_move_dry.py — measure the public titan MOVE packet.

Owner Slack 1787628542.573719: stop dodging the substrate. Organs
1–31 excerpts can sit on main while titan.gguf is still NOT_WRITTEN.

This instrument reads the public packet and excerpt files. It does
not open titan.gguf. It does not smash commons.mno. Claimed offsets
are dest FROM FILE. A write still needs titan.gguf.

  python3 host/titan_move_dry.py
  python3 host/titan_move_dry.py --root /path/to/clone
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys


PACKET_REL = os.path.join("excerpts", "20260823", "titan_move_packet.json")
EXCERPT_REL = os.path.join("excerpts", "20260823")


def classify(row):
    """Turn a measured packet row into a land-desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": "titan move packet not measured. Absence was not stillness.",
        }
    count = int(row.get("count") or 0)
    excerpts = int(row.get("excerpt_count") or 0)
    written = str(row.get("titan") or "").upper()
    nonzero = int(row.get("nonzero_offsets") or 0)
    reread = row.get("reread") is True
    if written == "WRITTEN" and reread and nonzero == count and count >= 31:
        return {
            "state": "INTEGRATED",
            "note": "titan write and reread measured for %s organs." % count,
        }
    if excerpts < 31:
        return {
            "state": "NOT_LANDED",
            "note": (
                "only %s/31 excerpts on this tree. Fabricate the missing "
                "organ. Do not write titan yet."
            )
            % excerpts,
        }
    if written == "NOT_WRITTEN" and nonzero == count and count >= 31:
        return {
            "state": "CLAIMED",
            "note": (
                "%s/31 claimed append offsets dest FROM FILE. "
                "titan write still NOT_WRITTEN. Run host/titan_move_apply.py "
                "--go on the machine that has titan.gguf."
            )
            % excerpts,
        }
    if written == "NOT_WRITTEN" or nonzero == 0:
        return {
            "state": "NOT_LANDED",
            "note": (
                "%s/31 excerpts on this tree. Packet still has zero "
                "offsets. Fill claimed append offsets dest FROM FILE "
                "(titan_size 103803350291), then apply."
            )
            % excerpts,
        }
    return {
        "state": "NOT_LANDED",
        "note": "titan move not closed. Measure the packet and the reread.",
    }


def measure_from_packet(packet, excerpt_dir):
    """Pure parser so tests do not need titan.gguf."""
    packet = packet or {}
    organs = list(packet.get("organs") or [])
    excerpt_count = 0
    sha_ok = 0
    nonzero = 0
    missing = []
    for row in organs:
        container = os.path.basename(
            str(row.get("container") or row.get("path") or "")
        )
        if not container:
            missing.append("(unnamed)")
            continue
        path = os.path.join(excerpt_dir, container)
        if not os.path.isfile(path):
            missing.append(container)
            continue
        excerpt_count += 1
        expected = str(row.get("sha256") or "")
        if expected:
            with open(path, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            if digest == expected:
                sha_ok += 1
        try:
            offset = int(row.get("offset") or 0)
        except (TypeError, ValueError):
            offset = 0
        if offset != 0:
            nonzero += 1
    return {
        "measured": True,
        "kind": packet.get("kind") or "TITAN_MOVE_PACKET",
        "count": int(packet.get("count") or len(organs)),
        "excerpt_count": excerpt_count,
        "sha_ok": sha_ok,
        "titan": packet.get("titan") or "NOT_WRITTEN",
        "nonzero_offsets": nonzero,
        "reread": False,
        "missing": missing,
        "computer": "titan.gguf is the computer. This packet is not.",
    }


def owner_blocker(row, verdict):
    """NEED / WHY ONLY BRYCE / SMALLEST ACTION / EVIDENCE / AFTER."""
    excerpts = int((row or {}).get("excerpt_count") or 0)
    return {
        "NEED": (
            "Run host/titan_move_apply.py --go against dest-FROM-FILE "
            "C:\\llm\\models\\titan.gguf and journal the 31-organ MOVE "
            "(new = old | mask; ones only rise; re-read before every write)."
        ),
        "WHY_ONLY_BRYCE": (
            "titan.gguf is not on this cloud box. Claimed offsets are "
            "already dest FROM FILE (titan_size 103803350291). Apply and "
            "reread need the file. Dirty LocalDeviceAgent/kite-help is on "
            "the owner PC working tree."
        ),
        "SMALLEST_ACTION": (
            "On the owner PC: python3 host/titan_move_apply.py --go. "
            "If live size != 103803350291 the button reallocates from "
            "live size. Post the reread receipt. Do not smash "
            "commons.mno. Do not fire 337. Commit and push the dirty "
            "LocalDeviceAgent kite-help tree."
        ),
        "EVIDENCE": (
            "Measured %s/31 excerpts. Packet titan=%s. nonzero_offsets=%s. "
            "reread=%s. Desk state %s."
        )
        % (
            excerpts,
            (row or {}).get("titan") or "UNMEASURED",
            (row or {}).get("nonzero_offsets") or 0,
            (row or {}).get("reread"),
            (verdict or {}).get("state") or "UNMEASURED",
        ),
        "AFTER": (
            "Land desk titanMoveState becomes INTEGRATED. Packet rows carry "
            "nonzero offsets and titan=WRITTEN. A new p/{id}.md names the "
            "reread. Organs 1–31 excerpts stay as they are."
        ),
    }


def measure_tree(root):
    root = os.path.abspath(root)
    packet_path = os.path.join(root, PACKET_REL)
    excerpt_dir = os.path.join(root, EXCERPT_REL)
    if not os.path.isfile(packet_path):
        return {
            "measured": False,
            "root": root,
            "error": "missing " + PACKET_REL,
            "titan": "NOT_WRITTEN",
            "reread": False,
        }
    with open(packet_path, encoding="utf-8") as handle:
        packet = json.load(handle)
    row = measure_from_packet(packet, excerpt_dir)
    row["root"] = root
    row["packet_path"] = PACKET_REL
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Measure public titan MOVE packet. Does not write titan."
    )
    parser.add_argument("--root", default=".", help="clone to measure")
    args = parser.parse_args(argv)
    row = measure_tree(args.root)
    verdict = classify(row)
    payload = dict(row)
    payload.update(verdict)
    payload["owner_blocker"] = owner_blocker(row, verdict)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if row.get("measured") else 2


if __name__ == "__main__":
    sys.exit(main())
