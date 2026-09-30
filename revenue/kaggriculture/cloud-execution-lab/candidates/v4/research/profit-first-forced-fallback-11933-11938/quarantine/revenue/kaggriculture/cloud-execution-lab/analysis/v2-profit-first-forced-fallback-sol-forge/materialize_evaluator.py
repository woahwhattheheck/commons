# SPDX-License-Identifier: Apache-2.0
"""Profit-first lane adapter for exact candidate-action evaluator receipts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import materialize as lane
from delegate import load_parent, reexport

_PARENT = load_parent(
    "materialize_evaluator.py", "_sol_forge_parent_materialize_evaluator"
)
_ORIGINAL_MATERIALIZE_EVALUATOR = _PARENT.materialize_evaluator
reexport(_PARENT, globals())


def materialize_evaluator(
    source: Path,
    output: Path,
    *,
    expected_blob: str = EXPECTED_EVALUATOR_BLOB,
) -> dict[str, Any]:
    """Retain raw embedded old bytes without calling them unconsumed sites."""
    receipt = _ORIGINAL_MATERIALIZE_EVALUATOR(
        source,
        output,
        expected_blob=expected_blob,
    )
    patches = receipt["patched"]["patches"]
    if len(patches) != len(NEEDLES):
        raise EvaluatorMaterializeError("evaluator patch receipt is incomplete")

    for row, (old, new, label) in zip(patches, NEEDLES, strict=True):
        raw_after = row["old_occurrences_after"]
        embedded = new.count(old)
        unconsumed = raw_after - embedded
        if unconsumed != 0:
            raise EvaluatorMaterializeError(
                f"{label} left {unconsumed} unconsumed old patch sites"
            )
        row["old_occurrences_after_raw"] = raw_after
        row["old_occurrences_embedded_in_replacement"] = embedded
        row["old_occurrences_after"] = unconsumed
    return receipt


# Parent main() resolves this global at execution time.  Override only the
# materialization function; all source checks, patch bytes, compilation, atomic
# output, and receipt serialization remain the reviewed parent implementation.
_PARENT.materialize_evaluator = materialize_evaluator

if __name__ == "__main__":
    raise SystemExit(_PARENT.main())
