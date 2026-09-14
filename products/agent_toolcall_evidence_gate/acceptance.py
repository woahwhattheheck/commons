"""Golden 240-envelope acceptance: 192 allow, 48 hold (8 per defect class)."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from .engine import Policy, approval_intent_sha256, empty_ledger, evaluate, sha256

H = "a" * 64


def policy_fixture() -> dict:
    return {
        "schema_version": 1,
        "policy_id": "enterprise-agent-sideeffects-v1",
        "revision": 1,
        "agents": [
            {"agent_id": "claims-agent", "versions": ["1.0.0"]},
            {"agent_id": "billing-agent", "versions": ["2.1.0"]},
        ],
        "restricted_data_classes": ["restricted", "secret"],
        "rules": [
            {"tool": "claim_api", "action": "update_note", "resource_prefix": "claim/", "allowed_roles": ["adjuster", "supervisor"], "allowed_data_classes": ["internal", "confidential"], "require_human_approval": False, "approval_roles": ["none"], "max_request_budget_cents": 1000, "max_window_budget_cents": 250000, "max_calls_per_window": 1000},
            {"tool": "payment_api", "action": "issue_refund", "resource_prefix": "payment/", "allowed_roles": ["supervisor"], "allowed_data_classes": ["internal"], "require_human_approval": True, "approval_roles": ["human-supervisor"], "max_request_budget_cents": 5000, "max_window_budget_cents": 750000, "max_calls_per_window": 1000},
        ],
    }


def request_fixture(i: int, *, payment: bool = False) -> dict:
    request = {
        "schema_version": 1,
        "request_id": f"req-{i:04d}",
        "agent": {"agent_id": "billing-agent" if payment else "claims-agent", "version": "2.1.0" if payment else "1.0.0"},
        "actor": {"actor_id": f"actor-{i%7}", "role": "supervisor" if payment else "adjuster"},
        "tool_call": {"tool": "payment_api" if payment else "claim_api", "action": "issue_refund" if payment else "update_note", "target_resource": f"payment/{i}" if payment else f"claim/{i}", "data_class": "internal"},
        "approval": None,
        "idempotency_key": f"idem-{i:04d}",
        "budget_cents": 500 if payment else 50,
        "window_id": "2026-09-13T21",
        "trace": {"trace_id": f"trace-{i:04d}", "parent_trace_id": None, "evidence_sha256": H},
    }
    if payment:
        request["approval"] = {"approval_id": f"approval-{i}", "approver_role": "human-supervisor", "evidence_sha256": H, "intent_sha256": approval_intent_sha256(request)}
    return request


def golden_sequence() -> list[tuple[str, dict]]:
    rows: list[tuple[str, dict]] = []
    # 192 clean requests. First 8 idempotency keys are reused by the replay defect set.
    for i in range(192):
        rows.append(("clean", request_fixture(i, payment=bool(i % 2))))
    base = 1000
    for j in range(8):
        r = request_fixture(base + j); r["tool_call"]["action"] = "delete_claim"; rows.append(("tool_action", r))
    for j in range(8):
        r = request_fixture(base + 8 + j); r["actor"]["role"] = "intern"; rows.append(("role_resource", r))
    for j in range(8):
        r = request_fixture(base + 16 + j); r["tool_call"]["data_class"] = "restricted"; rows.append(("restricted_data", r))
    for j in range(8):
        r = request_fixture(base + 24 + j, payment=True); r["approval"] = None; rows.append(("approval", r))
    for j in range(8):
        r = request_fixture(base + 32 + j, payment=True); r["budget_cents"] = 5001; r["approval"]["intent_sha256"] = approval_intent_sha256(r); rows.append(("budget_rate", r))
    for j in range(8):
        r = request_fixture(base + 40 + j); r["idempotency_key"] = f"idem-{j:04d}"; rows.append(("replay", r))
    return rows


def run_acceptance() -> dict:
    policy = policy_fixture(); ledger = empty_ledger(Policy.parse(policy))
    counts = {"EXECUTE_ALLOWED": 0, "HOLD": 0}
    defects: dict[str, int] = {}
    bad_allowed: list[str] = []
    receipts: list[str] = []
    for label, request in golden_sequence():
        receipt, new_ledger = evaluate(policy, request, ledger)
        counts[receipt["decision"]] += 1
        receipts.append(receipt["receipt_sha256"])
        if label != "clean":
            defects[label] = defects.get(label, 0) + (receipt["decision"] == "HOLD")
            if receipt["decision"] != "HOLD":
                bad_allowed.append(request["request_id"])
        ledger = new_ledger
    assert len(golden_sequence()) == 240
    assert counts == {"EXECUTE_ALLOWED": 192, "HOLD": 48}, counts
    assert defects == {"tool_action": 8, "role_resource": 8, "restricted_data": 8, "approval": 8, "budget_rate": 8, "replay": 8}, defects
    assert bad_allowed == []
    report = {"evidence_class": "SYNTHETIC_GOLDEN", "total": 240, "allowed": 192, "held": 48, "held_by_defect": defects, "zero_defective_allowed": True, "final_ledger_sha256": ledger["ledger_sha256"], "receipt_set_sha256": sha256(receipts)}
    return report

if __name__ == "__main__":
    print(json.dumps(run_acceptance(), sort_keys=True, separators=(",", ":")))
