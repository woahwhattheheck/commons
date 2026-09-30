# SPDX-License-Identifier: Apache-2.0
"""Component tests for the Antigravity melon planting-budget guard."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from melon_planting_budget import (
    MELON_LIFETIME_UNIT_CAP,
    MELON_UNITS_PER_PLANT,
    filter_proposals,
    lifetime_melon_sold,
    max_melon_plants,
    plants_blocked,
    remaining_melon_budget,
)


def obs(step=0, inv=10000, player=0, counters=None):
    farms = [{'sale_counters': counters or {}}]
    return {'player': player, 'step': step, 'farms': farms,
            'market': {'inventory': {'MELON': inv}}}


def test_budget_starts_full():
    assert remaining_melon_budget(obs()) == MELON_LIFETIME_UNIT_CAP


def test_counter_preferred_over_drift():
    o = obs(step=720, inv=10100, counters={'MELON': 12})
    assert lifetime_melon_sold(o) == 12


def test_drift_reconstruction_conservative():
    # inv +100 with 720 steps: town ate 30, so drift 100 + 30 eaten = 130 sold.
    assert lifetime_melon_sold(obs(step=720, inv=10100)) == 130


def test_filter_blocks_over_budget():
    o = obs(step=720, inv=10100)  # budget exhausted
    props = [{'crop': 'MELON', 'size': 4}, {'crop': 'WHEAT', 'size': 9}]
    out = filter_proposals(props, o)
    assert len(out) == 1 and out[0]['crop'] == 'WHEAT'


def test_filter_shrinks_to_budget():
    o = obs()  # 28 budget -> 4 plants at 6 units
    props = [{'crop': 'MELON', 'size': 10}]
    out = filter_proposals(props, o)
    assert out[0]['size'] == 4


def test_non_melon_passthrough():
    o = obs(step=720, inv=10100)
    props = [{'crop': 'TOMATO', 'size': 5}, 'not-a-dict']
    assert filter_proposals(props, o) == props


def test_plants_blocked_math():
    o = obs()
    assert plants_blocked(o, 10) == 10 - max_melon_plants(o)
    assert plants_blocked(o, 0) == 0
