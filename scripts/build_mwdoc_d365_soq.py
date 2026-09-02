#!/usr/bin/env python3
"""Validate the deterministic, public-safe MWDOC readiness packet."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "revenue" / "mwdoc_d365_soq"


def load() -> dict:
    data = json.loads((PACKET / "readiness.json").read_text(encoding="utf-8"))
    assert data["schema"] == "commons-mwdoc-d365-readiness/v1"
    assert data["decision"] == "NO_GO_AS_PRIME; CONDITIONAL_SUBCONTRACTOR_ONLY"
    gates = data["mandatory_responsiveness"]
    assert len(gates) == 3
    assert all(row["state"] == "NOT_EVIDENCED" for row in gates)
    assert all(row["effect"] == "NONRESPONSIVE_IF_PRIME" for row in gates)
    assert len(data["reference_slots"]) == 2
    assert all(row["state"] == "EMPTY_FAIL_CLOSED" for row in data["reference_slots"])
    return data


def summary(data: dict) -> str:
    result = {
        "decision": data["decision"],
        "external_action": False,
        "id": data["id"],
        "references_ready": False,
        "required_mandatory_gates": 3,
        "verified_mandatory_gates": 0,
    }
    return json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"


def main() -> int:
    print(summary(load()), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
