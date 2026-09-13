#!/usr/bin/env python3
"""Replayable acceptance matrix for the Agent Release Evidence Gate."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from gate import evaluate, sha256_json

HERE = Path(__file__).resolve().parent
NOW = datetime(2026, 9, 13, 8, 45, 0, tzinfo=timezone.utc)


def _load() -> dict:
    return json.loads((HERE / "fixtures" / "release.json").read_text(encoding="utf-8"))


def _rebind(manifest: dict) -> None:
    request_sha = sha256_json(manifest["request"])
    for check in manifest["evidence"]["checks"].values():
        check["subject_sha256"] = request_sha
    if "approval" in manifest:
        manifest["approval"]["request_sha256"] = request_sha


def main() -> int:
    base = _load()
    cases = [("release", base, "RELEASE", None)]

    stale = copy.deepcopy(base); stale["snapshot_at"] = "2026-09-13T08:42:00Z"
    cases.append(("stale_snapshot", stale, "HOLD", "STALE_SNAPSHOT"))
    missing_approval = copy.deepcopy(base); del missing_approval["approval"]
    cases.append(("missing_approval", missing_approval, "HOLD", "APPROVAL_MISSING"))
    stale_check = copy.deepcopy(base); stale_check["evidence"]["checks"]["unit"]["observed_at"] = "2026-09-13T08:40:00Z"
    cases.append(("stale_check", stale_check, "HOLD", "CHECK_STALE:unit"))
    hostile_target = copy.deepcopy(base); hostile_target["request"]["target"] = "hostile/example#42"; _rebind(hostile_target)
    cases.append(("hostile_target", hostile_target, "HOLD", "CAPABILITY_NOT_ALLOWED"))
    duplicate = copy.deepcopy(base); request_sha = sha256_json(duplicate["request"])
    duplicate["evidence"]["completed_effects"].append({"effect_id": "prior-effect-42", "effect": "external", "request_sha256": request_sha, "status": "committed"})
    cases.append(("duplicate_effect", duplicate, "HOLD", "ALREADY_EFFECTED"))
    zero_budget = copy.deepcopy(base); zero_budget["policy"]["effect_budget"]["external"] = 0
    cases.append(("zero_budget", zero_budget, "HOLD", "EFFECT_BUDGET_EXHAUSTED"))
    wrong_scope = copy.deepcopy(base); wrong_scope["approval"]["request_sha256"] = "0" * 64
    cases.append(("wrong_approval_scope", wrong_scope, "HOLD", "APPROVAL_SCOPE_MISMATCH"))

    output = []
    for name, manifest, expected_decision, expected_reason in cases:
        receipt = evaluate(manifest, NOW)
        assert receipt["decision"] == expected_decision, (name, receipt)
        if expected_reason is not None:
            assert expected_reason in receipt["reasons"], (name, receipt)
        output.append({
            "case": name,
            "decision": receipt["decision"],
            "reasons": receipt["reasons"],
            "request_sha256": receipt["request_sha256"],
            "receipt_sha256": receipt["receipt_sha256"],
            "release_expires_at": receipt.get("release_expires_at"),
        })

    first = json.dumps(evaluate(_load(), NOW), sort_keys=True, separators=(",", ":"))
    second = json.dumps(evaluate(_load(), NOW), sort_keys=True, separators=(",", ":"))
    assert first == second
    print(json.dumps({"accepted": len(output), "cases": output}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
