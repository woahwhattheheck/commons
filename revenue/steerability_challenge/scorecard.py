"""Public, data-free scorecard for the 2026 Steerability Challenge.

This module does not reproduce the organizers' private evaluator.  It consumes
*normalized local evaluation outputs* and gives a deterministic way to compare
one shared pipeline recipe across the three announced competition models.

Positive deltas always mean "better".  Target metrics reward improvement over
the unsteered baseline.  Side-effect metrics charge regressions only, matching
the public competition description at a high level.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any, Iterable, Mapping, Sequence

COMPETITION_MODELS: tuple[str, ...] = (
    "google/gemma-4-31B-it",
    "ibm-granite/granite-4.2-30b",
    "Qwen/Qwen3.8-27B",
)
KINDS = frozenset({"target", "side_effect"})


class ScorecardError(ValueError):
    """Raised when local evaluation evidence violates the scorecard contract."""


def _finite(value: Any, *, field: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ScorecardError(f"{field} must be numeric: {value!r}") from exc
    if not math.isfinite(out):
        raise ScorecardError(f"{field} must be finite: {value!r}")
    return out


@dataclass(frozen=True)
class EvaluationPoint:
    recipe_id: str
    model: str
    seed: int
    metric: str
    kind: str
    baseline: float
    candidate: float
    higher_is_better: bool = True
    weight: float = 1.0

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "EvaluationPoint":
        recipe_id = str(raw.get("recipe_id", "")).strip()
        model = str(raw.get("model", "")).strip()
        metric = str(raw.get("metric", "")).strip()
        kind = str(raw.get("kind", "")).strip()
        if not recipe_id:
            raise ScorecardError("recipe_id is required")
        if model not in COMPETITION_MODELS:
            raise ScorecardError(f"unsupported competition model: {model!r}")
        if not metric:
            raise ScorecardError("metric is required")
        if kind not in KINDS:
            raise ScorecardError(f"kind must be one of {sorted(KINDS)}")
        try:
            seed = int(raw.get("seed"))
        except (TypeError, ValueError) as exc:
            raise ScorecardError(f"seed must be an integer: {raw.get('seed')!r}") from exc
        weight = _finite(raw.get("weight", 1.0), field="weight")
        if weight <= 0:
            raise ScorecardError("weight must be > 0")
        hib = raw.get("higher_is_better", True)
        if not isinstance(hib, bool):
            raise ScorecardError("higher_is_better must be boolean")
        return cls(
            recipe_id=recipe_id,
            model=model,
            seed=seed,
            metric=metric,
            kind=kind,
            baseline=_finite(raw.get("baseline"), field="baseline"),
            candidate=_finite(raw.get("candidate"), field="candidate"),
            higher_is_better=hib,
            weight=weight,
        )

    @property
    def oriented_delta(self) -> float:
        raw = self.candidate - self.baseline
        return raw if self.higher_is_better else -raw


def load_jsonl(path: str | Path) -> list[EvaluationPoint]:
    points: list[EvaluationPoint] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ScorecardError(f"{path}:{line_no}: invalid JSON") from exc
        if not isinstance(raw, dict):
            raise ScorecardError(f"{path}:{line_no}: expected JSON object")
        try:
            points.append(EvaluationPoint.from_mapping(raw))
        except ScorecardError as exc:
            raise ScorecardError(f"{path}:{line_no}: {exc}") from exc
    if not points:
        raise ScorecardError("evaluation file is empty")
    return points


def _weighted_mean(values: Iterable[tuple[float, float]]) -> float:
    values = list(values)
    total_weight = sum(weight for _, weight in values)
    if not values or total_weight <= 0:
        raise ScorecardError("cannot average an empty metric group")
    return sum(value * weight for value, weight in values) / total_weight


def _dedupe(points: Sequence[EvaluationPoint]) -> None:
    seen: set[tuple[str, str, int, str, str]] = set()
    for point in points:
        key = (point.recipe_id, point.model, point.seed, point.metric, point.kind)
        if key in seen:
            raise ScorecardError(f"duplicate evaluation point: {key!r}")
        seen.add(key)


def _metric_signature(points: Sequence[EvaluationPoint], recipe_id: str) -> dict[tuple[str, int], set[tuple[str, str]]]:
    signature: dict[tuple[str, int], set[tuple[str, str]]] = defaultdict(set)
    for point in points:
        if point.recipe_id == recipe_id:
            signature[(point.model, point.seed)].add((point.kind, point.metric))
    return signature


def _validate_complete_recipe(points: Sequence[EvaluationPoint], recipe_id: str) -> None:
    subset = [point for point in points if point.recipe_id == recipe_id]
    models = {point.model for point in subset}
    if models != set(COMPETITION_MODELS):
        missing = sorted(set(COMPETITION_MODELS) - models)
        extra = sorted(models - set(COMPETITION_MODELS))
        raise ScorecardError(f"{recipe_id}: model coverage mismatch missing={missing} extra={extra}")

    signatures = _metric_signature(points, recipe_id)
    by_model_seeds: dict[str, set[int]] = defaultdict(set)
    for model, seed in signatures:
        by_model_seeds[model].add(seed)
    seed_sets = list(by_model_seeds.values())
    if not seed_sets or any(seeds != seed_sets[0] for seeds in seed_sets[1:]):
        raise ScorecardError(f"{recipe_id}: every competition model must use the same seed set")

    expected: set[tuple[str, str]] | None = None
    for key in sorted(signatures):
        sig = signatures[key]
        if not any(kind == "target" for kind, _ in sig):
            raise ScorecardError(f"{recipe_id}: {key} has no target metric")
        if not any(kind == "side_effect" for kind, _ in sig):
            raise ScorecardError(f"{recipe_id}: {key} has no side-effect metric")
        if expected is None:
            expected = set(sig)
        elif sig != expected:
            raise ScorecardError(
                f"{recipe_id}: metric coverage differs for {key}; expected={sorted(expected)} got={sorted(sig)}"
            )


def score_recipe(
    points: Sequence[EvaluationPoint],
    recipe_id: str,
    *,
    model_spread_penalty: float = 0.25,
    run_instability_penalty: float = 0.10,
) -> dict[str, Any]:
    """Score one recipe using organizer-shaped but explicitly non-authoritative math."""
    _dedupe(points)
    _validate_complete_recipe(points, recipe_id)
    if model_spread_penalty < 0 or run_instability_penalty < 0:
        raise ScorecardError("penalties must be non-negative")

    grouped: dict[tuple[str, int], list[EvaluationPoint]] = defaultdict(list)
    for point in points:
        if point.recipe_id == recipe_id:
            grouped[(point.model, point.seed)].append(point)

    runs: list[dict[str, Any]] = []
    for (model, seed), run_points in sorted(grouped.items()):
        target = _weighted_mean(
            (point.oriented_delta, point.weight)
            for point in run_points
            if point.kind == "target"
        )
        regression = _weighted_mean(
            (max(0.0, -point.oriented_delta), point.weight)
            for point in run_points
            if point.kind == "side_effect"
        )
        runs.append(
            {
                "model": model,
                "seed": seed,
                "target_improvement": target,
                "side_effect_regression": regression,
                "composite_proxy": target - regression,
            }
        )

    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        by_model[str(run["model"])].append(run)
    model_rows: list[dict[str, Any]] = []
    for model in COMPETITION_MODELS:
        model_runs = by_model[model]
        model_rows.append(
            {
                "model": model,
                "seeds": len(model_runs),
                "target_improvement": fmean(float(r["target_improvement"]) for r in model_runs),
                "side_effect_regression": fmean(float(r["side_effect_regression"]) for r in model_runs),
                "composite_proxy": fmean(float(r["composite_proxy"]) for r in model_runs),
            }
        )

    model_scores = [float(row["composite_proxy"]) for row in model_rows]
    run_scores = [float(row["composite_proxy"]) for row in runs]
    mean_target = fmean(float(row["target_improvement"]) for row in model_rows)
    mean_regression = fmean(float(row["side_effect_regression"]) for row in model_rows)
    mean_composite = fmean(model_scores)
    model_spread = pstdev(model_scores) if len(model_scores) > 1 else 0.0
    run_instability = pstdev(run_scores) if len(run_scores) > 1 else 0.0
    selection_score = (
        mean_composite
        - model_spread_penalty * model_spread
        - run_instability_penalty * run_instability
    )
    return {
        "recipe_id": recipe_id,
        "models": model_rows,
        "runs": runs,
        "mean_target_improvement": mean_target,
        "mean_side_effect_regression": mean_regression,
        "mean_composite_proxy": mean_composite,
        "worst_model_composite_proxy": min(model_scores),
        "model_spread": model_spread,
        "run_instability": run_instability,
        "selection_score": selection_score,
        "penalties": {
            "model_spread": model_spread_penalty,
            "run_instability": run_instability_penalty,
        },
        "authoritative": False,
    }


def _dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    a_target = float(a["mean_target_improvement"])
    b_target = float(b["mean_target_improvement"])
    a_reg = float(a["mean_side_effect_regression"])
    b_reg = float(b["mean_side_effect_regression"])
    return (
        a_target >= b_target
        and a_reg <= b_reg
        and (a_target > b_target or a_reg < b_reg)
    )


def rank_recipes(
    points: Sequence[EvaluationPoint],
    *,
    model_spread_penalty: float = 0.25,
    run_instability_penalty: float = 0.10,
) -> dict[str, Any]:
    recipe_ids = sorted({point.recipe_id for point in points})
    if not recipe_ids:
        raise ScorecardError("no recipes to rank")
    rows = [
        score_recipe(
            points,
            recipe_id,
            model_spread_penalty=model_spread_penalty,
            run_instability_penalty=run_instability_penalty,
        )
        for recipe_id in recipe_ids
    ]
    for row in rows:
        row["pareto"] = not any(
            _dominates(other, row)
            for other in rows
            if other["recipe_id"] != row["recipe_id"]
        )
    rows.sort(
        key=lambda row: (
            float(row["selection_score"]),
            float(row["worst_model_composite_proxy"]),
            float(row["mean_target_improvement"]),
            -float(row["mean_side_effect_regression"]),
            str(row["recipe_id"]),
        ),
        reverse=True,
    )
    return {
        "schema_version": 1,
        "competition_models": list(COMPETITION_MODELS),
        "winner": rows[0]["recipe_id"],
        "recipes": rows,
        "authoritative": False,
        "warning": (
            "Proxy selection over declared local normalized metrics; it is not the "
            "organizers' private competition score."
        ),
    }
