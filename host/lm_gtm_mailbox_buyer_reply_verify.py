#!/usr/bin/env python3
"""Hermetic mailbox-only buyer-reply observation pin (CRM6).

A mailbox reply is evidence that mail arrived after an outbound SENT anchor.
It is NOT, by itself, evidence that the sender is a decision-maker, that the
reply is human, that its contents are commercially material, or that scope,
terms, payment, award, or consent were accepted.

This module therefore exposes two different concepts:

* BUYER_REPLY_OBSERVED: provider/thread/chronology evidence only.
* MATERIAL_REPLY: a separately evidenced semantic decision that this mailbox
  verifier is not authorized to mint.

Entry:
  python3 host/lm_gtm_mailbox_buyer_reply_verify.py SUBJECT
  python3 host/lm_gtm_mailbox_buyer_reply_verify.py SUBJECT --pin-buyer-reply-observed --organization ORG

Legacy --pin-material-reply is retained only as a fail-closed compatibility
surface. --send exits 3.
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
DECISION_OBSERVED = "BUYER_REPLY_OBSERVED"
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
    seen_ids: set[str] = set()
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
        mid = mid.strip()
        if mid in seen_ids:
            raise idx.IndexError_(
                f"mailbox fixture {subject_id!r} repeats message id {mid!r}"
            )
        seen_ids.add(mid)
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
            "id": mid,
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
    """Observe inbound buyer-labelled mail after an outbound in the SAME thread.

    This proves arrival/thread chronology only. The fixture role is an input to
    the hermetic verifier, not independent proof of human identity or materiality.
    """
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

    first_outbound_by_thread: dict[str, dt.datetime] = {}
    for message in outbound:
        stamp = idx.parse_time(str(message["ts"]))
        thread = message["thread_id"]
        prior = first_outbound_by_thread.get(thread)
        if prior is None or stamp < prior:
            first_outbound_by_thread[thread] = stamp

    inbound_hits: list[dict[str, Any]] = []
    for msg in messages:
        if msg["direction"] != "inbound" or msg["role"] != "buyer":
            continue
        anchor = first_outbound_by_thread.get(msg["thread_id"])
        if anchor is None:
            continue
        if idx.parse_time(str(msg["ts"])) < anchor:
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
        "thread_ids": sorted(first_outbound_by_thread),
        "verified_human_yes": False,
        "material_reply_verified": False,
        "cash_usd": 0,
        "transport": "NONE",
        "canonical_crm": idx.CANONICAL_CRM,
        "invent_guard": {
            "never_invent_verified_human_yes": True,
            "never_mint_material_reply_from_arrival": True,
            "hermetic_only": True,
            "no_index_remint": True,
            "no_cheri_contact": True,
            "no_resend": True,
        },
    }
    idx._assert_no_pii_in_index_blob(json.dumps(result, sort_keys=True))
    return result


def _evidence_path(paths: dict[str, Path]) -> Path:
    return Path(paths["root"]) / EVIDENCE_REL


def _append_unique_evidence(
    record: dict[str, Any],
    paths: dict[str, Path],
    *,
    observed_inbound_ids: set[str] | None = None,
) -> dict[str, Any]:
    evidence_path = _evidence_path(paths)
    existing = idx.load_jsonl(evidence_path)
    event_id = str(record["id"])
    if any(item.get("id") == event_id for item in existing):
        raise idx.IndexError_(f"relationship evidence remint refused: {event_id}")
    if observed_inbound_ids:
        for item in existing:
            if (
                item.get("type") == "STATUS"
                and item.get("decision") == DECISION_OBSERVED
            ):
                prior_paths = {
                    value
                    for value in (item.get("source_paths") or [])
                    if isinstance(value, str)
                }
                if prior_paths & observed_inbound_ids:
                    raise idx.IndexError_(
                        "buyer reply observation remint refused for already-pinned Gmail message"
                    )
    existing.append(record)
    idx.write_jsonl(evidence_path, existing)
    return record


def pin_buyer_reply_observed_evidence(
    subject_id: str,
    verify_result: dict[str, Any],
    paths: dict[str, Path] | None = None,
    *,
    event_id: str | None = None,
    organization: str,
    ts: str | None = None,
) -> dict[str, Any]:
    """Append neutral reply-arrival STATUS evidence; never MATERIAL_REPLY."""
    paths = paths or idx.default_paths()
    if verify_result.get("status") != STATUS_OBSERVED:
        raise idx.IndexError_(
            "BUYER_REPLY_OBSERVED pin refused: mailbox status is not BUYER_REPLY_OBSERVED"
        )
    if verify_result.get("verified_human_yes") is True:
        raise idx.IndexError_(
            "BUYER_REPLY_OBSERVED pin refused: mailbox verifier cannot assert VERIFIED_HUMAN_YES"
        )
    if verify_result.get("material_reply_verified") is True:
        raise idx.IndexError_(
            "BUYER_REPLY_OBSERVED pin refused: mailbox verifier cannot assert materiality"
        )
    inbound_ids = list(verify_result.get("inbound_buyer_message_ids") or [])
    outbound_ids = list(verify_result.get("outbound_message_ids") or [])
    if not inbound_ids:
        raise idx.IndexError_("BUYER_REPLY_OBSERVED pin refused: no inbound buyer ids")
    if not isinstance(organization, str) or not organization.strip():
        raise idx.IndexError_("BUYER_REPLY_OBSERVED pin requires organization")
    stamp = ts or idx.iso_z(dt.datetime.now(dt.timezone.utc))
    idx.parse_time(stamp)
    eid = event_id or (
        f"crm6-mailbox-reply-observed-{subject_id}-"
        f"{stamp.replace('-', '').replace(':', '')}"
    )
    eid = eid[:80]
    if not idx.EVENT_ID_RE.fullmatch(eid):
        raise idx.IndexError_(f"illegal relationship evidence id: {eid!r}")

    source_paths = outbound_ids + inbound_ids
    record = {
        "schema_version": idx.SCHEMA_VERSION,
        "kind": KIND_RELATIONSHIP_EVIDENCE,
        "id": eid,
        "subject_id": subject_id,
        "type": "STATUS",
        "organization": organization.strip(),
        "ts": stamp,
        "from": "FORGE",
        "body": (
            "Buyer reply arrival observed after a prior SENT anchor in the same thread. "
            "Human identity, commercial materiality, acceptance, award, and payment remain unverified."
        ),
        "decision": DECISION_OBSERVED,
        "dnr": False,
        "next_action": (
            "HUMAN_CLASSIFICATION_REQUIRED; inspect the source message before any "
            "material-reply, scope, acceptance, or commercial-state claim."
        ),
        "source_paths": source_paths,
        "cash_usd": 0,
        "transport": "NONE",
    }
    idx._assert_no_pii_in_index_blob(json.dumps(record, sort_keys=True))
    return _append_unique_evidence(
        record,
        paths,
        observed_inbound_ids=set(inbound_ids),
    )


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
    """Legacy API: always refuse raw mailbox-observation -> MATERIAL_REPLY."""
    del subject_id, verify_result, paths, event_id, organization, role, body, ts
    raise idx.IndexError_(
        "MATERIAL_REPLY pin refused: mailbox arrival/thread chronology does not "
        "verify human identity or commercial materiality. Pin BUYER_REPLY_OBSERVED "
        "and use separately evidenced semantic review for any MATERIAL_REPLY state."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subject", help="existing subject id")
    parser.add_argument(
        "--pin-buyer-reply-observed",
        action="store_true",
        help="when BUYER_REPLY_OBSERVED, append neutral STATUS evidence only",
    )
    parser.add_argument(
        "--pin-material-reply",
        action="store_true",
        help="legacy compatibility flag; always refused",
    )
    parser.add_argument(
        "--organization",
        default="",
        help="required with --pin-buyer-reply-observed",
    )
    parser.add_argument("--jsonl", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--send" in argv or argv[:1] == ["send"]:
        sys.stderr.write(
            "REFUSED live send: mailbox buyer-reply verify never transports mail.\n"
        )
        return 3
    args = build_parser().parse_args(argv)
    try:
        if args.pin_material_reply and args.pin_buyer_reply_observed:
            raise idx.IndexError_(
                "choose one pin mode; MATERIAL_REPLY mode is legacy-refused"
            )
        result = verify_mailbox_buyer_reply(args.subject)
        if args.pin_material_reply:
            pin_material_reply_evidence(
                args.subject,
                result,
                organization=args.organization.strip() or "UNSPECIFIED",
            )
        if args.pin_buyer_reply_observed:
            if not args.organization.strip():
                raise idx.IndexError_(
                    "--pin-buyer-reply-observed requires --organization"
                )
            pinned = pin_buyer_reply_observed_evidence(
                args.subject,
                result,
                organization=args.organization.strip(),
            )
            result = dict(result)
            result["buyer_reply_observed_pinned"] = pinned["id"]
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
