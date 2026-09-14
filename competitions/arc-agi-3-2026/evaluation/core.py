"""Dependency-free paired-ablation statistics and canonical evidence receipts.

This module does not know game semantics.  It compiles already-observed paired trials into
an auditable report, keeping mock/public-development/public-validation evidence distinct.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from random import Random
from typing import Iterable, Mapping, Sequence

EVIDENCE_CLASSES = frozenset({"mock", "public-development", "public-validation"})
HYPOTHESES = frozenset({"H1", "H2", "H3", "H4"})


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _finite(value: object, name: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be an exact int/float")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


@dataclass(frozen=True)
class ExperimentSpec:
    hypothesis: str
    name: str
    baseline: str
    candidate: str
    primary_metric: str
    higher_is_better: bool
    evidence_class: str
    action_budget: int
    source_revision: str
    config: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.hypothesis not in HYPOTHESES:
            raise ValueError("hypothesis must be H1..H4")
        for field in (self.name, self.baseline, self.candidate, self.primary_metric, self.source_revision):
            if not field or not isinstance(field, str):
                raise ValueError("text fields must be non-empty strings")
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError("invalid evidence_class")
        if type(self.action_budget) is not int or not 1 <= self.action_budget <= 1_000_000:
            raise ValueError("action_budget must be an exact int in [1,1000000]")
        canonical_json(dict(self.config))


@dataclass(frozen=True)
class TrialPair:
    seed: int
    baseline_metrics: Mapping[str, float | int]
    candidate_metrics: Mapping[str, float | int]
    observation_digest: str

    def __post_init__(self) -> None:
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a non-negative exact int")
        if not self.observation_digest or not isinstance(self.observation_digest, str):
            raise ValueError("observation_digest required")
        if set(self.baseline_metrics) != set(self.candidate_metrics):
            raise ValueError("paired metrics must have identical keys")
        if not self.baseline_metrics:
            raise ValueError("at least one metric required")
        for key in sorted(self.baseline_metrics):
            if not key or not isinstance(key, str):
                raise ValueError("metric names must be non-empty strings")
            _finite(self.baseline_metrics[key], f"baseline.{key}")
            _finite(self.candidate_metrics[key], f"candidate.{key}")


def _normalized_delta(spec: ExperimentSpec, pair: TrialPair) -> float:
    base = _finite(pair.baseline_metrics[spec.primary_metric], "baseline primary")
    cand = _finite(pair.candidate_metrics[spec.primary_metric], "candidate primary")
    return cand - base if spec.higher_is_better else base - cand


def _bootstrap_mean_ci(deltas: Sequence[float], *, seed: int, draws: int = 2000) -> tuple[float, float]:
    if not deltas:
        raise ValueError("cannot bootstrap zero trials")
    if len(deltas) == 1:
        return deltas[0], deltas[0]
    rng = Random(seed)
    n = len(deltas)
    means = []
    for _ in range(draws):
        means.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int(0.025 * (draws - 1))]
    hi = means[int(0.975 * (draws - 1))]
    return lo, hi


def _two_sided_sign_flip_p(deltas: Sequence[float], *, seed: int, max_draws: int = 32768) -> float:
    nonzero = [d for d in deltas if d != 0.0]
    if not nonzero:
        return 1.0
    observed = abs(sum(nonzero) / len(nonzero))
    n = len(nonzero)
    if n <= 15:
        extreme = 0
        total = 1 << n
        for mask in range(total):
            value = sum(d if (mask >> i) & 1 else -d for i, d in enumerate(nonzero)) / n
            extreme += abs(value) >= observed - 1e-15
        return extreme / total
    rng = Random(seed)
    extreme = 0
    for _ in range(max_draws):
        value = sum(d if rng.getrandbits(1) else -d for d in nonzero) / n
        extreme += abs(value) >= observed - 1e-15
    return (extreme + 1) / (max_draws + 1)


def compile_report(spec: ExperimentSpec, pairs: Iterable[TrialPair]) -> dict[str, object]:
    rows = sorted(tuple(pairs), key=lambda row: row.seed)
    if not rows:
        raise ValueError("at least one trial pair required")
    if len({row.seed for row in rows}) != len(rows):
        raise ValueError("duplicate trial seed")
    if any(spec.primary_metric not in row.baseline_metrics for row in rows):
        raise ValueError("primary metric missing from a trial")
    deltas = tuple(_normalized_delta(spec, row) for row in rows)
    spec_obj = asdict(spec)
    seed_material = int(digest(spec_obj)[:16], 16)
    lo, hi = _bootstrap_mean_ci(deltas, seed=seed_material)
    p_value = _two_sided_sign_flip_p(deltas, seed=seed_material ^ 0xA5A5A5A5)
    mean_delta = sum(deltas) / len(deltas)
    body: dict[str, object] = {
        "schema": "arc3-sage-ablation-report/v1",
        "spec": spec_obj,
        "spec_sha256": digest(spec_obj),
        "trials": [asdict(row) for row in rows],
        "trial_count": len(rows),
        "normalized_primary_deltas": list(deltas),
        "mean_normalized_delta": mean_delta,
        "bootstrap_95pct": [lo, hi],
        "paired_sign_flip_p": p_value,
        "candidate_wins": sum(d > 0 for d in deltas),
        "ties": sum(d == 0 for d in deltas),
        "baseline_wins": sum(d < 0 for d in deltas),
        "claim_ceiling": (
            "MOCK_EVIDENCE_ONLY" if spec.evidence_class == "mock" else
            "PUBLIC_DEVELOPMENT_NOT_LEADERBOARD" if spec.evidence_class == "public-development" else
            "PUBLIC_VALIDATION_NOT_PROVIDER_SCORE"
        ),
    }
    body["report_sha256"] = digest(body)
    return body


def verify_report(report: Mapping[str, object]) -> bool:
    try:
        if report.get("schema") != "arc3-sage-ablation-report/v1":
            return False
        supplied = report.get("report_sha256")
        if not isinstance(supplied, str):
            return False
        body = dict(report)
        del body["report_sha256"]
        if digest(body) != supplied:
            return False
        spec_obj = body["spec"]
        if not isinstance(spec_obj, dict) or digest(spec_obj) != body["spec_sha256"]:
            return False
        ExperimentSpec(**spec_obj)
        trials = body["trials"]
        if not isinstance(trials, list) or not trials:
            return False
        for row in trials:
            if not isinstance(row, dict):
                return False
            TrialPair(**row)
        return True
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
