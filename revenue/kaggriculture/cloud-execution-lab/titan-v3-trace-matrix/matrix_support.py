#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compile a deterministic constrained t-wise experiment matrix for TITAN V3.

The compiler starts from the current configuration, enumerates only configurations
that satisfy explicit runtime constraints, and greedily selects a compact matrix
covering every reachable 1..t-way feature interaction.  It never edits runtime
source, executes games, or treats coverage as score evidence.

Exit codes:
    0  complete reachable interaction coverage (COMPLETE)
    2  invalid spec/base input (INVALID)
    3  valid inputs but budget cannot cover all reachable interactions (BLOCKED)
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import stat
import tempfile
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 4 * 1024 * 1024


class MatrixError(ValueError):
    """Raised for malformed or internally inconsistent matrix contracts."""


def _reject_constant(value: str) -> None:
    raise MatrixError(f"non-finite JSON constant is forbidden: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MatrixError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_loads(text: str, label: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except MatrixError:
        raise
    except json.JSONDecodeError as exc:
        raise MatrixError(f"{label}: invalid JSON: {exc}") from exc


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MatrixError(f"value is not finite canonical JSON: {exc}") from exc


def _canonical_text(value: Any) -> str:
    return _canonical_bytes(value).decode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _as_int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if not _is_int(value):
        raise MatrixError(f"{label} must be an integer (boolean is not accepted)")
    if minimum is not None and value < minimum:
        raise MatrixError(f"{label} must be >= {minimum}")
    return value


def _as_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MatrixError(f"{label} must be a nonempty string")
    return value.strip()


def _read_regular_json(path: Path, label: str) -> tuple[Any, bytes]:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise MatrixError(f"{label}: missing file: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise MatrixError(f"{label}: symlink inputs are forbidden: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise MatrixError(f"{label}: input must be a regular file: {path}")
    if metadata.st_size > MAX_INPUT_BYTES:
        raise MatrixError(f"{label}: input exceeds {MAX_INPUT_BYTES} bytes")
    data = path.read_bytes()
    if len(data) != metadata.st_size:
        raise MatrixError(f"{label}: file changed while being read")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MatrixError(f"{label}: input is not UTF-8: {exc}") from exc
    return _strict_loads(text, label), data


def _primitive(value: Any, label: str) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if _is_int(value):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MatrixError(f"{label} must be finite")
        return value
    raise MatrixError(f"{label} must be a JSON scalar")


def _value_key(value: Any) -> str:
    # Canonical JSON text keeps booleans distinct from integers (true != 1).
    return _canonical_text(value)


def _mapping_matches(config: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(
        key in config and _value_key(config[key]) == _value_key(value)
        for key, value in expected.items()
    )


def _validate_assignment(
    value: Any,
    *,
    label: str,
    known_keys: set[str],
    domains: Mapping[str, tuple[Any, ...]] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MatrixError(f"{label} must be an object")
    result: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = _as_nonempty_string(raw_key, f"{label} key")
        if key not in known_keys:
            raise MatrixError(f"{label}: unknown configuration key {key!r}")
        item = _primitive(raw_value, f"{label}.{key}")
        if domains is not None and key in domains:
            legal = {_value_key(candidate) for candidate in domains[key]}
            if _value_key(item) not in legal:
                raise MatrixError(
                    f"{label}.{key}={item!r} is outside declared factor domain"
                )
        result[key] = item
    return result


@dataclass(frozen=True)
class Constraint:
    name: str
    kind: str
    condition: Mapping[str, Any]
    consequence: Mapping[str, Any]

    def allows(self, config: Mapping[str, Any]) -> bool:
        if self.kind == "forbid":
            return not _mapping_matches(config, self.condition)
        return not _mapping_matches(config, self.condition) or _mapping_matches(
            config, self.consequence
        )

    def explain_failure(self, config: Mapping[str, Any]) -> str | None:
        if self.allows(config):
            return None
        if self.kind == "forbid":
            return f"{self.name}: forbidden assignment matched"
        return f"{self.name}: antecedent matched but consequence did not"


Interaction = tuple[tuple[str, str], ...]


def _interaction_keys(
    projection: Mapping[str, Any], factor_names: Sequence[str], strength: int
) -> set[Interaction]:
    result: set[Interaction] = set()
    upper = min(strength, len(factor_names))
    for size in range(1, upper + 1):
        for names in itertools.combinations(factor_names, size):
            result.add(tuple((name, _value_key(projection[name])) for name in names))
    return result


def _interaction_json(interaction: Interaction) -> dict[str, Any]:
    return {name: _strict_loads(encoded, f"interaction.{name}") for name, encoded in interaction}


def _distance(left: Mapping[str, Any], right: Mapping[str, Any], names: Sequence[str]) -> int:
    return sum(_value_key(left[name]) != _value_key(right[name]) for name in names)


def _project(config: Mapping[str, Any], names: Sequence[str]) -> dict[str, Any]:
    return {name: config[name] for name in names}


def _compile_constraints(
    raw_constraints: Any,
    *,
    known_keys: set[str],
    domains: Mapping[str, tuple[Any, ...]],
) -> tuple[Constraint, ...]:
    if raw_constraints is None:
        return ()
    if not isinstance(raw_constraints, list):
        raise MatrixError("spec.constraints must be a list")
    result: list[Constraint] = []
    names: set[str] = set()
    for index, raw in enumerate(raw_constraints):
        label = f"spec.constraints[{index}]"
        if not isinstance(raw, Mapping):
            raise MatrixError(f"{label} must be an object")
        name = _as_nonempty_string(raw.get("name"), f"{label}.name")
        if name in names:
            raise MatrixError(f"duplicate constraint name: {name}")
        names.add(name)
        if "forbid" in raw:
            if "if" in raw or "then" in raw:
                raise MatrixError(f"{label} cannot combine forbid with if/then")
            condition = _validate_assignment(
                raw["forbid"],
                label=f"{label}.forbid",
                known_keys=known_keys,
                domains=domains,
            )
            if not condition:
                raise MatrixError(f"{label}.forbid cannot be empty")
            result.append(Constraint(name, "forbid", condition, {}))
            continue
        if "if" not in raw or "then" not in raw:
            raise MatrixError(f"{label} must contain either forbid or both if and then")
        condition = _validate_assignment(
            raw["if"],
            label=f"{label}.if",
            known_keys=known_keys,
            domains=domains,
        )
        consequence = _validate_assignment(
            raw["then"],
            label=f"{label}.then",
            known_keys=known_keys,
            domains=domains,
        )
        if not condition or not consequence:
            raise MatrixError(f"{label}.if and .then cannot be empty")
        result.append(Constraint(name, "implication", condition, consequence))
    return tuple(result)


def _config_id(projection: Mapping[str, Any]) -> str:
    return "cfg-" + _sha256(_canonical_bytes(projection))[:16]


def _reason_map_append(reasons: dict[str, list[str]], key: str, reason: str) -> None:
    bucket = reasons.setdefault(key, [])
    if reason not in bucket:
        bucket.append(reason)

