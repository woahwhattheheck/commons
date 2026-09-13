from __future__ import annotations

import copy
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from revenue.teaming_conversion.control import (
    ControlError, DuplicateKeyError, INPUT_SCHEMA, POLICY_SCHEMA, canonical_bytes,
    compile_bytes, compile_control, parse_json_bytes, parse_receipt_bytes,
    read_bounded_regular, render_markdown, verify_bytes, verify_control,
    write_exclusive_regular, digest_object,
)

NOW = datetime(2026, 9, 13, 13, 0, 0, tzinfo=timezone.utc)
D, E, F = "a" * 64, "b" * 64, "c" * 64


def safe_asset() -> dict:
    return {
        "asset_id": "asset-summary", "title": "Prospect-safe capability summary",
        "version": "v1", "sha256": F, "prep_state": "READY",
        "release_class": "PROSPECT_SAFE_SUMMARY", "required_for_followup": True,
        "safe_snippets": ["Assessment delivery is evidence-led and bounded to the agreed scope."],
    }


def internal_asset() -> dict:
    return {
        "asset_id": "asset-internal-method", "title": "Internal scoring workbook",
        "version": "v3", "sha256": D, "prep_state": "READY",
        "release_class": "INTERNAL_ONLY", "required_for_followup": False,
        "safe_snippets": ["THIS MUST NEVER LEAK"],
    }


def asset_rule(asset: dict) -> dict:
    projection = {
        "asset_id": asset["asset_id"], "title": asset["title"], "version": asset["version"],
        "sha256": asset["sha256"], "release_class": asset["release_class"],
        "safe_snippets": list(asset["safe_snippets"]),
    }
    return {
        "asset_id": asset["asset_id"], "asset_version": asset["version"],
        "asset_sha256": asset["sha256"], "release_class": asset["release_class"],
        "projection_sha256": digest_object(projection),
    }


def policy() -> dict:
    assets = [safe_asset(), internal_asset()]
    return {
        "schema_version": POLICY_SCHEMA, "max_reply_age_seconds": 7 * 86400,
        "max_source_age_seconds": 2 * 86400, "max_future_skew_seconds": 60,
        "required_asset_ids": ["asset-summary"], "required_clear_gate_ids": ["gate-prime"],
        "asset_rules": [asset_rule(a) for a in assets],
    }


def packet() -> dict:
    return {
        "schema_version": INPUT_SCHEMA,
        "opportunity": {
            "opportunity_id": "opp-iowa-18649", "counterparty_ref": "org-clarks",
            "thread_id": "thread-clarks-1", "source_digest": D,
            "source_checked_at": "2026-09-13T12:00:00Z",
        },
        "observations": [{
            "observation_id": "obs-1", "thread_id": "thread-clarks-1", "message_id": "msg-1",
            "sender_ref": "contact-prime-1", "sender_role": "PRIME_CONTACT",
            "received_at": "2026-09-13T12:30:00Z", "content_sha256": E,
            "source_class": "GMAIL", "interpretation": "POSITIVE_CONTINUE",
            "supersedes_observation_id": None, "clarification_codes": [],
        }],
        "assets": [safe_asset(), internal_asset()], "release_records": [],
        "qualification_gates": [{"gate_id": "gate-prime", "mandatory": True, "state": "CLEAR", "owner_action": None}],
        "commitments": [], "requested_asset_ids": [],
    }


def obs2(*, interpretation="DECLINED", at="2026-09-13T12:45:00Z", supersedes="obs-1") -> dict:
    return {
        "observation_id": "obs-2", "thread_id": "thread-clarks-1", "message_id": "msg-2",
        "sender_ref": "contact-prime-1", "sender_role": "PRIME_CONTACT", "received_at": at,
        "content_sha256": F, "source_class": "GMAIL", "interpretation": interpretation,
        "supersedes_observation_id": supersedes, "clarification_codes": [],
    }


class BaseTeamingConversionTest(unittest.TestCase):
    def comp(self, p=None, pol=None):
        return compile_control(p or packet(), pol or policy(), as_of=NOW)
