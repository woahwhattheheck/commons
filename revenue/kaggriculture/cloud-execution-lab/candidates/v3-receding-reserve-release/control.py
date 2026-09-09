# SPDX-License-Identifier: Apache-2.0
"""Source-tree control entrypoint for exact paired evaluation."""
from __future__ import annotations

from bootstrap import load_canonical

_CANONICAL = load_canonical("_sol_level_receding_reserve_control")


def agent(observation, configuration=None):
    return _CANONICAL.agent(observation, configuration)
