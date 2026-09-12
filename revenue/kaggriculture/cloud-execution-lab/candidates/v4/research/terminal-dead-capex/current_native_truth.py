#!/usr/bin/env python3
"""Authenticated truth-scope wrapper for DEADCAP's current-native probe.

The historical donor theorem lives in :mod:`deadcap_oracle`.  This module owns
only the current-production evidence boundary: authenticate the exact production
bytes *before* importing/replaying them, then describe the one measured cell
without promoting that observation into a global COLD claim.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import deadcap_oracle as donor

SCHEMA = "titan-v4-deadcap-current-native-truth/v1"
DISPOSITION = "ONE_CELL_DONOR_WITNESS_ABSENT_GENERAL_ENGAGEMENT_UNMEASURED"


def authenticated_single_cell_probe(
    runtime_root: Path,
    engine: Any,
    tapes: Any,
    *,
    seed: int = 0,
    rival_tape: int = 0,
) -> dict[str, Any]:
    """Run the historical current-native probe only after exact byte custody.

    This deliberately does *not* claim that DEADCAP is globally cold.  The
    inherited probe observes seat 0, one seed/opponent cell, and one exact donor
    witness row at step 284.  A global COLD conclusion requires a separate
    current-native census that detects dead seed acquisitions generically.
    """
    source_auth = donor.authenticate_current(runtime_root)
    probe = donor.current_native_probe(
        runtime_root,
        engine,
        tapes,
        seed=seed,
        rival_tape=rival_tape,
    )
    if probe.get("seat") != 0:
        raise RuntimeError(f"unexpected inherited probe seat: {probe.get('seat')!r}")
    if probe.get("seed") != seed or probe.get("rival_tape") != rival_tape:
        raise RuntimeError("inherited probe scope mismatch")
    if probe.get("step") != donor.WITNESS["step"]:
        raise RuntimeError(f"unexpected inherited probe step: {probe.get('step')!r}")

    return {
        "schema": SCHEMA,
        "source_auth": source_auth,
        "scope": {
            "seat": 0,
            "seed": seed,
            "rival_tape": rival_tape,
            "step": donor.WITNESS["step"],
            "detection": "exact donor row equality only",
        },
        "probe": probe,
        "general_dead_seed_engagement_cold_proven": False,
        "disposition": DISPOSITION,
    }
