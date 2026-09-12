#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Promotion-grade custody checks for a future TITAN own-value holdout.

This module deliberately runs no games.  It validates five boundaries that a
future, fresh-seed native paired panel must close before its economics can be
used as an integration input:

* immutable first-attempt seed/run custody;
* dependency-closed executable roots;
* first-divergence action -> world -> terminal causality;
* deterministic replay for every score-active cell; and
* seed-clustered, explicitly tail-bounded economic evidence.

It is not release, merge, provider, Kaggle, submission, or promotion authority.
"""
from __future__ import annotations

import argparse
import copy
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import statistics
import sys
from typing import Any, Mapping, Sequence

LEDGER_SCHEMA = "titan-v3-holdout-seed-ledger/v1"
CLOSURE_SCHEMA = "titan-v3-executable-closure/v1"
TRAJECTORY_SCHEMA = "titan-v3-native-paired-trajectory/v1"
POLICY_SCHEMA = "titan-v3-own-value-promotion-policy/v1"
EXPECTED_STEPS = 719
OUTCOME_RANK = {"loss": 0, "tie": 1, "win": 2}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


class PromotionClosureError(ValueError):
    """Evidence is malformed, detached, confounded, or insufficient."""


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PromotionClosureError(f"value is not canonical strict JSON: {exc}") from exc


def json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def strict_load(path: Path, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise PromotionClosureError(f"{label} has duplicate key {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise PromotionClosureError(f"{label} has non-finite constant {value}")

    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromotionClosureError(f"cannot load {label}: {exc}") from exc


def require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise PromotionClosureError(
            f"{label} keys differ: missing={sorted(expected - actual)!r}, "
            f"unexpected={sorted(actual - expected)!r}"
        )


def nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PromotionClosureError(f"{label} must be a nonempty string")
    return value


def true_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise PromotionClosureError(f"{label} must be an integer >= {minimum}")
    return value


def finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PromotionClosureError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise PromotionClosureError(f"{label} must be finite")
    return result


def sha40(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA40.fullmatch(value) is None:
        raise PromotionClosureError(f"{label} must be lowercase 40-hex")
    return value


def sha64(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA64.fullmatch(value) is None:
        raise PromotionClosureError(f"{label} must be lowercase 64-hex")
    return value


def canonical_name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise PromotionClosureError(f"{label} is not a canonical relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise PromotionClosureError(f"{label} is not a canonical relative path")
    return value


