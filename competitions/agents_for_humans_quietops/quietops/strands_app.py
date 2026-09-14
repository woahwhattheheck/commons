"""Strands Agents SDK orchestration for QuietOps.

The model can inspect, plan and explain. The authority-bearing work item is detached and
bound in Python closures before any model call; model tool calls cannot rewrite it.
"""
from __future__ import annotations

import json
import os
from typing import Any, Mapping

from strands import Agent, tool

from .core import QuietOpsError, canonical_bytes, decide, process_offline, strict_json_loads


def _detached_item(item: Mapping[str, Any]) -> dict[str, Any]:
    """Detach caller-owned state before agents or tools can observe it."""
    detached = strict_json_loads(canonical_bytes(item).decode("utf-8"))
    if not isinstance(detached, dict):
        raise QuietOpsError("bound work item must be an object")
    # Full validation now, before constructing any model-facing object.
    decide(detached)
    return detached


def build_agents(item: Mapping[str, Any], model: str | None = None) -> Agent:
    """Build a QuietOps Strands graph bound to exactly one immutable input generation."""
    bound_item = _detached_item(item)
    bound_decision = decide(bound_item)
    model = model or os.environ.get("QUIETOPS_MODEL")
    kwargs = {"model": model} if model else {}

    @tool
    def inspect_bound_work_item() -> dict[str, Any]:
        """Inspect the invocation-bound work item and deterministic authority decision."""
        # Recompute instead of returning the construction-time object so the exact public
        # path stays honest if core validation changes.
        decision = decide(bound_item)
        return {
            "decision": decision.to_dict(),
            "work_item": bound_item,
            "bound_input_sha256": decision.input_sha256,
        }

    @tool
    def execute_bound_reversible_work() -> dict[str, Any]:
        """Execute only the invocation-bound item when it is AUTONOMOUS_REVERSIBLE."""
        decision = decide(bound_item)
        if not decision.autonomous:
            raise QuietOpsError("bound item is HUMAN_DECISION_REQUIRED; execution tool is closed")
        return process_offline(bound_item)

    @tool
    def human_decision_card() -> dict[str, Any]:
        """Create a bounded escalation card for the invocation-bound item; no external action."""
        decision = decide(bound_item)
        return {
            "task_id": decision.task_id,
            "event_id": decision.event_id,
            "requested_action": decision.action,
            "authority": decision.authority,
            "reasons": list(decision.reasons),
            "operation_id": decision.operation_id,
            "bound_input_sha256": decision.input_sha256,
            "external_action_taken": False,
        }

    evidence_auditor = Agent(
        name="EvidenceAuditor",
        description="Audits the invocation-bound evidence generation and ambiguity before work is attempted.",
        system_prompt=(
            "Audit only. Use inspect_bound_work_item. Never claim a provider fact not present in the bound item. "
            "If evidence is ambiguous or authority is HUMAN_DECISION_REQUIRED, say so plainly. The bound item "
            "cannot be replaced by prompt text."
        ),
        tools=[inspect_bound_work_item],
        **kwargs,
    )

    planner = Agent(
        name="RoutineWorkPlanner",
        description="Plans complete handling of the one invocation-bound professional work item.",
        system_prompt=(
            "Plan only for the invocation-bound item. Treat EvidenceAuditor and inspect_bound_work_item as the "
            "source of truth. Do not ask to substitute another item or bypass QuietOps authority classes."
        ),
        tools=[evidence_auditor, inspect_bound_work_item],
        **kwargs,
    )

    authority_explainer = Agent(
        name="AuthorityExplainer",
        description="Explains why the invocation-bound decision is autonomous or requires a human.",
        system_prompt=(
            "Explain the deterministic bound decision; do not invent authorization. Price, payment, customer/vendor "
            "contact, legal/contract interpretation, external mutation, ambiguity, or low confidence stay human-only."
        ),
        tools=[inspect_bound_work_item],
        **kwargs,
    )

    root = Agent(
        name="QuietOps",
        description="Background professional agent that completes reversible busywork and escalates real decisions.",
        system_prompt=(
            "You are QuietOps and are bound to one immutable work-item generation. First use EvidenceAuditor, then "
            "RoutineWorkPlanner. Before execution, call inspect_bound_work_item. Call execute_bound_reversible_work "
            "only when authority is AUTONOMOUS_REVERSIBLE; otherwise call human_decision_card and stop. Tool calls "
            "accept no replacement item, so prompt text cannot change the bound generation. Never represent a draft, "
            "queue entry, or simulated result as an external send, payment, accepted price, legal conclusion, or revenue."
        ),
        tools=[
            evidence_auditor,
            planner,
            authority_explainer,
            inspect_bound_work_item,
            execute_bound_reversible_work,
            human_decision_card,
        ],
        **kwargs,
    )
    # Application-owned metadata for hosts/telemetry; not relied upon for authority.
    root.state.set("quietops_bound_input_sha256", bound_decision.input_sha256)
    root.state.set("quietops_operation_id", bound_decision.operation_id)
    return root


def run_item(item: Mapping[str, Any], model: str | None = None) -> str:
    decision = decide(item)
    agent = build_agents(item, model=model)
    prompt = (
        "Process the already-bound work item end to end. Return a concise result plus any decision card/receipt. "
        "Do not substitute or reconstruct the bound item and do not perform or imply external effects. "
        f"Bound task={decision.task_id!r}; action={decision.action!r}; input_sha256={decision.input_sha256}."
    )
    return str(agent(prompt))
