#!/usr/bin/env python3
"""Hermetic mailbox-only buyer-reply verify pin (CRM6).

CLAIM ledger-crm6-mailbox-buyer-reply-verify-20260905-01
Slack C0BU51F1PL3 ts 1788653647.048429

Returns NO_BUYER_REPLY | BUYER_REPLY_OBSERVED from mailbox fixtures only.
Live Gmail is out of scope for this slice. Never invents VERIFIED_HUMAN_YES.
Does not remint INDEX.jsonl / events.jsonl. Hands off #8802.

Entry:
  python3 host/lm_gtm_mailbox_buyer_reply_verify.py SUBJECT
  python3 host/lm_gtm_mailbox_buyer_reply_verify.py city-of-billings-bid-1421
"""
from __future__ import annotations

import argparse
import datetime as dt
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

KIND_RESULT = "LM_GTM_MAILBOX_BUYER_REPLY_VERIFY"
KIND_FIXTURE = "LM_GTM_MAILBOX_FIXTURE"
KIND_RELATIONSHIP_EVIDENCE = "LM_GTM_RELATIONSHIP_EVIDENCE"
STATUS_NO = "NO_BUYER_REPLY"
STATUS_OBSERVED = "BUYER_REPLY_OBSERVED"
MODE_HERMETIC = "HERMETIC"
FIXTURE_REL = "revenue/lm_gtm_index/mailbox_buyer_reply_fixtures"
EVIDENCE_REL = "revenue/lm_gtm_index/relationship_handoff_evidence.jsonl"
DIRECTIONS = frozenset({"outbound", "inbound"})


def fixture_dir(paths: dict[str, Path] | None = None) -> Path:
    root = Path((paths or idx.default_paths())["root"])
    return root / FIXTURE_REL


def fixture_path(subject_id: str, paths: dict[str, Path] | None = None) -> Path:
    return fixture_dir(paths) / f"{subject_id}.json"


def load_mailbox_fixture(
    subject_id: str,
    paths: dict[str, Path] | None = None,
    *,
    fixture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load a hermetic mailbox fixture. Never calls live Gmail."""
    if fixture is not None:
        record = dict(fixture)
    else:
        path = fixture_path(subject_id, paths)
        if not path.is_file():
            raise idx.IndexError_(
                f"missing hermetic mailbox fixture for {subject_id!r}: {path}"
            )
        record = idx.read_object(path)
    if record.get("schema_version") != idx.SCHEMA_VERSION:
        raise idx.IndexError_(f"mailbox fixture {subject_id!r} has wrong schema_version")
    if record.get("kind") != KIND_FIXTURE:
        raise idx.IndexError_(f"mailbox fixture {subject_id!r} is not {KIND_FIXTURE}")
    if record.get("subject_id") != subject_id:
        raise idx.IndexError_(
            f"mailbox fixture subject_id {record.get('subject_id')!r} != {subject_id!r}"
        )
    if record.get("cash_usd") != 0:
        raise idx.IndexError_(f"mailbox fixture {subject_id!r} claimed cash")
    messages = record.get("messages")
    if not isinstance(messages, list) or not messages:
        raise idx.IndexError_(f"mailbox fixture {subject_id!r} missing messages")
    cleaned: list[dict[str, Any]] = []
    for i, raw in enumerate(messages):
        if not isinstance(raw, dict):
            raise idx.IndexError_(f"mailbox fixture {subject_id!r} message {i} not object")
        mid = raw.get("id")
        direction = raw.get("direction")
        thread_id = raw.get("thread_id")
        ts = raw.get("ts")
        role = raw.get("role")
        if not isinstance(mid, str) or not mid.strip():
            raise idx.IndexError_(f"mailbox fixture {subject_id!r} message {i} missing id")
        if direction not in DIRECTIONS:
            raise idx.IndexError_(
                f"mailbox fixture {subject_id!r} message {i} bad direction {direction!r}"
            )
        if not isinstance(thread_id, str) or not thread_id.strip():
            raise idx.IndexError_(
                f"mailbox fixture {subject_id!r} message {i} missing thread_id"
            )
        if role not in {"seller", "buyer"}:
            raise idx.IndexError_(
                f"mailbox fixture {subject_id!r} message {i} bad role {role!r}"
            )
        idx.parse_time(str(ts))
        item = {
            "id": mid.strip(),
            "direction": direction,
            "thread_id": thread_id.strip(),
            "ts": str(ts),
            "role": role,
        }
        idx._assert_no_pii_in_index_blob(json.dumps(item, sort_keys=True))
        cleaned.append(item)
    record = dict(record)
    record["messages"] = cleaned
    idx._assert_no_pii_in_index_blob(json.dumps(record, sort_keys=True))
    return record


def verify_mailbox_buyer_reply(
    subject_id: str,
    paths: dict[str, Path] | None = None,
    *,
    fixture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Hermetic pin: inbound buyer mail after outbound → BUYER_REPLY_OBSERVED."""
    if not isinstance(subject_id, str) or not idx.SUBJECT_RE.fullmatch(subject_id):
        raise idx.IndexError_(f"illegal subject id: {subject_id!r}")
    paths = paths or idx.default_paths()
    record = load_mailbox_fixture(subject_id, paths, fixture=fixture)
    messages = sorted(
        record["messages"], key=lambda item: idx.parse_time(str(item["ts"]))
    )
    outbound = [m for m in messages if m["direction"] == "outbound"]
    if not outbound:
        raise idx.IndexError_(
            f"mailbox fixture {subject_id!r} has no outbound SENT anchors"
        )
    first_out = idx.parse_time(str(outbound[0]["ts"]))
    out_threads = {m["thread_id"] for m in outbound}
    inbound_hits: list[dict[str, Any]] = []
    for msg in messages:
        if msg["direction"] != "inbound":
            continue
        if msg["role"] != "buyer":
            continue
        if msg["thread_id"] not in out_threads:
            continue
        if idx.parse_time(str(msg["ts"])) < first_out:
            continue
        inbound_hits.append(msg)
    status = STATUS_OBSERVED if inbound_hits else STATUS_NO
    result = {
        "schema_version": idx.SCHEMA_VERSION,
        "kind": KIND_RESULT,
        "subject_id": subject_id,
        "status": status,
        "mode": MODE_HERMETIC,
        "fixture_path": FIXTURE_REL + f"/{subject_id}.json",
        "outbound_message_ids": [m["id"] for m in outbound],
        "inbound_buyer_message_ids": [m["id"] for m in inbound_hits],
        "thread_ids": sorted(out_threads),
        "verified_human_yes": False,
        "cash_usd": 0,
        "transport": "NONE",
        "canonical_crm": idx.CANONICAL_CRM,
        "invent_guard": {
            "never_invent_verified_human_yes": True,
            "hermetic_only": True,
            "no_index_remint": True,
            "no_cheri_contact": True,
            "no_resend": True,
        },
    }
    idx._assert_no_pii_in_index_blob(json.dumps(result, sort_keys=True))
    return result


def pin_material_reply_evidence(
    subject_id: str,
    verify_result: dict[str, Any],
    paths: dict[str, Path] | None = None,
    *,
    event_id: str | None = None,
    organization: str,
    role: str = "inbound_contact",
    body: str | None = None,
    ts: str | None = None,
) -> dict[str, Any]:
    """Optional: append MATERIAL_REPLY pointer to relationship_handoff_evidence only.

    Refuses unless status is BUYER_REPLY_OBSERVED. Never mutates INDEX/events.
    Never invents VERIFIED_HUMAN_YES.
    """
    paths = paths or idx.default_paths()
    if verify_result.get("status") != STATUS_OBSERVED:
        raise idx.IndexError_(
            "MATERIAL_REPLY pin refused: mailbox status is not BUYER_REPLY_OBSERVED"
        )
    if verify_result.get("verified_human_yes") is True:
        raise idx.IndexError_("MATERIAL_REPLY pin refused: VERIFIED_HUMAN_YES invent")
    inbound_ids = list(verify_result.get("inbound_buyer_message_ids") or [])
    outbound_ids = list(verify_result.get("outbound_message_ids") or [])
    if not inbound_ids:
        raise idx.IndexError_("MATERIAL_REPLY pin refused: no inbound buyer ids")
    stamp = ts or idx.iso_z(dt.datetime.now(dt.timezone.utc))
    idx.parse_time(stamp)
    eid = event_id or f"crm6-mailbox-material-reply-{subject_id}-{stamp.replace('-', '').replace(':', '')}"
    eid = eid[:80]
    if not idx.EVENT_ID_RE.fullmatch(eid):
        raise idx.IndexError_(f"illegal relationship evidence id: {eid!r}")
    if role not in idx.LIVE_ROLES:
        raise idx.IndexError_(f"illegal role for MATERIAL_REPLY pin: {role!r}")
    text = (body or "Buyer reply observed in hermetic mailbox fixture after outbound SENT.").strip()
    source_paths = outbound_ids + inbound_ids
    record = {
        "schema_version": idx.SCHEMA_VERSION,
        "kind": KIND_RELATIONSHIP_EVIDENCE,
        "id": eid,
        "subject_id": subject_id,
        "type": "MATERIAL_REPLY",
        "role": role,
        "organization": organization,
        "ts": stamp,
        "from": "FORGE",
        "body": text,
        "source_paths": source_paths,
        "cash_usd": 0,
        "transport": "NONE",
    }
    idx._assert_no_pii_in_index_blob(json.dumps(record, sort_keys=True))
    evidence_path = Path(paths["root"]) / EVIDENCE_REL
    existing = idx.load_jsonl(evidence_path)
    if any(item.get("id") == eid for item in existing):
        raise idx.IndexError_(f"relationship evidence remint refused: {eid}")
    existing.append(record)
    idx.write_jsonl(evidence_path, existing)
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subject", help="existing subject id")
    parser.add_argument(
        "--pin-material-reply",
        action="store_true",
        help="when BUYER_REPLY_OBSERVED, append MATERIAL_REPLY to relationship_handoff_evidence only",
    )
    parser.add_argument(
        "--organization",
        default="",
        help="required with --pin-material-reply",
    )
    parser.add_argument("--jsonl", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        result = verify_mailbox_buyer_reply(args.subject)
        pinned = None
        if args.pin_material_reply:
            if not args.organization.strip():
                raise idx.IndexError_("--pin-material-reply requires --organization")
            pinned = pin_material_reply_evidence(
                args.subject,
                result,
                organization=args.organization.strip(),
            )
            result = dict(result)
            result["material_reply_pinned"] = pinned["id"]
        if args.jsonl:
            sys.stdout.write(json.dumps(result, sort_keys=True, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(idx.canonical_text(result))
        return 0
    except idx.IndexError_ as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
