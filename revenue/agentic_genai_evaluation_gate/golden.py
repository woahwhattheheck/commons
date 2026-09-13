"""Synthetic 180-scenario acceptance fixture for the agentic evaluation gate."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any


def _h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


CATEGORIES = ("NORMAL", "TOOL_USING", "ADVERSARIAL", "DEGRADED_OBSERVABILITY")


def build_golden_packet() -> dict[str, Any]:
    build_sha = _h("agent-build:cat-eval:v7")
    rubric_sha = _h("rubric:agentic-release:v3")
    scenario_ids = [f"scenario-{index:03d}" for index in range(180)]
    scenarios: list[dict[str, Any]] = []
    for index, scenario_id in enumerate(scenario_ids):
        category = CATEGORIES[index // 45]
        trace_sha = _h(f"trace:{scenario_id}")
        tool_calls = []
        if category in {"TOOL_USING", "ADVERSARIAL"}:
            tool_calls.append(
                {
                    "call_id": f"call-{index:03d}-01",
                    "tool": "synthetic.customer-records",
                    "action": "lookup" if category == "TOOL_USING" else "policy-probe",
                    "effect_class": "READ_ONLY",
                    "result_status": "SUCCESS",
                    "trace_sha256": trace_sha,
                }
            )
        if category == "ADVERSARIAL":
            tool_calls.append(
                {
                    "call_id": f"call-{index:03d}-02",
                    "tool": "synthetic.notification",
                    "action": "blocked-send",
                    "effect_class": "EXTERNAL_SIDE_EFFECT",
                    "result_status": "SUCCESS",
                    "trace_sha256": trace_sha,
                }
            )
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "category": category,
                "agent_build_sha256": build_sha,
                "rubric_sha256": rubric_sha,
                "trace_sha256": trace_sha,
                "result_sha256": _h(f"result:{scenario_id}"),
                "evidence_at": "2026-09-13T13:45:00Z",
                "automated_score_bps": 9700 - (index % 7) * 25,
                "automated_status": "PASS",
                "human_review": {
                    "review_id": f"review-{index:03d}",
                    "reviewer_role": "synthetic-evaluation-reviewer",
                    "decision": "PASS",
                    "decided_at": "2026-09-13T13:50:00Z",
                    "agent_build_sha256": build_sha,
                    "rubric_sha256": rubric_sha,
                    "trace_sha256": trace_sha,
                },
                "safety": {
                    "status": "PASS",
                    "checks_sha256": _h(f"safety:{scenario_id}"),
                    "observed_at": "2026-09-13T13:48:00Z",
                    "agent_build_sha256": build_sha,
                    "trace_sha256": trace_sha,
                },
                "observability": {
                    "status": "COMPLETE",
                    "pointer_sha256": _h(f"observability:{scenario_id}"),
                    "observed_at": "2026-09-13T13:49:00Z",
                    "trace_sha256": trace_sha,
                },
                "tool_calls": tool_calls,
            }
        )
    return {
        "schema_version": 1,
        "evaluation_id": "synthetic-caterpillar-agentic-eval-20260913",
        "evaluation_set": {
            "set_id": "agentic-release-portfolio",
            "generation": 1,
            "sha256": _h("evaluation-set:agentic-release-portfolio:g1"),
            "required_scenarios": scenario_ids,
        },
        "agent_build": {
            "agent_id": "synthetic-enterprise-agent",
            "version": "7.0.0",
            "sha256": build_sha,
        },
        "rubric": {
            "rubric_id": "agentic-release-rubric",
            "generation": 3,
            "sha256": rubric_sha,
            "minimum_score_bps": 9000,
        },
        "policy": {
            "max_evidence_age_seconds": 86400,
            "require_human_review": True,
            "require_complete_observability": True,
        },
        "scenarios": scenarios,
    }


def clone_golden_packet() -> dict[str, Any]:
    return deepcopy(build_golden_packet())
