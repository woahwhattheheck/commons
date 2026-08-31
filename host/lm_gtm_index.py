#!/usr/bin/env python3
"""LLM-native compose/query layer over existing Commons GTM ledgers.

This is not a CRM. Canonical records stay in Airtable
`JOJO Revenue Recovery CRM / Revenue Pipeline` and the in-repo ledgers this
tool reads. The public artifact is one index-first projection plus an
append-only overlay of events that cite existing subject ids.

It does not mint crm/, people/, contacts/, sales/, accounts, or deals.
It does not rewrite website-people-email-book loop.json schema v2.
Live send is refused. Cash stays USD 0 without payment evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "commons-lm-gtm-index/v1"
KIND_STATE = "LM_GTM_INDEX_STATE"
KIND_HEADER = "LM_GTM_INDEX_HEADER"
KIND_ROW = "LM_GTM_INDEX_ROW"
KIND_EVENT = "LM_GTM_OVERLAY_EVENT"
INDEX_REL = "revenue/lm_gtm_index/INDEX.jsonl"
EVENTS_REL = "revenue/lm_gtm_index/events.jsonl"
CANONICAL_CRM = "JOJO Revenue Recovery CRM / Revenue Pipeline"
SUBJECT_RE = re.compile(r"^[A-Za-z0-9._-]{3,80}$")
EVENT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
EMAIL_AT_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
ROLE_ORDER = {
    "external_prospect": 0,
    "inbound_contact": 1,
    "seller_context": 2,
    "research_universe": 3,
    "mailbox_manifest": 4,
}
ROW_KEYS = {
    "schema_version",
    "kind",
    "id",
    "role",
    "live",
    "organization",
    "source_ledgers",
    "source_paths",
    "route_kind",
    "route_ref",
    "decision",
    "next_action",
    "due",
    "owner",
    "dnr",
    "occupied_by",
    "overlay_event_ids",
    "cash_usd",
}
DOES_NOT_REPLACE = [
    "revenue/website_people_email_book",
    "revenue/smart_outreach",
    "revenue/marketing_sales",
    "revenue/reply_to_revenue",
    "revenue/payment_ready/outreach_receipts",
    "revenue/swarm_mail",
    "Airtable JOJO Revenue Recovery CRM / Revenue Pipeline",
]
DOES_NOT_CREATE = ["crm/", "people/", "contacts/", "sales/"]
COMPOSE = {
    "website_people_email_book": "external prospects vs seller contacts; drafts only; --send exits 3",
    "smart_outreach": "evidence-bound candidates; does not open a second CRM",
    "reply_to_revenue": "inbound cash truth; never opens a second CRM",
    "marketing_sales": "public research universe; Airtable remains canonical CRM",
    "outreach_receipts": "DNR / collision receipts; not a contact book",
    "swarm_mail": "public inbox manifest; private addresses stay off git",
}


class IndexError_(ValueError):
    """Projection, overlay, or lookup failed closed."""


class SendError(IndexError_):
    """Live send was requested. This composer never transports mail."""


def canonical_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def default_paths(root: Path = ROOT) -> dict[str, Path]:
    base = root / "revenue" / "lm_gtm_index"
    return {
        "root": root,
        "loop": root / "revenue" / "website_people_email_book" / "loop.json",
        "candidates": root / "revenue" / "smart_outreach" / "candidates.json",
        "funnel": root / "revenue" / "reply_to_revenue" / "funnel.json",
        "pipeline": root / "revenue" / "marketing_sales" / "pipeline.json",
        "receipts": root / "revenue" / "payment_ready" / "outreach_receipts",
        "inboxes": root / "revenue" / "swarm_mail" / "inboxes.json",
        "index": base / "INDEX.jsonl",
        "state": base / "state.json",
        "events": base / "events.jsonl",
    }


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IndexError_(f"cannot read JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise IndexError_(f"{path} must contain one JSON object")
    return value


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def parse_time(value: str) -> dt.datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(text)
    except (TypeError, ValueError) as error:
        raise IndexError_(f"invalid date-time: {value}") from error
    if parsed.tzinfo is None:
        raise IndexError_("date-time must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def iso_z(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise IndexError_(f"{path}:{line_no} is not JSONL: {error}") from error
        if not isinstance(item, dict):
            raise IndexError_(f"{path}:{line_no} must be a JSON object")
        rows.append(item)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(rendered, encoding="utf-8")


def _blank_row(subject_id: str, role: str) -> dict[str, Any]:
    if not SUBJECT_RE.fullmatch(subject_id):
        raise IndexError_(f"illegal subject id: {subject_id}")
    live = role in {"external_prospect", "inbound_contact"}
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_ROW,
        "id": subject_id,
        "role": role,
        "live": live,
        "organization": None,
        "source_ledgers": [],
        "source_paths": [],
        "route_kind": None,
        "route_ref": None,
        "decision": None,
        "next_action": None,
        "due": None,
        "owner": "UNSEATED",
        "dnr": False,
        "occupied_by": None,
        "overlay_event_ids": [],
        "cash_usd": 0,
    }


def _touch(row: dict[str, Any], ledger: str, path: str) -> None:
    if ledger not in row["source_ledgers"]:
        row["source_ledgers"].append(ledger)
    if path not in row["source_paths"]:
        row["source_paths"].append(path)


def _route_from(source: dict[str, Any], row: dict[str, Any]) -> None:
    route = source.get("route")
    if not isinstance(route, dict):
        return
    kind = route.get("kind")
    if isinstance(kind, str) and kind:
        row["route_kind"] = kind
    if kind == "EXISTING_CRM_RECORD":
        value = route.get("value")
        if isinstance(value, str) and value.startswith("airtable:"):
            row["route_ref"] = value


def _assert_no_email_in_index_blob(blob: str) -> None:
    if EMAIL_AT_RE.search(blob):
        raise IndexError_("INDEX projection copied an email; keep emails in source ledgers")


def load_receipts(paths: dict[str, Path]) -> list[dict[str, Any]]:
    folder = paths["receipts"]
    if not folder.is_dir():
        raise IndexError_(f"missing receipts directory {folder}")
    loaded: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        receipt = read_object(path)
        target = receipt.get("target_id")
        if not isinstance(target, str) or not target:
            raise IndexError_(f"{path} missing target_id")
        dedupe = receipt.get("dedupe") if isinstance(receipt.get("dedupe"), dict) else {}
        loaded.append(
            {
                "target_id": target,
                "path": rel(paths["root"], path),
                "do_not_resend": bool(dedupe.get("do_not_resend")),
                "organization": receipt.get("organization"),
            }
        )
    return loaded


def load_events(paths: dict[str, Path]) -> list[dict[str, Any]]:
    events = load_jsonl(paths["events"])
    seen: set[str] = set()
    for event in events:
        if event.get("schema_version") != SCHEMA_VERSION or event.get("kind") != KIND_EVENT:
            raise IndexError_(f"overlay event {event.get('id')!r} is not {KIND_EVENT}")
        event_id = event.get("id")
        subject = event.get("subject_id")
        if not isinstance(event_id, str) or not EVENT_ID_RE.fullmatch(event_id):
            raise IndexError_(f"illegal overlay event id: {event_id}")
        if event_id in seen:
            raise IndexError_(f"overlay event remint refused: {event_id}")
        seen.add(event_id)
        if not isinstance(subject, str) or not SUBJECT_RE.fullmatch(subject):
            raise IndexError_(f"overlay event {event_id} missing subject_id")
        if event.get("cash_usd") != 0:
            raise IndexError_(f"overlay event {event_id} claimed cash")
        if event.get("transport") not in {None, "NONE"}:
            raise IndexError_(f"overlay event {event_id} claimed transport")
        parse_time(str(event.get("ts")))
    return events


def compose_subjects(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    loop = read_object(paths["loop"])
    if loop.get("schema_version") != "commons-website-people-email-book/v2":
        raise IndexError_("website-people-email-book loop.json is not schema v2; do not rewrite it")
    candidates = read_object(paths["candidates"])
    funnel = read_object(paths["funnel"])
    pipeline = read_object(paths["pipeline"])
    inboxes = read_object(paths["inboxes"])
    receipts = load_receipts(paths)
    events = load_events(paths)
    subjects: dict[str, dict[str, Any]] = {}

    def row_for(subject_id: str, role: str) -> dict[str, Any]:
        existing = subjects.get(subject_id)
        if existing is None:
            existing = _blank_row(subject_id, role)
            subjects[subject_id] = existing
            return existing
        if existing["role"] == "seller_context" and role != "seller_context":
            raise IndexError_(f"{subject_id} is seller context and cannot become a prospect")
        if existing["role"] == "inbound_contact" and role == "external_prospect":
            existing["role"] = "external_prospect"
            existing["live"] = True
        return existing

    loop_rel = rel(paths["root"], paths["loop"])
    for prospect in loop.get("prospects") or []:
        if not isinstance(prospect, dict):
            raise IndexError_("loop.prospects entries must be objects")
        subject_id = prospect.get("prospect_id")
        if not isinstance(subject_id, str):
            raise IndexError_("loop prospect missing prospect_id")
        row = row_for(subject_id, "external_prospect")
        _touch(row, "website_people_email_book", loop_rel)
        row["organization"] = prospect.get("organization")
        row["decision"] = prospect.get("decision")
        row["next_action"] = prospect.get("next_action")
        row["occupied_by"] = prospect.get("occupied_by")
        if prospect.get("decision") in {"HOLD_DO_NOT_RESEND", "HOLD_DO_NOT_CONTACT"}:
            row["dnr"] = True
        _route_from(prospect, row)

    for seller in loop.get("seller_contacts") or []:
        if not isinstance(seller, dict):
            raise IndexError_("loop.seller_contacts entries must be objects")
        subject_id = seller.get("contact_id")
        if not isinstance(subject_id, str):
            raise IndexError_("seller contact missing contact_id")
        row = row_for(subject_id, "seller_context")
        _touch(row, "website_people_email_book", loop_rel)
        row["organization"] = "Commons seller fixture (not a buyer)"
        row["decision"] = "SELLER_CONTEXT_NOT_PROSPECT"
        row["next_action"] = seller.get("next_action")
        row["live"] = False
        _route_from(seller, row)
        row["route_ref"] = None

    cand_rel = rel(paths["root"], paths["candidates"])
    for prospect in candidates.get("prospects") or []:
        if not isinstance(prospect, dict):
            raise IndexError_("candidates.prospects entries must be objects")
        subject_id = prospect.get("prospect_id")
        if not isinstance(subject_id, str):
            raise IndexError_("candidate missing prospect_id")
        row = row_for(subject_id, "external_prospect")
        _touch(row, "smart_outreach", cand_rel)
        if not row["organization"]:
            row["organization"] = prospect.get("organization")
        if prospect.get("occupied_by") and not row["occupied_by"]:
            row["occupied_by"] = prospect.get("occupied_by")
        if prospect.get("do_not_contact"):
            row["dnr"] = True
        _route_from(prospect, row)

    funnel_rel = rel(paths["root"], paths["funnel"])
    for contact in funnel.get("contacts") or []:
        if not isinstance(contact, dict):
            raise IndexError_("funnel.contacts entries must be objects")
        subject_id = contact.get("prospect_key")
        if not isinstance(subject_id, str):
            raise IndexError_("funnel contact missing prospect_key")
        role = "external_prospect" if subject_id in subjects and subjects[subject_id]["role"] == "external_prospect" else "inbound_contact"
        row = row_for(subject_id, role)
        _touch(row, "reply_to_revenue", funnel_rel)
        if not row["organization"]:
            row["organization"] = contact.get("organization")
        if contact.get("hard_dnr"):
            row["dnr"] = True
        if not row["decision"]:
            row["decision"] = contact.get("lane")
        if not row["next_action"]:
            row["next_action"] = contact.get("next_action")
        if row["dnr"] and row["decision"] not in {
            "HOLD_DO_NOT_RESEND",
            "HOLD_DO_NOT_CONTACT",
            "SELLER_CONTEXT_NOT_PROSPECT",
        }:
            if not row["next_action"]:
                row["next_action"] = contact.get("next_action")

    for receipt in receipts:
        row = row_for(receipt["target_id"], "inbound_contact")
        _touch(row, "outreach_receipts", receipt["path"])
        if receipt["do_not_resend"]:
            row["dnr"] = True
        if not row["organization"] and receipt["organization"]:
            row["organization"] = receipt["organization"]
        if row["dnr"] and not row["decision"]:
            row["decision"] = "HOLD_DO_NOT_RESEND"
        if row["dnr"] and not row["next_action"]:
            row["next_action"] = "retain canonical receipt suppression; no draft and no transport handoff"

    research = _blank_row("marketing-sales-research-universe", "research_universe")
    pipe_rel = rel(paths["root"], paths["pipeline"])
    _touch(research, "marketing_sales", pipe_rel)
    current = pipeline.get("current") if isinstance(pipeline.get("current"), dict) else {}
    count = int(current.get("research_entities") or 0)
    research["organization"] = "public GitHub research universe (not live sales)"
    research["decision"] = "RESEARCH_UNIVERSE_NOT_LIVE_SALES"
    research["next_action"] = (
        f"do not treat {count} RESEARCH_REQUIRED GitHub entities as live sales next-actions"
    )
    research["live"] = False
    subjects[research["id"]] = research

    mailbox = _blank_row("swarm-mail-public-inboxes", "mailbox_manifest")
    box_rel = rel(paths["root"], paths["inboxes"])
    _touch(mailbox, "swarm_mail", box_rel)
    mailbox["organization"] = "Commons swarm mail public manifest"
    mailbox["decision"] = inboxes.get("transport", {}).get("state") if isinstance(inboxes.get("transport"), dict) else None
    mailbox["next_action"] = "NEEDS_OWNER_MAILBOX"
    mailbox["live"] = False
    subjects[mailbox["id"]] = mailbox

    by_subject: dict[str, list[str]] = {}
    for event in events:
        by_subject.setdefault(event["subject_id"], []).append(event["id"])
    for subject_id, event_ids in by_subject.items():
        if subject_id not in subjects:
            raise IndexError_(
                f"overlay event cites unknown subject {subject_id}; composer does not mint a contact book"
            )
        row = subjects[subject_id]
        if row["role"] not in {"external_prospect", "inbound_contact"}:
            raise IndexError_(f"overlay event cannot attach to {row['role']} {subject_id}")
        row["overlay_event_ids"] = list(event_ids)

    for row in subjects.values():
        if set(row) != ROW_KEYS:
            raise IndexError_(f"row {row.get('id')} keys drifted: {sorted(row)}")
        if row["cash_usd"] != 0:
            raise IndexError_(f"row {row['id']} claimed cash")
        if row["role"] == "seller_context" and row["live"]:
            raise IndexError_(f"seller contact {row['id']} marked live")
        if row["id"] in {"ava-example-test", "noah-example-test", "riley-quiet", "sam-example-test"}:
            if row["role"] != "seller_context" or row["live"]:
                raise IndexError_(f"seller fixture {row['id']} leaked into live sales")
    return subjects


def composed_at(paths: dict[str, Path], events: list[dict[str, Any]]) -> str:
    stamps = [
        read_object(paths["loop"]).get("generated_at"),
        read_object(paths["funnel"]).get("measured_at"),
        read_object(paths["pipeline"]).get("observed_at"),
        read_object(paths["inboxes"]).get("measured_at"),
        read_object(paths["candidates"]).get("generated_at"),
    ]
    stamps.extend(event.get("ts") for event in events)
    parsed = [parse_time(str(item)) for item in stamps if item]
    if not parsed:
        raise IndexError_("no source timestamps")
    return iso_z(max(parsed))


def build_index(paths: dict[str, Path] | None = None) -> dict[str, Any]:
    paths = paths or default_paths()
    loop = read_object(paths["loop"])
    pipeline = read_object(paths["pipeline"])
    events = load_events(paths)
    subjects = compose_subjects(paths)
    rows = sorted(
        subjects.values(),
        key=lambda row: (ROLE_ORDER.get(row["role"], 99), row["id"]),
    )
    live_rows = [row for row in rows if row["live"]]
    header = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_HEADER,
        "canonical_crm": CANONICAL_CRM,
        "public_projection_is_not_crm": True,
        "does_not_replace": list(DOES_NOT_REPLACE),
        "does_not_create": list(DOES_NOT_CREATE),
        "compose": dict(COMPOSE),
        "composed_at": composed_at(paths, events),
        "row_count": len(rows),
        "live_next_action_count": len(live_rows),
        "cash_usd": 0,
    }
    truth = {
        "index_rows": len(rows),
        "live_next_actions": len(live_rows),
        "seller_context_rows": sum(1 for row in rows if row["role"] == "seller_context"),
        "external_prospects": sum(1 for row in rows if row["role"] == "external_prospect"),
        "inbound_contacts": sum(1 for row in rows if row["role"] == "inbound_contact"),
        "research_entities_not_live": int(
            (pipeline.get("current") or {}).get("research_entities") or 0
        ),
        "overlay_events": len(events),
        "calls_booked": int((loop.get("truth") or {}).get("calls_booked") or 0),
        "transport_actions": 0,
        "cash_usd": 0,
        "mailbox": (loop.get("truth") or {}).get("mailbox") or "NEEDS_OWNER_MAILBOX",
    }
    if truth["calls_booked"] != 0 or truth["cash_usd"] != 0:
        raise IndexError_("composer claimed bookings or cash")
    state = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_STATE,
        "canonical_crm": CANONICAL_CRM,
        "public_projection_is_not_crm": True,
        "does_not_replace": list(DOES_NOT_REPLACE),
        "does_not_create": list(DOES_NOT_CREATE),
        "compose": dict(COMPOSE),
        "composed_at": header["composed_at"],
        "index": INDEX_REL,
        "events": EVENTS_REL,
        "truth": truth,
        "named_subjects": {
            "composio": "external_prospect READY_TO_DRAFT from loop.json + candidates.json",
            "signoz": "external_prospect RESEARCH_REQUIRED from loop.json + candidates.json",
            "metaforms": "EXISTING_CRM_RECORD airtable:recWHbHxQoQfGhS0q; HOLD_DO_NOT_RESEND",
            "anythingllm-mintplex": "HOLD_DO_NOT_RESEND from receipts + loop.json",
        },
        "contract": {
            "read_index": "revenue/lm_gtm_index/INDEX.jsonl",
            "read_state": "revenue/lm_gtm_index/state.json",
            "list_next": "python3 host/lm_gtm_index.py next",
            "open_by_ref": "python3 host/lm_gtm_index.py show <existing-id>",
            "append_event": "python3 host/lm_gtm_index.py append-event --subject <existing-id> --id <new-event-id> --body <text>",
            "send": "illegal; exits 3",
        },
    }
    blob = "".join(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n" for item in [header, *rows])
    _assert_no_email_in_index_blob(blob)
    _assert_no_email_in_index_blob(canonical_text(state))
    return {"header": header, "rows": rows, "state": state, "events": events, "blob": blob}


def write_index(paths: dict[str, Path] | None = None) -> dict[str, Any]:
    paths = paths or default_paths()
    built = build_index(paths)
    paths["index"].parent.mkdir(parents=True, exist_ok=True)
    paths["index"].write_text(built["blob"], encoding="utf-8")
    paths["state"].write_text(canonical_text(built["state"]), encoding="utf-8")
    if not paths["events"].exists():
        paths["events"].write_text("", encoding="utf-8")
    return built


def validate_index(paths: dict[str, Path] | None = None) -> dict[str, Any]:
    paths = paths or default_paths()
    built = build_index(paths)
    actual_index = paths["index"].read_text(encoding="utf-8")
    if actual_index != built["blob"]:
        raise IndexError_("committed INDEX.jsonl differs from composed ledgers")
    actual_state = json.loads(paths["state"].read_text(encoding="utf-8"))
    if actual_state != built["state"]:
        raise IndexError_("committed state.json differs from composed ledgers")
    if built["state"]["truth"]["cash_usd"] != 0:
        raise IndexError_("cash_usd is not 0")
    for name in DOES_NOT_CREATE:
        if (paths["root"] / name.rstrip("/")).exists():
            raise IndexError_(f"remint root present: {name}")
    return built


def live_next_actions(paths: dict[str, Path] | None = None) -> list[dict[str, Any]]:
    built = build_index(paths)
    return [row for row in built["rows"] if row["live"]]


def _source_excerpt(items: list[Any], key: str, value: str) -> dict[str, Any] | None:
    for item in items:
        if isinstance(item, dict) and item.get(key) == value:
            return item
    return None


def show_subject(subject_id: str, paths: dict[str, Path] | None = None) -> dict[str, Any]:
    paths = paths or default_paths()
    built = build_index(paths)
    row = next((item for item in built["rows"] if item["id"] == subject_id), None)
    if row is None:
        raise IndexError_(
            f"unknown subject {subject_id!r}: composer opens existing ledger ids only and does not mint a contact book"
        )
    sources: dict[str, Any] = {}
    loop = read_object(paths["loop"])
    if "website_people_email_book" in row["source_ledgers"]:
        if row["role"] == "seller_context":
            sources["website_people_email_book"] = _source_excerpt(
                loop.get("seller_contacts") or [], "contact_id", subject_id
            )
        else:
            sources["website_people_email_book"] = _source_excerpt(
                loop.get("prospects") or [], "prospect_id", subject_id
            )
            emails = [
                item
                for item in (loop.get("emails") or [])
                if isinstance(item, dict) and item.get("prospect_id") == subject_id
            ]
            bookings = [
                item
                for item in (loop.get("bookings") or [])
                if isinstance(item, dict) and item.get("prospect_id") == subject_id
            ]
            if emails:
                sources["website_people_email_book_emails"] = emails
            if bookings:
                sources["website_people_email_book_bookings"] = bookings
    if "smart_outreach" in row["source_ledgers"]:
        candidates = read_object(paths["candidates"])
        sources["smart_outreach"] = _source_excerpt(
            candidates.get("prospects") or [], "prospect_id", subject_id
        )
    if "reply_to_revenue" in row["source_ledgers"]:
        funnel = read_object(paths["funnel"])
        sources["reply_to_revenue"] = _source_excerpt(
            funnel.get("contacts") or [], "prospect_key", subject_id
        )
    if "outreach_receipts" in row["source_ledgers"]:
        sources["outreach_receipts"] = [
            {"path": item["path"], "do_not_resend": item["do_not_resend"]}
            for item in load_receipts(paths)
            if item["target_id"] == subject_id
        ]
    overlay = [event for event in built["events"] if event.get("subject_id") == subject_id]
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "LM_GTM_INDEX_SHOW",
        "subject_id": subject_id,
        "index": row,
        "sources": sources,
        "overlay_events": overlay,
        "canonical_crm": CANONICAL_CRM,
        "cash_usd": 0,
    }


def append_event(
    *,
    subject_id: str,
    event_id: str,
    body: str,
    speaker: str = "UNSEATED",
    ts: str | None = None,
    paths: dict[str, Path] | None = None,
) -> dict[str, Any]:
    paths = paths or default_paths()
    if not EVENT_ID_RE.fullmatch(event_id):
        raise IndexError_(f"illegal overlay event id: {event_id}")
    text = body.strip()
    if not text:
        raise IndexError_("overlay event body is empty")
    built = build_index(paths)
    row = next((item for item in built["rows"] if item["id"] == subject_id), None)
    if row is None:
        raise IndexError_(
            f"unknown subject {subject_id!r}: composer does not mint a contact book"
        )
    if row["role"] not in {"external_prospect", "inbound_contact"}:
        raise IndexError_(
            f"{subject_id} is {row['role']}; overlay events cite live ledger subjects only"
        )
    existing_ids = {event["id"] for event in built["events"]}
    if event_id in existing_ids:
        raise IndexError_(f"overlay event remint refused: {event_id}")
    stamp = ts or iso_z(dt.datetime.now(dt.timezone.utc))
    parse_time(stamp)
    event = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_EVENT,
        "id": event_id,
        "subject_id": subject_id,
        "ts": stamp,
        "from": speaker or "UNSEATED",
        "body": text,
        "cash_usd": 0,
        "transport": "NONE",
    }
    events = list(built["events"])
    events.append(event)
    write_jsonl(paths["events"], events)
    written = write_index(paths)
    return {"event": event, "index": written}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("write-index")
    sub.add_parser("snapshot")
    sub.add_parser("next")
    show = sub.add_parser("show")
    show.add_argument("subject")
    append = sub.add_parser("append-event")
    append.add_argument("--subject", required=True)
    append.add_argument("--id", dest="event_id", required=True)
    append.add_argument("--body", required=True)
    append.add_argument("--from", dest="speaker", default="UNSEATED")
    append.add_argument("--ts")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--send" in argv or argv[:1] == ["send"]:
        sys.stderr.write(
            "REFUSED live send: this composer never transports mail. "
            "Use Swarm Mail after measured provisioning; overlay events stay local.\n"
        )
        return 3
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            built = validate_index()
            truth = built["state"]["truth"]
            print(
                "VALID "
                f"{truth['live_next_actions']} live-next "
                f"{truth['external_prospects']} prospects "
                f"{truth['inbound_contacts']} inbound "
                f"{truth['seller_context_rows']} seller-context "
                f"{truth['overlay_events']} overlay-events "
                f"USD {truth['cash_usd']} cash"
            )
            return 0
        if args.command in {"write-index", "snapshot"}:
            built = write_index()
            print(canonical_text(built["state"]), end="")
            return 0
        if args.command == "next":
            rows = live_next_actions()
            sys.stdout.write(
                "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
            )
            return 0
        if args.command == "show":
            print(canonical_text(show_subject(args.subject)), end="")
            return 0
        if args.command == "append-event":
            result = append_event(
                subject_id=args.subject,
                event_id=args.event_id,
                body=args.body,
                speaker=args.speaker,
                ts=args.ts,
            )
            print(canonical_text(result["event"]), end="")
            return 0
        raise IndexError_(f"unknown command {args.command}")
    except SendError as error:
        print(str(error), file=sys.stderr)
        return 3
    except IndexError_ as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
