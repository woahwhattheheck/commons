#!/usr/bin/env python3
"""Bind right-now buyer-response truth to canonical reply evidence.

Catalog counters are assertions only.  Production derivation loads the current
reply-to-revenue observations and outreach receipts, proves that their complete
source set is stable across loading, compiles the funnel from those loaded
objects, and returns the exact source digests that must be bound into the final
right-now control manifest.

This module never reads a mailbox, sends mail, accepts a scope, or publishes
private message content.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host import reply_to_revenue  # noqa: E402


EXPECTED_SCHEMA_VERSION = "commons-reply-to-revenue/v1"
EXPECTED_KIND = "REPLY_TO_REVENUE_FUNNEL"


class HumanOutcomeAuthorityError(ValueError):
    """Catalog assertions or canonical reply evidence failed closed."""


def _non_negative_integer(value: Any, where: str) -> int:
    if type(value) is not int or value < 0:
        raise HumanOutcomeAuthorityError(f"{where} must be a non-negative integer")
    return value


def _canonical_utc_seconds(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise HumanOutcomeAuthorityError(f"{where} must be canonical UTC seconds")
    try:
        moment = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as error:
        raise HumanOutcomeAuthorityError(
            f"{where} must be canonical UTC seconds"
        ) from error
    if moment.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise HumanOutcomeAuthorityError(f"{where} must be canonical UTC seconds")
    return value


def source_paths() -> list[Path]:
    """Return the complete deterministic source set for the live compiler."""

    receipts = sorted(reply_to_revenue.RECEIPTS_DIR.glob("*.json"))
    if not receipts:
        raise HumanOutcomeAuthorityError("canonical outreach receipt set is empty")
    return [reply_to_revenue.OBSERVATIONS_PATH, *receipts]


def _source_snapshot() -> list[dict[str, str]]:
    snapshot: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in source_paths():
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError as error:
            raise HumanOutcomeAuthorityError(
                "reply-to-revenue source escaped the repository root"
            ) from error
        if relative in seen:
            raise HumanOutcomeAuthorityError(
                f"duplicate reply-to-revenue source path: {relative}"
            )
        seen.add(relative)
        try:
            data = path.read_bytes()
        except OSError as error:
            raise HumanOutcomeAuthorityError(
                f"cannot read reply-to-revenue source {relative}: {error}"
            ) from error
        # Match host.right_now_revenue_core.sha256_file so one path has one
        # manifest identity on Windows and Linux working copies.
        normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        snapshot.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(normalized).hexdigest(),
            }
        )
    return snapshot


def _compile_current_funnel() -> tuple[dict[str, Any], list[dict[str, str]]]:
    before = _source_snapshot()
    try:
        receipts = reply_to_revenue.load_receipts()
        observations = reply_to_revenue.load_observations()
    except (OSError, reply_to_revenue.ReplyRevenueError) as error:
        raise HumanOutcomeAuthorityError(
            f"canonical reply compiler rejected its source evidence: {error}"
        ) from error
    after_load = _source_snapshot()
    if after_load != before:
        raise HumanOutcomeAuthorityError(
            "reply-to-revenue source generation changed while loading"
        )
    try:
        funnel = reply_to_revenue.build_funnel(
            receipts=receipts,
            observations=observations,
        )
    except reply_to_revenue.ReplyRevenueError as error:
        raise HumanOutcomeAuthorityError(
            f"canonical reply compiler rejected its source evidence: {error}"
        ) from error
    after_compile = _source_snapshot()
    if after_compile != before:
        raise HumanOutcomeAuthorityError(
            "reply-to-revenue source generation changed while compiling"
        )
    return funnel, before


def derive_human_truth(catalog_truth: dict[str, Any]) -> dict[str, Any]:
    """Derive public human-outcome truth from canonical repository evidence."""

    if type(catalog_truth) is not dict:
        raise HumanOutcomeAuthorityError("catalog truth must be an exact object")
    asserted_positive = _non_negative_integer(
        catalog_truth.get("verified_positive_replies"),
        "catalog truth.verified_positive_replies",
    )
    asserted_acceptances = _non_negative_integer(
        catalog_truth.get("accepted_scopes"),
        "catalog truth.accepted_scopes",
    )

    funnel, source_entries = _compile_current_funnel()

    if type(funnel) is not dict:
        raise HumanOutcomeAuthorityError("compiled reply funnel must be an object")
    if funnel.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise HumanOutcomeAuthorityError(
            "compiled reply funnel schema version is unsupported"
        )
    if funnel.get("kind") != EXPECTED_KIND:
        raise HumanOutcomeAuthorityError("compiled reply funnel kind is unsupported")
    measured_at = _canonical_utc_seconds(
        funnel.get("measured_at"),
        "compiled reply funnel measured_at",
    )
    truth = funnel.get("truth")
    if type(truth) is not dict:
        raise HumanOutcomeAuthorityError(
            "compiled reply funnel truth must be an exact object"
        )
    positive = _non_negative_integer(
        truth.get("human_positive"), "reply truth.human_positive"
    )
    acceptances = _non_negative_integer(
        truth.get("scope_acceptances"), "reply truth.scope_acceptances"
    )

    if asserted_positive != positive:
        raise HumanOutcomeAuthorityError(
            "catalog verified_positive_replies differs from compiled human-positive truth"
        )
    if asserted_acceptances != acceptances:
        raise HumanOutcomeAuthorityError(
            "catalog accepted_scopes differs from compiled scope-acceptance truth"
        )

    return {
        "measured_at": measured_at,
        "authority": "REPLY_TO_REVENUE_COMPILED_PUBLIC_EVIDENCE",
        "verified_positive_replies": positive,
        "accepted_scopes": acceptances,
        "sources": source_entries,
    }
