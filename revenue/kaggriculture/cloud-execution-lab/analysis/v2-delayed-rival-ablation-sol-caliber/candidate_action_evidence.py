# SPDX-License-Identifier: Apache-2.0
"""Candidate-only activation custody for the delayed-rival causal screen."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any, Mapping

OPERATION = "titan-v2-delayed-rival-ablation-20260909-sol-caliber-01"
REPAIR = "sol-caliber-candidate-action-evidence-v1"
EXPECTED_EVALUATOR_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTIONS = EXPECTED_EPISODE_STEPS - 1
EXPECTED_PATCH_RETENTION = {
    "candidate digest initialization": 0,
    "pre-interpreter candidate action capture": 1,
    "candidate digest publication": 0,
}

GameKey = tuple[str, int, int]


class CandidateActionEvidenceError(ValueError):
    """Candidate-only activation evidence is absent, detached, or malformed."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CandidateActionEvidenceError(f"{label} is not an object")
    return value


def _hex(value: Any, label: str, length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise CandidateActionEvidenceError(
            f"{label} is not a lowercase {length}-hex digest"
        )
    return value


def _regular_bytes(path: Path, label: str) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise CandidateActionEvidenceError(f"{label} is not one regular file: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CandidateActionEvidenceError(f"cannot read {label} {path}: {exc}") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def validate_evaluator_materialization(
    receipt: Mapping[str, Any],
    *,
    source_evaluator: Path,
    patched_evaluator: Path,
) -> dict[str, Any]:
    """Bind the receipt to exact evaluator bytes and zero unconsumed patch sites."""
    if receipt.get("schema_version") != 1:
        raise CandidateActionEvidenceError("evaluator materialization schema mismatch")
    if receipt.get("operation") != OPERATION:
        raise CandidateActionEvidenceError("evaluator materialization operation mismatch")
    if receipt.get("repair") != REPAIR:
        raise CandidateActionEvidenceError("evaluator materialization repair mismatch")

    source = _mapping(receipt.get("source"), "evaluator source receipt")
    patched = _mapping(receipt.get("patched"), "patched evaluator receipt")
    source_bytes = _regular_bytes(source_evaluator, "source evaluator")
    patched_bytes = _regular_bytes(patched_evaluator, "patched evaluator")

    source_blob = _git_blob_sha1(source_bytes)
    source_sha = _sha256(source_bytes)
    if source_blob != EXPECTED_EVALUATOR_BLOB:
        raise CandidateActionEvidenceError(
            f"source evaluator Git blob drifted: {source_blob}"
        )
    if source.get("git_blob_sha1") != source_blob:
        raise CandidateActionEvidenceError("evaluator receipt source blob is detached")
    if source.get("sha256") != source_sha:
        raise CandidateActionEvidenceError("evaluator receipt source SHA-256 is detached")
    if source.get("bytes") != len(source_bytes):
        raise CandidateActionEvidenceError("evaluator receipt source size is detached")

    patched_blob = _git_blob_sha1(patched_bytes)
    patched_sha = _sha256(patched_bytes)
    if patched.get("git_blob_sha1") != patched_blob:
        raise CandidateActionEvidenceError("patched evaluator Git blob is detached")
    if patched.get("sha256") != patched_sha:
        raise CandidateActionEvidenceError("patched evaluator SHA-256 is detached")
    if patched.get("bytes") != len(patched_bytes):
        raise CandidateActionEvidenceError("patched evaluator size is detached")
    if patched_sha == source_sha:
        raise CandidateActionEvidenceError("patched evaluator equals source evaluator")

    if patched.get("candidate_action_field") != "candidate_action_sha256":
        raise CandidateActionEvidenceError("candidate action digest field mismatch")
    if patched.get("candidate_action_count_field") != "candidate_action_count":
        raise CandidateActionEvidenceError("candidate action count field mismatch")
    if patched.get("capture_phase") != (
        "after both returned actions, before interpreter"
    ):
        raise CandidateActionEvidenceError("candidate action capture phase mismatch")

    patches = patched.get("patches")
    if not isinstance(patches, list) or len(patches) != len(EXPECTED_PATCH_RETENTION):
        raise CandidateActionEvidenceError("evaluator patch receipt is incomplete")
    seen: set[str] = set()
    for index, row in enumerate(patches):
        row = _mapping(row, f"evaluator patch {index}")
        label = row.get("label")
        if type(label) is not str or label not in EXPECTED_PATCH_RETENTION or label in seen:
            raise CandidateActionEvidenceError(
                f"evaluator patch {index} label is invalid or duplicated"
            )
        seen.add(label)
        retained = row.get("old_occurrences_retained_in_replacement")
        raw_after = row.get("old_occurrences_after")
        unconsumed = row.get("unconsumed_old_occurrences_after")
        if (
            row.get("old_occurrences_before") != 1
            or retained != EXPECTED_PATCH_RETENTION[label]
            or raw_after != retained
            or unconsumed != 0
            or row.get("new_occurrences_after") != 1
        ):
            raise CandidateActionEvidenceError(
                f"evaluator patch {index} consumed-site cardinality is invalid"
            )
        _hex(row.get("old_sha256"), f"evaluator patch {index} old SHA-256", 64)
        _hex(row.get("new_sha256"), f"evaluator patch {index} new SHA-256", 64)
    if seen != set(EXPECTED_PATCH_RETENTION):
        raise CandidateActionEvidenceError("evaluator patch labels are incomplete")

    return {
        "source_git_blob_sha1": source_blob,
        "source_sha256": source_sha,
        "patched_git_blob_sha1": patched_blob,
        "patched_sha256": patched_sha,
        "field": "candidate_action_sha256",
        "count_field": "candidate_action_count",
        "capture_phase": "after both returned actions, before interpreter",
        "expected_episode_steps": EXPECTED_EPISODE_STEPS,
        "expected_candidate_actions": EXPECTED_ACTIONS,
        "whole_trace_field": "trace_sha256",
        "whole_trace_is_activation": False,
    }


def _normalize_report(
    report: Mapping[str, Any],
    *,
    label: str,
) -> tuple[dict[str, Any], dict[GameKey, str]]:
    normalized = deepcopy(dict(report))
    games = normalized.get("games")
    if not isinstance(games, list) or not games:
        raise CandidateActionEvidenceError(f"{label} games is not a nonempty list")

    whole: dict[GameKey, str] = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise CandidateActionEvidenceError(f"{label} game {index} is not an object")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if type(opponent) is not str or not opponent:
            raise CandidateActionEvidenceError(
                f"{label} game {index} opponent is invalid"
            )
        if type(seed) is not int:
            raise CandidateActionEvidenceError(f"{label} game {index} seed is invalid")
        if type(seat) is not int or seat not in (0, 1):
            raise CandidateActionEvidenceError(
                f"{label} game {index} candidate_seat is invalid"
            )
        steps = game.get("steps")
        episode_steps = game.get("episode_steps")
        count = game.get("candidate_action_count")
        if (
            type(episode_steps) is not int
            or episode_steps != EXPECTED_EPISODE_STEPS
            or type(steps) is not int
            or steps != EXPECTED_ACTIONS
            or type(count) is not int
            or count != steps
        ):
            raise CandidateActionEvidenceError(
                f"{label} game {index} candidate action count/episode is invalid"
            )
        candidate_digest = _hex(
            game.get("candidate_action_sha256"),
            f"{label} game {index} candidate action SHA-256",
            64,
        )
        whole_digest = _hex(
            game.get("trace_sha256"),
            f"{label} game {index} whole trace SHA-256",
            64,
        )
        key: GameKey = (opponent, seed, seat)
        if key in whole:
            raise CandidateActionEvidenceError(
                f"{label} contains duplicate game key {key!r}"
            )
        whole[key] = whole_digest
        game["trace_sha256"] = candidate_digest
    return normalized, whole


def prepare_pair(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    evaluator_materialization: Mapping[str, Any],
    *,
    source_evaluator: Path,
    patched_evaluator: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return comparator-ready deep copies plus candidate-action custody metadata."""
    binding = validate_evaluator_materialization(
        evaluator_materialization,
        source_evaluator=source_evaluator,
        patched_evaluator=patched_evaluator,
    )
    normalized_control, control_whole = _normalize_report(control, label="control")
    normalized_candidate, candidate_whole = _normalize_report(
        candidate, label="candidate"
    )
    if set(control_whole) != set(candidate_whole):
        raise CandidateActionEvidenceError("control/candidate game grids differ")
    whole_changed = {
        key: control_whole[key] != candidate_whole[key]
        for key in sorted(control_whole)
    }
    return normalized_control, normalized_candidate, {
        "binding": binding,
        "whole_trace_changed": whole_changed,
    }


def annotate_report(
    report: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    output = deepcopy(dict(report))
    whole_changed = evidence.get("whole_trace_changed")
    if not isinstance(whole_changed, Mapping):
        raise CandidateActionEvidenceError("whole-trace evidence is missing")
    rows = output.get("rows")
    if not isinstance(rows, list):
        raise CandidateActionEvidenceError("comparison rows are missing")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CandidateActionEvidenceError(f"comparison row {index} is not an object")
        key: GameKey = (str(row["opponent"]), int(row["seed"]), int(row["seat"]))
        if key not in whole_changed:
            raise CandidateActionEvidenceError(
                f"comparison row {index} is outside candidate-action grid: {key!r}"
            )
        row["candidate_action_changed"] = bool(row.get("trace_changed"))
        row["whole_trace_changed"] = bool(whole_changed[key])

    overall = output.get("overall")
    if isinstance(overall, dict) and "changed_cells" in overall:
        overall["candidate_action_changed_cells"] = overall["changed_cells"]
    for name in ("by_opponent", "by_opponent_seat"):
        groups = output.get(name)
        if isinstance(groups, Mapping):
            for values in groups.values():
                if isinstance(values, dict) and "changed_cells" in values:
                    values["candidate_action_changed_cells"] = values["changed_cells"]

    binding = evidence.get("binding")
    if not isinstance(binding, Mapping):
        raise CandidateActionEvidenceError("activation binding is missing")
    output["activation_binding"] = dict(binding)
    output["schema_version"] = max(int(output.get("schema_version", 1)), 2)
    return output
