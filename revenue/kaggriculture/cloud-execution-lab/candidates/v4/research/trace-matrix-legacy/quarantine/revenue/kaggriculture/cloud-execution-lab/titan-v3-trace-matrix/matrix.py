#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compile a deterministic constrained t-wise experiment matrix for TITAN V3.

The compiler enumerates runtime-legal configurations and greedily covers every
reachable declared 1..t-way interaction. It does not run games or claim score.

Exit codes: 0 COMPLETE, 2 INVALID, 3 BLOCKED.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

from matrix_support import (
    SCHEMA_VERSION,
    Interaction,
    MatrixError,
    _as_int,
    _as_nonempty_string,
    _canonical_bytes,
    _canonical_text,
    _compile_constraints,
    _config_id,
    _distance,
    _interaction_json,
    _interaction_keys,
    _mapping_matches,
    _primitive,
    _project,
    _read_regular_json,
    _reason_map_append,
    _sha256,
    _value_key,
    _validate_assignment,
)


def compile_matrix(base: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(base, Mapping):
        raise MatrixError("base root must be an object")
    if not isinstance(spec, Mapping):
        raise MatrixError("spec root must be an object")
    schema_version = _as_int(spec.get("schema_version"), "spec.schema_version")
    if schema_version != SCHEMA_VERSION:
        raise MatrixError(
            f"unsupported spec.schema_version {schema_version}; expected {SCHEMA_VERSION}"
        )
    _canonical_bytes(base)
    _canonical_bytes(spec)

    strength = _as_int(spec.get("strength", 2), "spec.strength", minimum=1)
    if strength > 3:
        raise MatrixError("spec.strength > 3 is intentionally unsupported")
    budget = _as_int(spec.get("budget"), "spec.budget", minimum=1)
    max_state_space = _as_int(
        spec.get("max_state_space", 200_000), "spec.max_state_space", minimum=1
    )

    raw_factors = spec.get("factors")
    if not isinstance(raw_factors, Mapping) or not raw_factors:
        raise MatrixError("spec.factors must be a nonempty object")
    domains: dict[str, tuple[Any, ...]] = {}
    for raw_name, raw_values in raw_factors.items():
        name = _as_nonempty_string(raw_name, "spec.factors key")
        if name not in base:
            raise MatrixError(f"factor {name!r} is absent from base configuration")
        if not isinstance(raw_values, list) or not raw_values:
            raise MatrixError(f"spec.factors.{name} must be a nonempty list")
        values: list[Any] = []
        seen: set[str] = set()
        for index, raw_value in enumerate(raw_values):
            value = _primitive(raw_value, f"spec.factors.{name}[{index}]")
            encoded = _value_key(value)
            if encoded in seen:
                raise MatrixError(f"spec.factors.{name} has duplicate value {value!r}")
            seen.add(encoded)
            values.append(value)
        if _value_key(base[name]) not in seen:
            raise MatrixError(f"base value for factor {name!r} is outside its domain")
        domains[name] = tuple(values)
    factor_names = tuple(sorted(domains))
    known_keys = set(base)
    constraints = _compile_constraints(
        spec.get("constraints", []), known_keys=known_keys, domains=domains
    )

    raw_space = math.prod(len(domains[name]) for name in factor_names)
    if raw_space > max_state_space:
        raise MatrixError(
            f"factor state space {raw_space} exceeds max_state_space {max_state_space}"
        )

    legal: list[dict[str, Any]] = []
    rejected_by_primary_constraint: dict[str, int] = {
        constraint.name: 0 for constraint in constraints
    }
    constraint_violation_incidence: dict[str, int] = {
        constraint.name: 0 for constraint in constraints
    }
    for values in itertools.product(*(domains[name] for name in factor_names)):
        projection = dict(zip(factor_names, values))
        config = dict(base)
        config.update(projection)
        failed = [constraint for constraint in constraints if not constraint.allows(config)]
        if failed:
            rejected_by_primary_constraint[failed[0].name] += 1
            for constraint in failed:
                constraint_violation_incidence[constraint.name] += 1
            continue
        legal.append(projection)
    legal.sort(key=_canonical_text)
    if not legal:
        raise MatrixError("constraints reject every factor configuration")

    base_projection = _project(base, factor_names)
    base_key = _canonical_text(base_projection)
    legal_by_key = {_canonical_text(row): row for row in legal}
    if base_key not in legal_by_key:
        failures = [
            constraint.explain_failure(base)
            for constraint in constraints
            if constraint.explain_failure(base) is not None
        ]
        raise MatrixError(f"base configuration violates constraints: {failures}")

    coverage_by_key = {
        _canonical_text(row): _interaction_keys(row, factor_names, strength) for row in legal
    }
    reachable: set[Interaction] = set().union(*coverage_by_key.values())

    selected_keys: list[str] = []
    selected_set: set[str] = set()
    reasons: dict[str, list[str]] = {}

    def select(key: str, reason: str) -> None:
        if key not in selected_set:
            selected_keys.append(key)
            selected_set.add(key)
        _reason_map_append(reasons, key, reason)

    select(base_key, "current-base")

    raw_mandatory = spec.get("mandatory", [])
    if not isinstance(raw_mandatory, list):
        raise MatrixError("spec.mandatory must be a list")
    mandatory_names: set[str] = set()
    for index, raw in enumerate(raw_mandatory):
        label = f"spec.mandatory[{index}]"
        if not isinstance(raw, Mapping):
            raise MatrixError(f"{label} must be an object")
        name = _as_nonempty_string(raw.get("name"), f"{label}.name")
        if name in mandatory_names:
            raise MatrixError(f"duplicate mandatory name: {name}")
        mandatory_names.add(name)
        assignment = _validate_assignment(
            raw.get("assignment"),
            label=f"{label}.assignment",
            known_keys=set(factor_names),
            domains=domains,
        )
        matches = [row for row in legal if _mapping_matches(row, assignment)]
        if not matches:
            raise MatrixError(f"mandatory assignment {name!r} has no legal completion")
        chosen = min(
            matches,
            key=lambda row: (
                _distance(base_projection, row, factor_names),
                _canonical_text(row),
            ),
        )
        select(_canonical_text(chosen), f"mandatory:{name}")

    if len(selected_keys) > budget:
        raise MatrixError(
            f"base plus mandatory rows require {len(selected_keys)} slots, budget is {budget}"
        )

    covered: set[Interaction] = set()
    for key in selected_keys:
        covered.update(coverage_by_key[key])

    while covered != reachable and len(selected_keys) < budget:
        uncovered = reachable - covered
        candidates: list[tuple[int, int, str]] = []
        for key, row in legal_by_key.items():
            if key in selected_set:
                continue
            gain = len(coverage_by_key[key] & uncovered)
            if gain <= 0:
                continue
            candidates.append((-gain, _distance(base_projection, row, factor_names), key))
        if not candidates:
            break
        _, _, chosen_key = min(candidates)
        select(chosen_key, "greedy-new-interactions")
        covered.update(coverage_by_key[chosen_key])

    uncovered = reachable - covered
    verdict = "COMPLETE" if not uncovered else "BLOCKED"
    rows: list[dict[str, Any]] = []
    for ordinal, key in enumerate(selected_keys):
        projection = legal_by_key[key]
        config = dict(base)
        config.update(projection)
        rows.append(
            {
                "ordinal": ordinal,
                "id": _config_id(projection),
                "reasons": reasons[key],
                "distance_from_base": _distance(base_projection, projection, factor_names),
                "factors": projection,
                "config": config,
                "config_sha256": _sha256(_canonical_bytes(config)),
            }
        )

    reachable_count = len(reachable)
    covered_count = len(covered)
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
        "complete": not uncovered,
        "strength": strength,
        "coverage_sizes": list(range(1, min(strength, len(factor_names)) + 1)),
        "budget": budget,
        "factor_names": list(factor_names),
        "factor_domains": {name: list(domains[name]) for name in factor_names},
        "state_space": {
            "cartesian": raw_space,
            "legal": len(legal),
            "rejected": raw_space - len(legal),
            "rejected_by_primary_constraint": rejected_by_primary_constraint,
            "constraint_violation_incidence": constraint_violation_incidence,
        },
        "coverage": {
            "reachable_interactions": reachable_count,
            "covered_interactions": covered_count,
            "uncovered_interactions": len(uncovered),
            "coverage_fraction": covered_count / reachable_count if reachable_count else 1.0,
            "uncovered_examples": [_interaction_json(item) for item in sorted(uncovered)[:50]],
        },
        "matrix_size": len(rows),
        "configurations": rows,
        "boundary": (
            "COMPLETE proves only that every reachable declared 1..t-way factor interaction "
            "appears in at least one legal configuration. It is not game, score, leaderboard, "
            "causality, or promotion evidence. Each row still requires official-engine paired evaluation."
        ),
    }


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def evaluate(base_path: Path, spec_path: Path) -> dict[str, Any]:
    base, base_bytes = _read_regular_json(base_path, "base")
    spec, spec_bytes = _read_regular_json(spec_path, "spec")
    report = compile_matrix(base, spec)
    report["base"] = {"path": str(base_path), "sha256": _sha256(base_bytes)}
    report["spec"] = {"path": str(spec_path), "sha256": _sha256(spec_bytes)}
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.base, args.spec)
    except MatrixError as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "verdict": "INVALID",
            "complete": False,
            "error": str(exc),
        }
        _atomic_json(args.output, report)
        print(json.dumps(report, sort_keys=True))
        return 2
    _atomic_json(args.output, report)
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "matrix_size": report["matrix_size"],
                "legal_state_space": report["state_space"]["legal"],
                "covered_interactions": report["coverage"]["covered_interactions"],
                "reachable_interactions": report["coverage"]["reachable_interactions"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["complete"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
