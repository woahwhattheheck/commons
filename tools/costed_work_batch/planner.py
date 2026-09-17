#!/usr/bin/env python3
"""Deadline-aware costed work-batch optimizer.

This module evaluates owner-entered what-if economics.  It does not establish
task ownership, payout authenticity, collection probability, or authority to
spend/send/collect.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable

SCHEMA = "costed-work-batch/v1"
RESULT_SCHEMA = "costed-work-batch-result/v1"
PPM = 1_000_000


class ScenarioError(ValueError):
    """Stable validation error for malformed or unsupported scenarios."""


def _strict_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ScenarioError(f"duplicate key: {key}")
        out[key] = value
    return out


def load_strict_json(text: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ScenarioError(f"non-finite number: {value}")

    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=reject_constant,
        )
    except ScenarioError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ScenarioError("invalid JSON") from exc
    if not isinstance(value, dict):
        raise ScenarioError("top-level JSON must be an object")
    return value


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ScenarioError("value is not canonical-JSON encodable") from exc


def digest_json(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _expect_keys(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] | None = None,
    where: str,
) -> None:
    optional = optional or set()
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise ScenarioError(f"{where}: missing keys {sorted(missing)}")
    if extra:
        raise ScenarioError(f"{where}: unexpected keys {sorted(extra)}")


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise ScenarioError(f"{where}: must be boolean")
    return value


def _int(
    value: Any,
    where: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if type(value) is not int:
        raise ScenarioError(f"{where}: must be integer")
    if value < minimum:
        raise ScenarioError(f"{where}: must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ScenarioError(f"{where}: must be <= {maximum}")
    return value


def _string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ScenarioError(f"{where}: must be a non-empty trimmed string")
    return value


@dataclass(frozen=True)
class Family:
    family_id: str
    setup_cash_minor: int
    setup_effort_cost_minor: int
    setup_minutes: int


@dataclass(frozen=True)
class Job:
    operation_id: str
    family_id: str
    available: bool
    already_owned: bool
    duration_minutes: int
    cash_cost_minor: int
    effort_cost_minor: int
    payout_minor: int | None
    success_probability_ppm: int | None
    collection_probability_ppm: int | None
    deadline_minutes: int

    @property
    def valued(self) -> bool:
        return (
            self.payout_minor is not None
            and self.success_probability_ppm is not None
            and self.collection_probability_ppm is not None
        )

    @property
    def expected_collection_minor(self) -> int | None:
        if not self.valued:
            return None
        # Two floors are deliberate and conservative: no sub-minor-unit value
        # may be resurrected by later multiplication.
        success_value = (
            self.payout_minor * self.success_probability_ppm // PPM
        )
        return success_value * self.collection_probability_ppm // PPM

    @property
    def base_net_minor(self) -> int | None:
        expected = self.expected_collection_minor
        if expected is None:
            return None
        return expected - self.cash_cost_minor - self.effort_cost_minor


@dataclass(frozen=True)
class Limits:
    cash_limit_minor: int
    effort_limit_minutes: int
    horizon_minutes: int
    minimum_batch_net_minor: int
    node_budget: int


@dataclass(frozen=True)
class Scenario:
    families: dict[str, Family]
    jobs: tuple[Job, ...]
    limits: Limits
    source_digest: str


@dataclass(frozen=True)
class Evaluation:
    feasible: bool
    net_minor: int
    expected_collection_minor: int
    cash_cost_minor: int
    effort_cost_minor: int
    effort_minutes: int
    completion_minutes: int
    schedule: tuple[dict[str, Any], ...]
    reason: str | None


def parse_scenario(raw: dict[str, Any]) -> Scenario:
    if not isinstance(raw, dict):
        raise ScenarioError("scenario must be object")
    _expect_keys(
        raw,
        required={"schema", "limits", "families", "jobs"},
        where="scenario",
    )
    if raw["schema"] != SCHEMA:
        raise ScenarioError(f"scenario.schema: expected {SCHEMA!r}")

    limits_raw = raw["limits"]
    if not isinstance(limits_raw, dict):
        raise ScenarioError("limits: must be object")
    _expect_keys(
        limits_raw,
        required={
            "cash_limit_minor",
            "effort_limit_minutes",
            "horizon_minutes",
            "minimum_batch_net_minor",
            "node_budget",
        },
        where="limits",
    )
    limits = Limits(
        cash_limit_minor=_int(
            limits_raw["cash_limit_minor"], "limits.cash_limit_minor"
        ),
        effort_limit_minutes=_int(
            limits_raw["effort_limit_minutes"],
            "limits.effort_limit_minutes",
        ),
        horizon_minutes=_int(
            limits_raw["horizon_minutes"], "limits.horizon_minutes"
        ),
        minimum_batch_net_minor=_int(
            limits_raw["minimum_batch_net_minor"],
            "limits.minimum_batch_net_minor",
        ),
        node_budget=_int(
            limits_raw["node_budget"],
            "limits.node_budget",
            minimum=1,
            maximum=10_000_000,
        ),
    )

    families_raw = raw["families"]
    if not isinstance(families_raw, list):
        raise ScenarioError("families: must be array")
    families: dict[str, Family] = {}
    for i, item in enumerate(families_raw):
        where = f"families[{i}]"
        if not isinstance(item, dict):
            raise ScenarioError(f"{where}: must be object")
        _expect_keys(
            item,
            required={
                "family_id",
                "setup_cash_minor",
                "setup_effort_cost_minor",
                "setup_minutes",
            },
            where=where,
        )
        family_id = _string(item["family_id"], f"{where}.family_id")
        if family_id in families:
            raise ScenarioError(f"families: duplicate family_id {family_id!r}")
        families[family_id] = Family(
            family_id=family_id,
            setup_cash_minor=_int(
                item["setup_cash_minor"], f"{where}.setup_cash_minor"
            ),
            setup_effort_cost_minor=_int(
                item["setup_effort_cost_minor"],
                f"{where}.setup_effort_cost_minor",
            ),
            setup_minutes=_int(
                item["setup_minutes"], f"{where}.setup_minutes"
            ),
        )

    jobs_raw = raw["jobs"]
    if not isinstance(jobs_raw, list):
        raise ScenarioError("jobs: must be array")
    jobs: list[Job] = []
    seen_ops: set[str] = set()
    for i, item in enumerate(jobs_raw):
        where = f"jobs[{i}]"
        if not isinstance(item, dict):
            raise ScenarioError(f"{where}: must be object")
        _expect_keys(
            item,
            required={
                "operation_id",
                "family_id",
                "available",
                "already_owned",
                "duration_minutes",
                "cash_cost_minor",
                "effort_cost_minor",
                "payout_minor",
                "success_probability_ppm",
                "collection_probability_ppm",
                "deadline_minutes",
            },
            where=where,
        )
        operation_id = _string(
            item["operation_id"], f"{where}.operation_id"
        )
        if operation_id in seen_ops:
            raise ScenarioError(f"jobs: duplicate operation_id {operation_id!r}")
        seen_ops.add(operation_id)
        family_id = _string(item["family_id"], f"{where}.family_id")
        if family_id not in families:
            raise ScenarioError(
                f"{where}.family_id: unknown family {family_id!r}"
            )

        payout = item["payout_minor"]
        success = item["success_probability_ppm"]
        collection = item["collection_probability_ppm"]
        all_none = payout is None and success is None and collection is None
        all_present = payout is not None and success is not None and collection is not None
        if not (all_none or all_present):
            raise ScenarioError(
                f"{where}: payout/probability fields must be all null or all integers"
            )
        if all_present:
            payout = _int(payout, f"{where}.payout_minor")
            success = _int(
                success,
                f"{where}.success_probability_ppm",
                maximum=PPM,
            )
            collection = _int(
                collection,
                f"{where}.collection_probability_ppm",
                maximum=PPM,
            )

        jobs.append(
            Job(
                operation_id=operation_id,
                family_id=family_id,
                available=_bool(item["available"], f"{where}.available"),
                already_owned=_bool(
                    item["already_owned"], f"{where}.already_owned"
                ),
                duration_minutes=_int(
                    item["duration_minutes"],
                    f"{where}.duration_minutes",
                    minimum=1,
                ),
                cash_cost_minor=_int(
                    item["cash_cost_minor"], f"{where}.cash_cost_minor"
                ),
                effort_cost_minor=_int(
                    item["effort_cost_minor"],
                    f"{where}.effort_cost_minor",
                ),
                payout_minor=payout,
                success_probability_ppm=success,
                collection_probability_ppm=collection,
                deadline_minutes=_int(
                    item["deadline_minutes"],
                    f"{where}.deadline_minutes",
                    minimum=1,
                ),
            )
        )

    return Scenario(
        families=families,
        jobs=tuple(jobs),
        limits=limits,
        source_digest=digest_json(raw),
    )


def _eligibility_reason(job: Job) -> str | None:
    if not job.available:
        return "UNAVAILABLE"
    if job.already_owned:
        return "ALREADY_OWNED"
    if not job.valued:
        return "UNVALUED_PAYOUT"
    if job.base_net_minor is None or job.base_net_minor <= 0:
        return "NONPOSITIVE_STANDALONE_VALUE"
    return None


def evaluate_subset(scenario: Scenario, selected: Iterable[Job]) -> Evaluation:
    jobs = tuple(
        sorted(selected, key=lambda j: (j.deadline_minutes, j.operation_id))
    )
    used_families: set[str] = set()
    elapsed = 0
    cash = 0
    effort_cost = 0
    expected = 0
    schedule: list[dict[str, Any]] = []

    for job in jobs:
        family = scenario.families[job.family_id]
        if family.family_id not in used_families:
            setup_start = elapsed
            elapsed += family.setup_minutes
            cash += family.setup_cash_minor
            effort_cost += family.setup_effort_cost_minor
            schedule.append(
                {
                    "kind": "SETUP",
                    "family_id": family.family_id,
                    "start_minute": setup_start,
                    "end_minute": elapsed,
                }
            )
            used_families.add(family.family_id)

        start = elapsed
        elapsed += job.duration_minutes
        cash += job.cash_cost_minor
        effort_cost += job.effort_cost_minor
        assert job.expected_collection_minor is not None
        expected += job.expected_collection_minor
        schedule.append(
            {
                "kind": "JOB",
                "operation_id": job.operation_id,
                "family_id": job.family_id,
                "start_minute": start,
                "end_minute": elapsed,
                "deadline_minute": job.deadline_minutes,
            }
        )
        if elapsed > job.deadline_minutes:
            return Evaluation(
                False,
                expected - cash - effort_cost,
                expected,
                cash,
                effort_cost,
                elapsed,
                elapsed,
                tuple(schedule),
                f"DEADLINE_MISSED:{job.operation_id}",
            )

    if cash > scenario.limits.cash_limit_minor:
        reason = "CASH_LIMIT_EXCEEDED"
    elif elapsed > scenario.limits.effort_limit_minutes:
        reason = "EFFORT_LIMIT_EXCEEDED"
    elif elapsed > scenario.limits.horizon_minutes:
        reason = "HORIZON_EXCEEDED"
    else:
        reason = None

    return Evaluation(
        reason is None,
        expected - cash - effort_cost,
        expected,
        cash,
        effort_cost,
        elapsed,
        elapsed,
        tuple(schedule),
        reason,
    )


def _search_candidates(scenario: Scenario) -> tuple[Job, ...]:
    candidates = [
        job for job in scenario.jobs if _eligibility_reason(job) is None
    ]
    # Value-first search improves incumbents; tie-breakers keep replay exact.
    candidates.sort(
        key=lambda j: (
            -(j.base_net_minor or 0),
            j.deadline_minutes,
            j.operation_id,
        )
    )
    return tuple(candidates)


def _upper_bound(
    scenario: Scenario,
    candidates: tuple[Job, ...],
    idx: int,
    selected: tuple[int, ...],
) -> tuple[int, Evaluation] | None:
    evaluation = evaluate_subset(
        scenario, (candidates[i] for i in selected)
    )
    if not evaluation.feasible:
        return None
    remaining_gain = sum(
        max(0, candidates[i].base_net_minor or 0)
        for i in range(idx, len(candidates))
    )
    return evaluation.net_minor + remaining_gain, evaluation


def exhaustive_optimum(scenario: Scenario) -> tuple[tuple[str, ...], Evaluation]:
    """Independent small-instance oracle; raises when input is too large."""
    candidates = _search_candidates(scenario)
    if len(candidates) > 20:
        raise ScenarioError("exhaustive oracle supports at most 20 candidates")
    best_ids: tuple[str, ...] = ()
    best = evaluate_subset(scenario, ())
    for mask in range(1 << len(candidates)):
        selected = tuple(
            candidates[i] for i in range(len(candidates)) if mask & (1 << i)
        )
        evaluation = evaluate_subset(scenario, selected)
        if not evaluation.feasible:
            continue
        ids = tuple(sorted(job.operation_id for job in selected))
        if (
            evaluation.net_minor > best.net_minor
            or (
                evaluation.net_minor == best.net_minor
                and ids < best_ids
            )
        ):
            best = evaluation
            best_ids = ids
    return best_ids, best


def optimize(scenario: Scenario) -> dict[str, Any]:
    candidates = _search_candidates(scenario)
    best_selected: tuple[int, ...] = ()
    best_eval = evaluate_subset(scenario, ())
    # stack rows: (idx, selected_indices, admissible_upper_bound)
    root = _upper_bound(scenario, candidates, 0, ())
    stack: list[tuple[int, tuple[int, ...], int]] = []
    if root is not None:
        stack.append((0, (), root[0]))

    visited = 0
    pruned = 0
    while stack and visited < scenario.limits.node_budget:
        idx, selected, node_ub = stack.pop()
        visited += 1
        if node_ub < best_eval.net_minor:
            pruned += 1
            continue

        bound = _upper_bound(scenario, candidates, idx, selected)
        if bound is None:
            pruned += 1
            continue
        node_ub, current_eval = bound

        current_ids = tuple(
            sorted(candidates[i].operation_id for i in selected)
        )
        best_ids = tuple(
            sorted(candidates[i].operation_id for i in best_selected)
        )
        if (
            current_eval.net_minor > best_eval.net_minor
            or (
                current_eval.net_minor == best_eval.net_minor
                and current_ids < best_ids
            )
        ):
            best_eval = current_eval
            best_selected = selected

        if idx >= len(candidates):
            continue

        # Exclude child.
        exclude_bound = _upper_bound(
            scenario, candidates, idx + 1, selected
        )
        exclude_row = None
        if exclude_bound is not None and exclude_bound[0] >= best_eval.net_minor:
            exclude_row = (idx + 1, selected, exclude_bound[0])
        else:
            pruned += 1

        # Include child. Adding jobs cannot repair an infeasible prefix because
        # all costs/times are nonnegative and EDD completion times only grow.
        included = tuple(sorted((*selected, idx)))
        include_bound = _upper_bound(
            scenario, candidates, idx + 1, included
        )
        include_row = None
        if include_bound is not None and include_bound[0] >= best_eval.net_minor:
            include_row = (idx + 1, included, include_bound[0])
        else:
            pruned += 1

        # Push exclude first so include/value-seeking path is visited next.
        if exclude_row is not None:
            stack.append(exclude_row)
        if include_row is not None:
            stack.append(include_row)

    complete = not stack
    if complete:
        upper = best_eval.net_minor
        proof = "OPTIMAL"
    else:
        upper = max(
            [best_eval.net_minor, *(row[2] for row in stack)]
        )
        proof = "BOUNDED_SEARCH_INCOMPLETE"

    selected_jobs = tuple(candidates[i] for i in best_selected)
    selected_ids = tuple(sorted(job.operation_id for job in selected_jobs))
    meets_minimum = (
        bool(selected_ids)
        and best_eval.net_minor
        >= scenario.limits.minimum_batch_net_minor
    )
    decision = "SELECT_BATCH" if meets_minimum else "NO_BATCH_MEETS_MINIMUM"

    excluded: list[dict[str, str]] = []
    selected_set = set(selected_ids)
    for job in sorted(scenario.jobs, key=lambda j: j.operation_id):
        if job.operation_id in selected_set:
            continue
        reason = _eligibility_reason(job)
        if reason is None:
            reason = "NOT_IN_OPTIMAL_INCUMBENT"
        excluded.append(
            {"operation_id": job.operation_id, "reason": reason}
        )

    result = {
        "schema": RESULT_SCHEMA,
        "scenario_sha256": scenario.source_digest,
        "decision": decision,
        "search": {
            "proof": proof,
            "node_budget": scenario.limits.node_budget,
            "nodes_visited": visited,
            "nodes_pruned": pruned,
            "incumbent_net_minor": best_eval.net_minor,
            "upper_bound_net_minor": upper,
            "optimality_gap_minor": upper - best_eval.net_minor,
        },
        "batch": {
            "selected_operation_ids": list(selected_ids),
            "expected_collection_minor": best_eval.expected_collection_minor,
            "cash_cost_minor": best_eval.cash_cost_minor,
            "effort_cost_minor": best_eval.effort_cost_minor,
            "effort_minutes": best_eval.effort_minutes,
            "completion_minutes": best_eval.completion_minutes,
            "net_minor": best_eval.net_minor,
            "minimum_batch_net_minor": scenario.limits.minimum_batch_net_minor,
            "schedule": list(best_eval.schedule),
        },
        "excluded": excluded,
        "authority": {
            "scenario_values_authenticated": False,
            "task_ownership_authorized": False,
            "external_send_authorized": False,
            "spend_authorized": False,
            "collection_guaranteed": False,
            "payment_received": False,
            "revenue_recognized": False,
        },
    }
    result["result_sha256"] = digest_json(result)
    return result


def verify_result(raw_scenario: dict[str, Any], result: dict[str, Any]) -> bool:
    try:
        expected = optimize(parse_scenario(raw_scenario))
        return canonical_json(expected) == canonical_json(result)
    except (ScenarioError, TypeError, ValueError):
        return False


def render_schedule(result: dict[str, Any]) -> str:
    search = result["search"]
    batch = result["batch"]
    lines = [
        f"decision: {result['decision']}",
        (
            "search: "
            f"{search['proof']} "
            f"incumbent={search['incumbent_net_minor']} "
            f"upper={search['upper_bound_net_minor']} "
            f"gap={search['optimality_gap_minor']}"
        ),
        (
            "batch: "
            f"net={batch['net_minor']} "
            f"expected_collection={batch['expected_collection_minor']} "
            f"cash={batch['cash_cost_minor']} "
            f"effort_cost={batch['effort_cost_minor']} "
            f"minutes={batch['completion_minutes']}"
        ),
    ]
    for row in batch["schedule"]:
        if row["kind"] == "SETUP":
            lines.append(
                f"  {row['start_minute']:>4}-{row['end_minute']:<4} "
                f"SETUP {row['family_id']}"
            )
        else:
            lines.append(
                f"  {row['start_minute']:>4}-{row['end_minute']:<4} "
                f"JOB {row['operation_id']} "
                f"(deadline {row['deadline_minute']})"
            )
    if not batch["schedule"]:
        lines.append("  (empty)")
    return "\n".join(lines) + "\n"
