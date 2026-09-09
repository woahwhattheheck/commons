# SPDX-License-Identifier: Apache-2.0
"""Default-off evaluator entrypoint for the receding reserve-release candidate."""
from __future__ import annotations

from bootstrap import install_source_paths, load_canonical

install_source_paths()

import reserve_release

reserve_release.install()
_CANONICAL = load_canonical("_sol_level_receding_reserve_candidate")
LAST_TELEMETRY: dict = {}


def agent(observation, configuration=None):
    """Run unchanged canonical Titan with only the guarded feasibility patch."""
    global LAST_TELEMETRY
    output = _CANONICAL.agent(observation, configuration)
    instance = getattr(_CANONICAL, "_INSTANCE", None)
    consumer = getattr(instance, "consumer", None)
    diagnostics = getattr(consumer, "diagnostics", {}) if consumer is not None else {}
    LAST_TELEMETRY = {
        "step": int(observation.get("step", -1)),
        "reserve_release": list(diagnostics.get("reserve_release", []))
        if isinstance(diagnostics, dict)
        else [],
    }
    return output
