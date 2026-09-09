# SPDX-License-Identifier: Apache-2.0
"""Admit V2 target-domain results only from candidate-only returned-action evidence."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import bind_execution
import compare
import strict_compare

EXPECTED_EVALUATOR_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTIONS = EXPECTED_EPISODE_STEPS - 1
REPAIR = "sol-candidate-action-evidence-v1"


class CandidateActionCompareError(strict_compare.StrictCompareError):
    """Candidate-only activation evidence is absent, detached, or malformed."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CandidateActionCompareError(f"{label} is not an object")
    return value


def _hex(value: Any, label: str, length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise CandidateActionCompareError(
            f"{label} is not a lowercase {length}-hex digest"
        )
    return value


def _regular_bytes(path: Path, label: str) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise CandidateActionCompareError(f"{label} is not one regular file: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CandidateActionCompareError(f"cannot read {label} {path}: {exc}") from exc


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
) -> dict[str, str]:
    if receipt.get("schema_version") != 1:
        raise CandidateActionCompareError("evaluator materialization schema mismatch")
    if receipt.get("operation") != (
        "titan-v2-target-domain-ablation-20260909-sol-bulwark-01"
    ):
        raise CandidateActionCompareError("evaluator materialization operation mismatch")
    if receipt.get("repair") != REPAIR:
        raise CandidateActionCompareError("evaluator materialization repair mismatch")

    source = _mapping(receipt.get("source"), "evaluator source receipt")
    patched = _mapping(receipt.get("patched"), "patched evaluator receipt")
    source_bytes = _regular_bytes(source_evaluator, "source evaluator")
    patched_bytes = _regular_bytes(patched_evaluator, "patched evaluator")

    source_blob = _git_blob_sha1(source_bytes)
    if source_blob != EXPECTED_EVALUATOR_BLOB:
        raise CandidateActionCompareError(
            f"source evaluator Git blob drifted: {source_blob}"
        )
    if source.get("git_blob_sha1") != source_blob:
        raise CandidateActionCompareError("evaluator receipt source blob is detached")
    if source.get("sha256") != _sha256(source_bytes):
        raise CandidateActionCompareError("evaluator receipt source SHA-256 is detached")
    if source.get("bytes") != len(source_bytes):
        raise CandidateActionCompareError("evaluator receipt source size is detached")

    patched_sha = _sha256(patched_bytes)
    patched_blob = _git_blob_sha1(patched_bytes)
    if patched.get("sha256") != patched_sha:
        raise CandidateActionCompareError("patched evaluator SHA-256 is detached")
    if patched.get("git_blob_sha1") != patched_blob:
        raise CandidateActionCompareError("patched evaluator Git blob is detached")
    if patched.get("bytes") != len(patched_bytes):
        raise CandidateActionCompareError("patched evaluator size is detached")
    if patched_sha == _sha256(source_bytes):
        raise CandidateActionCompareError("patched evaluator equals source evaluator")

    if patched.get("candidate_action_field") != "candidate_action_sha256":
        raise CandidateActionCompareError("candidate action digest field mismatch")
    if patched.get("candidate_action_count_field") != "candidate_action_count":
        raise CandidateActionCompareError("candidate action count field mismatch")
    if patched.get("capture_phase") != (
        "after both returned actions, before interpreter"
    ):
        raise CandidateActionCompareError("candidate action capture phase mismatch")

    patches = patched.get("patches")
    if not isinstance(patches, list) or len(patches) != 3:
        raise CandidateActionCompareError("evaluator patch receipt is incomplete")
    for index, row in enumerate(patches):
        row = _mapping(row, f"evaluator patch {index}")
        if (
            row.get("old_occurrences_before") != 1
            or row.get("old_occurrences_after") != 0
            or row.get("new_occurrences_after") != 1
        ):
            raise CandidateActionCompareError(
                f"evaluator patch {index} cardinality is invalid"
            )
        _hex(row.get("old_sha256"), f"evaluator patch {index} old SHA-256", 64)
        _hex(row.get("new_sha256"), f"evaluator patch {index} new SHA-256", 64)

    return {
        "source_git_blob_sha1": source_blob,
        "source_sha256": _sha256(source_bytes),
        "patched_git_blob_sha1": patched_blob,
        "patched_sha256": patched_sha,
    }


def _normalize_candidate_activation(
    report: Mapping[str, Any],
    *,
    label: str,
) -> tuple[dict[str, Any], dict[tuple[str, int, int], str]]:
    normalized = deepcopy(dict(report))
    games = normalized.get("games")
    if not isinstance(games, list):
        raise CandidateActionCompareError(f"{label} games is not a list")

    whole_traces: dict[tuple[str, int, int], str] = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise CandidateActionCompareError(f"{label} game {index} is not an object")
        seat = game.get("candidate_seat")
        seed = game.get("seed")
        opponent = game.get("opponent")
        if type(seat) is not int or seat not in (0, 1):
            raise CandidateActionCompareError(
                f"{label} game {index} candidate_seat is invalid"
            )
        if type(seed) is not int:
            raise CandidateActionCompareError(f"{label} game {index} seed is invalid")
        if type(opponent) is not str or not opponent:
            raise CandidateActionCompareError(
                f"{label} game {index} opponent is invalid"
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
            raise CandidateActionCompareError(
                f"{label} game {index} candidate action count/episode is invalid"
            )
        candidate_digest = _hex(
            game.get("candidate_action_sha256"),
            f"{label} game {index} candidate action SHA-256",
            64,
        )
        whole = _hex(
            game.get("trace_sha256"),
            f"{label} game {index} whole trace SHA-256",
            64,
        )
        key = (opponent, seed, seat)
        if key in whole_traces:
            raise CandidateActionCompareError(
                f"{label} contains duplicate game key {key!r}"
            )
        whole_traces[key] = whole
        game["trace_sha256"] = candidate_digest

    return normalized, whole_traces


def compare_action_bound(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    execution_binding: Mapping[str, Any],
    evaluator_materialization: Mapping[str, Any],
    *,
    source_evaluator: Path,
    git_head: str,
    control_root: Path,
    candidate_root: Path,
    control_wrapper: Path,
    candidate_wrapper: Path,
    engine_dir: Path,
    loader: Path,
    evaluator: Path,
    opponents: Mapping[str, str],
) -> dict[str, Any]:
    evaluator_binding = validate_evaluator_materialization(
        evaluator_materialization,
        source_evaluator=source_evaluator,
        patched_evaluator=evaluator,
    )
    normalized_control, control_whole = _normalize_candidate_activation(
        control, label="control"
    )
    normalized_candidate, candidate_whole = _normalize_candidate_activation(
        candidate, label="candidate"
    )
    if set(control_whole) != set(candidate_whole):
        raise CandidateActionCompareError("control/candidate whole-trace grids differ")

    report = strict_compare.compare_bound(
        normalized_control,
        normalized_candidate,
        receipt,
        execution_binding,
        git_head=git_head,
        control_root=control_root,
        candidate_root=candidate_root,
        control_wrapper=control_wrapper,
        candidate_wrapper=candidate_wrapper,
        engine_dir=engine_dir,
        loader=loader,
        evaluator=evaluator,
        opponents=opponents,
    )

    for row in report.get("rows", []):
        key = (str(row["opponent"]), int(row["seed"]), int(row["seat"]))
        row["candidate_action_changed"] = bool(row["trace_changed"])
        row["whole_trace_changed"] = control_whole[key] != candidate_whole[key]
    overall = report.get("overall")
    if isinstance(overall, dict) and "changed_cells" in overall:
        overall["candidate_action_changed_cells"] = overall["changed_cells"]
    by_opponent = report.get("by_opponent")
    if isinstance(by_opponent, Mapping):
        for values in by_opponent.values():
            if isinstance(values, dict) and "changed_cells" in values:
                values["candidate_action_changed_cells"] = values["changed_cells"]
    by_stratum = report.get("by_opponent_seat")
    if isinstance(by_stratum, Mapping):
        for values in by_stratum.values():
            if isinstance(values, dict) and "changed_cells" in values:
                values["candidate_action_changed_cells"] = values["changed_cells"]

    report["activation_binding"] = {
        **evaluator_binding,
        "field": "candidate_action_sha256",
        "count_field": "candidate_action_count",
        "capture_phase": "after both returned actions, before interpreter",
        "expected_episode_steps": EXPECTED_EPISODE_STEPS,
        "expected_candidate_actions": EXPECTED_ACTIONS,
        "whole_trace_field": "trace_sha256",
        "whole_trace_is_activation": False,
    }
    report["schema_version"] = max(int(report.get("schema_version", 1)), 2)
    return report


def markdown(report: Mapping[str, Any]) -> str:
    text = strict_compare.markdown(report)
    text = text.replace("Trace-changed cells", "Candidate-action-changed cells")
    text = text.replace("Trace-changed", "Candidate-action-changed")
    binding = report.get("activation_binding")
    if not isinstance(binding, Mapping):
        return text
    section = [
        "",
        "## Candidate-only activation custody",
        "",
        f"- Source evaluator Git blob: `{binding['source_git_blob_sha1']}`",
        f"- Patched evaluator SHA-256: `{binding['patched_sha256']}`",
        "- Activation: pre-interpreter `candidate_action_sha256` only",
        f"- Required episode: {binding['expected_candidate_actions']} returned actions / "
        f"{binding['expected_episode_steps']} configured steps",
        "- Whole-game `trace_sha256` is retained for reproducibility only and cannot activate the screen.",
        "",
    ]
    return text.rstrip() + "\n" + "\n".join(section)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--control-wrapper", type=Path, required=True)
    parser.add_argument("--candidate-wrapper", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--evaluator-source", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--opponent", action="append", default=[])
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = compare_action_bound(
            compare.strict_object(args.control),
            compare.strict_object(args.candidate),
            compare.strict_object(args.receipt),
            compare.strict_object(args.binding),
            compare.strict_object(args.evaluator_receipt),
            source_evaluator=args.evaluator_source,
            git_head=args.head,
            control_root=args.control_root,
            candidate_root=args.candidate_root,
            control_wrapper=args.control_wrapper,
            candidate_wrapper=args.candidate_wrapper,
            engine_dir=args.engine_dir,
            loader=args.loader,
            evaluator=args.evaluator,
            opponents=bind_execution._parse_opponents(args.opponent),
        )
    except (
        CandidateActionCompareError,
        strict_compare.StrictCompareError,
        compare.CompareError,
        bind_execution.BindingError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        report = {
            "schema_version": 2,
            "operation": "titan-v2-target-domain-ablation-20260909-sol-bulwark-01",
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }

    compare.atomic_write(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    compare.atomic_write(args.markdown, markdown(report))
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "reason": report["reason"],
                "exit_code": report["exit_code"],
                "overall": report.get("overall"),
                "by_opponent": report.get("by_opponent"),
                "by_opponent_seat": report.get("by_opponent_seat"),
                "activation_binding": report.get("activation_binding"),
            },
            sort_keys=True,
        )
    )
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
