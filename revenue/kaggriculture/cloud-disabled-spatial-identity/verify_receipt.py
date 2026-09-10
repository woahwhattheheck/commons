#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the compact, non-secret causal receipt committed beside this file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_cell(cell: dict[str, Any]) -> None:
    baseline = cell["terminal"]["v1"]
    bad = cell["terminal"]["v2_core_disabled_flags_bad"]
    patched = cell["terminal"]["v2_core_guarded"]

    require(patched["scores"] == baseline["scores"], "patched scores do not match V1")
    require(
        patched["trace_sha256"] == baseline["trace_sha256"],
        "patched official trace does not match V1",
    )
    require(
        bad["scores"] != baseline["scores"] and bad["trace_sha256"] != baseline["trace_sha256"],
        "bad core does not demonstrate the regression",
    )

    prefix = cell["prefix_through_step_96"]
    require(prefix["v2_core_guarded_sha256"] == prefix["v1_sha256"], "patched prefix differs")
    require(prefix["v2_core_bad_sha256"] != prefix["v1_sha256"], "bad prefix unexpectedly matches")
    require(prefix["rows"] == 97, "prefix must include steps 0 through 96")

    divergence = cell["causal_chain"]
    require(divergence["first_action_divergence"]["step"] == 30, "unexpected first divergence")
    require(divergence["cash_threshold_divergence"]["step"] == 88, "unexpected cash divergence")
    require(divergence["cash_threshold_divergence"]["v1_after"] - divergence["cash_threshold_divergence"]["bad_after"] == 304, "cash gap is not $304")
    require(divergence["day_end_confirmation"]["v1_bank"] - divergence["day_end_confirmation"]["bad_bank"] == 304, "step-95 gap is not $304")


def main() -> int:
    receipt = json.loads((ROOT / "receipt.json").read_text(encoding="utf-8"))
    require(receipt["schema_version"] == 1, "unsupported receipt schema")
    require(receipt["scope"]["fresh_seed_cells"] == 0, "receipt must remain spent-cell-only")
    require(receipt["patch"]["bad_spatial_tempo_sha256"] != receipt["patch"]["guarded_spatial_tempo_sha256"], "patch did not change source")
    for cell in receipt["witnesses"]:
        verify_cell(cell)
    print(json.dumps({"pass": True, "witnesses": len(receipt["witnesses"]), "claim": receipt["claim"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
