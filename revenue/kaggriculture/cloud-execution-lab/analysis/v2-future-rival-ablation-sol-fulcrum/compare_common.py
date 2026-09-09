# SPDX-License-Identifier: Apache-2.0
"""Shared strict types and execution constants for the paired comparator."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

from activation_eval import (
    ACTION_CAPTURE_BOUNDARY,
    ACTION_DIGEST_SCHEMA,
    CORE_EVALUATOR_GIT_BLOB,
)
from materialize import (
    ABLATION_SCENARIOS,
    ENTRYPOINT_SHA256,
    FREEZE_GIT_BLOB,
    OPERATION,
    SCHEDULER_GIT_BLOB,
    SCHEDULER_SHA256,
    V2_SCENARIOS,
    closure_digest,
)


EXPECTED_SEEDS = (
    539131249,
    1834999074,
    2609097301,
    2609097302,
    2609097303,
    2609097304,
    2611092201,
    2611092207,
)
EXPECTED_OPPONENTS = ("arlene", "v1")
EXPECTED_CELLS = len(EXPECTED_SEEDS) * len(EXPECTED_OPPONENTS) * 2
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_LIMITS = {
    "action_rpc_seconds": 1.0,
    "startup_seconds": 15.0,
    "game_seconds_between_steps": 180.0,
    "remaining_overage_time": 0.0,
}


class CompareError(ValueError):
    """A report, receipt, or comparison failed closed."""


def _reject_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise CompareError(f"duplicate JSON key: {key!r}")
        output[key] = value
    return output


def strict_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CompareError(f"non-finite JSON token: {token}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompareError(f"cannot read strict JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CompareError(f"expected JSON object in {path}")
    return value


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompareError(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise CompareError(f"{label} must be finite")
    return number


def require_hex(value: Any, length: int, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(rf"[0-9a-f]{{{length}}}", value):
        raise CompareError(f"{label} must be lowercase {length}-hex")
    return value




def validate_inventory(value: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or not value:
        raise CompareError(f"{label} inventory must be a nonempty object")
    output: dict[str, dict[str, Any]] = {}
    for path, metadata in value.items():
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or "\\" in path
            or ".." in Path(path).parts
        ):
            raise CompareError(f"{label} inventory path is unsafe: {path!r}")
        if not isinstance(metadata, dict) or set(metadata) != {"bytes", "sha256"}:
            raise CompareError(f"{label} inventory metadata mismatch for {path}")
        size = metadata.get("bytes")
        if type(size) is not int or size < 0:
            raise CompareError(f"{label} inventory byte count mismatch for {path}")
        digest = require_hex(metadata.get("sha256"), 64, f"{label} inventory digest {path}")
        output[path] = {"bytes": size, "sha256": digest}
    for required in ("FREEZE.json", "candidate.py", "scheduler.py"):
        if required not in output:
            raise CompareError(f"{label} inventory lacks {required}")
    return output
