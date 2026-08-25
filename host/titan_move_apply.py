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
CLOSED_WRITE_RECEIPT = "p/claudelocal-titan-move-go-20260825-01.md"
CLOSED_WRITE_COMMIT = "b3fe1449560a359c87963d113c022ae3b8f86f73"
CLOSED_RECEIPT_MARKERS = (
    "id: claudelocal-titan-move-go-20260825-01",
    "state INTEGRATED, wrote=true, reread=true",
    "31/31 organs journaled, 31/31 reread true, 31/31 past_eof",
    "titan.gguf after: 103812669582 bytes (+9319291",
)


def atomic_write_json(path, payload):
    """Replace a JSON state file atomically in its own directory."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".titan-move-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def persisted_execution_complete(packet, root=None):
    """Whether the public packet carries a complete apply+reread attestation."""
    packet = packet or {}
    count = int(packet.get("count") or 0)
    organs = list(packet.get("organs") or [])
    base = int(packet.get("claimed_append_base") or -1)
    end = int(packet.get("claimed_append_end") or -1)
    before = int(packet.get("titan_size_before") or 0)
    after = int(packet.get("titan_size_after") or 0)
    written_bytes = int(packet.get("written_bytes") or 0)
    top_complete = (
        str(packet.get("titan") or "").upper() == "WRITTEN"
        and str(packet.get("state") or "").upper() == "INTEGRATED"
        and packet.get("wrote") is True
        and packet.get("reread") is True
        and count == len(organs)
        and count > 0
        and int(packet.get("write_count") or 0) == count
        and int(packet.get("reread_count") or 0) == count
        and int(packet.get("past_eof_count") or 0) == count
        and before == base
        and after == end
        and int(packet.get("live_size_before") or 0) == before
        and int(packet.get("live_size_after") or 0) == after
        and written_bytes == end - base
        and written_bytes > 0
        and packet.get("write_receipt") == CLOSED_WRITE_RECEIPT
        and packet.get("integrated_commit") == CLOSED_WRITE_COMMIT
    )
    if not top_complete:
        return False
    if not root:
        return False
    receipt_path = os.path.join(os.path.abspath(root), CLOSED_WRITE_RECEIPT)
    if not os.path.isfile(receipt_path):
        return False
    with open(receipt_path, encoding="utf-8") as handle:
        receipt_body = handle.read()
    if not all(marker in receipt_body for marker in CLOSED_RECEIPT_MARKERS):
        return False
    expected_offset = base
    names = set()
    containers = set()
    excerpt_dir = os.path.join(os.path.abspath(root), EXCERPT_REL)
    for row in organs:
        name = str(row.get("name") or "")
        declared_container = str(row.get("container") or "")
        container = os.path.basename(declared_container)
        source_digest = str(row.get("sha256") or "").lower()
        digest = str(
            row.get("written_sha256") or row.get("sha256") or ""
        ).lower()
        try:
            offset = int(row.get("offset"))
            length = int(row.get("len"))
            int(digest, 16)
            int(source_digest, 16)
        except (TypeError, ValueError):
            return False
        if (
            not name
            or name in names
            or not container
            or declared_container != container
            or container != name + ".mno"
            or container in containers
            or offset != expected_offset
            or length <= 0
            or len(digest) != 64
            or len(source_digest) != 64
            or str(row.get("titan") or "").upper() != "WRITTEN"
        ):
            return False
        excerpt_path = os.path.join(excerpt_dir, container)
        if not os.path.isfile(excerpt_path):
            return False
        with open(excerpt_path, "rb") as handle:
            source = handle.read()
        if (
            len(source) != length
            or hashlib.sha256(source).hexdigest() != source_digest
        ):
            return False
        names.add(name)
        containers.add(container)
        expected_offset += length
    return (
        expected_offset == end
        and len(names) == count
        and len(containers) == count
    )


def validate_titan_context(titan_path):
    """Measure GGUF format context without restricting the caller's path."""
    with open(titan_path, "rb") as handle:
        magic = handle.read(4)
    if magic != b"GGUF":
        raise RuntimeError("target is not a measured GGUF artifact")
    return True


def verify_written_packet(titan_path, packet):
    """Reread a packet already marked WRITTEN without allocating or writing.

    The persisted digest is ``written_sha256`` when a MOVE overlaid existing
    bytes, otherwise the excerpt ``sha256`` is also the written digest (the
    current 31-organ MOVE was a pure append). Any missing or malformed span
    fails closed. This is the idempotency guard for ``--go``.
    """
    packet = packet or {}
    organs = list(packet.get("organs") or [])
    expected_count = int(packet.get("count") or len(organs))
    titan_size = os.path.getsize(titan_path)
    before = int(packet.get("titan_size_before") or 0)
    claimed_base = int(packet.get("claimed_append_base") or -1)
    claimed_end = int(packet.get("claimed_append_end") or -1)
    rows = []
    exact_count = 0
    previous_end = claimed_base
    names = set()
    containers = set()
    with open(titan_path, "rb") as handle:
        for source in organs:
            row = dict(source)
            try:
                offset = int(row.get("offset"))
                length = int(row.get("len"))
            except (TypeError, ValueError):
                offset, length = -1, -1
            expected = str(
                row.get("written_sha256") or row.get("sha256") or ""
            ).lower()
            name = str(row.get("name") or "")
            declared_container = str(row.get("container") or "")
            container = os.path.basename(declared_container)
            geometry_ok = (
                offset >= 0
                and length > 0
                and offset == previous_end
                and offset + length <= titan_size
                and len(expected) == 64
                and bool(name)
                and name not in names
                and bool(container)
                and declared_container == container
                and container == name + ".mno"
                and container not in containers
            )
            actual = ""
            if geometry_ok:
                handle.seek(offset)
                actual = hashlib.sha256(handle.read(length)).hexdigest()
            exact = geometry_ok and actual == expected
            if exact:
                exact_count += 1
            rows.append({
                "name": name,
                "container": container,
                "offset": offset,
                "len": length,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "reread": exact,
                "past_eof": bool(before and offset >= before),
            })
            if geometry_ok:
                previous_end = offset + length
                names.add(name)
                containers.add(container)
    count_ok = expected_count == len(organs) and expected_count > 0
    geometry_complete = (
        claimed_base >= 0
        and previous_end == claimed_end
        and titan_size >= claimed_end
        and len(names) == expected_count
        and len(containers) == expected_count
    )
    reread = count_ok and geometry_complete and exact_count == expected_count
    return {
        "kind": "TITAN_MOVE_EXISTING_REREAD",
        "count": expected_count,
        "exact_count": exact_count,
        "reread": reread,
        "titan_size": titan_size,
        "claimed_append_base": claimed_base,
        "claimed_append_end": claimed_end,
        "geometry_complete": geometry_complete,
        "organs": rows,
    }


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


def preflight_plan(plan, excerpt_dir):
    """Read and hash every source plus exact allocation before any write."""
    organs = list((plan or {}).get("organs") or [])
    count = int((plan or {}).get("count") or len(organs))
    expected_offset = int((plan or {}).get("claimed_append_base") or -1)
    expected_end = int((plan or {}).get("claimed_append_end") or -1)
    names = set()
    containers = set()
    prepared = []
    if count != len(organs) or count <= 0 or expected_offset < 0:
        raise RuntimeError("invalid MOVE count/base")
    for row in organs:
        name = str(row.get("name") or "")
        declared_container = str(row.get("container") or "")
        container = os.path.basename(declared_container)
        offset = int(row.get("offset") or -1)
        length = int(row.get("len") or -1)
        if not name or name in names:
            raise RuntimeError("duplicate/empty organ name %r" % name)
        if (
            not container
            or declared_container != container
            or container != name + ".mno"
            or container in containers
        ):
            raise RuntimeError(
                "invalid/duplicate source container %r for %s"
                % (declared_container, name)
            )
        if offset != expected_offset or length <= 0:
            raise RuntimeError("non-contiguous MOVE geometry %s" % name)
        excerpt_path = os.path.join(excerpt_dir, container)
        with open(excerpt_path, "rb") as raw_handle:
            mask = raw_handle.read()
        digest = hashlib.sha256(mask).hexdigest()
        if len(mask) != length or digest != str(row.get("sha256") or ""):
            raise RuntimeError("excerpt len/sha mismatch %s" % name)
        prepared.append((row, mask))
        names.add(name)
        containers.add(container)
        expected_offset += length
    if expected_offset != expected_end:
        raise RuntimeError("claimed append end mismatch")
    return prepared


def verify_applying_prefix(titan_path, plan, prepared, original_size):
    """An append retry may only continue an exact prefix at its fixed base."""
    base = int((plan or {}).get("claimed_append_base") or -1)
    end = int((plan or {}).get("claimed_append_end") or -1)
    size = os.path.getsize(titan_path)
    origin = int(original_size)
    if origin != base:
        raise RuntimeError("APPLYING original size/base mismatch")
    if size < origin or size > end:
        raise RuntimeError("APPLYING live size is outside fixed append span")
    expected = b"".join(mask for _, mask in prepared)
    prefix_len = size - base
    with open(titan_path, "rb") as handle:
        handle.seek(base)
        actual = handle.read(prefix_len)
    if actual != expected[:prefix_len]:
        raise RuntimeError("APPLYING target tail is not the exact written prefix")
    return {"live_size": size, "resume_bytes": prefix_len}


def apply_plan(
    titan_path, plan, excerpt_dir, original_size=None, prepared=None
):
    """Journaled MOVE. Preflight all sources, write, then re-read each span."""
    prepared = prepared if prepared is not None else preflight_plan(plan, excerpt_dir)
    journals = []
    with open(titan_path, "r+b") as handle:
        size = os.path.getsize(titan_path)
        origin = int(size if original_size is None else original_size)
        for row, mask in prepared:
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
                "pre_sha256": str(
                    row.get("pre_sha256") or hashlib.sha256(old).hexdigest()
                ),
                "resume_pre_sha256": hashlib.sha256(old).hexdigest(),
                "new_sha256": hashlib.sha256(new).hexdigest(),
                "reread": ok,
                "past_eof": offset >= origin,
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
    packet_written = str(packet.get("titan") or "").upper() == "WRITTEN"
    packet_applying = str(packet.get("state") or "").upper() == "APPLYING"
    fixed_allocation = packet_written or packet_applying
    # WRITTEN and APPLYING packets keep their original allocation. Reallocating
    # from a now-larger live size would duplicate a completed or partial MOVE.
    plan = plan_from_packet(
        packet,
        live_size=None if fixed_allocation else live_size,
    )
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
    if packet_written and args.journal:
        complete = persisted_execution_complete(packet, root=root)
        payload["already_written"] = True
        payload["state"] = "INTEGRATED" if complete else "NOT_LANDED"
        payload["reread"] = packet.get("reread") is True
        payload["note"] = (
            "Titan MOVE is already persisted as INTEGRATED; historical public "
            "journal left unchanged."
            if complete
            else "packet says WRITTEN without a complete execution attestation; journal left unchanged."
        )
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        print("DIE")
        return 0 if complete else 2
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
        complete = persisted_execution_complete(packet, root=root)
        if packet_written:
            payload["already_written"] = True
            payload["reread"] = packet.get("reread") is True
            payload["state"] = "INTEGRATED" if complete else "NOT_LANDED"
            payload["note"] = (
                "persisted Titan MOVE execution is INTEGRATED; no new plan "
                "allocated. Use --go with titan present for a fresh read-only reread."
                if complete
                else "packet says WRITTEN without complete execution evidence; no new plan allocated."
            )
        else:
            payload["state"] = "CLAIMED" if titan_path else "NOT_LANDED"
            payload["note"] = (
                "plan-only. %s fixed append offsets FROM FILE. "
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
        complete = persisted_execution_complete(packet, root=root)
        if packet_written and complete:
            payload["already_written"] = True
            payload["reread"] = True
            payload["state"] = "INTEGRATED"
            payload["note"] = (
                "persisted Titan MOVE execution is INTEGRATED; titan.gguf is "
                "absent here, so no fresh reread was attempted and no write is needed."
            )
        else:
            payload["state"] = "NOT_LANDED"
            payload["note"] = (
                "titan.gguf ABSENT. dest FROM FILE is %s. "
                "Offsets stay fixed. No write."
                % r"C:\llm\models\titan.gguf"
            )
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        print("DIE")
        return 0 if packet_written and complete else 2
    validate_titan_context(titan_path)
    if packet_written:
        verification = verify_written_packet(titan_path, packet)
        durable_complete = persisted_execution_complete(packet, root=root)
        payload["already_written"] = True
        payload["verification"] = verification
        payload["journals"] = verification["organs"]
        payload["reread"] = verification["reread"]
        payload["state"] = (
            "INTEGRATED"
            if verification["reread"] and durable_complete
            else "NOT_LANDED"
        )
        payload["note"] = (
            "packet already WRITTEN; performed read-only exact reread of "
            "%s/%s spans. No allocation and no write.%s"
            % (
                verification["exact_count"],
                verification["count"],
                ""
                if durable_complete
                else " Durable closure evidence is still missing.",
            )
        )
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        print("DIE")
        return 0 if verification["reread"] else 2
    # Validate every source and exact fixed geometry before changing packet or
    # titan. Then persist APPLYING atomically so a crash retries these offsets.
    prepared = preflight_plan(plan, excerpt_dir)
    original_size = int(packet.get("titan_size_before") or live_size)
    if packet_applying:
        empty_sha256 = hashlib.sha256(b"").hexdigest()
        for row in plan["organs"]:
            try:
                pre_len = int(row.get("pre_len"))
            except (TypeError, ValueError):
                pre_len = -1
            if (
                pre_len != 0
                or str(row.get("pre_sha256") or "").lower() != empty_sha256
            ):
                raise RuntimeError("APPLYING packet lacks original preimage evidence")
    else:
        # Every first MOVE allocation starts at the live EOF, so each original
        # preimage is the empty byte string. Persist that before any target byte.
        if int(live_size) != int(plan["claimed_append_base"]):
            raise RuntimeError("first MOVE base is not live EOF")
        for row in plan["organs"]:
            row["pre_len"] = 0
            row["pre_sha256"] = hashlib.sha256(b"").hexdigest()
    resume = verify_applying_prefix(
        titan_path, plan, prepared, original_size=original_size
    )
    payload["resume"] = resume
    if not packet_applying:
        packet["state"] = "APPLYING"
        packet["wrote"] = False
        packet["reread"] = False
        packet["write_count"] = 0
        packet["reread_count"] = 0
        packet["past_eof_count"] = 0
        packet["titan_size_before"] = int(live_size)
        packet["titan_size_after"] = None
        packet["live_size_before"] = int(live_size)
        packet["live_size_after"] = None
        packet["written_bytes"] = 0
        packet["claimed_append_base"] = plan["claimed_append_base"]
        packet["claimed_append_end"] = plan["claimed_append_end"]
        packet["organs"] = plan["organs"]
        atomic_write_json(packet_path, packet)
    journals = apply_plan(
        titan_path,
        plan,
        excerpt_dir,
        original_size=original_size,
        prepared=prepared,
    )
    payload["wrote"] = True
    payload["reread"] = all(row["reread"] for row in journals)
    payload["journals"] = journals
    payload["state"] = "NOT_LANDED"
    payload["execution_state"] = "WRITTEN"
    payload["note"] = (
        "journaled MOVE locally. new=old|mask. reread=%s. Target execution "
        "is WRITTEN, but Commons integration remains NOT_LANDED until its "
        "durable receipt and integrated main commit are attached."
        % payload["reread"]
    )
    packet["titan"] = "WRITTEN"
    packet["state"] = "WRITTEN"
    packet["wrote"] = True
    packet["reread"] = payload["reread"]
    packet["write_count"] = len(journals)
    packet["reread_count"] = sum(1 for row in journals if row["reread"])
    packet["past_eof_count"] = sum(1 for row in journals if row["past_eof"])
    packet["titan_size_before"] = original_size
    packet["titan_size_after"] = os.path.getsize(titan_path)
    packet["live_size_before"] = packet["titan_size_before"]
    packet["live_size_after"] = packet["titan_size_after"]
    packet["written_bytes"] = packet["titan_size_after"] - original_size
    packet["claimed_append_base"] = plan["claimed_append_base"]
    packet["claimed_append_end"] = plan["claimed_append_end"]
    packet["organs"] = plan["organs"]
    journal_by_name = {row.get("name"): row for row in journals}
    for row in packet["organs"]:
        journal = journal_by_name.get(row.get("name")) or {}
        row["titan"] = "WRITTEN"
        row["written_sha256"] = journal.get("new_sha256")
        row["reread"] = journal.get("reread") is True
        row["past_eof"] = journal.get("past_eof") is True
    atomic_write_json(packet_path, packet)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    print("DIE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
