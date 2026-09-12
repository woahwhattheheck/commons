# SPDX-License-Identifier: Apache-2.0
"""R04-EXPANDTAX: BUY_LAND weed-tax gate. Default-OFF (config key r04_expandtax).

Mechanic (verified vs pinned official kaggriculture.py, 2026-09-12):
  * _do_buy_land: unlocks a quadrant, converting every "LOCKED" tile in it to
    None. LAND_ORDER = ["NE", "SW", "SE"], LAND_PRICES = [1000, 2000, 4000].
  * _spawn_weeds: at EOD, for EVERY tile that is None,
    rng.random() < weed_chance (default 0.005) spawns {"kind": "WEED"}.
    "LOCKED" tiles are the string "LOCKED", never None -> exempt from weeds.
  * DIG removes a weed (1 action + travel to reach it); a weeded tile cannot
    be PLANTed until dug -> each weed is a disrupted planting.

Consequence: every expansion permanently adds ~25 tiles of weed-spawn surface.
Measured on the pinned engine (100 seeds x 30 days, 1-quadrant vs 4-quadrant
boards, identical otherwise, carrot-monoculture sweeper policy):
  WEED_TAX_ACTIONS_PER_TILE_DAY = <measured; see MEASUREMENT.md>

Gate rule (the lane):
    expand iff  E  >  W * A  +  C / (T * D)
      E = expected marginal $/tile/day from the new quadrant
          (agent's trailing books: trailing mean of daily net $/planted tile)
      W = measured weed-tax actions per new tile per day (constant above)
      A = trailing net $/action (daily net $ / daily non-PASS actions)
      C = unlock price of the next quadrant
      T = tiles per quadrant (25 on the 10x10 board)
      D = days remaining in the episode

OFF (r04_expandtax absent or anything other than literal True):
filter_market_orders returns the action byte-identical -> OFF == base.

When enabled, the filter deliberately admits at most one BUY_LAND per callback.
The official engine executes market rows sequentially, so multiple BUY_LAND rows
would advance through $1000 -> $2000 -> $4000 prices in one callback.  A single
pre-callback gate verdict cannot safely authorize those later prices.
"""
from __future__ import annotations

TILES_PER_QUADRANT = 25
LAND_ORDER = ("NE", "SW", "SE")
LAND_PRICES = (1000, 2000, 4000)

# Measured on the pinned official engine (2026-09-12; see MEASUREMENT.md):
#   spawn rate on newly unlocked tiles: 0.00460/tile/day (100 seeds x 30 days,
#     'four'-vs-'one' arm delta / 75 new tiles / 30 days; theory 0.00500)
#   clearing cost per spawned weed: 2.83 actions (30 scattered-placement runs,
#     sweeper digs + chase moves, stdev 0.41)
# W = 0.00460 * 2.83 = 0.0130 actions/tile/day.
WEED_TAX_ACTIONS_PER_TILE_DAY = 0.013


def should_expand(unlock_price, expected_dollars_per_tile_day,
                  dollars_per_action, days_remaining):
    """Pure gate rule. True iff the expansion clears its weed tax + amortized cost."""
    try:
        C = float(unlock_price)
        E = float(expected_dollars_per_tile_day)
        A = float(dollars_per_action)
        D = float(days_remaining)
    except (TypeError, ValueError):
        return False
    if not (C > 0 and D > 0 and E > 0):
        return False
    weed_tax_dollars = WEED_TAX_ACTIONS_PER_TILE_DAY * max(0.0, A)
    amortized = C / (TILES_PER_QUADRANT * D)
    return E > weed_tax_dollars + amortized


class TrailingBooks:
    """Trailing 3-day books from daily (money, planted_tiles, actions) notes.

    rev_per_tile_day: trailing mean of max(0, daily net $) / planted tiles.
    dollars_per_action: trailing mean of daily net $ / daily non-PASS actions.
    Both need >= 1 day-over-day delta; before that they read 0.0 (gate blocks).
    """

    WINDOW = 3

    def __init__(self):
        self._days = []  # (money, planted_tiles, actions_total)

    def note_day(self, money, planted_tiles, actions_total):
        self._days.append((float(money), int(planted_tiles), int(actions_total)))
        del self._days[:-self.WINDOW - 1]

    def _deltas(self):
        ds = self._days
        out = []
        for (m1, p1, a1), (m0, p0, a0) in zip(ds[1:], ds[:-1]):
            out.append((m1 - m0, p1, a1 - a0))
        return out

    @property
    def rev_per_tile_day(self):
        ds = self._deltas()
        if not ds:
            return 0.0
        vals = [max(0.0, dm) / max(1, p) for dm, p, _ in ds]
        return sum(vals) / len(vals)

    @property
    def dollars_per_action(self):
        ds = self._deltas()
        if not ds:
            return 0.0
        vals = [dm / max(1, da) for dm, _, da in ds]
        return sum(vals) / len(vals)

    def snapshot(self):
        return {"rev_per_tile_day": self.rev_per_tile_day,
                "dollars_per_action": self.dollars_per_action,
                "days": len(self._days)}


def _farm_of(observation):
    if isinstance(observation, dict):
        if "farm" in observation:
            return observation["farm"]
        farms = observation.get("farms") or []
        player = observation.get("player", 0)
        if farms and 0 <= player < len(farms):
            return farms[player]
    return {}


def _days_remaining(observation, configuration):
    tpd = max(1, int(configuration.get("turnsPerDay", 24)))
    steps = int(configuration.get("episodeSteps", 722))
    total_days = steps // tpd
    if isinstance(observation, dict):
        day = observation.get("day")
        if day is None and observation.get("step") is not None:
            day = int(observation["step"]) // tpd
    else:
        day = 0
    return max(0, total_days - int(day or 0))


def next_unlock_price(observation):
    """Price of the next quadrant, or None when all are unlocked."""
    farm = _farm_of(observation)
    n = len(farm.get("unlocked_quadrants", ["NW"])) - 1
    if n < 0:
        n = 0
    if n >= len(LAND_PRICES):
        return None
    return LAND_PRICES[n]


def _is_buy_land(order):
    return isinstance(order, list) and bool(order) and order[0] == "BUY_LAND"


def _keep_at_most_one_buy_land(market, *, allow_one):
    """Preserve market order and all non-land rows; retain <=1 BUY_LAND."""
    kept = []
    land_kept = False
    for order in market:
        if not _is_buy_land(order):
            kept.append(order)
            continue
        if allow_one and not land_kept:
            kept.append(order)
            land_kept = True
    return kept


def filter_market_orders(action, observation, configuration, books):
    """Gate BUY_LAND safely. OFF is exact identity; enabled admits <=1 land buy."""
    if not isinstance(configuration, dict) or configuration.get("r04_expandtax") is not True:
        return action
    market = (action or {}).get("market") if isinstance(action, dict) else None
    if not market:
        return action
    if not any(_is_buy_land(order) for order in market):
        return action

    price = next_unlock_price(observation)
    if price is None:
        # Nothing left to unlock: strip all no-op BUY_LAND orders.
        kept = _keep_at_most_one_buy_land(market, allow_one=False)
        return {**action, "market": kept} if kept != market else action

    E = books.rev_per_tile_day if books is not None else 0.0
    A = books.dollars_per_action if books is not None else 0.0
    D = _days_remaining(observation, configuration)
    allow_one = should_expand(price, E, A, D)
    kept = _keep_at_most_one_buy_land(market, allow_one=allow_one)

    # Preserve exact object identity when the gate changes nothing (the common
    # single-BUY_LAND allowed case and every unrelated row byte-for-byte).
    if kept == market:
        return action
    out = dict(action)
    out["market"] = kept
    return out
