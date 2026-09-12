# SPDX-License-Identifier: Apache-2.0
"""Regression contract for exact TITAN runtime feature types.

Run under both normal Python and ``python -O``: these checks protect runtime
policy authorization and therefore must not depend on optimization-removable
assertions in production code.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from titan_runtime import Features


HERE = Path(__file__).resolve().parent
BOOL_FIELDS = (
    'seed', 'funding', 'redundant_hire', 'terminal_route', 'committed',
    'terminal_history', 'spatial_pathing', 'spatial_tempo', 'fourth_quadrant',
    'market_pressure', 'committed_seed_retry', 'operating_stock',
    'idle_fertilizer', 'crop_release', 'early_capital',
)


def must_reject(name, thunk):
    try:
        thunk()
    except (TypeError, ValueError):
        return
    raise AssertionError(f'{name}: malformed feature value was accepted')


def canonical_features():
    raw = json.loads((HERE / 'TITAN-CONFIG.json').read_text())
    # main.py owns this top-level integration switch; Features owns the rest.
    raw.pop('town_procurement', None)
    return Features(**raw)


def main():
    canonical = canonical_features()
    if canonical.consumer != 'frozen' or canonical.budget_seconds != 1.0:
        raise AssertionError('canonical TITAN-CONFIG changed while constructing Features')

    # Every policy switch is an exact bool.  Truthy strings/integers/containers
    # must not silently authorize or disable behavior.
    aliases = ('false', 1, 0, [], {})
    for field in BOOL_FIELDS:
        for alias in aliases:
            must_reject(f'{field}={alias!r}',
                        lambda field=field, alias=alias: replace(canonical, **{field: alias}))

    # Deadline arithmetic accepts ordinary finite int/float values, but never
    # bool aliases, strings, NaN or infinities.
    replace(canonical, budget_seconds=1, reserve_seconds=0)
    for field, bad_values in (
        ('budget_seconds', (False, '1.0', float('nan'), float('inf'), -float('inf'))),
        ('reserve_seconds', (False, '0.01', float('nan'), float('inf'), -float('inf'))),
    ):
        for value in bad_values:
            must_reject(f'{field}={value!r}',
                        lambda field=field, value=value: replace(canonical, **{field: value}))

    # Optional history hypotheses are a real dictionary or None; tie-break is
    # a string.  Existing semantic checks still decide whether a validly typed
    # value is compatible with terminal-history mode.
    replace(canonical, history_hypotheses={})
    replace(canonical, history_hypotheses=None)
    for value in ([], (), 'baseline', 1, False):
        must_reject(f'history_hypotheses={value!r}',
                    lambda value=value: replace(canonical, history_hypotheses=value))
    for value in (None, 1, False, [], {}):
        must_reject(f'terminal_tie_break={value!r}',
                    lambda value=value: replace(canonical, terminal_tie_break=value))

    # Preserve existing semantic/range contracts after the new type boundary.
    must_reject('unknown consumer', lambda: replace(canonical, consumer='unknown'))
    must_reject('invalid deadline ordering',
                lambda: replace(canonical, reserve_seconds=0.5, budget_seconds=0.5))
    must_reject('terminal history missing hypotheses',
                lambda: replace(canonical, terminal_history=True, history_hypotheses=None))

    print('feature-type-exactness: PASS')


if __name__ == '__main__':
    main()
