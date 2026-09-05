#!/usr/bin/env python3
"""Relationship handoff over the existing LLM-native GTM floor.

CRM6: a successor peer continues a real relationship from evidence, not from
an invented summary. Canonical CRM stays Airtable JOJO Revenue Recovery CRM /
Revenue Pipeline. This module does not mint a second CRM, does not contact
customers, and does not rewrite overlay events.

Entry point:
  python3 host/lm_gtm_relationship_handoff.py SUBJECT
  python3 host/lm_gtm_relationship_handoff.py city-of-billings-bid-1421
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "host" / "lm_gtm_index.py"

import importlib.util

_SPEC = importlib.util.spec_from_file_location("lm_gtm_index", HOST)
assert _SPEC and _SPEC.loader
idx = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(idx)

KIND_HANDOFF = "LM_GTM_RELATIONSHIP_HANDOFF"
ACTUAL_MESSAGE = "ACTUAL_MESSAGE"
LEDGER_STATUS = "LEDGER_STATUS"
SUMMARY_POINTER = "SUMMARY_POINTER"
EXPLICIT_SENT_RE = re.compile(
    r"(\bSENT\b|accepted SENT|Attachment E sent|Attachment E SENT)",
    re.IGNORECASE,
)
WANTISH_RE = re.compile(
    r"\b(wants?|request|ask|deadline|due|accepts?|delivered|reopen)\b",
    re.IGNORECASE,
)


def _absent() -> dict[str, Any]:
    return {
        "value": None,
        "status": "ABSENT",
        "evidence": [],
        "provenance": None,
    }


def _sourced(
    value: str,
    evidence: list[str],
    provenance: str,
) -> dict[str, Any]:
    text = (value or "").strip()
    if not text:
        return _absent()
    clean_evidence = [item for item in evidence if isinstance(item, str) and item]
    field = {
        "value": text,
        "status": "SOURCED",
        "evidence": clean_evidence,
        "provenance": provenance,
    }
    blob = json.dumps(field, sort_keys=True, ensure_ascii=False)
    idx._assert_no_pii_in_index_blob(blob)
    return field


def _message_paths(paths: list[str]) -> list[str]:
    return [
        path
        for path in paths
        if isinstance(path, str)
        and (path.startswith("gmail:") or path.startswith("slack:"))
    ]


def _event_paths(event: dict[str, Any]) -> list[str]:
    raw = event.get("source_paths") or []
    return [item for item in raw if isinstance(item, str) and item]


def successor_reads_next_action(packet: dict[str, Any]) -> str | None:
    """Successor peer: read next action from the handoff packet only."""
    fields = packet.get("fields") if isinstance(packet.get("fields"), dict) else {}
    nxt = fields.get("successor_next_action") if isinstance(fields, dict) else None
    if not isinstance(nxt, dict):
        return None
    if nxt.get("status") != "SOURCED":
        return None
    value = nxt.get("value")
    return value if isinstance(value, str) and value.strip() else None


def relationship_handoff(
    subject_id: str,
    paths: dict[str, Path] | None = None,
) -> dict[str, Any]:
    """Compose an evidence-bound relationship handoff for one existing subject."""
    paths = paths or idx.default_paths()
    built = idx.build_index(paths)
    row = next((item for item in built["rows"] if item["id"] == subject_id), None)
    if row is None:
        raise idx.IndexError_(
            f"unknown subject {subject_id!r}: handoff opens existing ledger ids only "
            "and does not mint a contact book"
        )
    if row["role"] not in idx.LIVE_ROLES:
        raise idx.IndexError_(
            f"{subject_id} is {row['role']}; handoff cites live ledger subjects only"
        )

    events = [
        event
        for event in built["events"]
        if event.get("subject_id") == subject_id
    ]
    events_sorted = sorted(events, key=lambda item: str(item.get("ts") or ""))

    evidence_chain = [
        {
            "id": event.get("id"),
            "type": event.get("type"),
            "ts": event.get("ts"),
            "body": event.get("body"),
            "source_paths": _event_paths(event),
        }
        for event in events_sorted
    ]

    # wants: MATERIAL_REPLY bodies first; else ABSENT (never invent)
    wants = _absent()
    for event in reversed(events_sorted):
        if event.get("type") != "MATERIAL_REPLY":
            continue
        body = str(event.get("body") or "")
        paths_e = _event_paths(event)
        provenance = ACTUAL_MESSAGE if _message_paths(paths_e) else SUMMARY_POINTER
        wants = _sourced(body, paths_e + [f"overlay:{event.get('id')}"], provenance)
        break

    # learned: chronological factual STATUS / MATERIAL_REPLY / SENT bodies
    learned_bits: list[str] = []
    learned_evidence: list[str] = []
    for event in events_sorted:
        etype = event.get("type")
        if etype not in {"MATERIAL_REPLY", "STATUS", "SENT_AWAITING_REPLY"}:
            continue
        body = str(event.get("body") or "").strip()
        if not body:
            continue
        learned_bits.append(f"[{etype} {event.get('ts')}] {body}")
        learned_evidence.append(f"overlay:{event.get('id')}")
        learned_evidence.extend(_event_paths(event))
    learned = (
        _sourced(" | ".join(learned_bits), learned_evidence, SUMMARY_POINTER)
        if learned_bits
        else _absent()
    )

    # promised: ONLY explicit SENT language or SENT_AWAITING_REPLY; never invent
    promised = _absent()
    for event in reversed(events_sorted):
        body = str(event.get("body") or "")
        paths_e = _event_paths(event)
        etype = event.get("type")
        if etype == "SENT_AWAITING_REPLY" or EXPLICIT_SENT_RE.search(body):
            msg_paths = _message_paths(paths_e)
            provenance = ACTUAL_MESSAGE if msg_paths else SUMMARY_POINTER
            evidence = (msg_paths or paths_e) + [f"overlay:{event.get('id')}"]
            promised = _sourced(body, evidence, provenance)
            break

    # unresolved + successor next action from composed row (ledger truth)
    next_action = row.get("next_action")
    decision = row.get("decision")
    unresolved_parts: list[str] = []
    if isinstance(decision, str) and decision:
        unresolved_parts.append(f"decision={decision}")
    if row.get("dnr"):
        unresolved_parts.append("dnr=true")
    if isinstance(next_action, str) and next_action.strip():
        unresolved_parts.append(next_action.strip())
    unresolved_evidence = [
        f"overlay:{item}" for item in (row.get("overlay_event_ids") or [])
    ]
    unresolved_evidence.extend(
        [path for path in (row.get("source_paths") or []) if isinstance(path, str)]
    )
    unresolved = (
        _sourced("; ".join(unresolved_parts), unresolved_evidence, LEDGER_STATUS)
        if unresolved_parts
        else _absent()
    )

    successor = (
        _sourced(str(next_action), unresolved_evidence, LEDGER_STATUS)
        if isinstance(next_action, str) and next_action.strip()
        else _absent()
    )

    due = row.get("due")
    due_evidence: list[str] = []
    for event in reversed(events_sorted):
        if event.get("due") == due and due:
            due_evidence = _event_paths(event) + [f"overlay:{event.get('id')}"]
            break
    if not due_evidence and due:
        due_evidence = unresolved_evidence[:]
    next_time = (
        _sourced(str(due), due_evidence, LEDGER_STATUS)
        if isinstance(due, str) and due
        else _absent()
    )

    owner = row.get("owner") or "UNSEATED"
    packet = {
        "schema_version": idx.SCHEMA_VERSION,
        "kind": KIND_HANDOFF,
        "subject_id": subject_id,
        "organization": row.get("organization"),
        "person": row.get("person"),
        "lane": idx.compact_lane(row),
        "decision": row.get("decision"),
        "dnr": bool(row.get("dnr")),
        "due": row.get("due"),
        "route_kind": row.get("route_kind"),
        "route_ref": row.get("route_ref"),
        "canonical_crm": idx.CANONICAL_CRM,
        "cash_usd": 0,
        "transport": "NONE",
        "fields": {
            "wants": wants,
            "learned": learned,
            "promised": promised,
            "unresolved": unresolved,
            "next_time_sensitive": next_time,
            "successor_next_action": successor,
        },
        "evidence_chain": evidence_chain,
        "invent_guard": {
            "emails_forbidden": True,
            "phones_forbidden": True,
            "no_second_crm": True,
            "no_customer_contact": True,
        },
    }
    if owner != "UNSEATED":
        packet["owner"] = owner
    blob = json.dumps(packet, sort_keys=True, ensure_ascii=False)
    idx._assert_no_pii_in_index_blob(blob)
    return packet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "subject",
        help="existing live subject id (e.g. city-of-billings-bid-1421)",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="emit one JSON line instead of pretty JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--send" in argv or argv[:1] == ["send"]:
        sys.stderr.write(
            "REFUSED live send: relationship handoff never transports mail.\n"
        )
        return 3
    args = build_parser().parse_args(argv)
    try:
        packet = relationship_handoff(args.subject)
        if args.jsonl:
            sys.stdout.write(json.dumps(packet, sort_keys=True, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(idx.canonical_text(packet))
        return 0
    except idx.IndexError_ as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
