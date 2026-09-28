# SPDX-License-Identifier: Apache-2.0
"""S02 guard wrapper around the unchanged canonical TITAN entrypoint.

Default behavior is shadow-only. Set TITAN_MPC_MODE=execute only for an
admitted experimental package with the required paired scenario provider and
full official-engine game receipt.
"""
import os

from canonical_main import agent as _canonical_agent
from planner_mpc import Planner

_H = int(os.environ.get("TITAN_MPC_H", "12"))
_BUDGET = float(os.environ.get("TITAN_MPC_BUDGET", "0.08"))
_PLANNER = Planner(_canonical_agent, horizon=_H, budget_s=_BUDGET)


def agent(observation, configuration=None):
    return _PLANNER.act(observation, configuration)
