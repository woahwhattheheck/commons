# SPDX-License-Identifier: Apache-2.0
"""Melon planting-budget guard (Antigravity evidence lane).

SCOPED THEOREM (narrowed per red-team review on PR #12947):
This module is a *fourth_quadrant planting-proposal budget guard*. It is NOT a
lifetime sales hard-cap: it filters planting proposals only, has no seller-side
enforcement, and does not cover other melon producers. The broader "lifetime
melon sales cap" framing from the original Antigravity dump is evidence-only
until runtime-wide producer coverage exists.

MECHANICS (verified vs pinned official kaggriculture.py 2026-09-12):
- MELON MARKET_PARAMS: base=250, I0=10000, above_func='sq', above_target=3.6.
- NO shop in SHOPS consumes MELON. _town_consume takes exactly 1 unit of each
  TOWN_CENTER_PRODUCTS every 24 steps (~28-29 melons per 720-step game).
- Every melon sold above the town trickle PERMANENTLY raises market inventory:
    lifetime sold  28 -> net inv ~10004 -> price ~$250 (safe)
    lifetime sold  50 -> net inv ~10026 -> price ~$243
    lifetime sold 100 -> net inv ~10076 -> price ~$192
    lifetime sold 150 -> net inv ~10126 -> price ~$91
    lifetime sold 200 -> net inv ~10176 -> price ~$1 (floor, permanent)
- A single 5x5 melon harvest (~150 units) destroys the melon price for the
  rest of the game. Melon must never be a scale cash crop.

POLICY: cap PLANTINGS so expected harvest stays within the town-center
trickle budget. Blocked/shrunk proposals are left for the scheduler's normal
crop choice; this guard does not redirect to any specific crop.

HARM RECEIPT (full-pipeline variant, do not re-run blind):
A separate full-pipeline variant that additionally REDIRECTED overflow melon
plantings to strawberry measured HARDENED-GATE REJECT: mean dM -22355,
stdev 21211, SE 5303, 16/16 stable, 16/16 engaged, 2/16 positive. The redirect
variant is dead. This evidence-only guard ships source custody default-OFF;
any runtime activation needs its own gate.

Default OFF. OFF == base behavior exactly (this module is not even called).
"""

from __future__ import annotations

# Lifetime melon units the market can absorb without price damage.
# == town-center consumption over a full game (1 per 24 steps, 720 steps).
MELON_LIFETIME_UNIT_CAP = 28

# Expected units per planted melon tile (engine max_yield; fourth_quadrant
# books 5/tile — use the conservative engine figure for the budget).
MELON_UNITS_PER_PLANT = 6


def _as_int(value, default=0):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return n if n >= 0 else default


def lifetime_melon_sold(observation):
    """Best-effort count of melon units already sold this game.

    Prefers an explicit receipt counter when the runtime tracks one;
    otherwise reconstructs from market inventory drift vs the town trickle.
    """
    player = int(observation.get('player', 0))
    farm = (observation.get('farms') or [{}])[player]
    counters = farm.get('sale_counters') or {}
    if 'MELON' in counters:
        return _as_int(counters['MELON'])
    market = ((observation.get('market') or {}).get('inventory')) or {}
    try:
        inv = int(market.get('MELON', 10000))
    except (TypeError, ValueError):
        return 0
    step = _as_int(observation.get('step'))
    town_eaten = step // 24  # 1 per day via _town_consume
    # Opponent sales also raise inventory; attributing all drift to us is
    # conservative (shrinks our budget) — safe direction for a cap.
    return max(0, inv - 10000 + town_eaten)


def remaining_melon_budget(observation, cap=MELON_LIFETIME_UNIT_CAP):
    """Melon units we may still sell without crashing the price."""
    return max(0, int(cap) - lifetime_melon_sold(observation))


def max_melon_plants(observation, cap=MELON_LIFETIME_UNIT_CAP):
    """How many more melon tiles may be planted under the cap."""
    return remaining_melon_budget(observation, cap) // MELON_UNITS_PER_PLANT


def filter_proposals(proposals, observation, cap=MELON_LIFETIME_UNIT_CAP):
    """Drop or shrink MELON planting proposals that breach the lifetime cap.

    `proposals` is an iterable of dicts with at least 'crop' and a tile count
    under 'tiles' (list) or 'size' (int). Returns a new list; non-melon
    proposals pass through untouched. OFF callers must not call this.
    """
    budget = max_melon_plants(observation, cap)
    out = []
    for p in proposals:
        if not isinstance(p, dict) or p.get('crop') != 'MELON':
            out.append(p)
            continue
        tiles = p.get('tiles')
        size = len(tiles) if isinstance(tiles, (list, tuple)) else _as_int(p.get('size'))
        if budget <= 0 or size <= 0:
            continue  # over budget: no melon planting
        if size <= budget:
            out.append(p)
            continue
        # Shrink the proposal to fit the remaining budget.
        shrunk = dict(p)
        if isinstance(tiles, (list, tuple)):
            shrunk['tiles'] = list(tiles)[:budget]
        else:
            shrunk['size'] = budget
        if 'seed_units' in shrunk:
            try:
                shrunk['seed_units'] = int(shrunk['seed_units']) * budget // max(1, size)
            except (TypeError, ValueError):
                pass
        out.append(shrunk)
        budget = 0
    return out


def plants_blocked(observation, planned_melon_plants, cap=MELON_LIFETIME_UNIT_CAP):
    """Number of planned melon plants that must be refused under the cap."""
    return max(0, _as_int(planned_melon_plants) - max_melon_plants(observation, cap))
