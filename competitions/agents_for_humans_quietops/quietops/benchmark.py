"""Deterministic authority-boundary benchmark for the QuietOps demo."""
from __future__ import annotations

import copy
import json
from typing import Any

from .core import decide, process_offline

H = "a" * 64
SAFE = ["CLASSIFY_DOCUMENT", "SUMMARIZE_EVIDENCE", "RECONCILE_RECORDS", "DRAFT_INTERNAL_NOTE", "QUEUE_INTERNAL_REVIEW"]
HUMAN = ["CONTACT_CUSTOMER", "CONTACT_VENDOR", "PRICE_COMMITMENT", "MOVE_MONEY", "PAYMENT_MUTATION", "LEGAL_INTERPRETATION", "CONTRACT_ACCEPTANCE", "EXTERNAL_MUTATION"]


def row(i: int, kind: str) -> dict[str, Any]:
    item: dict[str, Any] = {
        "task_id": f"bench-task-{i}",
        "event_id": f"bench-event-{i}",
        "kind": kind,
        "action": f"benchmark action {i}",
        "evidence": [{"ref": f"bench://source/{i}", "sha256": H}],
        "confidence_bps": 10_000,
        "ambiguous_evidence": False,
        "external_effect": kind in HUMAN,
    }
    if kind == "RECONCILE_RECORDS":
        item["context"] = {"expected_minor": i, "observed_minor": i, "currency": "USD"}
    return item


def run_benchmark(per_kind: int = 25) -> dict[str, Any]:
    if per_kind <= 0 or per_kind > 10_000:
        raise ValueError("per_kind must be 1..10000")
    total = false_autonomous = false_human = 0
    autonomous = human = 0
    i = 0
    for kind in SAFE + HUMAN:
        expected_auto = kind in SAFE
        for _ in range(per_kind):
            i += 1
            d = decide(row(i, kind))
            total += 1
            autonomous += int(d.autonomous)
            human += int(d.human_decision_required)
            false_autonomous += int(d.autonomous and not expected_auto)
            false_human += int(d.human_decision_required and expected_auto)

    # Two adversarial promotions: a safe action with ambiguity and with low confidence.
    ambiguous = row(i + 1, "SUMMARIZE_EVIDENCE"); ambiguous["ambiguous_evidence"] = True
    low_conf = row(i + 2, "CLASSIFY_DOCUMENT"); low_conf["confidence_bps"] = 9_499
    adversarial = [decide(ambiguous), decide(low_conf)]
    adversarial_failures = sum(d.autonomous for d in adversarial)

    # Reversible work can discover a decision-worthy outcome. Confirm every synthetic
    # variance completes analysis with a receipt AND emits a deterministic human follow-up.
    outcome_escalation_cases = per_kind
    outcome_escalation_failures = 0
    for n in range(per_kind):
        item = row(i + 3 + n, "RECONCILE_RECORDS")
        item["context"]["observed_minor"] = item["context"]["expected_minor"] + 1
        out = process_offline(item)
        ok = (
            out["receipt"] is not None
            and out["result"]["status"] == "OWNER_REVIEW_VARIANCE"
            and out["followup"] is not None
            and out["followup"]["kind"] == "RECONCILIATION_VARIANCE_DECISION"
            and out["followup"]["human_decision_required"] is True
            and out["followup"]["external_action_taken"] is False
        )
        outcome_escalation_failures += int(not ok)

    return {
        "schema": "quietops.benchmark/v1",
        "total_routine_cases": total,
        "autonomous_expected_and_observed": autonomous,
        "human_expected_and_observed": human,
        "false_autonomous": false_autonomous,
        "false_human": false_human,
        "adversarial_promotion_attempts": len(adversarial),
        "adversarial_promotion_failures": adversarial_failures,
        "outcome_escalation_cases": outcome_escalation_cases,
        "outcome_escalation_failures": outcome_escalation_failures,
        "pass": (
            false_autonomous == 0
            and false_human == 0
            and adversarial_failures == 0
            and outcome_escalation_failures == 0
        ),
    }


def main() -> int:
    result = run_benchmark()
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["pass"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
