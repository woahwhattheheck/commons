"""Executable acceptance-evidence contract for the four DCSA prototype phases."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Mapping

from .strict import ValidationError, canonical_json_bytes, require_exact_keys, require_plain_list, require_string

ACCEPTANCE_SCHEMA = "dcsa-innovation-call-01/acceptance-matrix/v1"
PHASES = (
    "PHASE_1_DISCOVERY_BASELINE",
    "PHASE_2_CORE_PROTOTYPE",
    "PHASE_3_APPLICATION_ONBOARDING",
    "PHASE_4_VALIDATION_AUTHORIZATION_TRANSITION",
)

MATRIX: tuple[dict[str, Any], ...] = (
    {
        "phase": PHASES[0],
        "decision_point": "Government can judge whether the baseline, architecture, sustainment transition, and test strategy are credible.",
        "required_evidence": [
            "approved persona, role, attribute, and workflow inventory",
            "application, interface, dependency, and authority inventory",
            "IE sustainment transition receipt and known-issue baseline",
            "common-shell and role-based-navigation design evidence",
            "security approach, authorization evidence plan, and data-flow baseline",
            "test plan, backlog, measurable success criteria, and rollback model",
        ],
        "failure_conditions": [
            "unowned sustainment dependency",
            "unresolved mission-workflow authority",
            "missing rollback or continuity baseline",
            "security authorization deferred to a later phase",
        ],
    },
    {
        "phase": PHASES[1],
        "decision_point": "Government can observe a common entry point, policy-aware navigation, and at least one end-to-end workflow without hidden legacy disruption.",
        "required_evidence": [
            "single-entry shell with approved identity-provider assertions",
            "CAC/PIV, ECA, and other approved MFA adapter contract tests",
            "role, permission, attribute, resource, and data-aware policy tests",
            "common dashboard and approved-user-information projection tests",
            "one end-to-end workflow with continuity canary and visible fallback",
            "modular API and event adapter contracts with idempotency and ambiguity handling",
            "accessibility and design-system conformance evidence",
        ],
        "failure_conditions": [
            "shell mints identity or bypasses policy authority",
            "silent partial success across an adapter boundary",
            "legacy workflow unavailable after prototype deployment",
            "accessibility or zero-trust control is untested",
        ],
    },
    {
        "phase": PHASES[2],
        "decision_point": "Government can judge whether eApp, IEP, required forms/PVQ, and PDT can be onboarded through reusable patterns while remaining operational.",
        "required_evidence": [
            "authorized-role access evidence for each initial application/form family",
            "validated handoff and user-context continuity tests",
            "representative cross-application workflow demonstrations",
            "operational impact, integration issue, and recommendation ledger",
            "reusable onboarding checklist, interface specification, and lessons learned",
            "application-specific rollback and continuity receipts",
        ],
        "failure_conditions": [
            "one-off integration with no reusable contract",
            "unresolved cross-application authority or data ownership",
            "context transplant between users, roles, or workflows",
            "application sustainment degradation during onboarding",
        ],
    },
    {
        "phase": PHASES[3],
        "decision_point": "Government can decide whether the prototype is viable, authorized, and bounded for production transition.",
        "required_evidence": [
            "GAT, UAT, regression, integration, performance, reliability, accessibility, and security results",
            "exact defect, usability, integration, security, and operational-risk disposition",
            "authorization documentation, evidence, remediation, and ATO decision support",
            "final prototype design and prioritized enhancement backlog",
            "production-readiness assessment and transition recommendation",
            "phased production plan and owner-approved deployment/operations/sustainment/onboarding ROM",
        ],
        "failure_conditions": [
            "critical finding lacks owner, disposition, or remediation evidence",
            "test result is not bound to exact source/configuration/environment generations",
            "ATO-critical evidence remains planned rather than produced",
            "production ROM relies on unverified staffing, scope, or environment assumptions",
        ],
    },
)


def compile_matrix() -> Dict[str, Any]:
    matrix = {
        "schema": ACCEPTANCE_SCHEMA,
        "phases": [
            {
                "phase": row["phase"],
                "decision_point": row["decision_point"],
                "required_evidence": sorted(row["required_evidence"]),
                "failure_conditions": sorted(row["failure_conditions"]),
            }
            for row in MATRIX
        ],
        "external_action_authorized": False,
        "receipt_sha256": "",
    }
    matrix["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes({**matrix, "receipt_sha256": ""})
    ).hexdigest()
    return matrix


def verify_matrix(value: Any) -> bool:
    try:
        obj = require_exact_keys(
            value,
            {"schema", "phases", "external_action_authorized", "receipt_sha256"},
            field="acceptance matrix",
        )
        if obj["schema"] != ACCEPTANCE_SCHEMA or obj["external_action_authorized"] is not False:
            return False
        phases = require_plain_list(obj["phases"], field="acceptance matrix phases")
        if len(phases) != len(PHASES):
            return False
        for index, phase in enumerate(phases):
            row = require_exact_keys(
                phase,
                {"phase", "decision_point", "required_evidence", "failure_conditions"},
                field=f"acceptance phase {index}",
            )
            if row["phase"] != PHASES[index]:
                return False
            require_string(row["decision_point"], field="decision_point", maximum=800)
            for key in ("required_evidence", "failure_conditions"):
                values = require_plain_list(row[key], field=key)
                if not values or values != sorted(values) or len(set(values)) != len(values):
                    return False
                for item in values:
                    require_string(item, field=key, maximum=800)
        return canonical_json_bytes(obj) == canonical_json_bytes(compile_matrix())
    except ValidationError:
        return False


def render_matrix_markdown(value: Mapping[str, Any] | None = None) -> str:
    matrix = compile_matrix() if value is None else dict(value)
    if not verify_matrix(matrix):
        raise ValidationError("acceptance matrix does not verify")
    lines = [
        "# DCSA Innovation Call #01 — Prototype Acceptance Evidence",
        "",
        "> Internal evidence contract only. No Government acceptance, ATO, award, payment, or production authority is claimed.",
        "",
    ]
    for phase in matrix["phases"]:
        lines.extend(
            [
                f"## {phase['phase']}",
                "",
                f"**Decision point:** {phase['decision_point']}",
                "",
                "**Required evidence**",
                "",
                *[f"- {item}" for item in phase["required_evidence"]],
                "",
                "**Fail-closed conditions**",
                "",
                *[f"- {item}" for item in phase["failure_conditions"]],
                "",
            ]
        )
    lines.append(f"Receipt: `{matrix['receipt_sha256']}`")
    lines.append("")
    return "\n".join(lines)
