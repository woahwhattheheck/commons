from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .common import sorted_unique
from .parse import ParsedCandidate, ParsedEvidence
from .policy import policy_dict


def evaluate_qualification(
    candidate: ParsedCandidate,
    evidence: ParsedEvidence,
    *,
    now: datetime,
) -> dict[str, Any]:
    policy = policy_dict()
    future_skew = timedelta(seconds=policy["max_future_skew_seconds"])
    blockers: list[str] = []
    owner_actions: list[str] = []
    gates = {row["gate_id"]: row for row in evidence.qualification_gates}
    commitments = {row["commitment_id"]: row for row in evidence.commitments}

    for gate in evidence.qualification_gates:
        if gate["decided_at"] > evidence.captured_at:
            blockers.append(f"qualification_decision_after_capture:{gate['gate_id']}")
        if gate["decided_at"] > now + future_skew:
            blockers.append(f"qualification_decision_in_future:{gate['gate_id']}")
        if gate["mandatory"] and gate["state"] != "CLEAR":
            blockers.append(f"mandatory_gate_not_clear:{gate['gate_id']}:{gate['state']}")
            owner_actions.append(gate["owner_action"])

    required_gate_ids = set(evidence.requirements["required_gate_ids"])
    required_gate_ids.update(policy["required_clear_gate_ids"])
    for gate_id in sorted(required_gate_ids):
        gate = gates.get(gate_id)
        if gate is None:
            blockers.append(f"required_gate_missing:{gate_id}")
        elif gate["state"] != "CLEAR":
            blockers.append(f"required_gate_not_clear:{gate_id}:{gate['state']}")
            owner_actions.append(gate["owner_action"])

    for commitment in evidence.commitments:
        if commitment["decided_at"] > evidence.captured_at:
            blockers.append(f"commitment_decision_after_capture:{commitment['commitment_id']}")
        if commitment["decided_at"] > now + future_skew:
            blockers.append(f"commitment_decision_in_future:{commitment['commitment_id']}")
        if commitment["mandatory"] and not commitment["approved"]:
            blockers.append(f"mandatory_commitment_unapproved:{commitment['commitment_id']}")

    required_commitment_ids = set(evidence.requirements["required_commitment_ids"])
    required_commitment_ids.update(candidate.required_commitment_ids)
    required_commitment_ids.update(policy["required_commitment_ids"])
    for commitment_id in sorted(required_commitment_ids):
        commitment = commitments.get(commitment_id)
        if commitment is None:
            blockers.append(f"required_commitment_missing:{commitment_id}")
        elif not commitment["approved"]:
            blockers.append(f"required_commitment_unapproved:{commitment_id}")

    safe_facts = [
        {
            "commitment_id": row["commitment_id"],
            "safe_fact": row["safe_fact"],
            "approval_ref": row["approval_ref"],
            "approval_sha256": row["approval_sha256"],
        }
        for row in sorted(evidence.commitments, key=lambda item: item["commitment_id"])
        if row["approved"]
    ]
    return {
        "blockers": sorted_unique(blockers),
        "owner_actions": sorted_unique(owner_actions),
        "safe_facts": safe_facts,
    }
