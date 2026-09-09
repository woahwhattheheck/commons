# SPDX-License-Identifier: Apache-2.0
"""Active-prefix certificate for TITAN seed-budget funding dispatch.

The canonical seed budget edits only orders the Kaggriculture interpreter can
execute, but the current dispatch decides whether a funding certificate is
needed by scanning every later market row, including the inert tail beyond
``maxMarketOrdersPerTurn``.  This module installs a default-off, instance-local
adapter.  It delegates every active-prefix or malformed case to the canonical
selector and bypasses that conservative selector only when the *sole* apparent
capital dependency is in the engine-inactive tail.

No producer, controller, route, selected unit action, seed-demand calculation,
or canonical module object is replaced.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import hashlib
import inspect
from types import MethodType
from typing import Any, Mapping

CAPITAL_OPERATIONS = frozenset(
    {"HIRE", "BUY_LAND", "BUY_PRODUCT", "BUY_ANIMAL"}
)

# inspect.getsource(TitanAgent._seed_selected) on
# woahwhattheheck/commons@e2b99bb417675ad574aa4d12cf1c32e5795124c5.
EXPECTED_SEED_SELECTED_SHA256 = (
    "b3bf094820b77a7b871b017c78fdfa18ef3663c94970c96c2eb572e5c693ff01"
)
EXPECTED_RUNTIME_GIT_BLOB = "b952c9c228ecbde592bf3d2df01638677abb0d24"


def _order_limit(configuration: Mapping[str, Any] | None) -> int:
    """Return the official active market width, rejecting ambiguous inputs."""
    if configuration is None:
        return 10
    if not isinstance(configuration, Mapping):
        raise TypeError("configuration must be a mapping")
    raw = configuration.get("maxMarketOrdersPerTurn", 10)
    # Production configuration is integral.  Do not turn bools, fractional
    # values, or strings into a new policy decision in this additive adapter.
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("maxMarketOrdersPerTurn must be an integer")
    return max(1, raw)


def _operation(order: Any) -> str | None:
    if not isinstance(order, list) or not order or not isinstance(order[0], str):
        return None
    return order[0]


def _strict_seed_reduction(before: Any, after: Any) -> bool:
    """Recognize only the exact SeedBudget edit shape."""
    if (
        not isinstance(before, list)
        or len(before) != 3
        or before[0] != "BUY_SEED"
        or not isinstance(before[1], str)
        or isinstance(before[2], bool)
        or not isinstance(before[2], int)
        or before[2] <= 0
    ):
        return False
    if after == []:
        return True
    return (
        isinstance(after, list)
        and len(after) == 3
        and after[:2] == before[:2]
        and not isinstance(after[2], bool)
        and isinstance(after[2], int)
        and 0 <= after[2] < before[2]
    )


def classify_prefix_dependency(
    baseline_action: Mapping[str, Any],
    proposed_action: Mapping[str, Any],
    configuration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify changed seed slots against the engine's executable prefix.

    ``inactive_tail_only`` is the only status that authorizes bypassing the
    current funding selector.  Every malformed or broader mutation is
    ``delegate`` so the canonical fail-closed behavior remains authoritative.
    """
    report: dict[str, Any] = {
        "status": "delegate",
        "reason": "invalid_input",
        "active_prefix_only": False,
    }
    try:
        if not isinstance(baseline_action, Mapping) or not isinstance(
            proposed_action, Mapping
        ):
            raise TypeError("actions must be mappings")
        limit = _order_limit(configuration)
        original = baseline_action.get("market", [])
        proposed = proposed_action.get("market", [])
        if not isinstance(original, list) or not isinstance(proposed, list):
            raise TypeError("market fields must be lists")
        if len(original) != len(proposed):
            raise ValueError("market slot count changed")
        before_nonmarket = {
            key: value for key, value in baseline_action.items() if key != "market"
        }
        after_nonmarket = {
            key: value for key, value in proposed_action.items() if key != "market"
        }
        if before_nonmarket != after_nonmarket:
            raise ValueError("non-market action fields changed")

        changed = [
            slot
            for slot, (before, after) in enumerate(zip(original, proposed))
            if before != after
        ]
        report.update(order_limit=limit, changed_slots=changed)
        if not changed:
            report.update(status="delegate", reason="no_seed_edit")
            return report
        if any(slot >= limit for slot in changed):
            raise ValueError("proposal edits an engine-inactive market row")
        if any(
            not _strict_seed_reduction(original[slot], proposed[slot])
            for slot in changed
        ):
            raise ValueError("proposal is not a strict active-prefix seed reduction")

        active_end = min(limit, len(original))
        active_dependencies = sorted(
            {
                slot
                for edit in changed
                for slot in range(edit + 1, active_end)
                if _operation(original[slot]) in CAPITAL_OPERATIONS
            }
        )
        inactive_dependencies = sorted(
            {
                slot
                for edit in changed
                for slot in range(max(edit + 1, limit), len(original))
                if _operation(original[slot]) in CAPITAL_OPERATIONS
            }
        )
        report.update(
            active_dependency_slots=active_dependencies,
            inactive_dependency_slots=inactive_dependencies,
            active_prefix_only=True,
        )
        if active_dependencies:
            report.update(
                status="delegate",
                reason="executable_downstream_capital_dependency",
            )
        elif inactive_dependencies:
            report.update(
                status="inactive_tail_only",
                reason="only_engine_inactive_tail_has_downstream_capital",
            )
        else:
            report.update(
                status="delegate",
                reason="no_downstream_capital_dependency",
            )
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        report["reason"] = str(error)
    return report



def _method_sha256(method: Any) -> str:
    function = getattr(method, "__func__", method)
    return hashlib.sha256(inspect.getsource(function).encode("utf-8")).hexdigest()


def install_seed_prefix_dependency(
    agent: Any,
    *,
    expected_method_sha256: str = EXPECTED_SEED_SELECTED_SHA256,
) -> dict[str, Any]:
    """Install the adapter on one TITAN instance, or preserve it unchanged.

    A source mismatch is a normal fail-closed result, not permission to guess a
    new integration.  Repeated installation on the same instance is idempotent.
    """
    existing = getattr(agent, "_seed_prefix_dependency_install_report", None)
    if isinstance(existing, dict):
        return deepcopy(existing)

    report: dict[str, Any] = {
        "status": "not_installed",
        "expected_method_sha256": expected_method_sha256,
        "expected_runtime_git_blob": EXPECTED_RUNTIME_GIT_BLOB,
    }
    original = getattr(agent, "_seed_selected", None)
    if not callable(original):
        report["reason"] = "agent lacks callable _seed_selected"
        agent._seed_prefix_dependency_install_report = deepcopy(report)
        return report

    try:
        observed = _method_sha256(original)
    except (OSError, TypeError) as error:
        report["reason"] = f"source unavailable: {type(error).__name__}: {error}"
        agent._seed_prefix_dependency_install_report = deepcopy(report)
        return report
    report["observed_method_sha256"] = observed
    if observed != expected_method_sha256:
        report["reason"] = "canonical _seed_selected source mismatch"
        agent._seed_prefix_dependency_install_report = deepcopy(report)
        return report

    original_function = getattr(original, "__func__", None)
    if original_function is None:
        report["reason"] = "canonical _seed_selected is not a bound method"
        agent._seed_prefix_dependency_install_report = deepcopy(report)
        return report

    @wraps(original_function)
    def wrapped(this: Any, obs: Any, cfg: Any, selected: Any) -> Any:
        # This is the exact source-bound predecessor method with one admitted
        # branch: a strict seed reduction whose only apparent capital
        # dependency is outside the official executable prefix.  Reusing the
        # already-computed proposal avoids a second SeedBudget call and keeps
        # its route/ledger state single-consumer.
        if not this.features.seed or not any(
            order and order[0] == "BUY_SEED" for order in selected["market"]
        ):
            return selected

        from scheduler import post_units, m

        snapshot = getattr(this.consumer, "selected_post_units", None)
        farm, private = (
            snapshot if snapshot is not None else post_units(obs, selected, cfg)
        )
        proposed = this.seed_budget.apply(
            selected,
            private["seeds"],
            int(obs["step"]),
            this.controller.cur,
            int(cfg.get("maxMarketOrdersPerTurn", 10)),
            extra_requests=(
                {}
                if this.spatial is None
                else this.spatial.future_seed_requests(int(obs["step"]))
            ),
        )
        decision = classify_prefix_dependency(selected, proposed, cfg)
        diagnostics = getattr(this, "diagnostics", None)

        if decision["status"] == "inactive_tail_only":
            report = {
                "status": "certified",
                "reason": "no_executable_downstream_capital_dependency",
                "scope": "current_market_active_prefix",
                "rival_private_used": False,
                "controller_calls": 0,
                "non_seed_execution_preserved": True,
                "edited_slots": list(decision["changed_slots"]),
                "active_dependency_slots": [],
                "ignored_inactive_dependency_slots": list(
                    decision["inactive_dependency_slots"]
                ),
            }
            returned = deepcopy(proposed)
            decision.update(
                bypassed_funding_selector=True,
                returned_proposal=True,
                funding_report=deepcopy(report),
                changed_action=returned != selected,
            )
            if isinstance(diagnostics, dict):
                diagnostics["seed_funding"] = report
                diagnostics["seed_prefix_dependency"] = deepcopy(decision)
            return returned

        # Preserve the exact predecessor disposition for every case not
        # admitted above.  In particular funding=False remains fail-closed for
        # real active-prefix dependencies, while tail-only dependencies now
        # take the same proposal path as the one-line canonical repair.
        edits = [
            slot
            for slot, (before, after) in enumerate(
                zip(selected["market"], proposed["market"])
            )
            if before != after
        ]
        dependent = any(
            order
            and order[0]
            in ("HIRE", "BUY_LAND", "BUY_PRODUCT", "BUY_ANIMAL")
            for slot in edits
            for order in selected["market"][slot + 1 :]
        )
        funding_report = None
        if not dependent:
            returned = proposed
        elif not this.features.funding:
            returned = selected
        else:
            post = deepcopy(obs)
            post["farms"][int(obs["player"])] = farm
            post["private"] = private
            returned, funding_report = this.funding_module.select_seed_queue(
                m,
                post,
                deepcopy(selected),
                deepcopy(proposed),
                deepcopy(cfg),
            )
            this.diagnostics["seed_funding"] = funding_report

        decision.update(
            bypassed_funding_selector=False,
            returned_proposal=returned == proposed,
            changed_action=returned != selected,
        )
        if funding_report is not None:
            decision["funding_report"] = deepcopy(funding_report)
        if isinstance(diagnostics, dict):
            diagnostics["seed_prefix_dependency"] = deepcopy(decision)
        return returned

    agent._seed_prefix_dependency_original = original
    agent._seed_selected = MethodType(wrapped, agent)
    report.update(status="installed", reason="exact canonical method matched")
    agent._seed_prefix_dependency_install_report = deepcopy(report)
    return report


def uninstall_seed_prefix_dependency(agent: Any) -> bool:
    """Restore the exact bound method retained by the installer."""
    original = getattr(agent, "_seed_prefix_dependency_original", None)
    if original is None:
        return False
    agent._seed_selected = original
    for name in (
        "_seed_prefix_dependency_original",
        "_seed_prefix_dependency_install_report",
    ):
        try:
            delattr(agent, name)
        except AttributeError:
            pass
    return True


__all__ = [
    "CAPITAL_OPERATIONS",
    "EXPECTED_RUNTIME_GIT_BLOB",
    "EXPECTED_SEED_SELECTED_SHA256",
    "classify_prefix_dependency",
    "install_seed_prefix_dependency",
    "uninstall_seed_prefix_dependency",
]
