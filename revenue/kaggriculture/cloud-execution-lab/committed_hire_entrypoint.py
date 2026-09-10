# SPDX-License-Identifier: Apache-2.0
"""Executable candidate: canonical TITAN plus committed-HIRE solvency and arity."""
from __future__ import annotations

import committed_hire

# Install before main imports/constructs the frozen consumer.
committed_hire.install()

import main as canonical_main  # noqa: E402


def agent(observation, configuration=None):
    selected = canonical_main.agent(observation, configuration)
    return committed_hire.normalize_actor_arity(selected, observation)
