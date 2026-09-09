# SPDX-License-Identifier: Apache-2.0
"""Strictly compare closure-bound V2 control and target-ownership ablation arms."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import compare as parent

EXPECTED_EPISODE_STEPS = 720
EXPECTED_EVALUATOR_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
EXPECTED_V1_SCHEDULER_BLOB = "cbc502a92fe9d790cfaf763f6990d1057bc9b82d"


class BoundCompareError(parent.CompareError):
    """Execution custody or candidate-only activation evidence is invalid."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any, label: str, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise BoundCompareError(f"{label} is not a lowercase hex digest")
    return value


def mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BoundCompareError(f"{label} is not an object")
    return value


def validate_materialization(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if receipt.get("schema_version") != 2:
        raise BoundCompareError("ordered materialization schema mismatch")
    if receipt.get("repair") != "sol-vector-execution-custody-and-order-v1":
        raise BoundCompareError("ordered materialization repair identity mismatch")
    source = mapping(receipt.get("source"), "materialization source")
    v1 = mapping(receipt.get("v1_reference"), "V1 source reference")
    ablation = mapping(receipt.get("ablation"), "materialization ablation")
    if source.get("scheduler_git_blob_sha1") != parent.V2_SCHEDULER_BLOB:
        raise BoundCompareError("materialization is not bound to frozen V2")
    if v1.get("scheduler_git_blob_sha1") != EXPECTED_V1_SCHEDULER_BLOB:
        raise BoundCompareError("materialization is not bound to frozen V1")
    if ablation.get("changed_files") != ["scheduler.py"]:
        raise BoundCompareError("ablation is not scheduler-only")
    if ablation.get("target_iteration_order") != "PRODUCTS":
        raise BoundCompareError("ablation did not preserve V2 target order")
    if (
        ablation.get("old_occurrences_before") != 1
        or ablation.get("old_occurrences_after") != 0
        or ablation.get("v1_expression_occurrences_after") != 0
        or ablation.get("ordered_policy_occurrences_after") != 1
    ):
        raise BoundCompareError("ordered target-policy cardinality is invalid")
    source_closure = digest(source.get("closure_sha256"), "source closure")
    ablation_closure = digest(
        ablation.get("closure_sha256"), "ablation closure"
    )
    if source_closure == ablation_closure:
        raise BoundCompareError("source and ablation closures are equal")
    return {
        "source_closure": source_closure,
        "ablation_closure": ablation_closure,
        "source_scheduler_sha256": digest(
            source.get("scheduler_sha256"), "source scheduler"
        ),
        "ablation_scheduler_sha256": digest(
            ablation.get("scheduler_sha256"), "ablation scheduler"
        ),
        "ablation_scheduler_git_blob_sha1": digest(
            ablation.get("scheduler_git_blob_sha1"),
            "ablation scheduler Git blob",
            40,
        ),
    }


def validate_binding(
    receipt: Mapping[str, Any],
    materialization_path: Path,
    materialization: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    if receipt.get("schema_version") != 1:
        raise BoundCompareError("execution-binding schema mismatch")
    if receipt.get("repair") != "sol-vector-bound-arm-entrypoints-v1":
        raise BoundCompareError("execution-binding repair identity mismatch")
    if receipt.get("materialization_receipt_sha256") != file_sha256(
        materialization_path
    ):
        raise BoundCompareError(
            "execution binding does not name the exact materialization receipt"
        )
    material = validate_materialization(materialization)
    arms = mapping(receipt.get("arms"), "execution-binding arms")
    if set(arms) != {"control", "ablation"}:
        raise BoundCompareError("execution-binding arm set is invalid")
    expected = {
        "control": (
            material["source_closure"],
            material["source_scheduler_sha256"],
        ),
        "ablation": (
            material["ablation_closure"],
            material["ablation_scheduler_sha256"],
        ),
    }
    normalized: dict[str, dict[str, str]] = {}
    for arm, (closure, scheduler) in expected.items():
        row = mapping(arms.get(arm), f"{arm} execution binding")
        if row.get("payload_closure_sha256") != closure:
            raise BoundCompareError(f"{arm} payload closure is detached")
        if row.get("scheduler_sha256") != scheduler:
            raise BoundCompareError(f"{arm} scheduler digest is detached")
        if row.get("payload_entry_sha256") != parent.V2_ENTRY_SHA256:
            raise BoundCompareError(f"{arm} payload entry bytes drifted")
        if row.get("wrapper") != f"{arm}/bound_entry.py::agent":
            raise BoundCompareError(f"{arm} wrapper path/callable is invalid")
        normalized[arm] = {
            "payload_closure_sha256": closure,
            "scheduler_sha256": scheduler,
            "wrapper_sha256": digest(
                row.get("wrapper_sha256"), f"{arm} wrapper"
            ),
            "wrapper_git_blob_sha1": digest(
                row.get("wrapper_git_blob_sha1"),
                f"{arm} wrapper Git blob",
                40,
            ),
        }
    if normalized["control"]["wrapper_sha256"] == normalized["ablation"][
        "wrapper_sha256"
    ]:
        raise BoundCompareError("control and ablation wrappers are equal")
    return normalized


def validate_evaluator(receipt: Mapping[str, Any]) -> str:
    if receipt.get("schema_version") != 1:
        raise BoundCompareError("evaluator materialization schema mismatch")
    if receipt.get("repair") != "sol-vector-candidate-action-digest-v1":
        raise BoundCompareError("evaluator materialization identity mismatch")
    source = mapping(receipt.get("source"), "evaluator source")
    patched = mapping(receipt.get("patched"), "patched evaluator")
    if source.get("git_blob_sha1") != EXPECTED_EVALUATOR_BLOB:
        raise BoundCompareError("evaluator source blob mismatch")
    if patched.get("candidate_action_field") != "candidate_action_sha256":
        raise BoundCompareError("candidate action digest field mismatch")
    if patched.get("candidate_action_count_field") != "candidate_action_count":
        raise BoundCompareError("candidate action count field mismatch")
    if patched.get("capture_phase") != (
        "after both returned actions, before interpreter"
    ):
        raise BoundCompareError("candidate action capture phase mismatch")
    patches = patched.get("patches")
    if not isinstance(patches, list) or len(patches) != 3:
        raise BoundCompareError("evaluator patch receipt is incomplete")
    for index, row in enumerate(patches):
        row = mapping(row, f"evaluator patch {index}")
        if (
            row.get("old_occurrences_before") != 1
            or row.get("old_occurrences_after") != 0
            or row.get("new_occurrences_after") != 1
        ):
            raise BoundCompareError(
                f"evaluator patch {index} cardinality is invalid"
            )
    return digest(patched.get("sha256"), "patched evaluator")


def validate_report_binding(
    report: Mapping[str, Any],
    *,
    arm: str,
    wrapper_sha256: str,
    evaluator_sha256: str,
) -> None:
    candidate = mapping(report.get("candidate"), f"{arm} report candidate")
    if candidate.get("entry") != "bound_entry.py":
        raise BoundCompareError(f"{arm} report used the wrong entry file")
    if candidate.get("callable") != "agent":
        raise BoundCompareError(f"{arm} report used the wrong callable")
    if candidate.get("sha256") != wrapper_sha256:
        raise BoundCompareError(
            f"{arm} report is not bound to its closure-verifying wrapper"
        )
    if report.get("evaluator_sha256") != evaluator_sha256:
        raise BoundCompareError(
            f"{arm} report was not emitted by the patched evaluator"
        )
    rows = report.get("games")
    if not isinstance(rows, list):
        raise BoundCompareError(f"{arm} games is not a list")
    for index, game in enumerate(rows):
        game = mapping(game, f"{arm} game {index}")
        seat = game.get("candidate_seat")
        if isinstance(seat, bool) or not isinstance(seat, int) or seat not in (0, 1):
            raise BoundCompareError(f"{arm} game {index} seat is invalid")
        steps = game.get("steps")
        episode_steps = game.get("episode_steps")
        if (
            isinstance(steps, bool)
            or not isinstance(steps, int)
            or isinstance(episode_steps, bool)
            or not isinstance(episode_steps, int)
            or episode_steps != EXPECTED_EPISODE_STEPS
            or steps != EXPECTED_EPISODE_STEPS - 1
        ):
            raise BoundCompareError(
                f"{arm} game {index} does not cover the official episode"
            )
        count = game.get("candidate_action_count")
        if isinstance(count, bool) or not isinstance(count, int) or count != steps:
            raise BoundCompareError(
                f"{arm} game {index} candidate action count is invalid"
            )
        digest(
            game.get("candidate_action_sha256"),
            f"{arm} game {index} candidate action digest",
        )


def normalized_for_parent(report: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(report))
    candidate = dict(value["candidate"])
    candidate["sha256"] = parent.V2_ENTRY_SHA256
    value["candidate"] = candidate
    for game in value["games"]:
        game["trace_sha256"] = game["candidate_action_sha256"]
    return value


def parent_receipt(materialization: Mapping[str, Any]) -> dict[str, Any]:
    source = mapping(materialization["source"], "materialization source")
    ablation = mapping(materialization["ablation"], "materialization ablation")
    return {
        "schema_version": 1,
        "source": {
            "scheduler_git_blob_sha1": source["scheduler_git_blob_sha1"],
            "closure_sha256": source["closure_sha256"],
        },
        "ablation": {
            "changed_files": ["scheduler.py"],
            "scheduler_git_blob_sha1": ablation[
                "scheduler_git_blob_sha1"
            ],
            "closure_sha256": ablation["closure_sha256"],
            "old_occurrences_before": 1,
            "old_occurrences_after": 0,
            "new_occurrences_before": 0,
            "new_occurrences_after": 1,
        },
    }


def whole_trace_map(report: Mapping[str, Any]) -> dict[tuple[str, int, int], str]:
    output: dict[tuple[str, int, int], str] = {}
    for index, game in enumerate(report["games"]):
        key = (game.get("opponent"), game.get("seed"), game.get("candidate_seat"))
        output[key] = digest(
            game.get("trace_sha256"), f"whole trace {index}"
        )
    return output


def compare_bound(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    materialization: Mapping[str, Any],
    binding: Mapping[str, Any],
    evaluator: Mapping[str, Any],
    *,
    materialization_path: Path,
    git_head: str,
) -> dict[str, Any]:
    digest(git_head, "git head", 40)
    arms = validate_binding(binding, materialization_path, materialization)
    evaluator_sha = validate_evaluator(evaluator)
    validate_report_binding(
        control,
        arm="control",
        wrapper_sha256=arms["control"]["wrapper_sha256"],
        evaluator_sha256=evaluator_sha,
    )
    validate_report_binding(
        candidate,
        arm="ablation",
        wrapper_sha256=arms["ablation"]["wrapper_sha256"],
        evaluator_sha256=evaluator_sha,
    )
    control_whole = whole_trace_map(control)
    candidate_whole = whole_trace_map(candidate)
    if set(control_whole) != set(candidate_whole):
        raise BoundCompareError("whole-trace game grids differ")

    result = parent.compare(
        normalized_for_parent(control),
        normalized_for_parent(candidate),
        parent_receipt(materialization),
        git_head=git_head,
    )
    for row in result["rows"]:
        key = (row["opponent"], row["seed"], row["seat"])
        row["candidate_action_changed"] = row["trace_changed"]
        row["whole_trace_changed"] = control_whole[key] != candidate_whole[key]
    result["changed_rows"] = [
        row for row in result["rows"] if row["candidate_action_changed"]
    ]
    result["overall"]["candidate_action_changed_cells"] = result["overall"][
        "changed_cells"
    ]
    for values in result["by_opponent"].values():
        values["candidate_action_changed_cells"] = values["changed_cells"]
    result["execution_binding"] = {
        "control": arms["control"],
        "ablation": arms["ablation"],
        "patched_evaluator_sha256": evaluator_sha,
        "candidate_activation_field": "candidate_action_sha256",
        "candidate_activation_capture_phase": (
            "after both returned actions, before interpreter"
        ),
        "whole_trace_field": "trace_sha256",
        "expected_episode_steps": EXPECTED_EPISODE_STEPS,
    }
    result["schema_version"] = 2
    return result


def markdown(report: Mapping[str, Any]) -> str:
    text = parent.markdown(report)
    text = text.replace("Trace-changed cells", "Candidate-action-changed cells")
    text = text.replace("Trace-changed", "Candidate-action-changed")
    text = text.replace(
        "returned action trace", "candidate returned-action digest"
    )
    binding = report.get("execution_binding")
    if binding:
        lines = [
            "## Execution custody",
            "",
            "- Control wrapper SHA-256: `"
            + binding["control"]["wrapper_sha256"]
            + "`",
            "- Ablation wrapper SHA-256: `"
            + binding["ablation"]["wrapper_sha256"]
            + "`",
            "- Patched evaluator SHA-256: `"
            + binding["patched_evaluator_sha256"]
            + "`",
            "- Activation field: candidate-only pre-interpreter `candidate_action_sha256`",
            "- Required episode: 719 returned actions / 720 configured steps",
            "",
        ]
        marker = "This is a one-factor offline causal screen"
        text = text.replace(marker, "\n".join(lines) + marker)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--materialization-receipt", type=Path, required=True)
    parser.add_argument("--binding-receipt", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    try:
        materialization = parent.strict_object(args.materialization_receipt)
        result = compare_bound(
            parent.strict_object(args.control),
            parent.strict_object(args.candidate),
            materialization,
            parent.strict_object(args.binding_receipt),
            parent.strict_object(args.evaluator_receipt),
            materialization_path=args.materialization_receipt,
            git_head=args.head,
        )
    except parent.CompareError as exc:
        result = {
            "schema_version": 2,
            "operation": "titan-v2-target-domain-ablation-20260909-sol-bulwark-01",
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }
    parent.atomic_write(
        args.output,
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    parent.atomic_write(args.markdown, markdown(result))
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "reason": result["reason"],
                "exit_code": result["exit_code"],
                "overall": result.get("overall"),
                "by_opponent": result.get("by_opponent"),
                "execution_binding": result.get("execution_binding"),
            },
            sort_keys=True,
        )
    )
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
