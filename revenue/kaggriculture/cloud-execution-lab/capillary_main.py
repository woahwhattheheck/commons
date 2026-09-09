# SPDX-License-Identifier: Apache-2.0
"""Canonical whole-call entrypoint for the isolated Capillary candidate."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _load_control_main():
    path = HERE / "main.py"
    spec = importlib.util.spec_from_file_location(
        "_sol_janus_capillary_exact_control_main",
        path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import exact control entrypoint: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_CONTROL_MAIN = _load_control_main()


def _new_instance(root, feature_data):
    """Replace only construction inside the exact canonical outer entrypoint."""
    from titan_capillary import CapillaryTitanAgent
    from titan_runtime import Features, load

    features = Features(**feature_data)
    admission = None
    if features.fourth_quadrant:
        source = root / "funded_payback.py"
        if not source.is_file():
            source = root / "../cloud-economic-stress/funded_payback/funded_payback.py"
        module = load("_titan_capillary_funded_payback", source, cache=True)
        adapter = load(
            "_titan_capillary_funded_payback_runtime",
            root / "funded_payback_runtime.py",
            cache=True,
        )
        admission = adapter.make_admission(module.FundedPaybackAdmission)(
            seconds=features.budget_seconds,
            max_proposals=24,
        )
    return CapillaryTitanAgent(
        features,
        fourth_quadrant_admission=admission,
    )


# Reuse canonical configuration loading, singleton/reset semantics, completed
# fallback selection, and the whole-call deadline. Only the runtime factory is
# replaced inside this candidate-local module instance.
_CONTROL_MAIN._new_instance = _new_instance


def agent(observation, configuration=None):
    return _CONTROL_MAIN.agent(observation, configuration)
