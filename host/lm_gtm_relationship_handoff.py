#!/usr/bin/env python3
"""Relationship handoff over the existing LLM-native GTM floor.

CRM6: a successor peer continues a real relationship from evidence, not from
an invented summary. Canonical CRM stays Airtable JOJO Revenue Recovery CRM /
Revenue Pipeline. This module does not mint a second CRM, contact customers,
or rewrite the canonical GTM overlay. A small, source-pointer-only relationship
evidence file may add newer facts needed for handoff without copying private
messages into Git.

Entry point:
  python3 host/lm_gtm_relationship_handoff.py SUBJECT
  python3 host/lm_gtm_relationship_handoff.py city-of-billings-bid-1421
"""

from __future__ import annotations

import argparse
import json
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
KIND_RELATIONSHIP_EVIDENCE = "LM_GTM_RELATIONSHIP_EVIDENCE"
RELATIONSHIP_EVIDENCE_REL = "revenue/lm_gtm_index/relationship_handoff_evidence.jsonl"
RELATIONSHIP_EVIDENCE_TYPES = frozenset(
    {"MATERIAL_REPLY", "SENT_AWAITING_REPLY", "STATUS"}
)
SOURCE_INDEX_OVERLAY = "INDEX_OVERLAY"
SOURCE_RELATIONSHIP_EVIDENCE = "RELATIONSHIP_EVIDENCE"
LEDGER_STATUS = "LEDGER_STATUS"
SUMMARY_POINTER = "SUMMARY_POINTER"
_INTERNAL_SOURCE = "_handoff_source"


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


def _event_paths(event: dict[str, Any]) -> list[str]:
    raw = event.get("source_paths") or []
    return [item for item in raw if isinstance(item, str) and item]


def _event_ref(event: dict[str, Any]) -> str:
    prefix = (
        "relationship"
        if event.get(_INTERNAL_SOURCE) == SOURCE_RELATIONSHIP_EVIDENCE
        else "overlay"
    )
    return f"{prefix}:{event.get('id')}"


def _relationship_evidence_path(paths: dict[str, Path]) -> Path:
    root = Path(paths.get("root") or ROOT)
    return root / RELATIONSHIP_EVIDENCE_REL


def _load_relationship_evidence(
    paths: dict[str, Path],
    canonical_event_ids: set[str],
) -> list[dict[str, Any]]:
    """Load pointer-only evidence used by handoff, not by the canonical INDEX."""
    evidence_path = _relationship_evidence_path(paths)
    rows = idx.load_jsonl(evidence_path)
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for source in rows:
        record = dict(source)
        event_id = record.get("id")
        subject_id = record.get("subject_id")
        event_type = record.get("type")
        if record.get("schema_version") != idx.SCHEMA_VERSION:
            raise idx.IndexError_(
                f"relationship evidence {event_id!r} has wrong schema_version"
            )
        if record.get("kind") != KIND_RELATIONSHIP_EVIDENCE:
            raise idx.IndexError_(
                f"relationship evidence {event_id!r} is not {KIND_RELATIONSHIP_EVIDENCE}"
            )
        if not isinstance(event_id, str) or not idx.EVENT_ID_RE.fullmatch(event_id):
            raise idx.IndexError_(f"illegal relationship evidence id: {event_id!r}")
        if event_id in seen or event_id in canonical_event_ids:
            raise idx.IndexError_(f"relationship evidence id collision: {event_id}")
        seen.add(event_id)
        if not isinstance(subject_id, str) or not idx.SUBJECT_RE.fullmatch(subject_id):
            raise idx.IndexError_(
                f"relationship evidence {event_id} missing legal subject_id"
            )
        if event_type not in RELATIONSHIP_EVIDENCE_TYPES:
            raise idx.IndexError_(
                f"relationship evidence {event_id} has illegal type {event_type!r}"
            )
        if record.get("cash_usd") != 0:
            raise idx.IndexError_(f"relationship evidence {event_id} claimed cash")
        if record.get("transport") not in {None, "NONE"}:
            raise idx.IndexError_(f"relationship evidence {event_id} claimed transport")
        idx.parse_time(str(record.get("ts")))
        source_paths = record.get("source_paths")
        if (
            not isinstance(source_paths, list)
            or not source_paths
            or not all(isinstance(item, str) and item for item in source_paths)
        ):
            raise idx.IndexError_(
                f"relationship evidence {event_id} missing source_paths"
            )
        if event_type in {"MATERIAL_REPLY", "SENT_AWAITING_REPLY"}:
            role = record.get("role")
            organization = record.get("organization")
            if role not in idx.LIVE_ROLES:
                raise idx.IndexError_(
                    f"relationship evidence {event_id} cannot cite role {role!r}"
                )
            if not isinstance(organization, str) or not organization.strip():
                raise idx.IndexError_(
                    f"relationship evidence {event_id} missing organization"
                )
        if event_type == "STATUS":
            due = record.get("due")
            if due is not None and (
                not isinstance(due, str) or not idx.DUE_RE.fullmatch(due)
            ):
                raise idx.IndexError_(
                    f"relationship evidence {event_id} has illegal due {due!r}"
                )
        idx._assert_no_pii_in_index_blob(
            json.dumps(record, sort_keys=True, ensure_ascii=False)
        )
        record[_INTERNAL_SOURCE] = SOURCE_RELATIONSHIP_EVIDENCE
        validated.append(record)
    return validated


def _apply_relationship_evidence(
    row: dict[str, Any],
    events_sorted: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """Project newer handoff evidence without mutating the canonical INDEX row."""
    effective = dict(row)
    effective["source_paths"] = list(row.get("source_paths") or [])
    effective["overlay_event_ids"] = list(row.get("overlay_event_ids") or [])
    relationship_ids: list[str] = []
    for event in events_sorted:
        if event.get(_INTERNAL_SOURCE) != SOURCE_RELATIONSHIP_EVIDENCE:
            continue
        event_id = str(event.get("id"))
        relationship_ids.append(event_id)
        for source_path in _event_paths(event):
            if source_path not in effective["source_paths"]:
                effective["source_paths"].append(source_path)
        if RELATIONSHIP_EVIDENCE_REL not in effective["source_paths"]:
            effective["source_paths"].append(RELATIONSHIP_EVIDENCE_REL)
        event_type = event.get("type")
        if event_type == "MATERIAL_REPLY":
            effective["decision"] = "MATERIAL_REPLY"
            effective["dnr"] = False
            effective["live"] = True
        elif event_type == "SENT_AWAITING_REPLY":
            effective["decision"] = "SENT_AWAITING_REPLY"
            effective["live"] = True
            if event.get("dnr") is True or event.get("decision") in {
                "HARD_DO_NOT_RESEND",
                "OWNER_HOLD",
            }:
                effective["dnr"] = True
        elif event_type == "STATUS":
            if event.get("decision"):
                effective["decision"] = event["decision"]
            if event.get("dnr") is True:
                effective["dnr"] = True
            elif event.get("dnr") is False:
                effective["dnr"] = False
            if event.get("due"):
                effective["due"] = event["due"]
            if event.get("route_kind"):
                effective["route_kind"] = event["route_kind"]
            if event.get("route_ref"):
                effective["route_ref"] = event["route_ref"]
        if event.get("next_action"):
            effective["next_action"] = event["next_action"]
    return effective, relationship_ids


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

    canonical_events = []
    for source in built["events"]:
        event = dict(source)
        event[_INTERNAL_SOURCE] = SOURCE_INDEX_OVERLAY
        canonical_events.append(event)
    canonical_ids = {
        str(event.get("id")) for event in canonical_events if event.get("id")
    }
    relationship_events = _load_relationship_evidence(paths, canonical_ids)
    events = [
        event
        for event in canonical_events + relationship_events
        if event.get("subject_id") == subject_id
    ]
    events_sorted = sorted(
        events, key=lambda item: idx.parse_time(str(item.get("ts") or ""))
    )
    effective_row, relationship_ids = _apply_relationship_evidence(row, events_sorted)

    evidence_chain = [
        {
            "id": event.get("id"),
            "type": event.get("type"),
            "ts": event.get("ts"),
            "body": event.get("body"),
            "source_kind": event.get(_INTERNAL_SOURCE),
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
        # Pointer prose remains a summary even when it links a real message.
        # This composer does not fetch the linked source or verify a quote.
        wants = _sourced(
            body,
            paths_e + [_event_ref(event)],
            SUMMARY_POINTER,
        )
        break

    # learned: chronological factual STATUS / MATERIAL_REPLY / SENT bodies
    learned_bits: list[str] = []
    learned_evidence: list[str] = []
    for event in events_sorted:
        event_type = event.get("type")
        if event_type not in RELATIONSHIP_EVIDENCE_TYPES:
            continue
        body = str(event.get("body") or "").strip()
        if not body:
            continue
        learned_bits.append(f"[{event_type} {event.get('ts')}] {body}")
        learned_evidence.append(_event_ref(event))
        learned_evidence.extend(_event_paths(event))
    learned = (
        _sourced(" | ".join(learned_bits), learned_evidence, SUMMARY_POINTER)
        if learned_bits
        else _absent()
    )

    # A typed sent event records communication, not the contents of a promise.
    sent_communication = _absent()
    for event in reversed(events_sorted):
        if event.get("type") != "SENT_AWAITING_REPLY":
            continue
        sent_communication = _sourced(
            str(event.get("body") or ""),
            _event_paths(event) + [_event_ref(event)],
            SUMMARY_POINTER,
        )
        break
    # Neither the canonical overlay nor the handoff evidence file carries
    # separately verified commitment contents. The source messages remain
    # reachable by pointer and must be inspected before attributing a promise.
    promised = _absent()

    # unresolved + successor next action from effective source-linked state
    next_action = effective_row.get("next_action")
    decision = effective_row.get("decision")
    unresolved_parts: list[str] = []
    if isinstance(decision, str) and decision:
        unresolved_parts.append(f"decision={decision}")
    if effective_row.get("dnr"):
        unresolved_parts.append("dnr=true")
    if isinstance(next_action, str) and next_action.strip():
        unresolved_parts.append(next_action.strip())
    unresolved_evidence = [
        f"overlay:{item}" for item in (row.get("overlay_event_ids") or [])
    ]
    unresolved_evidence.extend(
        f"relationship:{item}" for item in relationship_ids
    )
    unresolved_evidence.extend(
        [
            path
            for path in (effective_row.get("source_paths") or [])
            if isinstance(path, str)
        ]
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

    due = effective_row.get("due")
    due_evidence: list[str] = []
    for event in reversed(events_sorted):
        if event.get("due") == due and due:
            due_evidence = _event_paths(event) + [_event_ref(event)]
            break
    if not due_evidence and due:
        due_evidence = unresolved_evidence[:]
    next_time = (
        _sourced(str(due), due_evidence, LEDGER_STATUS)
        if isinstance(due, str) and due
        else _absent()
    )

    owner = effective_row.get("owner") or "UNSEATED"
    packet = {
        "schema_version": idx.SCHEMA_VERSION,
        "kind": KIND_HANDOFF,
        "subject_id": subject_id,
        "organization": effective_row.get("organization"),
        "person": effective_row.get("person"),
        "lane": idx.compact_lane(effective_row),
        "decision": effective_row.get("decision"),
        "dnr": bool(effective_row.get("dnr")),
        "due": effective_row.get("due"),
        "route_kind": effective_row.get("route_kind"),
        "route_ref": effective_row.get("route_ref"),
        "canonical_crm": idx.CANONICAL_CRM,
        "cash_usd": 0,
        "transport": "NONE",
        "relationship_evidence": {
            "path": RELATIONSHIP_EVIDENCE_REL,
            "event_ids": relationship_ids,
            "canonical_index_mutated": False,
        },
        "fields": {
            "wants": wants,
            "learned": learned,
            "promised": promised,
            "sent_communication": sent_communication,
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
            "pointer_is_not_message": True,
            "relationship_evidence_is_not_crm": True,
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
