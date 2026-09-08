# SPDX-License-Identifier: Apache-2.0
"""Opt-in CEDAR funding selection over the existing integrated TITAN agent.

Run from a repository checkout with cloud-execution-lab beside this directory.
This is a research variant, not a replacement for the frozen selected archive.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'cloud-execution-lab'
for directory in (HERE, LAB):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from integrated_selected import absolute_step, make_agent as _make_integrated
from seed_funding import select_seed_queue


def make_agent(production=None, *, funded=True, seed=True, committed=True,
               sell=True, horizon=8):
    """Reuse one producer; funded=False is the unchanged integrated control.

    The selector only handles proposals the original route-demand stage allows.
    It does not create seeds, change worker routes, or infer rival inventories.
    """
    return _make_integrated(
        production, seed=seed, committed=committed, sell=sell, horizon=horizon,
        seed_queue_selector=select_seed_queue if funded else None)


_INSTANCE = None


def agent(observation, configuration=None):
    global _INSTANCE
    configuration = dict(configuration or {})
    if _INSTANCE is None or absolute_step(observation, configuration) == 0:
        _INSTANCE = make_agent()
    return _INSTANCE.act(observation, configuration)
