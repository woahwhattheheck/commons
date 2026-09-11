#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-package H10 evaluator entrypoint.

This file is a *template*: ``materialize_h10_e11_r04_candidate.py`` copies it beside
an already-built V3.1 package's ``main.py`` as ``h10_candidate.py``. Loading that
copy preserves the package's live entrypoint/config and wraps it with the reviewed
H10 debt-aware E11 adapter using the exact seller callback object
``scheduler.absorption`` used by the canonical pre-pending E11 seam.

It is intentionally not importable in the source checkout, where the canonical
package modules do not exist. That fail-closed boundary prevents a source-only
semantic mirror from being mislabeled as the executable carrier.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REQUIRED_PACKAGE_FILES = (
    "main.py",
    "scheduler.py",
    "r04_full_router.py",
    "e11_rival_sell.py",
    "TITAN-CONFIG.json",
    "h10_e11_r04_reachability.py",
)
missing = [name for name in REQUIRED_PACKAGE_FILES if not (ROOT / name).is_file()]
if missing:
    raise RuntimeError(
        "H10 candidate must be materialized beside an exact V3.1 package: missing "
        + ", ".join(missing)
    )

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED_CONFIG = {
    "e11_rival_sell": False,
    "r04_sale_window": True,
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
}
config = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
for key, expected in EXPECTED_CONFIG.items():
    if key not in config:
        raise RuntimeError(f"H10 candidate package missing config key {key}")
    actual = config[key]
    if type(actual) is not type(expected) or actual != expected:
        raise RuntimeError(
            f"H10 candidate config mismatch for {key}: {actual!r} != {expected!r}"
        )

# Load the untouched package entrypoint by exact path under a private module name.
# Do not ``import main``: some evaluator loaders name the candidate module ``main``,
# which would create a circular/self import instead of loading the baseline file.
_parent_spec = importlib.util.spec_from_file_location("_h10_v31_parent_main", ROOT / "main.py")
if _parent_spec is None or _parent_spec.loader is None:
    raise RuntimeError("cannot load exact parent main.py")
live_main = importlib.util.module_from_spec(_parent_spec)
_parent_spec.loader.exec_module(live_main)

import scheduler  # noqa: E402
import h10_e11_r04_reachability as h10  # noqa: E402

ABSORPTION_FN = scheduler.absorption
if getattr(ABSORPTION_FN, "__module__", None) != "scheduler":
    raise RuntimeError("canonical E11 absorption callback is not scheduler.absorption")

E11_PARAMS = {
    "rival_dump_price_drop": 15.0,
    "rival_dump_lookback_steps": 8,
    "e11_min_future_absorption": 2,
}

agent = h10.wrap_r04_agent(
    live_main.agent,
    ABSORPTION_FN,
    enabled=True,
    params=E11_PARAMS,
)


def _sha256(name: str) -> str:
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


CUSTODY = {
    "schema": "titan-v31-h10-e11-r04-candidate/v1",
    "parent_entrypoint": "main.py:agent (exact-path private load)",
    "absorption_callable": "scheduler.absorption",
    "baseline_config": dict(EXPECTED_CONFIG),
    "e11_params": dict(E11_PARAMS),
    "main_sha256": _sha256("main.py"),
    "scheduler_sha256": _sha256("scheduler.py"),
    "r04_sha256": _sha256("r04_full_router.py"),
    "config_sha256": _sha256("TITAN-CONFIG.json"),
    "h10_adapter_sha256": _sha256("h10_e11_r04_reachability.py"),
    "truth_boundary": (
        "execution-custody carrier only; H10 wraps the live package entrypoint after "
        "its parent call; economics and deadline-fidelity remain official-gate evidence"
    ),
}
agent.h10_custody = CUSTODY
