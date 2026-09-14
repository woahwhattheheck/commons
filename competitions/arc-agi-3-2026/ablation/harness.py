"""Deterministic paired-ablation ledger for ARC-AGI-3 SAGE experiments.

This module is intentionally environment-agnostic.  Runners emit TrialRecord rows;
this layer enforces a complete paired design, computes bounded descriptive deltas, and
hash-binds the exact plan + rows into a replayable receipt.  It never upgrades mock or
public-development evidence into an official competition-score claim.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from statistics import mean, median
from typing import Iterable, Mapping, Sequence

_ALLOWED_EVIDENCE = {"mock", "public_development", "public_validation", "provider_verified"}


@dataclass(frozen=True)
class Variant:
    name: str
    full_animation: bool = True
    action_policy: str = "information_gain"
    coordinate_mode: str = "reduced"
    preserve_knowledge: bool = True

    def __post_init__(self) -> None:
        if not self.name or any(ch.isspace() for ch in self.name):
            raise ValueError("variant name must be a non-empty token")
        if self.action_policy not in {"information_gain", "uniform_random"}:
            raise ValueError("unsupported action_policy")
        if self.coordinate_mode not in {"reduced", "all_grid"}:
            raise ValueError("unsupported coordinate_mode")


BASELINE = Variant("sage_full")
DEFAULT_VARIANTS = (
    BASELINE,
    Variant("settled_frame", full_animation=False),
    Variant("uniform_random", action_policy="uniform_random"),
    Variant("all_grid_coordinates", coordinate_mode="all_grid"),
    Variant("reset_between_levels", preserve_knowledge=False),
)


@dataclass(frozen=True)
class ExperimentPlan:
    experiment_id: str
    variants: tuple[Variant, ...]
    seeds: tuple[int, ...]
    levels: tuple[int, ...]
    max_actions: int
    evidence_kind: str = "mock"
    source_revision: str = "unknown"

    def __post_init__(self) -> None:
        if not self.experiment_id:
            raise ValueError("experiment_id is required")
        if not self.variants or self.variants[0] != BASELINE:
            raise ValueError("baseline must be first")
        if len({v.name for v in self.variants}) != len(self.variants):
            raise ValueError("variant names must be unique")
        baseline = self.variants[0]
        for variant in self.variants[1:]:
            changed = sum(
                getattr(variant, field) != getattr(baseline, field)
                for field in ("full_animation", "action_policy", "coordinate_mode", "preserve_knowledge")
            )
            if changed != 1:
                raise ValueError(f"variant {variant.name} must change exactly one baseline factor")
        if not self.seeds or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("seeds must be non-empty and unique")
        if any(type(seed) is not int or seed < 0 for seed in self.seeds):
            raise ValueError("seeds must be non-negative exact ints")
        if not self.levels or self.levels != tuple(sorted(set(self.levels))):
            raise ValueError("levels must be sorted, non-empty, and unique")
        if self.levels[0] != 0:
            raise ValueError("levels must start at 0")
        if type(self.max_actions) is not int or not 1 <= self.max_actions <= 10_000:
            raise ValueError("max_actions must be an exact int in 1..10000")
        if self.evidence_kind not in _ALLOWED_EVIDENCE:
            raise ValueError("unsupported evidence_kind")
        if not self.source_revision:
            raise ValueError("source_revision is required")

    @property
    def keys(self) -> tuple[tuple[int, int], ...]:
        return tuple((seed, level) for seed in self.seeds for level in self.levels)


@dataclass(frozen=True)
class TrialRecord:
    variant: str
    seed: int
    level: int
    won: bool
    actions: int
    no_effect_actions: int
    first_progress_action: int | None
    animation_frames_observed: int
    coordinate_candidates_considered: int
    coordinate_actions_taken: int
    skill_replays: int
    learned_skills: int

    def __post_init__(self) -> None:
        if not self.variant:
            raise ValueError("variant is required")
        if type(self.seed) is not int or self.seed < 0 or type(self.level) is not int or self.level < 0:
            raise ValueError("seed/level must be non-negative exact ints")
        ints = (
            self.actions,
            self.no_effect_actions,
            self.animation_frames_observed,
            self.coordinate_candidates_considered,
            self.coordinate_actions_taken,
            self.skill_replays,
            self.learned_skills,
        )
        if any(type(value) is not int or value < 0 for value in ints):
            raise ValueError("trial counters must be non-negative exact ints")
        if self.no_effect_actions > self.actions or self.coordinate_actions_taken > self.actions or self.skill_replays > self.actions:
            raise ValueError("sub-counters cannot exceed actions")
        if self.first_progress_action is not None and (
            type(self.first_progress_action) is not int or not 1 <= self.first_progress_action <= self.actions
        ):
            raise ValueError("first_progress_action must index an executed action")


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _plan_payload(plan: ExperimentPlan) -> dict[str, object]:
    return {
        "experiment_id": plan.experiment_id,
        "variants": [asdict(v) for v in plan.variants],
        "seeds": list(plan.seeds),
        "levels": list(plan.levels),
        "max_actions": plan.max_actions,
        "evidence_kind": plan.evidence_kind,
        "source_revision": plan.source_revision,
    }


def validate_records(plan: ExperimentPlan, records: Sequence[TrialRecord]) -> tuple[TrialRecord, ...]:
    expected_variants = {v.name for v in plan.variants}
    expected_keys = set(plan.keys)
    seen: set[tuple[str, int, int]] = set()
    by_variant: dict[str, set[tuple[int, int]]] = {name: set() for name in expected_variants}
    out: list[TrialRecord] = []
    for record in records:
        if record.variant not in expected_variants:
            raise ValueError(f"unexpected variant {record.variant}")
        key = (record.variant, record.seed, record.level)
        if key in seen:
            raise ValueError(f"duplicate trial {key}")
        seen.add(key)
        pair_key = (record.seed, record.level)
        if pair_key not in expected_keys:
            raise ValueError(f"trial outside plan {pair_key}")
        by_variant[record.variant].add(pair_key)
        out.append(record)
    for name, keys in sorted(by_variant.items()):
        missing = expected_keys - keys
        extra = keys - expected_keys
        if missing or extra:
            raise ValueError(f"incomplete paired design for {name}: missing={sorted(missing)} extra={sorted(extra)}")
    expected_count = len(plan.variants) * len(expected_keys)
    if len(out) != expected_count:
        raise ValueError(f"expected {expected_count} trials, got {len(out)}")
    return tuple(sorted(out, key=lambda r: (r.variant, r.seed, r.level)))


def _aggregate(rows: Sequence[TrialRecord]) -> dict[str, object]:
    if not rows:
        raise ValueError("rows required")
    wins = [row for row in rows if row.won]
    first = [row.first_progress_action for row in rows if row.first_progress_action is not None]
    total_actions = sum(row.actions for row in rows)
    return {
        "trials": len(rows),
        "wins": len(wins),
        "win_rate": len(wins) / len(rows),
        "mean_actions_all": mean(row.actions for row in rows),
        "mean_actions_wins": mean(row.actions for row in wins) if wins else None,
        "median_actions_wins": median(row.actions for row in wins) if wins else None,
        "no_effect_rate": sum(row.no_effect_actions for row in rows) / total_actions if total_actions else 0.0,
        "mean_first_progress_action": mean(first) if first else None,
        "animation_frames_observed": sum(row.animation_frames_observed for row in rows),
        "coordinate_candidates_considered": sum(row.coordinate_candidates_considered for row in rows),
        "coordinate_actions_taken": sum(row.coordinate_actions_taken for row in rows),
        "skill_replays": sum(row.skill_replays for row in rows),
        "learned_skills_max": max(row.learned_skills for row in rows),
    }


def _paired_delta(baseline: Mapping[tuple[int, int], TrialRecord], candidate: Mapping[tuple[int, int], TrialRecord]) -> dict[str, object]:
    keys = sorted(baseline)
    both_win_action_delta = [candidate[key].actions - baseline[key].actions for key in keys if candidate[key].won and baseline[key].won]
    baseline_only = sum(baseline[key].won and not candidate[key].won for key in keys)
    candidate_only = sum(candidate[key].won and not baseline[key].won for key in keys)
    return {
        "baseline_only_wins": baseline_only,
        "candidate_only_wins": candidate_only,
        "paired_win_delta": candidate_only - baseline_only,
        "both_win_pairs": len(both_win_action_delta),
        "candidate_minus_baseline_mean_actions_both_win": mean(both_win_action_delta) if both_win_action_delta else None,
        "candidate_minus_baseline_median_actions_both_win": median(both_win_action_delta) if both_win_action_delta else None,
    }


def compile_report(plan: ExperimentPlan, records: Sequence[TrialRecord]) -> dict[str, object]:
    rows = validate_records(plan, records)
    groups = {variant.name: [r for r in rows if r.variant == variant.name] for variant in plan.variants}
    baseline = {(r.seed, r.level): r for r in groups[BASELINE.name]}
    aggregates = {name: _aggregate(group) for name, group in groups.items()}
    paired = {
        variant.name: _paired_delta(baseline, {(r.seed, r.level): r for r in groups[variant.name]})
        for variant in plan.variants[1:]
    }
    payload = {
        "schema": "arc3-sage-ablation-v1",
        "plan": _plan_payload(plan),
        "aggregates": aggregates,
        "paired_against_baseline": paired,
        "records": [asdict(r) for r in rows],
        "authority": {
            "evidence_kind": plan.evidence_kind,
            "competition_score_authorized": plan.evidence_kind == "provider_verified",
            "note": "Mock/public-development results are comparative evidence only; they are not official ARC/Kaggle scores.",
        },
    }
    receipt = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return {**payload, "receipt_sha256": receipt}


def verify_report(report: Mapping[str, object]) -> bool:
    try:
        receipt = report["receipt_sha256"]
        if not isinstance(receipt, str) or len(receipt) != 64:
            return False
        payload = {key: value for key, value in report.items() if key != "receipt_sha256"}
        expected = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        return expected == receipt
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def rows_from_dicts(rows: Iterable[Mapping[str, object]]) -> tuple[TrialRecord, ...]:
    allowed = set(TrialRecord.__dataclass_fields__)
    out: list[TrialRecord] = []
    for raw in rows:
        if set(raw) != allowed:
            raise ValueError("trial row schema mismatch")
        out.append(TrialRecord(**raw))  # type: ignore[arg-type]
    return tuple(out)
