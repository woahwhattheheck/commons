from __future__ import annotations

import copy
from typing import Any

from .desk import append_event, build_package, sha256_json, sha256_text, verify_package

EVALUATION_TIME = "2026-09-13T10:00:00Z"
DECISION_DIGEST = sha256_text("buyer-decision:change-001:approve:v1")


def make_baseline() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "baseline_id": "baseline-001",
        "baseline_version": 3,
        "currency": "USD",
        "accepted_at": "2026-09-10T12:00:00Z",
        "scope_digest": sha256_text("accepted-scope-v3"),
        "line_items": [
            {
                "item_id": "discovery",
                "description": "Discovery and reviewed implementation plan",
                "quantity": 1,
                "unit_price_cents": 250_000,
            },
            {
                "item_id": "implementation",
                "description": "Implementation and buyer review package",
                "quantity": 1,
                "unit_price_cents": 350_000,
            },
        ],
        "discount_cents": 50_000,
        "tax_cents": 0,
        "subtotal_cents": 600_000,
        "total_cents": 550_000,
        "schedule": {
            "start_date": "2026-09-15",
            "end_date": "2026-10-15",
            "milestones": [
                {"milestone_id": "kickoff", "due_date": "2026-09-15", "amount_cents": 200_000},
                {"milestone_id": "delivery", "due_date": "2026-10-15", "amount_cents": 350_000},
            ],
        },
        "evidence_refs": [
            {"ref_id": "proposal-v3", "kind": "proposal", "sha256": sha256_text("proposal-v3")},
            {"ref_id": "acceptance-v3", "kind": "acceptance", "sha256": sha256_text("acceptance-v3")},
            {"ref_id": "scope-v3", "kind": "scope", "sha256": sha256_text("scope-v3")},
        ],
    }


def make_change(baseline: dict[str, Any] | None = None) -> dict[str, Any]:
    baseline = copy.deepcopy(baseline or make_baseline())
    return {
        "schema_version": 1,
        "change_id": "change-001",
        "change_version": 1,
        "supersedes_change_sha256": None,
        "baseline_id": baseline["baseline_id"],
        "baseline_version": baseline["baseline_version"],
        "baseline_sha256": sha256_json(baseline),
        "currency": baseline["currency"],
        "created_at": "2026-09-13T09:00:00Z",
        "expires_at": "2026-09-20T09:00:00Z",
        "summary": "Add two migration-support sessions and extend delivery by five days.",
        "scope_delta_digest": sha256_text("change-001-scope-delta"),
        "line_items": [
            {
                "item_id": "migration-support",
                "description": "Migration-support working session",
                "quantity": 2,
                "unit_delta_cents": 37_500,
            }
        ],
        "discount_delta_cents": 5_000,
        "tax_delta_cents": 6_000,
        "subtotal_delta_cents": 75_000,
        "total_delta_cents": 76_000,
        "schedule_delta_days": 5,
        "updated_end_date": "2026-10-20",
        "milestones": [
            {"milestone_id": "delivery", "due_date": "2026-10-20", "amount_delta_cents": 76_000}
        ],
        "evidence_refs": [
            {"ref_id": "scope-delta-v1", "kind": "scope", "sha256": sha256_text("scope-delta-v1")},
            {"ref_id": "schedule-delta-v1", "kind": "schedule", "sha256": sha256_text("schedule-delta-v1")},
            {"ref_id": "decision-v1", "kind": "buyer_decision", "sha256": DECISION_DIGEST},
        ],
    }


def make_events(change: dict[str, Any] | None = None, *, approved: bool = False) -> list[dict[str, Any]]:
    change = copy.deepcopy(change or make_change())
    events, replay = append_event(
        [],
        change=change,
        evaluation_time=EVALUATION_TIME,
        event_id="event-submit-001",
        kind="SUBMIT_FOR_REVIEW",
        occurred_at="2026-09-13T09:05:00Z",
        actor_ref="operator-01",
        expected_state="DRAFT",
        expected_change_version=change["change_version"],
    )
    assert replay is False
    if approved:
        events, replay = append_event(
            events,
            change=change,
            evaluation_time=EVALUATION_TIME,
            event_id="event-approve-001",
            kind="APPROVE",
            occurred_at="2026-09-13T09:10:00Z",
            actor_ref="operator-02",
            expected_state="READY_FOR_HUMAN_REVIEW",
            expected_change_version=change["change_version"],
            decision_ref_sha256=DECISION_DIGEST,
        )
        assert replay is False
    return events


def build_fixture(*, approved: bool = False) -> dict[str, Any]:
    baseline = make_baseline()
    change = make_change(baseline)
    events = make_events(change, approved=approved)
    expected = sha256_json(baseline)
    package = build_package(
        baseline,
        change,
        events,
        expected_baseline_sha256=expected,
        evaluation_time=EVALUATION_TIME,
    )
    verification = verify_package(package)
    return {
        "baseline": baseline,
        "change": change,
        "events": events,
        "expected_baseline_sha256": expected,
        "evaluation_time": EVALUATION_TIME,
        "package": package,
        "verification": verification,
    }


def acceptance_manifest() -> dict[str, Any]:
    ready = build_fixture(approved=False)
    approved = build_fixture(approved=True)
    rows = [
        {
            "case": "ready_for_human_review",
            "status": ready["package"]["receipt"]["status"],
            "receipt_sha256": ready["package"]["receipt"]["receipt_sha256"],
            "package_sha256": ready["package"]["package_sha256"],
        },
        {
            "case": "operator_recorded_approval",
            "status": approved["package"]["receipt"]["status"],
            "receipt_sha256": approved["package"]["receipt"]["receipt_sha256"],
            "package_sha256": approved["package"]["package_sha256"],
        },
    ]
    manifest = {
        "schema_version": 1,
        "product": "service_change_order_desk",
        "evaluation_time": EVALUATION_TIME,
        "cases": rows,
        "authority": ready["package"]["receipt"]["authority"],
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    return manifest
