# SPDX-License-Identifier: Apache-2.0
"""Patch the exact evaluator to retain candidate-only pre-interpreter actions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import materialize

EXPECTED_EVALUATOR_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
REPAIR = "sol-candidate-action-evidence-v1"

NEEDLES: tuple[tuple[bytes, bytes, str], ...] = (
    (
        b"    actors, trace = [], hashlib.sha256()\n",
        b"    actors, trace, candidate_trace = [], hashlib.sha256(), hashlib.sha256()\n",
        "candidate digest initialization",
    ),
    (
        b"            for seat in range(2):\n"
        b"                state[seat].action = actions[seat]\n",
        b"            candidate_trace.update(encoded({\"step\": step, \"action\": actions[candidate_seat]}))\n"
        b"            for seat in range(2):\n"
        b"                state[seat].action = actions[seat]\n",
        "pre-interpreter candidate action capture",
    ),
    (
        b"        else:\n"
        b"            result[\"trace_sha256\"] = trace.hexdigest()\n"
        b"        if finalization_errors:\n",
        b"        else:\n"
        b"            result[\"trace_sha256\"] = trace.hexdigest()\n"
        b"        result[\"candidate_action_sha256\"] = candidate_trace.hexdigest()\n"
        b"        result[\"candidate_action_count\"] = result[\"steps\"]\n"
        b"        if finalization_errors:\n",
        "candidate digest publication",
    ),
)


class EvaluatorMaterializeError(ValueError):
    """The evaluator source or patch cardinality is invalid."""


def materialize_evaluator(
    source: Path,
    output: Path,
    *,
    expected_blob: str = EXPECTED_EVALUATOR_BLOB,
) -> dict[str, Any]:
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise EvaluatorMaterializeError(f"output already exists: {output}")
    original = source.read_bytes()
    actual_blob = materialize.git_blob_sha1(original)
    if actual_blob != expected_blob:
        raise EvaluatorMaterializeError(
            f"evaluator blob mismatch: expected {expected_blob}, got {actual_blob}"
        )

    patched = original
    receipts: list[dict[str, Any]] = []
    for old, new, label in NEEDLES:
        before = patched.count(old)
        new_before = patched.count(new)
        if before != 1 or new_before != 0:
            raise EvaluatorMaterializeError(
                f"{label} cardinality mismatch: old={before}, new={new_before}"
            )
        patched = patched.replace(old, new, 1)
        old_after_raw = patched.count(old)
        embedded = new.count(old)
        unconsumed = old_after_raw - embedded
        if unconsumed != 0 or patched.count(new) != 1:
            raise EvaluatorMaterializeError(f"{label} patch did not consume one site")
        receipts.append(
            {
                "label": label,
                "old_sha256": materialize.sha256(old),
                "new_sha256": materialize.sha256(new),
                "old_occurrences_before": before,
                "old_occurrences_after": unconsumed,
                "old_occurrences_after_raw": old_after_raw,
                "old_occurrences_embedded_in_replacement": embedded,
                "new_occurrences_after": patched.count(new),
            }
        )

    if patched == original:
        raise EvaluatorMaterializeError("evaluator patch changed no bytes")
    try:
        compile(patched.decode("utf-8"), str(output), "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise EvaluatorMaterializeError(f"patched evaluator is invalid: {exc}") from exc
    materialize.atomic_write(output, patched)
    if source.read_bytes() != original:
        raise EvaluatorMaterializeError("source evaluator changed during patching")
    return {
        "schema_version": 1,
        "operation": materialize.OPERATION,
        "experiment": materialize.EXPERIMENT,
        "repair": REPAIR,
        "source": {
            "path_name": source.name,
            "git_blob_sha1": actual_blob,
            "sha256": materialize.sha256(original),
            "bytes": len(original),
        },
        "patched": {
            "path_name": output.name,
            "git_blob_sha1": materialize.git_blob_sha1(patched),
            "sha256": materialize.sha256(patched),
            "bytes": len(patched),
            "patches": receipts,
            "candidate_action_field": "candidate_action_sha256",
            "candidate_action_count_field": "candidate_action_count",
            "capture_phase": "after both returned actions, before interpreter",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize_evaluator(args.source, args.output)
    materialize.atomic_write(
        args.receipt,
        (
            json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "source_blob": receipt["source"]["git_blob_sha1"],
                "patched_blob": receipt["patched"]["git_blob_sha1"],
                "capture_phase": receipt["patched"]["capture_phase"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
