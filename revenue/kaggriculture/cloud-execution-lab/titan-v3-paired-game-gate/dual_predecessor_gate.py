#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Public dual-predecessor gate with outcome/identity separation.

The full custody-bound implementation from merge 8141dd77 is preserved byte for
byte in ``_dual_predecessor_gate_core.py``.  This facade corrects one theorem:
two closure-distinct predecessors may legitimately produce byte-identical game
rows on a finite grid.  Distinct execution identity is proven by the observed,
receipt-bound predecessor closure bundles, not by inequality of result bytes.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

import _dual_predecessor_gate_core as _core

# Preserve the public and test-facing surface of the landed implementation.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def _validate_cross_comparison(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    *,
    outer_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Validate shared execution identity without comparing outcome bytes.

    A byte-equality constraint on predecessor game panels is unsound in both
    directions: closure-distinct agents may tie on every measured cell, while a
    copied panel can be reserialized to obtain a different file digest.  The
    surrounding custody gate already binds each panel to its own observed
    predecessor closure and requires those closures to be distinct.
    """
    drift: dict[str, Any] = {}

    if first["candidate_name"] != second["candidate_name"]:
        drift["candidate_name"] = {
            "predecessor_a": first["candidate_name"],
            "predecessor_b": second["candidate_name"],
        }

    first_shared = {
        key: first["provenance"][key]
        for key in _SHARED_PROVENANCE
    }
    second_shared = {
        key: second["provenance"][key]
        for key in _SHARED_PROVENANCE
    }
    if first_shared != second_shared:
        drift["shared_provenance"] = {
            key: {
                "predecessor_a": first_shared[key],
                "predecessor_b": second_shared[key],
            }
            for key in _SHARED_PROVENANCE
            if first_shared[key] != second_shared[key]
        }

    first_grid = _normalized_grid(first)
    second_grid = _normalized_grid(second)
    if first_grid != second_grid:
        drift["grid"] = {
            "predecessor_a": first_grid,
            "predecessor_b": second_grid,
        }

    if first["policy"] != second["policy"]:
        drift["policy"] = {
            "predecessor_a": first["policy"],
            "predecessor_b": second["policy"],
        }

    first_candidate_games = first["input_sha256"]["candidate_games"]
    second_candidate_games = second["input_sha256"]["candidate_games"]
    candidate_games_sha256 = outer_hashes["candidate_games"]
    if (
        first_candidate_games != candidate_games_sha256
        or second_candidate_games != candidate_games_sha256
    ):
        drift["candidate_games_sha256"] = {
            "outer_snapshot": candidate_games_sha256,
            "predecessor_a": first_candidate_games,
            "predecessor_b": second_candidate_games,
        }

    first_baseline_name = first["baseline_name"]
    second_baseline_name = second["baseline_name"]
    if first_baseline_name == second_baseline_name:
        drift["baseline_name"] = {
            "error": "predecessor names must be distinct",
            "value": first_baseline_name,
        }

    first_declared_baseline = first["provenance"][
        "baseline_artifact_sha256"
    ]
    second_declared_baseline = second["provenance"][
        "baseline_artifact_sha256"
    ]
    if first_declared_baseline == second_declared_baseline:
        drift["baseline_artifact_sha256"] = {
            "error": "declared predecessor artifacts must be distinct",
            "value": first_declared_baseline,
        }

    first_observed_baseline = outer_hashes["predecessor_a_artifact"]
    second_observed_baseline = outer_hashes["predecessor_b_artifact"]
    if first_observed_baseline == second_observed_baseline:
        drift["observed_baseline_artifact_sha256"] = {
            "error": "observed predecessor artifact bytes must be distinct",
            "value": first_observed_baseline,
        }

    declared_candidate = first_shared["candidate_artifact_sha256"]
    observed_candidate = outer_hashes["candidate_artifact"]
    declared_aliases = []
    if declared_candidate == first_declared_baseline:
        declared_aliases.append("predecessor_a")
    if declared_candidate == second_declared_baseline:
        declared_aliases.append("predecessor_b")
    if declared_aliases:
        drift["declared_candidate_artifact_alias"] = {
            "candidate_artifact_sha256": declared_candidate,
            "aliases": declared_aliases,
        }

    observed_aliases = []
    if observed_candidate == first_observed_baseline:
        observed_aliases.append("predecessor_a")
    if observed_candidate == second_observed_baseline:
        observed_aliases.append("predecessor_b")
    if observed_aliases:
        drift["observed_candidate_artifact_alias"] = {
            "candidate_artifact_sha256": observed_candidate,
            "aliases": observed_aliases,
        }

    if drift:
        raise GateError(
            "dual-predecessor comparison drift: "
            + json.dumps(drift, sort_keys=True, allow_nan=False)
        )

    return {
        "candidate_name": first["candidate_name"],
        "declared_provenance": first_shared,
        "observed_artifact_sha256": {
            "engine_artifact": outer_hashes["engine_artifact"],
            "runner_artifact": outer_hashes["runner_artifact"],
            "candidate_artifact": outer_hashes["candidate_artifact"],
        },
        "candidate_games_sha256": candidate_games_sha256,
        "grid": first_grid,
        "policy": first["policy"],
    }


# Core run_dual_gate resolves this global at call time. Patch only that one
# boundary, then re-export the original CLI/runtime functions unchanged.
_core._validate_cross_comparison = _validate_cross_comparison
run_dual_gate = _core.run_dual_gate
main = _core.main


if __name__ == "__main__":
    raise SystemExit(main())
