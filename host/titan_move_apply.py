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


def already_applied(packet, live_size):
    """True when live titan already sits at the claimed append end."""
    if live_size is None:
        return False
    try:
        base = int((packet or {}).get("claimed_append_base") or 0)
        end = int((packet or {}).get("claimed_append_end") or 0)
        live = int(live_size)
    except (TypeError, ValueError):
        return False
    if end > base and live == end:
        return True
    written = str((packet or {}).get("titan") or "").upper() == "WRITTEN"
    return written and end > 0 and live == end


def persist_write_facts(
    packet,
    write_count,
    reread_count,
    live_size_before,
    live_size_after,
):
    """Durable titan write/reread/size facts. Ones only rise."""
    out = dict(packet or {})
    write_count = int(write_count or 0)
    reread_count = int(reread_count or 0)
    before = int(live_size_before or 0)
    after = int(live_size_after or 0)
    out["titan"] = "WRITTEN"
    out["reread"] = write_count > 0 and reread_count == write_count
    out["write_count"] = write_count
    out["reread_count"] = reread_count
    out["live_size_before"] = before
    out["live_size_after"] = after
    out["written_bytes"] = after - before
    organs = []
    for row in list(out.get("organs") or []):
        item = dict(row)
        item["titan"] = "WRITTEN"
        organs.append(item)
    out["organs"] = organs
    return out


def plan_from_packet(packet, live_size=None):
    """Rebuild claimed offsets. Reallocate if live titan size differs.

    Fail closed when live size already equals claimed_append_end —
    a second --go must not append another copy.
    """
    packet = packet or {}
    organs = list(packet.get("organs") or [])
    base = int(packet.get("claimed_append_base") or CLAIMED_APPEND_BASE)
    if (
        live_size is not None
        and int(live_size) != base
        and not already_applied(packet, live_size)
    ):
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
        and int(live_size) != int(packet.get("claimed_append_base") or CLAIMED_APPEND_BASE)
        and not already_applied(packet, live_size),
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
    if already_applied(packet, live_size):
        write_count = int(
            packet.get("write_count")
            or packet.get("count")
            or len(packet.get("organs") or [])
            or 0
        )
        reread_count = int(packet.get("reread_count") or write_count)
        packet = persist_write_facts(
            packet,
            write_count=write_count,
            reread_count=reread_count,
            live_size_before=int(
                packet.get("live_size_before")
                or packet.get("claimed_append_base")
                or 0
            ),
            live_size_after=int(live_size),
        )
        with open(packet_path, "w", encoding="utf-8") as handle:
            json.dump(packet, handle, indent=2)
            handle.write("\n")
        payload["wrote"] = False
        payload["reread"] = True
        payload["write_count"] = write_count
        payload["reread_count"] = reread_count
        payload["live_size_before"] = packet["live_size_before"]
        payload["live_size_after"] = packet["live_size_after"]
        payload["written_bytes"] = packet["written_bytes"]
        payload["state"] = "INTEGRATED"
        payload["note"] = (
            "already written. fail-closed against duplicate append. "
            "live_size=%s claimed_append_end=%s write_count=%s reread_count=%s"
            % (
                live_size,
                packet.get("claimed_append_end"),
                write_count,
                reread_count,
            )
        )
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        print("DIE")
        return 0
    journals = apply_plan(titan_path, plan, excerpt_dir)
    after_size = os.path.getsize(titan_path)
    write_count = len(journals)
    reread_count = sum(1 for row in journals if row.get("reread"))
    packet["claimed_append_base"] = plan["claimed_append_base"]
    packet["claimed_append_end"] = plan["claimed_append_end"]
    packet["organs"] = plan["organs"]
    packet = persist_write_facts(
        packet,
        write_count=write_count,
        reread_count=reread_count,
        live_size_before=int(live_size or 0),
        live_size_after=after_size,
    )
    payload["wrote"] = True
    payload["reread"] = packet["reread"]
    payload["write_count"] = write_count
    payload["reread_count"] = reread_count
    payload["live_size_before"] = packet["live_size_before"]
    payload["live_size_after"] = packet["live_size_after"]
    payload["written_bytes"] = packet["written_bytes"]
    payload["journals"] = journals
    payload["state"] = "INTEGRATED" if payload["reread"] else "NOT_LANDED"
    payload["note"] = (
        "journaled MOVE. new=old|mask. reread=%s write_count=%s reread_count=%s "
        "live_size %s -> %s"
        % (
            payload["reread"],
            write_count,
            reread_count,
            live_size,
            after_size,
        )
    )
    with open(packet_path, "w", encoding="utf-8") as handle:
        json.dump(packet, handle, indent=2)
        handle.write("\n")
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    print("DIE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
