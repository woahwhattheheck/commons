# SPDX-License-Identifier: Apache-2.0
"""Thin research-only P02 wrapper over an exact production-v3 package."""
from __future__ import annotations

import baseline_main as baseline
import goose_capacity_economy as p02


def agent(observation, configuration=None):
    action = baseline.agent(observation, configuration)
    return p02.apply_goose_capacity_economy(
        action, observation, configuration, enabled=True
    )
