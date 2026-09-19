#!/usr/bin/env python3
"""Synthetic, offline walkthrough of the retained delivery-state compiler.

This is a consumer of outbound_delivery_truth, not another delivery engine.
It reads no inbox, sends no messages and writes only to standard output.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import sys
from typing import Any

if __package__:
    from . import outbound_delivery_truth as engine
else:
    import outbound_delivery_truth as engine


class DemoError(ValueError):
    """The real compiler did not reproduce a documented synthetic case."""


def _submission() -> dict[str, Any]:
    return {
        "operation_key": "SYNTHETIC-DELIVERY-WALKTHROUGH",
        "counterparty": "Fictional example only",
        "purpose": "Offline state walkthrough; not a real contact",
        "provider": "synthetic-mail",
        "provider_message_id": "synthetic-message-1",
        "provider_thread_id": "synthetic-thread-1",
        "sender": "synthetic-sender-token",
        "recipient": "synthetic-recipient-token",
        "submitted_at": "2026-09-17T12:00:00Z",
        "source_ref": "synthetic:walkthrough:submission",
        "source_sha256": "a" * 64,
    }


def _event(kind: str) -> dict[str, Any]:
    delivered = kind in {"delivered", "unbound"}
    return {
        "id": f"synthetic-{kind}",
        "kind": "PROVIDER_DELIVERY_CONFIRMATION" if delivered else "DSN",
        "observed_at": "2026-09-17T12:01:00Z",
        "provider": "synthetic-mail",
        "original_message_id": "other-message" if kind == "unbound" else "synthetic-message-1",
        "original_thread_id": "synthetic-thread-1",
        "sender": "synthetic-sender-token",
        "recipient": "synthetic-recipient-token",
        "action": "delivered" if delivered else "delayed" if kind == "delayed" else "failed",
        "status": "2.0.0" if delivered else "4.4.1" if kind == "delayed" else "5.4.1",
        "diagnostic_code": f"Fictional {kind} evidence; no provider event occurred",
        "source_ref": f"synthetic:walkthrough:{kind}",
        "source_sha256": {"delivered": "b", "failed": "c", "delayed": "d", "unbound": "e"}[kind] * 64,
    }


def _scenarios() -> list[tuple[str, str, tuple[str, ...], str, bool, bool, bool, str]]:
    # Expected outcomes are explicit, independent of compiler return values.
    return [
        ("unsent", "none", (), "UNSENT", False, False, False,
         "No send evidence exists. This is not permission to contact anyone."),
        ("submitted_only", "provider", (), "PROVIDER_SUBMITTED_PENDING_DELIVERY", True, True, False,
         "Submission is retained; delivery is still unproven. Missing bounce evidence is not delivery."),
        ("legacy_sent_only", "legacy", (), "DELIVERY_UNKNOWN", False, True, False,
         "An old local sent record preserves the duplicate-contact hold, not proof of provider submission."),
        ("provider_hard_failure", "provider", ("failed",), "DELIVERY_FAILED", True, True, False,
         "A bound permanent failure is not successful contact. No automatic resend follows."),
        ("legacy_late_failure", "legacy", ("failed",), "DELIVERY_FAILED", False, True, False,
         "Late failure evidence corrects the legacy history without inventing a submission receipt."),
        ("provider_delivered", "provider", ("delivered",), "DELIVERED_EVIDENCE", True, True, True,
         "Bound delivery evidence supports this route's contact projection, not a reply, acceptance or sale."),
        ("legacy_late_delivery", "legacy", ("delivered",), "DELIVERED_EVIDENCE", False, True, True,
         "Late delivery evidence can establish delivery while provider submission remains unretained."),
        ("temporary_delay", "provider", ("delayed",), "DELIVERY_UNKNOWN", True, True, False,
         "A temporary delay establishes neither delivery nor permanent route failure."),
        ("wrong_message_confirmation", "provider", ("unbound",), "DELIVERY_UNKNOWN", True, True, False,
         "A positive confirmation for a different message cannot be borrowed for this contact."),
        ("conflicting_terminals", "provider", ("failed", "delivered"), "DELIVERY_UNKNOWN", True, True, False,
         "Conflicting bound terminal evidence remains unknown rather than selecting a convenient outcome."),
        ("legacy_conflicting_terminals", "legacy", ("failed", "delivered"), "DELIVERY_UNKNOWN", False, True, False,
         "Legacy evidence with conflicting terminals stays unknown and retains duplicate-contact hold."),
    ]


def build_demo() -> dict[str, Any]:
    """Execute all examples against the real engine and verify each receipt."""
    rows = []
    authority_keys = {
        "send_authorized", "retry_authorized", "alternate_route_authorized",
        "provider_action_authorized", "buyer_acceptance", "payment_authorized",
        "cash_proven", "revenue_recognized",
    }
    for name, origin, event_kinds, state, observed, hold, contacted, explanation in _scenarios():
        packet = {
            "schema": engine.INPUT_SCHEMA,
            "submission": _submission() if origin == "provider" else None,
            "legacy_local_sent": _submission() if origin == "legacy" else None,
            "events": [_event(kind) for kind in event_kinds],
        }
        before = deepcopy(packet)
        artifact = engine.compile_delivery_truth(packet)
        if packet != before:
            raise DemoError(f"{name}: compiler mutated the retained input")
        expected = {
            "delivery_state": state,
            "provider_submission_observed": observed,
            "same_route_dedupe_hold": hold,
            "counts_as_contacted": contacted,
        }
        projection = engine.collision_projection(artifact)
        actual = {key: projection[key] for key in expected}
        if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise DemoError(f"{name}: delivery projection differs from the documented outcome")
        if artifact["delivery_state"] != state:
            raise DemoError(f"{name}: artifact and projection disagree")
        authority = artifact["authority"]
        if (type(authority) is not dict or set(authority) != authority_keys
                or any(value is not False for value in authority.values())):
            raise DemoError(f"{name}: diagnostic claims an external action")
        verification = engine.verify_delivery_truth(packet, artifact)
        if verification.get("valid") is not True:
            raise DemoError(f"{name}: diagnostic replay did not verify")
        rows.append({
            "id": name, "synthetic": True, "input": packet,
            "expected_projection": expected, "artifact": artifact,
            "verification": verification, "explanation": explanation,
        })
    return {
        "schema": "commons.outbound-delivery-walkthrough/v1",
        "synthetic": True,
        "notice": "All inputs are fictional. Replay proves consistency, not provider authenticity, buyer acceptance or revenue.",
        "case_count": len(rows),
        "cases": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Outbound delivery: synthetic walkthrough", "", report["notice"], "",
        "| Case | Delivery state | Submission retained | Duplicate-contact hold | Contact projection |",
        "|---|---|---|---|---|",
    ]
    for row in report["cases"]:
        p = row["artifact"]["collision_projection"]
        flags = ["yes" if p[key] else "no" for key in (
            "provider_submission_observed", "same_route_dedupe_hold", "counts_as_contacted")]
        lines.append(f"| {row['id']} | {p['delivery_state']} | {' | '.join(flags)} |")
    lines.extend(["", "## How to read the results", ""])
    for row in report["cases"]:
        lines.append(f"**{row['id']}**: {row['explanation']}\n")
    lines.append("No example sends, retries, changes providers, authorizes contact or recognizes revenue.\n")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    try:
        report = build_demo()
    except (DemoError, engine.DeliveryTruthError) as exc:
        print(f"delivery walkthrough failed: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
