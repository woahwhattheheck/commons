# SPDX-License-Identifier: Apache-2.0
"""Exact research helper for Kaggriculture end-of-day shop RNG robustness.

The pinned engine constructs one ``random.Random((seed * 1_000_003) ^ day)`` at
end of day.  Before a possible shop unlock it calls ``rng.random()`` exactly
once for every ``None`` tile on player 0's refreshed farm and then player 1's.
There are no other RNG consumers on that path.  The unlock draw is then
``rng.choice(sorted(SHOPS))``.

This module reproduces only that cursor theorem.  It does not alter actions,
predict a rival, infer a probability distribution, or assume any live-only town
shop payout rule.  Callers must supply the complete rival empty-tile delta set
they want certified and the own deltas they have already established as legal.
"""
from __future__ import annotations

import random

from mechanics import SHOPS


ENGINE_SEED_MULTIPLIER = 1_000_003
MAX_SHOP_INSTANCES = 8
DEFAULT_BOARD_SIZE = 10
DEFAULT_UNLOCK_INTERVAL = 3
SHOP_ORDER = tuple(sorted(SHOPS))


def _integer(name, value, *, minimum=None, maximum=None):
    if type(value) is not int:
        raise ValueError(f'{name}_must_be_integer')
    if minimum is not None and value < minimum:
        raise ValueError(f'{name}_below_supported_range')
    if maximum is not None and value > maximum:
        raise ValueError(f'{name}_above_supported_range')
    return value


def count_empty_tiles(farm, board_size=DEFAULT_BOARD_SIZE):
    """Count exact engine weed-RNG consumers: tiles whose value is ``None``."""
    board_size = _integer('board_size', board_size, minimum=1)
    if not isinstance(farm, dict) or not isinstance(farm.get('tiles'), list):
        raise ValueError('missing_farm_tiles')
    rows = farm['tiles']
    if len(rows) != board_size or any(not isinstance(row, list) or len(row) != board_size
                                      for row in rows):
        raise ValueError('unexpected_board_shape')
    return sum(tile is None for row in rows for tile in row)


def shop_after_empty_draws(seed, day, total_empty_tiles, shops=SHOP_ORDER):
    """Replay the exact Python RNG cursor through weeds and one shop choice."""
    _integer('seed', seed)
    day = _integer('day', day, minimum=0)
    total_empty_tiles = _integer('total_empty_tiles', total_empty_tiles, minimum=0)
    shops = tuple(shops)
    if not shops or any(not isinstance(shop, str) or not shop for shop in shops):
        raise ValueError('invalid_shop_order')
    rng = random.Random((seed * ENGINE_SEED_MULTIPLIER) ^ day)
    for _ in range(total_empty_tiles):
        rng.random()
    return rng.choice(shops)


def unlock_shop(seed, day, total_empty_tiles, *, unlock_interval=DEFAULT_UNLOCK_INTERVAL,
                unlocked_count=0, max_shop_instances=MAX_SHOP_INSTANCES,
                shops=SHOP_ORDER):
    """Return the exact unlock draw, or ``None`` when this EOD has no draw."""
    day = _integer('day', day, minimum=0)
    unlock_interval = _integer('unlock_interval', unlock_interval, minimum=1)
    unlocked_count = _integer('unlocked_count', unlocked_count, minimum=0)
    max_shop_instances = _integer('max_shop_instances', max_shop_instances, minimum=0)
    next_day = day + 1
    if next_day <= 0 or next_day % unlock_interval != 0:
        return None
    if unlocked_count >= max_shop_instances:
        return None
    return shop_after_empty_draws(seed, day, total_empty_tiles, shops)


def analyze_robust_shop(seed, day, own_empty_tiles, rival_empty_tiles,
                        own_legal_deltas, rival_bounded_deltas, target_shop, *,
                        board_size=DEFAULT_BOARD_SIZE,
                        unlock_interval=DEFAULT_UNLOCK_INTERVAL,
                        unlocked_count=0,
                        max_shop_instances=MAX_SHOP_INSTANCES,
                        shops=SHOP_ORDER):
    """Certify own cursor choices against every supplied rival empty-count delta.

    A candidate is ``robust`` only when every rival delta in the caller-supplied
    bound produces the same requested ``target_shop``.  The helper intentionally
    does not drop impossible-looking rival rows or manufacture a narrower bound:
    every supplied delta must keep the rival count physically within the board.

    The returned certificate is bounded, not probabilistic.  ``robust`` means
    robust *within the supplied rival delta set* and says nothing about rival
    states omitted by the caller.
    """
    _integer('seed', seed)
    day = _integer('day', day, minimum=0)
    board_size = _integer('board_size', board_size, minimum=1)
    capacity = board_size * board_size
    own_empty_tiles = _integer('own_empty_tiles', own_empty_tiles,
                               minimum=0, maximum=capacity)
    rival_empty_tiles = _integer('rival_empty_tiles', rival_empty_tiles,
                                 minimum=0, maximum=capacity)
    unlock_interval = _integer('unlock_interval', unlock_interval, minimum=1)
    unlocked_count = _integer('unlocked_count', unlocked_count, minimum=0)
    max_shop_instances = _integer('max_shop_instances', max_shop_instances, minimum=0)

    shops = tuple(shops)
    if target_shop not in shops:
        raise ValueError('target_shop_not_in_engine_order')
    if not isinstance(own_legal_deltas, (list, tuple, set)) or not own_legal_deltas:
        raise ValueError('own_legal_deltas_required')
    if not isinstance(rival_bounded_deltas, (list, tuple, set)) or not rival_bounded_deltas:
        raise ValueError('rival_bounded_deltas_required')
    own_deltas = sorted({_integer('own_delta', value) for value in own_legal_deltas})
    rival_deltas = sorted({_integer('rival_delta', value) for value in rival_bounded_deltas})

    next_day = day + 1
    unlock_due = (next_day > 0 and next_day % unlock_interval == 0
                  and unlocked_count < max_shop_instances)
    report = {
        'seed': seed,
        'day': day,
        'next_day': next_day,
        'target_shop': target_shop,
        'unlock_due': unlock_due,
        'unlock_interval': unlock_interval,
        'unlocked_count': unlocked_count,
        'max_shop_instances': max_shop_instances,
        'own_empty_tiles': own_empty_tiles,
        'rival_empty_tiles': rival_empty_tiles,
        'own_legal_deltas': own_deltas,
        'rival_bounded_deltas': rival_deltas,
        'robust_within_supplied_rival_bound': [],
        'candidates': [],
        'probability_model_used': False,
        'live_shop_payout_model_used': False,
    }
    if not unlock_due:
        report['reason'] = ('shop_instance_cap_reached'
                            if unlocked_count >= max_shop_instances
                            else 'not_shop_unlock_day')
        return report

    # Validate every supplied rival state up front.  Silently omitting an invalid
    # member would make the reported robustness stronger than the caller's bound.
    rival_counts = {}
    for delta in rival_deltas:
        count = rival_empty_tiles + delta
        if not 0 <= count <= capacity:
            raise ValueError('rival_delta_outside_board_capacity')
        rival_counts[delta] = count

    for own_delta in own_deltas:
        own_count = own_empty_tiles + own_delta
        if not 0 <= own_count <= capacity:
            raise ValueError('own_delta_outside_board_capacity')
        outcomes = []
        for rival_delta in rival_deltas:
            rival_count = rival_counts[rival_delta]
            total = own_count + rival_count
            shop = shop_after_empty_draws(seed, day, total, shops)
            outcomes.append({
                'rival_delta': rival_delta,
                'rival_empty_tiles': rival_count,
                'total_empty_tiles': total,
                'shop': shop,
            })
        observed = sorted({item['shop'] for item in outcomes})
        robust = len(observed) == 1 and observed[0] == target_shop
        candidate = {
            'own_delta': own_delta,
            'own_empty_tiles': own_count,
            'outcomes': outcomes,
            'distinct_shops': observed,
            'invariant_shop': observed[0] if len(observed) == 1 else None,
            'robust': robust,
        }
        report['candidates'].append(candidate)
        if robust:
            report['robust_within_supplied_rival_bound'].append(own_delta)

    report['reason'] = ('robust_target_found'
                        if report['robust_within_supplied_rival_bound']
                        else 'no_target_robust_to_supplied_rival_bound')
    return report
