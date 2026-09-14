#!/usr/bin/env python3
"""Bind right-now buyer-response truth to the canonical reply compiler.

The right-now catalog may state expected counters for reviewability, but those
numbers are assertions only.  This adapter derives counted human outcomes from
``host.reply_to_revenue`` and rejects any catalog drift.  It never reads a
mailbox, sends mail, accepts a scope, or publishes private message content.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host import reply_to_revenue  # noqa: E402


EXPECTED_KIND = "REPLY_TO_REVENUE_FUNNEL"


class HumanOutcomeAuthorityError(ValueError):
    """Catalog human-outcome assertions differ from compiled public evidence."""


def _non_negative_integer(value: Any, where: str) -> int:
    if type(value) is not int or value < 0:
        raise HumanOutcomeAuthorityError(f"{where} must be a non-negative integer")
    return value


def derive_human_truth(
    catalog_truth: dict[str, Any],
    *,
    funnel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return canonical public human-outcome truth and reconcile assertions.

    ``funnel`` exists only for deterministic unit/hostile tests.  Production
    callers omit it, which compiles from canonical outreach receipts and the
    normalized reply observation artifact via :func:`reply_to_revenue.build_funnel`.
    """
    if not isinstance(catalog_truth, dict):
        raise HumanOutcomeAuthorityError("catalog truth must be an object")
    asserted_positive = _non_negative_integer(
        catalog_truth.get("verified_positive_replies"),
        "catalog truth.verified_positive_replies",
    )
    asserted_acceptances = _non_negative_integer(
        catalog_truth.get("accepted_scopes"),
        "catalog truth.accepted_scopes",
    )

    if funnel is None:
        try:
            funnel = reply_to_revenue.build_funnel()
        except reply_to_revenue.ReplyRevenueError as error:
            raise HumanOutcomeAuthorityError(
                f"canonical reply compiler rejected its source evidence: {error}"
            ) from error
    if not isinstance(funnel, dict):
        raise HumanOutcomeAuthorityError("compiled reply funnel must be an object")
    if funnel.get("kind") != EXPECTED_KIND:
        raise HumanOutcomeAuthorityError("compiled reply funnel kind is unsupported")
    as_of = funnel.get("as_of")
    if not isinstance(as_of, str) or not as_of.strip():
        raise HumanOutcomeAuthorityError("compiled reply funnel as_of must be non-empty")
    truth = funnel.get("truth")
    if not isinstance(truth, dict):
        raise HumanOutcomeAuthorityError("compiled reply funnel truth must be an object")
    positive = _non_negative_integer(truth.get("human_positive"), "reply truth.human_positive")
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
        "as_of": as_of,
        "authority": "REPLY_TO_REVENUE_COMPILED_PUBLIC_EVIDENCE",
        "verified_positive_replies": positive,
        "accepted_scopes": acceptances,
    }


def source_paths() -> list[Path]:
    """Return the data files whose bytes feed the canonical reply compiler."""
    paths = [reply_to_revenue.OBSERVATIONS_PATH]
    paths.extend(sorted(reply_to_revenue.RECEIPTS_DIR.glob("*.json")))
    return paths
