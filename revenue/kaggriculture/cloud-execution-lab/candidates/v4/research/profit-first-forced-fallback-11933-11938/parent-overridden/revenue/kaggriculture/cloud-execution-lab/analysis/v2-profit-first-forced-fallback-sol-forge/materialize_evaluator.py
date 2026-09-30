# SPDX-License-Identifier: Apache-2.0
"""Profit-first lane adapter for the exact candidate-action evaluator patch."""
from __future__ import annotations

import materialize as lane
from delegate import load_parent, reexport

_PARENT = load_parent(
    "materialize_evaluator.py", "_sol_forge_parent_materialize_evaluator"
)
reexport(_PARENT, globals())

if __name__ == "__main__":
    raise SystemExit(_PARENT.main())
