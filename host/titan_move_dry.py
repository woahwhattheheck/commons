#!/usr/bin/env python3
"""host/titan_move_dry.py — measure the public Titan MOVE packet.

Owner Slack 1787628542.573719: stop dodging the substrate. Organs
1–31 excerpts landed first; the owner-PC write/reread later closed the MOVE.

This instrument reads the public packet and rehashes every excerpt. It does
not open titan.gguf. Persisted write/reread evidence is accepted only when
all counts, sizes, hashes, offsets, and the durable receipt are complete.

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
JOURNAL_REL = os.path.join("excerpts", "20260823", "titan_move_journal.json")
CLOSED_WRITE_RECEIPT = "p/claudelocal-titan-move-go-20260825-01.md"
CLOSED_WRITE_COMMIT = "b3fe1449560a359c87963d113c022ae3b8f86f73"
CLOSED_RECEIPT_MARKERS = (
    "id: claudelocal-titan-move-go-20260825-01",
    "state INTEGRATED, wrote=true, reread=true",
    "31/31 organs journaled, 31/31 reread true, 31/31 past_eof",
    "titan.gguf after: 103812669582 bytes (+9319291",
)


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
    sha_ok = int(row.get("sha_ok") or 0)
    wrote = row.get("wrote") is True
    reread = row.get("reread") is True
    write_count = int(row.get("write_count") or 0)
    reread_count = int(row.get("reread_count") or 0)
    past_eof_count = int(row.get("past_eof_count") or 0)
    packet_state = str(row.get("packet_state") or "").upper()
    before = int(row.get("titan_size_before") or 0)
    after = int(row.get("titan_size_after") or 0)
    written_bytes = int(row.get("written_bytes") or 0)
    write_receipt = str(row.get("write_receipt") or "")
    base = int(row.get("claimed_append_base") or 0)
    end = int(row.get("claimed_append_end") or 0)
    journal_reread = row.get("journal_reread") is True
    journal_count = int(row.get("journal_count") or 0)
    plan_structure_complete = row.get("plan_structure_complete") is True
    execution_complete = (
        written == "WRITTEN"
        and packet_state == "INTEGRATED"
        and wrote
        and reread
        and count >= 31
        and excerpts == count
        and sha_ok == count
        and nonzero == count
        and row.get("structure_complete") is True
        and row.get("write_receipt_exists") is True
        and row.get("write_receipt_content_ok") is True
        and row.get("integrated_commit_ok") is True
        and row.get("legacy_aliases_ok") is True
        and write_count == count
        and reread_count == count
        and past_eof_count == count
        and before == base
        and after == end
        and written_bytes == end - base
        and written_bytes > 0
        and bool(write_receipt)
    )
    if execution_complete:
        return {
            "state": "INTEGRATED",
            "note": (
                "Titan write and reread measured for %s organs; %s bytes "
                "appended; receipt %s."
            )
            % (count, written_bytes, write_receipt),
        }
    if excerpts < 31:
        return {
            "state": "NOT_LANDED",
            "note": (
                "only %s/31 excerpts on this tree. Pull/reconcile the landed "
                "owner receipt %s; this MOVE is closed, so do not append."
            )
            % (excerpts, CLOSED_WRITE_RECEIPT),
        }
    if (
        written == "NOT_WRITTEN"
        and journal_reread
        and journal_count >= 31
        and nonzero == count
        and count >= 31
        and plan_structure_complete
    ):
        return {
            "state": "CANDIDATE",
            "note": (
                "%s/31 historical excerpt binaries are journaled, but this "
                "public packet regressed to NOT_WRITTEN. Reconcile it from "
                "%s; do not append or reopen owner action."
            )
            % (journal_count, CLOSED_WRITE_RECEIPT),
        }
    if (
        written == "NOT_WRITTEN"
        and nonzero == count
        and count >= 31
        and plan_structure_complete
    ):
        return {
            "state": "CLAIMED",
            "note": (
                "%s/31 historical claimed append offsets are structurally "
                "complete, but this MOVE is already closed. Reconcile the "
                "landed WRITTEN packet from %s; do not append."
            )
            % (excerpts, CLOSED_WRITE_RECEIPT),
        }
    if written == "NOT_WRITTEN" or nonzero == 0:
        return {
            "state": "NOT_LANDED",
            "note": (
                "%s/31 excerpts on this tree, but NOT_WRITTEN plan evidence "
                "is missing or inconsistent. Repair public evidence from "
                "%s; do not allocate or append a closed MOVE."
            )
            % (excerpts, CLOSED_WRITE_RECEIPT),
        }
    if written == "WRITTEN":
        return {
            "state": "NOT_LANDED",
            "note": (
                "packet says WRITTEN but complete write/reread evidence is "
                "missing or inconsistent. Refuse marker-only integration."
            ),
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
    len_ok = 0
    nonzero = 0
    missing = []
    count = int(packet.get("count") or len(organs))
    canonical_containers = {
        entry
        for entry in os.listdir(excerpt_dir)
        if entry.endswith(".mno")
        and os.path.isfile(os.path.join(excerpt_dir, entry))
    } if os.path.isdir(excerpt_dir) else set()
    try:
        base = int(packet.get("claimed_append_base"))
        end = int(packet.get("claimed_append_end"))
    except (TypeError, ValueError):
        base, end = -1, -1
    expected_offset = base
    names = set()
    containers = set()
    declared_paths = set()
    geometry_count = 0
    row_state_count = 0
    plan_state_count = 0
    source_shape_count = 0
    for row in organs:
        name = str(row.get("name") or "")
        declared_container = str(row.get("container") or "")
        container = os.path.basename(declared_container)
        declared_path = str(row.get("path") or "")
        expected_container = name + ".mno" if name else ""
        expected_path = EXCERPT_REL.replace(os.sep, "/") + "/" + container
        expected_sha = str(row.get("sha256") or "").lower()
        try:
            offset = int(row.get("offset"))
            declared_len = int(row.get("len"))
            int(expected_sha, 16)
        except (TypeError, ValueError):
            offset, declared_len = -1, -1
        source_shape_ok = (
            bool(name)
            and name not in names
            and bool(container)
            and container not in containers
            and declared_container == container
            and container == expected_container
            and container in canonical_containers
            and bool(declared_path)
            and declared_path not in declared_paths
            and declared_path == expected_path
            and declared_len > 0
            and len(expected_sha) == 64
        )
        if source_shape_ok:
            source_shape_count += 1
        if name:
            names.add(name)
        if container:
            containers.add(container)
        if declared_path:
            declared_paths.add(declared_path)
        if offset > 0:
            nonzero += 1
        if source_shape_ok and offset == expected_offset:
            geometry_count += 1
        if declared_len > 0:
            expected_offset += declared_len
        if str(row.get("titan") or "").upper() == "WRITTEN":
            row_state_count += 1
        if str(row.get("titan") or "").upper() == "NOT_WRITTEN":
            plan_state_count += 1
        if not container:
            missing.append("(unnamed)")
            continue
        path = os.path.join(excerpt_dir, container)
        if not os.path.isfile(path):
            missing.append(container)
            continue
        excerpt_count += 1
        with open(path, "rb") as handle:
            raw = handle.read()
        if len(raw) == declared_len:
            len_ok += 1
        if hashlib.sha256(raw).hexdigest() == expected_sha:
            sha_ok += 1
    canonical_membership_complete = (
        count == len(organs) == 31
        and len(canonical_containers) == 31
        and containers == canonical_containers
        and len(names) == 31
        and len(declared_paths) == 31
    )
    common_structure_complete = (
        canonical_membership_complete
        and source_shape_count == count
        and geometry_count == count
        and len_ok == count
        and sha_ok == count
        and expected_offset == end
        and base > 0
    )
    structure_complete = common_structure_complete and row_state_count == count
    plan_structure_complete = (
        common_structure_complete and plan_state_count == count
    )
    write_receipt = str(packet.get("write_receipt") or "")
    root = os.path.abspath(os.path.join(excerpt_dir, "..", ".."))
    receipt_norm = os.path.normpath(write_receipt).replace("\\", "/")
    receipt_path = os.path.join(root, write_receipt)
    write_receipt_exists = (
        write_receipt == CLOSED_WRITE_RECEIPT
        and receipt_norm == write_receipt
        and os.path.isfile(receipt_path)
    )
    receipt_body = ""
    if write_receipt_exists:
        with open(receipt_path, encoding="utf-8") as handle:
            receipt_body = handle.read()
    write_receipt_content_ok = write_receipt_exists and all(
        marker in receipt_body for marker in CLOSED_RECEIPT_MARKERS
    )
    integrated_commit = str(packet.get("integrated_commit") or "").lower()
    integrated_commit_ok = integrated_commit == CLOSED_WRITE_COMMIT
    titan_size_before = int(packet.get("titan_size_before") or 0)
    titan_size_after = int(packet.get("titan_size_after") or 0)
    live_size_before = int(packet.get("live_size_before") or 0)
    live_size_after = int(packet.get("live_size_after") or 0)
    legacy_aliases_ok = (
        int(packet.get("write_count") or 0) == count
        and live_size_before == titan_size_before
        and live_size_after == titan_size_after
    )
    return {
        "measured": True,
        "kind": packet.get("kind") or "TITAN_MOVE_PACKET",
        "count": count,
        "excerpt_count": excerpt_count,
        "sha_ok": sha_ok,
        "len_ok": len_ok,
        "titan": packet.get("titan") or "NOT_WRITTEN",
        "nonzero_offsets": nonzero,
        "claimed_append_base": base,
        "claimed_append_end": end,
        "geometry_count": geometry_count,
        "row_state_count": row_state_count,
        "plan_state_count": plan_state_count,
        "source_shape_count": source_shape_count,
        "canonical_container_count": len(canonical_containers),
        "unique_container_count": len(containers),
        "unique_path_count": len(declared_paths),
        "canonical_membership_complete": canonical_membership_complete,
        "structure_complete": structure_complete,
        "plan_structure_complete": plan_structure_complete,
        "packet_state": packet.get("state") or "",
        "wrote": packet.get("wrote") is True,
        "reread": packet.get("reread") is True,
        "write_count": int(packet.get("write_count") or 0),
        "reread_count": int(packet.get("reread_count") or 0),
        "past_eof_count": int(packet.get("past_eof_count") or 0),
        "titan_size_before": titan_size_before,
        "titan_size_after": titan_size_after,
        "live_size_before": live_size_before,
        "live_size_after": live_size_after,
        "legacy_aliases_ok": legacy_aliases_ok,
        "written_bytes": int(packet.get("written_bytes") or 0),
        "write_receipt": write_receipt,
        "write_receipt_exists": write_receipt_exists,
        "write_receipt_content_ok": write_receipt_content_ok,
        "integrated_commit": integrated_commit,
        "integrated_commit_ok": integrated_commit_ok,
        "journal_reread": False,
        "journal_count": 0,
        "missing": missing,
        "computer": "titan.gguf is the computer. This packet is not.",
    }


def owner_blocker(row, verdict):
    """Historical schema, now a public-evidence reconciliation receipt."""
    excerpts = int((row or {}).get("excerpt_count") or 0)
    return {
        "NEED": (
            "Reconcile the public packet from the landed owner-PC receipt "
            "%s. No new Titan write is needed." % CLOSED_WRITE_RECEIPT
        ),
        "WHY_ONLY_BRYCE": (
            "No Bryce-only action remains: the owner-PC write and reread are "
            "already durable. Public evidence can be repaired by any peer."
        ),
        "SMALLEST_ACTION": (
            "Pull current main or restore the exact WRITTEN packet fields "
            "from the pinned receipt. Do not run --go, reallocate, or append."
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
            "Land desk titanMoveState returns INTEGRATED from the exact "
            "receipt, commit, sizes, geometry, hashes, and 31/31 reread."
        ),
    }


def closure_evidence(row):
    """Compact durable closure for an already integrated MOVE."""
    row = row or {}
    return {
        "state": "INTEGRATED",
        "receipt": row.get("write_receipt"),
        "integrated_commit": row.get("integrated_commit"),
        "reread_count": int(row.get("reread_count") or 0),
        "past_eof_count": int(row.get("past_eof_count") or 0),
        "titan_size_before": int(row.get("titan_size_before") or 0),
        "titan_size_after": int(row.get("titan_size_after") or 0),
        "written_bytes": int(row.get("written_bytes") or 0),
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
    journal_path = os.path.join(root, JOURNAL_REL)
    if os.path.isfile(journal_path):
        with open(journal_path, encoding="utf-8") as handle:
            journal = json.load(handle)
        row["journal_reread"] = journal.get("reread") is True
        row["journal_count"] = int(journal.get("count") or 0)
        row["journal_path"] = JOURNAL_REL
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
    if verdict.get("state") == "INTEGRATED":
        payload["closure_evidence"] = closure_evidence(row)
    else:
        payload["reconciliation_needed"] = owner_blocker(row, verdict)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if row.get("measured") else 2


if __name__ == "__main__":
    sys.exit(main())
