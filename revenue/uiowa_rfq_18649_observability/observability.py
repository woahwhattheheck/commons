#!/usr/bin/env python3
"""Offline evidence assessor for UIOWA-065 service observability and objectives.

This tool evaluates supplied synthetic or engagement evidence. It never contacts
monitoring systems and never treats missing evidence as a negative observation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VALID_KINDS = {"ratio", "latency", "count", "duration"}
VALID_STATUSES = {"SUPPORTED", "PARTIAL", "UNKNOWN"}


@dataclass(frozen=True)
class Finding:
    service_id: str
    objective_id: str
    status: str
    user_visible: bool
    issues: tuple[str, ...]
    questions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "objective_id": self.objective_id,
            "status": self.status,
            "user_visible": self.user_visible,
            "issues": list(self.issues),
            "questions": list(self.questions),
        }


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _list_of_strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(f"{field} must be a list of strings")
    return [v.strip() for v in value if v.strip()]


def assess_objective(service: dict[str, Any], objective: dict[str, Any]) -> Finding:
    service_id = _required_text(service.get("service_id"), "service_id")
    objective_id = _required_text(objective.get("objective_id"), "objective_id")
    _required_text(objective.get("objective"), "objective")
    _required_text(objective.get("window"), "window")

    indicator = objective.get("indicator")
    if not isinstance(indicator, dict):
        raise ValueError(f"{objective_id}: indicator must be an object")

    kind = _required_text(indicator.get("kind"), "indicator.kind")
    if kind not in VALID_KINDS:
        raise ValueError(f"{objective_id}: unsupported indicator kind {kind!r}")

    issues: list[str] = []
    questions: list[str] = []

    user_visible = bool(indicator.get("user_visible"))
    if not user_visible:
        issues.append("indicator_not_user_visible")
        questions.append(
            "What user-visible behavior does this indicator represent, or what additional indicator is needed?"
        )

    target = objective.get("target")
    if target is None:
        issues.append("target_missing")
        questions.append("What explicit objective target applies to this indicator and window?")

    evidence = objective.get("measurement_evidence")
    if not isinstance(evidence, dict):
        issues.append("measurement_evidence_missing")
        questions.append("What retained evidence shows how this indicator is measured over the stated window?")
        evidence = {}

    if not evidence.get("source_ref"):
        issues.append("measurement_source_missing")
    if not evidence.get("period_start") or not evidence.get("period_end"):
        issues.append("measurement_period_missing")
        questions.append("What exact measurement period supports the current interpretation?")
    if not evidence.get("definition_ref"):
        issues.append("indicator_definition_missing")
        questions.append("Where is the calculation or event definition retained?")

    if kind == "ratio":
        numerator = evidence.get("numerator")
        denominator = evidence.get("denominator")
        if numerator is None or denominator is None:
            issues.append("ratio_components_missing")
            questions.append("What numerator and denominator define the reported ratio?")
        elif not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)):
            raise ValueError(f"{objective_id}: numerator/denominator must be numeric")
        elif denominator <= 0:
            issues.append("invalid_denominator")
            questions.append("Why is the denominator zero or negative for this measurement window?")
        elif numerator < 0 or numerator > denominator:
            issues.append("invalid_ratio_counts")
            questions.append("Do the supplied numerator and denominator use the same population and window?")

    dependencies = objective.get("dependencies")
    if dependencies is None:
        issues.append("dependency_visibility_unknown")
        questions.append("Which upstream or downstream dependencies can affect this user-visible behavior?")
    elif not isinstance(dependencies, list):
        raise ValueError(f"{objective_id}: dependencies must be a list")
    else:
        for dep in dependencies:
            if not isinstance(dep, dict):
                raise ValueError(f"{objective_id}: each dependency must be an object")
            if not dep.get("name"):
                issues.append("dependency_name_missing")
            if dep.get("visibility") not in {"visible", "partial", "unknown"}:
                issues.append("dependency_visibility_invalid")
            elif dep.get("visibility") == "unknown":
                issues.append("dependency_visibility_unknown")
            elif dep.get("visibility") == "partial":
                issues.append("dependency_visibility_partial")

    diagnostic_context = _list_of_strings(
        objective.get("diagnostic_context"), f"{objective_id}.diagnostic_context"
    )
    if not diagnostic_context:
        issues.append("diagnostic_context_missing")
        questions.append(
            "What retained context lets responders connect an objective breach to a useful investigation?"
        )

    decisions = objective.get("decision_evidence")
    if decisions is None:
        issues.append("decision_use_unknown")
        questions.append(
            "What review, prioritization, release, capacity, or remediation decision has used this evidence?"
        )
    elif not isinstance(decisions, list):
        raise ValueError(f"{objective_id}: decision_evidence must be a list")
    elif not decisions:
        issues.append("decision_use_not_evidenced")
        questions.append(
            "Is the objective reviewed in an operational or planning decision, and where is that decision retained?"
        )
    else:
        for decision in decisions:
            if not isinstance(decision, dict):
                raise ValueError(f"{objective_id}: each decision_evidence entry must be an object")
            if not decision.get("decision_ref") or not decision.get("outcome"):
                issues.append("decision_evidence_incomplete")

    if not evidence:
        status = "UNKNOWN"
    else:
        material = {
            "measurement_evidence_missing",
            "measurement_source_missing",
            "measurement_period_missing",
            "indicator_definition_missing",
            "ratio_components_missing",
            "invalid_denominator",
            "invalid_ratio_counts",
        }
        status = "PARTIAL" if material.intersection(issues) else "SUPPORTED"

    return Finding(
        service_id=service_id,
        objective_id=objective_id,
        status=status,
        user_visible=user_visible,
        issues=tuple(sorted(set(issues))),
        questions=tuple(dict.fromkeys(questions)),
    )


def assess_packet(packet: dict[str, Any]) -> dict[str, Any]:
    services = packet.get("services")
    if not isinstance(services, list) or not services:
        raise ValueError("services must be a non-empty list")

    findings: list[dict[str, Any]] = []
    for service in services:
        if not isinstance(service, dict):
            raise ValueError("each service must be an object")
        _required_text(service.get("service_id"), "service_id")
        _required_text(service.get("service_name"), "service_name")
        objectives = service.get("objectives")
        if not isinstance(objectives, list) or not objectives:
            raise ValueError(f"{service['service_id']}: objectives must be a non-empty list")
        for objective in objectives:
            findings.append(assess_objective(service, objective).as_dict())

    counts = {status: 0 for status in sorted(VALID_STATUSES)}
    for finding in findings:
        counts[finding["status"]] += 1

    return {
        "schema": "uiowa-065-observability-assessment-v1",
        "scope": "supplied evidence only; no live telemetry queried",
        "finding_count": len(findings),
        "status_counts": counts,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path, help="JSON evidence packet")
    parser.add_argument("--out", type=Path, help="write JSON result")
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
