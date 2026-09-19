#!/usr/bin/env python3
"""UIOWA-067 offline incident-learning evidence assessor.

Consumes supplied JSON records and produces an evidence-oriented summary.
No live systems are queried and no individual performance score is produced.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ACTION_STATES = {"OPEN", "COMPLETED", "OVERDUE", "CHANGED_APPROACH", "UNKNOWN"}


def parse_time(value: Any, field: str) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 string or null")
    text = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} is not valid ISO-8601") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def assess_action(action: dict[str, Any], now: datetime) -> dict[str, Any]:
    action_id = required_text(action.get("action_id"), "action_id")
    description = required_text(action.get("description"), f"{action_id}.description")
    owner_role = action.get("owner_role")
    due = parse_time(action.get("due_at"), f"{action_id}.due_at")
    completed = parse_time(action.get("completed_at"), f"{action_id}.completed_at")
    changed = action.get("changed_approach")
    completion_ref = action.get("completion_evidence_ref")
    effectiveness_ref = action.get("effectiveness_evidence_ref")

    issues: list[str] = []
    questions: list[str] = []

    if not owner_role:
        issues.append("owner_role_missing")
        questions.append("Which role is accountable for carrying this action to disposition?")

    if completed is not None:
        if not completion_ref:
            issues.append("completion_evidence_missing")
            questions.append("What retained artifact shows the corrective work was actually completed?")
        state = "COMPLETED"
    elif isinstance(changed, dict):
        rationale = changed.get("rationale")
        decision_ref = changed.get("decision_ref")
        replacement = changed.get("replacement_action")
        if not rationale or not decision_ref or not replacement:
            issues.append("changed_approach_evidence_incomplete")
            questions.append("What decision record explains why the original action changed and what replaced it?")
            state = "UNKNOWN"
        else:
            state = "CHANGED_APPROACH"
    elif due is not None and due < now:
        state = "OVERDUE"
        questions.append("What blocked completion, and should the action be completed, revised, or explicitly retired?")
    elif due is None:
        state = "UNKNOWN"
        issues.append("due_date_missing")
        questions.append("What review point or due date determines when this action needs a disposition?")
    else:
        state = "OPEN"

    if state == "COMPLETED" and not effectiveness_ref:
        issues.append("effectiveness_followup_missing")
        questions.append(
            "What evidence will show whether the completed action changed the recurring condition or service outcome?"
        )

    return {
        "action_id": action_id,
        "description": description,
        "state": state,
        "owner_role": owner_role,
        "due_at": action.get("due_at"),
        "completed_at": action.get("completed_at"),
        "completion_evidence_ref": completion_ref,
        "effectiveness_evidence_ref": effectiveness_ref,
        "issues": sorted(set(issues)),
        "questions": list(dict.fromkeys(questions)),
    }


def assess_incident(record: dict[str, Any], now: datetime) -> dict[str, Any]:
    incident_id = required_text(record.get("incident_id"), "incident_id")
    service = required_text(record.get("service"), f"{incident_id}.service")

    detected = parse_time(record.get("detected_at"), f"{incident_id}.detected_at")
    restored = parse_time(record.get("restored_at"), f"{incident_id}.restored_at")
    if detected and restored and restored < detected:
        raise ValueError(f"{incident_id}: restored_at cannot precede detected_at")

    timeline = record.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        timeline_quality = "UNKNOWN"
    else:
        valid_events = 0
        for idx, event in enumerate(timeline):
            if not isinstance(event, dict):
                raise ValueError(f"{incident_id}.timeline[{idx}] must be an object")
            if event.get("at") and event.get("event"):
                parse_time(event["at"], f"{incident_id}.timeline[{idx}].at")
                valid_events += 1
        timeline_quality = "SUPPORTED" if valid_events == len(timeline) else "PARTIAL"

    postmortem = record.get("postmortem")
    if not isinstance(postmortem, dict):
        postmortem = {}

    narrative = postmortem.get("narrative")
    contributing = postmortem.get("contributing_conditions")
    evidence_refs = postmortem.get("evidence_refs")
    lessons = postmortem.get("lessons")

    pm_issues: list[str] = []
    if not narrative:
        pm_issues.append("narrative_missing")
    if not isinstance(contributing, list) or not contributing:
        pm_issues.append("contributing_conditions_missing")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        pm_issues.append("evidence_refs_missing")
    if not isinstance(lessons, list) or not lessons:
        pm_issues.append("lessons_missing")

    actions = record.get("corrective_actions")
    if not isinstance(actions, list):
        raise ValueError(f"{incident_id}.corrective_actions must be a list")
    assessed_actions = [assess_action(a, now) for a in actions]

    completed_with_effectiveness = sum(
        1
        for action in assessed_actions
        if action["state"] == "COMPLETED" and action["effectiveness_evidence_ref"]
    )
    completed_without_effectiveness = sum(
        1
        for action in assessed_actions
        if action["state"] == "COMPLETED" and not action["effectiveness_evidence_ref"]
    )
    overdue = sum(1 for action in assessed_actions if action["state"] == "OVERDUE")
    changed = sum(1 for action in assessed_actions if action["state"] == "CHANGED_APPROACH")

    if not postmortem:
        learning_evidence = "UNKNOWN"
    elif pm_issues:
        learning_evidence = "PARTIAL"
    elif completed_with_effectiveness > 0:
        learning_evidence = "FOLLOW_THROUGH_EVIDENCED"
    elif assessed_actions:
        learning_evidence = "NARRATIVE_WITH_ACTIONS_PENDING"
    else:
        learning_evidence = "NARRATIVE_ONLY"

    restore_minutes = None
    if detected and restored:
        restore_minutes = round((restored - detected).total_seconds() / 60.0, 2)

    return {
        "incident_id": incident_id,
        "service": service,
        "timeline_quality": timeline_quality,
        "restore_minutes": restore_minutes,
        "postmortem_issues": pm_issues,
        "learning_evidence": learning_evidence,
        "action_summary": {
            "total": len(assessed_actions),
            "completed_with_effectiveness": completed_with_effectiveness,
            "completed_without_effectiveness": completed_without_effectiveness,
            "overdue": overdue,
            "changed_approach": changed,
            "open_or_unknown": len(assessed_actions)
            - completed_with_effectiveness
            - completed_without_effectiveness
            - overdue
            - changed,
        },
        "actions": assessed_actions,
    }


def assess_packet(packet: dict[str, Any]) -> dict[str, Any]:
    evaluated_at = parse_time(packet.get("evaluated_at"), "evaluated_at")
    if evaluated_at is None:
        raise ValueError("evaluated_at is required for deterministic overdue evaluation")

    incidents = packet.get("incidents")
    if not isinstance(incidents, list) or not incidents:
        raise ValueError("incidents must be a non-empty list")

    results = [assess_incident(i, evaluated_at) for i in incidents]
    return {
        "schema": "uiowa-067-incident-learning-assessment-v1",
        "synthetic": bool(packet.get("synthetic")),
        "evaluated_at": packet["evaluated_at"],
        "incidents": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    result = assess_packet(packet)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
