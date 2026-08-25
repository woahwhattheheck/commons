#!/usr/bin/env python3
"""Build the journaled titan MOVE packet from public excerpt sidecars.

Claimed append offsets are dest FROM FILE (titan.gguf size
103803350291). This does not write titan.gguf. Apply reallocates
if live size differs. new = old | mask. Ones only rise.

  python3 muhl_titan_move_packet.py          # write packet JSON
  python3 muhl_titan_move_packet.py --dry    # print, write nothing
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "host"))
from titan_move_offsets import (
    CLAIMED_APPEND_BASE,
    CLAIMED_APPEND_SOURCE,
    allocate_rows,
)

EXCERPT_DIR = os.path.join(REPO_ROOT, "excerpts", "20260823")
PACKET_PATH = os.path.join(EXCERPT_DIR, "titan_move_packet.json")


def build_packet():
    rows = []
    for name in sorted(os.listdir(EXCERPT_DIR)):
        if not name.endswith("_circuits.json"):
            continue
        path = os.path.join(EXCERPT_DIR, name)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        for key, row in data.items():
            container = row.get("container")
            excerpt = os.path.join(EXCERPT_DIR, container)
            if not os.path.isfile(excerpt):
                raise RuntimeError("sidecar %s names missing %s" % (name, container))
            with open(excerpt, "rb") as raw_handle:
                raw = raw_handle.read()
            digest = hashlib.sha256(raw).hexdigest()
            expected = row.get("sha256")
            if expected and expected != digest:
                raise RuntimeError("sha mismatch %s" % excerpt)
            rows.append({
                "name": row.get("name") or key,
                "magic": row.get("magic"),
                "container": container,
                "path": "excerpts/20260823/" + container,
                "n_gate": row.get("n_gate"),
                "n_wires": row.get("n_wires"),
                "n_in": row.get("n_in"),
                "n_out": row.get("n_out"),
                "depth": row.get("depth"),
                "len": len(raw),
                "sha256": digest,
                "titan": "NOT_WRITTEN",
            })
    rows.sort(key=lambda row: row["name"])
    allocated, end = allocate_rows(rows, base=CLAIMED_APPEND_BASE)
    return {
        "kind": "TITAN_MOVE_PACKET",
        "computer": "titan.gguf is the computer. This packet is not.",
        "titan": "NOT_WRITTEN",
        "rule": (
            "claimed append offsets dest FROM FILE titan_size="
            "%d. Apply reallocates if live size differs."
            % CLAIMED_APPEND_BASE
        ),
        "journal": "every pre-image. new = old | mask. ones only rise.",
        "claimed_append_base": CLAIMED_APPEND_BASE,
        "claimed_append_end": end,
        "claimed_append_source": CLAIMED_APPEND_SOURCE,
        "count": len(allocated),
        "organs": allocated,
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry" in argv
    packet = build_packet()
    print("TITAN_MOVE_PACKET structural receipt")
    print(
        "  count=%d titan=NOT_WRITTEN base=%s end=%s"
        % (packet["count"], packet["claimed_append_base"], packet["claimed_append_end"])
    )
    for row in packet["organs"]:
        print(
            "  %s %s g off=%s sha256=%s"
            % (row["name"], row["n_gate"], row["offset"], row["sha256"][:12])
        )
    if dry:
        print("  --dry: no files written")
        return 0
    os.makedirs(os.path.dirname(PACKET_PATH), exist_ok=True)
    with open(PACKET_PATH, "w", encoding="utf-8") as handle:
        json.dump(packet, handle, indent=2)
        handle.write("\n")
    print("  wrote %s" % PACKET_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
