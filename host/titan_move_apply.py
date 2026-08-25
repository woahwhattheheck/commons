#!/usr/bin/env python3
"""host/titan_move_apply.py — journaled titan MOVE apply button. Dies.

Default is a plan. --journal OR-writes the 31 excerpt binaries
and rereads. --go writes titan.gguf only when the file is present.
Does not smash commons.mno. --inject is wipe; refused.

  python3 host/titan_move_apply.py
  python3 host/titan_move_apply.py --journal
  python3 host/titan_move_apply.py --titan /path/to/titan.gguf --go
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile

from titan_move_offsets import (
    CLAIMED_APPEND_BASE,
    CLAIMED_APPEND_SOURCE,
    allocate_rows,
    find_titan,
    or_bytes,
)


PACKET_REL = os.path.join("excerpts", "20260823", "titan_move_packet.json")
EXCERPT_REL = os.path.join("excerpts", "20260823")
JOURNAL_REL = os.path.join("excerpts", "20260823", "titan_move_journal.json")


def plan_from_packet(packet, live_size=None):
    """Rebuild claimed offsets. Reallocate if live titan size differs."""
    packet = packet or {}
    organs = list(packet.get("organs") or [])
    base = int(packet.get("claimed_append_base") or CLAIMED_APPEND_BASE)
    if live_size is not None and int(live_size) != base:
        base = int(live_size)
    allocated, end = allocate_rows(organs, base=base)
    return {
        "kind": "TITAN_MOVE_PLAN",
        "computer": "titan.gguf is the computer. This plan is not.",
        "titan": packet.get("titan") or "NOT_WRITTEN",
        "claimed_append_base": base,
        "claimed_append_end": end,
        "claimed_append_source": packet.get("claimed_append_source")
        or CLAIMED_APPEND_SOURCE,
        "count": len(allocated),
        "organs": allocated,
        "reallocated": live_size is not None
        and int(live_size) != int(packet.get("claimed_append_base") or CLAIMED_APPEND_BASE),
    }


def journal_rows(organs):
    """Pack organs from journal offset 0. Keep claimed titan offsets."""
    running = 0
    out = []
    for row in organs or []:
        item = dict(row)
        length = int(item.get("len") or 0)
        item["journal_offset"] = running
        try:
            item["claimed_titan_offset"] = int(item.get("offset") or 0)
        except (TypeError, ValueError):
            item["claimed_titan_offset"] = 0
        out.append(item)
        running += length
    return out, running


def apply_journal(journal_path, rows, excerpt_dir):
    """Journaled MOVE on a public image. new = old | mask. Re-read each span."""
    journals = []
    with open(journal_path, "w+b") as handle:
        for row in rows:
            container = os.path.basename(str(row.get("container") or ""))
            excerpt_path = os.path.join(excerpt_dir, container)
            with open(excerpt_path, "rb") as raw_handle:
                mask = raw_handle.read()
            offset = int(row["journal_offset"])
            handle.seek(offset)
            old = handle.read(len(mask))
            new = or_bytes(old, mask)
            handle.seek(offset)
            handle.write(new)
            handle.flush()
            os.fsync(handle.fileno())
            handle.seek(offset)
            reread = handle.read(len(new))
            ok = reread == new
            journals.append({
                "name": row.get("name"),
                "container": container,
                "journal_offset": offset,
                "claimed_titan_offset": int(row.get("claimed_titan_offset") or 0),
                "len": len(mask),
                "pre_sha256": hashlib.sha256(old).hexdigest(),
                "mask_sha256": hashlib.sha256(mask).hexdigest(),
                "new_sha256": hashlib.sha256(new).hexdigest(),
                "reread": ok,
            })
            if not ok:
                raise RuntimeError(
                    "journal reread mismatch %s @ %s" % (row.get("name"), offset)
                )
    return journals


def apply_plan(titan_path, plan, excerpt_dir):
    """Journaled MOVE. new = old | mask. Re-read each span."""
    journals = []
    with open(titan_path, "r+b") as handle:
        size = os.path.getsize(titan_path)
        for row in plan.get("organs") or []:
            container = os.path.basename(str(row.get("container") or ""))
            excerpt_path = os.path.join(excerpt_dir, container)
            with open(excerpt_path, "rb") as raw_handle:
                mask = raw_handle.read()
            offset = int(row["offset"])
            handle.seek(offset)
            old = handle.read(len(mask))
            new = or_bytes(old, mask)
            handle.seek(offset)
            handle.write(new)
            handle.flush()
            os.fsync(handle.fileno())
            handle.seek(offset)
            reread = handle.read(len(new))
            ok = reread == new
            journals.append({
                "name": row.get("name"),
                "offset": offset,
                "len": len(mask),
                "pre_sha256": hashlib.sha256(old).hexdigest(),
                "new_sha256": hashlib.sha256(new).hexdigest(),
                "reread": ok,
                "past_eof": offset >= size,
            })
            if not ok:
                raise RuntimeError("reread mismatch %s @ %s" % (row.get("name"), offset))
    return journals


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if "--inject" in argv:
        print("REFUSE: --inject 0x01 is WIPE. Law is new=old|mask.")
        return 2
    parser = argparse.ArgumentParser(
        description="Journaled titan MOVE. Default is a plan. --go writes."
    )
    parser.add_argument("--root", default=".", help="clone to read")
    parser.add_argument("--titan", default="", help="titan.gguf path")
    parser.add_argument(
        "--go",
        action="store_true",
        help="write titan.gguf if present. Default is plan-only.",
    )
    parser.add_argument(
        "--journal",
        action="store_true",
        help="OR-write the 31 excerpt binaries into a public journal and reread.",
    )
    parser.add_argument(
        "--journal-bin",
        default="",
        help="optional journal image path. Default is a temp file.",
    )
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    packet_path = os.path.join(root, PACKET_REL)
    excerpt_dir = os.path.join(root, EXCERPT_REL)
    with open(packet_path, encoding="utf-8") as handle:
        packet = json.load(handle)
    titan_path = find_titan(
        explicit=args.titan or None,
        env_path=os.environ.get("TITAN"),
    )
    live_size = os.path.getsize(titan_path) if titan_path else None
    plan = plan_from_packet(packet, live_size=live_size)
    payload = {
        "measured": True,
        "titan_path": titan_path,
        "titan_present": bool(titan_path),
        "live_size": live_size,
        "go": bool(args.go),
        "journal": bool(args.journal),
        "wrote": False,
        "reread": False,
        "plan": plan,
    }
    if args.journal:
        rows, end = journal_rows(packet.get("organs") or [])
        journal_bin = args.journal_bin or os.path.join(
            tempfile.mkdtemp(prefix="titan-journal-"),
            "titan_move_journal.bin",
        )
        os.makedirs(os.path.dirname(os.path.abspath(journal_bin)), exist_ok=True)
        journals = apply_journal(journal_bin, rows, excerpt_dir)
        reread_ok = all(row["reread"] for row in journals)
        sidecar = {
            "kind": "TITAN_MOVE_PUBLIC_JOURNAL",
            "computer": "titan.gguf is the computer. This journal is the public-tree MOVE.",
            "law": "new = old | mask; ones only rise; re-read before write",
            "count": len(journals),
            "bytes": end,
            "reread": reread_ok,
            "titan": packet.get("titan") or "NOT_WRITTEN",
            "organs": journals,
        }
        sidecar_path = os.path.join(root, JOURNAL_REL)
        with open(sidecar_path, "w", encoding="utf-8") as handle:
            json.dump(sidecar, handle, indent=2)
            handle.write("\n")
        payload["wrote"] = True
        payload["reread"] = reread_ok
        payload["journals"] = journals
        payload["journal_bin"] = journal_bin
        payload["journal_path"] = JOURNAL_REL
        payload["state"] = "CANDIDATE" if reread_ok else "NOT_LANDED"
        payload["note"] = (
            "public journal %s. %s/%s excerpt binaries OR-written and reread. "
            "titan.gguf still %s. Smash/wipe of commons.mno refused."
            % (
                payload["state"],
                len(journals),
                plan["count"],
                packet.get("titan") or "NOT_WRITTEN",
            )
        )
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        print("DIE")
        return 0 if reread_ok else 2
    if not args.go:
        payload["state"] = "CLAIMED" if titan_path else "NOT_LANDED"
        payload["note"] = (
            "plan-only. %s claimed append offsets FROM FILE. "
            "titan %s. Pass --go on the machine that has titan.gguf."
            % (
                plan["count"],
                "present (%s bytes)" % live_size if titan_path else "ABSENT",
            )
        )
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        print("DIE")
        return 0
    if not titan_path:
        payload["state"] = "NOT_LANDED"
        payload["note"] = (
            "titan.gguf ABSENT. dest FROM FILE is %s. "
            "Offsets stay claimed. No write."
            % r"C:\llm\models\titan.gguf"
        )
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        print("DIE")
        return 2
    journals = apply_plan(titan_path, plan, excerpt_dir)
    payload["wrote"] = True
    payload["reread"] = all(row["reread"] for row in journals)
    payload["journals"] = journals
    payload["state"] = "INTEGRATED" if payload["reread"] else "NOT_LANDED"
    payload["note"] = "journaled MOVE. new=old|mask. reread=%s" % payload["reread"]
    packet["titan"] = "WRITTEN"
    packet["claimed_append_base"] = plan["claimed_append_base"]
    packet["organs"] = plan["organs"]
    for row in packet["organs"]:
        row["titan"] = "WRITTEN"
    with open(packet_path, "w", encoding="utf-8") as handle:
        json.dump(packet, handle, indent=2)
        handle.write("\n")
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    print("DIE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
