# SPDX-License-Identifier: Apache-2.0
"""Validate the candidate's own bounded action-change receipts."""
from __future__ import annotations

import collections
import json
from pathlib import Path


def _units(action):
    return [action.get("farmer"), *list(action.get("hands") or [])]


def validate(path):
    rows = []
    source = Path(path)
    if source.is_file():
        rows = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    reasons = collections.Counter()
    products = collections.Counter()
    events = []
    errors = []
    duplicates = eligible = changed = 0
    for number, row in enumerate(rows, start=1):
        report = row.get("report") or {}
        before, after = row.get("before"), row.get("after")
        reasons[str(report.get("reason"))] += 1
        duplicates += int(report.get("duplicate_groups", 0))
        eligible += int(report.get("eligible_groups", 0))
        changed += int(report.get("changed_actions", 0))
        problems = []
        if not isinstance(before, dict) or not isinstance(after, dict):
            problems.append("actions_not_mappings")
        else:
            if before.get("market") != after.get("market"):
                problems.append("market_changed")
            left, right = _units(before), _units(after)
            if len(left) != len(right):
                problems.append("unit_cardinality_changed")
            else:
                diff = [(a, b) for a, b in zip(left, right) if a != b]
                if len(diff) != int(report.get("changed_actions", 0)):
                    problems.append("changed_action_count_mismatch")
                if any(a != ["HARVEST"] or b != ["CARE"] for a, b in diff):
                    problems.append("unexpected_unit_rewrite")
        if bool(report.get("changed")) != bool(report.get("changed_actions")):
            problems.append("changed_flag_mismatch")
        if problems:
            errors.append({"record": number, "step": row.get("step"), "problems": problems})
        for event in report.get("events") or []:
            products[str(event.get("product"))] += 1
            events.append({"step": row.get("step"), "player": row.get("player"), **event})
    return {
        "records": len(rows),
        "duplicate_groups": duplicates,
        "eligible_groups": eligible,
        "changed_actions": changed,
        "reasons": dict(sorted(reasons.items())),
        "products": dict(sorted(products.items())),
        "valid": not errors,
        "errors": errors[:20],
        "events": events[:40],
    }
