from __future__ import annotations

from typing import Any


def evaluate_qualification(
    parsed_policy: dict[str, Any],
    gates: list[dict[str, Any]],
    commitments: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    owner_actions: list[str] = []
    gate_by_id = {row["gate_id"]: row for row in gates}

    for gate in sorted(gates, key=lambda row: row["gate_id"]):
        if gate["mandatory"] and gate["state"] in {"BLOCKED", "UNKNOWN"}:
            blockers.append(f"mandatory_gate_{gate['state'].lower()}:{gate['gate_id']}")
            if gate["owner_action"]:
                owner_actions.append(gate["owner_action"])
        elif gate["mandatory"] and gate["state"] == "CURABLE" and gate["owner_action"]:
            owner_actions.append(gate["owner_action"])

    for gate_id in parsed_policy["required_clear_gate_ids"]:
        gate = gate_by_id.get(gate_id)
        if gate is None:
            blockers.append(f"required_clear_gate_missing:{gate_id}")
        elif gate["state"] != "CLEAR":
            blockers.append(f"required_clear_gate_not_clear:{gate_id}:{gate['state']}")
            if gate["owner_action"]:
                owner_actions.append(gate["owner_action"])

    approved: list[dict[str, Any]] = []
    for commitment in sorted(commitments, key=lambda row: row["commitment_id"]):
        if commitment["required_for_followup"] and not commitment["approved"]:
            blockers.append(
                f"required_commitment_not_approved:{commitment['commitment_id']}:{commitment['kind']}"
            )
        if commitment["approved"]:
            approved.append({
                "commitment_id": commitment["commitment_id"],
                "kind": commitment["kind"],
                "safe_fact": commitment["safe_fact"],
                "approval_ref": commitment["approval_ref"],
            })

    return {
        "qualification_blockers": sorted(set(blockers)),
        "owner_actions": sorted(set(owner_actions)),
        "approved_commitments": approved,
    }
