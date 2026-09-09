# SPDX-License-Identifier: Apache-2.0
"""Validate exact evaluator context and deterministic replay custody."""
from __future__ import annotations

from typing import Any

from compare_common import (
    ACTION_CAPTURE_BOUNDARY,
    ACTION_DIGEST_SCHEMA,
    CORE_EVALUATOR_GIT_BLOB,
    CompareError,
    ENGINE_REF,
    EXPECTED_CELLS,
    EXPECTED_LIMITS,
    EXPECTED_OPPONENTS,
    EXPECTED_SEEDS,
    finite_number,
    require_hex,
)

def validate_top_level(report: dict[str, Any], arm: str) -> None:
    if report.get("schema_version") != 1:
        raise CompareError(f"{arm} evaluator schema mismatch")
    require_hex(report.get("invocation_id"), 32, f"{arm} invocation id")
    if report.get("engine_ref") != ENGINE_REF:
        raise CompareError(f"{arm} engine ref mismatch")
    engine_hashes = report.get("engine_sha256")
    if not isinstance(engine_hashes, dict) or set(engine_hashes) != {
        "kaggriculture.py",
        "kaggriculture.json",
        "utils.py",
    }:
        raise CompareError(f"{arm} engine digest map mismatch")
    for name, digest in engine_hashes.items():
        require_hex(digest, 64, f"{arm} engine digest {name}")
    require_hex(report.get("loader_sha256"), 64, f"{arm} loader digest")
    require_hex(report.get("evaluator_sha256"), 64, f"{arm} evaluator digest")

    candidate = report.get("candidate")
    if not isinstance(candidate, dict):
        raise CompareError(f"{arm} candidate fingerprint missing")
    if candidate.get("entry") != "entry.py" or candidate.get("callable") != "agent":
        raise CompareError(f"{arm} candidate entry/callable mismatch")
    require_hex(candidate.get("sha256"), 64, f"{arm} candidate entry digest")

    opponents = report.get("opponents")
    if not isinstance(opponents, dict) or tuple(sorted(opponents)) != tuple(sorted(EXPECTED_OPPONENTS)):
        raise CompareError(f"{arm} opponent labels mismatch")
    for name, fingerprint in opponents.items():
        if not isinstance(fingerprint, dict):
            raise CompareError(f"{arm} opponent fingerprint {name} missing")
        require_hex(fingerprint.get("sha256"), 64, f"{arm} opponent digest {name}")

    if report.get("seeds") != list(EXPECTED_SEEDS):
        raise CompareError(f"{arm} seed grid mismatch")
    if type(report.get("agent_rng_seed")) is not int or report.get("agent_rng_seed") != 20260909:
        raise CompareError(f"{arm} agent RNG seed mismatch")
    limits = report.get("limits")
    if not isinstance(limits, dict) or set(limits) != set(EXPECTED_LIMITS):
        raise CompareError(f"{arm} limits object mismatch")
    normalized_limits = {
        key: finite_number(value, f"{arm} limit {key}")
        for key, value in limits.items()
    }
    if normalized_limits != EXPECTED_LIMITS:
        raise CompareError(f"{arm} exact evaluator limits mismatch")

    overlay = report.get("activation_overlay")
    if not isinstance(overlay, dict) or overlay.get("schema_version") != 1:
        raise CompareError(f"{arm} activation overlay identity missing")
    require_hex(overlay.get("sha256"), 64, f"{arm} overlay digest")
    if overlay.get("core_evaluator_git_blob") != CORE_EVALUATOR_GIT_BLOB:
        raise CompareError(f"{arm} core evaluator blob mismatch")
    if overlay.get("action_digest_schema") != ACTION_DIGEST_SCHEMA:
        raise CompareError(f"{arm} action digest schema mismatch")
    if overlay.get("action_digest_capture") != ACTION_CAPTURE_BOUNDARY:
        raise CompareError(f"{arm} action capture boundary mismatch")

    reproducibility = report.get("reproducibility")
    if (
        not isinstance(reproducibility, dict)
        or reproducibility.get("checked") is not True
        or reproducibility.get("same_trace_and_scores") is not True
    ):
        raise CompareError(f"{arm} first-cell deterministic replay mismatch")
    require_hex(reproducibility.get("original_trace"), 64, f"{arm} original replay trace")
    require_hex(reproducibility.get("replay_trace"), 64, f"{arm} repeated replay trace")
    if reproducibility.get("original_trace") != reproducibility.get("replay_trace"):
        raise CompareError(f"{arm} deterministic replay trace differs")

    progress = report.get("progress")
    if not isinstance(progress, dict):
        raise CompareError(f"{arm} progress receipt missing")
    if progress.get("state") != "complete" or progress.get("phase") != "finalize":
        raise CompareError(f"{arm} report is not finalized complete evidence")
    if progress.get("recheck_requested") is not True:
        raise CompareError(f"{arm} deterministic replay was not requested")
    if progress.get("planned_games") != EXPECTED_CELLS or progress.get("recorded_games") != EXPECTED_CELLS:
        raise CompareError(f"{arm} progress grid count mismatch")
