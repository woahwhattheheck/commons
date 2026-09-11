# SPDX-License-Identifier: Apache-2.0
"""V4 S6: idle-capacity ROI targets for the already-shipped fertilizer hand.

S6 does *not* create a hand, buy fertilizer, change the fert-hand hire test, or
change how much fertilizer that hand picks up. Once the existing r04_fert_hand
has already been hired and is carrying fertilizer, S6 may spend otherwise-idle
capacity on additional productive crops.

The incumbent hand owns CARROT. S6 therefore falls back to incumbent routing
whenever a current or authored-later CARROT obligation exists. Only when that
queue is empty does S6 consider:
- WHEAT annual-crop opportunities under the same marginal-yield calculation;
- TOMATO when tonight's production bonus is already guaranteed by a completed
  WATER, fertilizer coverage is absent, held yield has >=2 units of headroom,
  and the existing hand can reach and FERTILIZE the tile before EOD.

All candidate work must be reachable before this day-scoped hand resets at EOD,
and new WHEAT marginal yield is clipped to the official episode's last
actionable day so post-episode WATER is never priced as productive work.
Incumbent CARROT reservation deliberately mirrors the baseline's un-clipped,
price-independent target rule so S6 never steals an obligation the shipped
router would service. Malformed public state returns ``None`` so the caller
preserves incumbent CARROT-only behavior.
"""
from __future__ import annotations

from typing import Any

TURNS_PER_DAY = 24
EPISODE_STEPS = 720
BOARD_SIZE = 10
# The pinned interpreter marks DONE after processing step episodeSteps-2, so the
# last executable action belongs to day 29 under the standard 24-turn day.
FINAL_ACTION_DAY = (EPISODE_STEPS - 2) // TURNS_PER_DAY
ANNUAL = {
    "WHEAT": (2, 4, 6),
    "CARROT": (2, 3, 4),
}
TOMATO_FIRST_YIELD_DAY = 8
TOMATO_INTERVAL = 1
TOMATO_MAX_YIELD = 4

REPORT = {
    "choices": 0,
    "fertilize_requests": 0,
    "choice_by_crop": {"WHEAT": 0, "CARROT": 0, "TOMATO": 0},
}


def _plain_int(value: Any, *, minimum: int | None = None) -> bool:
    return type(value) is int and (minimum is None or value >= minimum)


def standard_configuration(configuration: Any) -> bool:
    """S6's calendar/geometry theorem is valid only on the pinned field config."""
    if configuration is None:
        return False
    expected = {
        "episodeSteps": EPISODE_STEPS,
        "turnsPerDay": TURNS_PER_DAY,
        "boardSize": BOARD_SIZE,
    }
    try:
        for name, value in expected.items():
            actual = configuration.get(name) if isinstance(configuration, dict) else getattr(configuration, name)
            if type(actual) is not int or actual != value:
                return False
    except (KeyError, TypeError, AttributeError):
        return False
    return True


def _annual_gain(
    tile: dict[str, Any],
    day: int,
    crop: str,
    *,
    clip_to_episode: bool,
) -> int | None:
    """Annual marginal units, with optional horizon clipping for new S6 work."""
    first, last, cap = ANNUAL[crop]
    planted = tile.get("planted_day")
    covered = tile.get("fertilized_until_day")
    have = tile.get("yield_units")
    watered = tile.get("watered_today")
    if (
        not _plain_int(planted, minimum=0)
        or not _plain_int(covered)
        or not _plain_int(have, minimum=0)
        or have > cap
        or type(watered) is not bool
    ):
        return None
    start = planted + (last + 1) // 2
    end = planted + last
    waters = [
        w for w in range(start, end + 1)
        if (not clip_to_episode or w <= FINAL_ACTION_DAY)
        and (w > day or (w == day and not watered))
    ]
    if not waters:
        return 0
    base = min(cap, have + sum(2 if w <= covered else 1 for w in waters))
    cover = max(covered, day + 2)
    fertilized = min(cap, have + sum(2 if w <= cover else 1 for w in waters))
    return max(0, fertilized - base)


def _tomato_gain(tile: dict[str, Any], day: int) -> int | None:
    """Guaranteed marginal units at tonight's ongoing TOMATO refresh only."""
    planted = tile.get("planted_day")
    covered = tile.get("fertilized_until_day")
    have = tile.get("yield_units")
    watered = tile.get("watered_today")
    if (
        not _plain_int(planted, minimum=0)
        or not _plain_int(covered)
        or not _plain_int(have, minimum=0)
        or have > TOMATO_MAX_YIELD
        or type(watered) is not bool
    ):
        return None
    # Ongoing-crop fertilizer is evaluated at EOD, so fertilizer applied after
    # today's WATER still boosts tonight. Requiring watered=True makes the +1
    # independent of any prediction about later parent commands.
    if not watered or covered >= day or have > TOMATO_MAX_YIELD - 2:
        return 0
    next_day = day + 1
    days_since_first = next_day - planted - TOMATO_FIRST_YIELD_DAY
    if days_since_first < 0 or days_since_first % TOMATO_INTERVAL:
        return 0
    production_count = days_since_first // TOMATO_INTERVAL + 1
    if not (1 <= production_count <= TOMATO_MAX_YIELD):
        return 0
    return 1


def _state(observation: Any):
    if not isinstance(observation, dict):
        return None
    step = observation.get("step")
    player = observation.get("player")
    farms = observation.get("farms")
    market = observation.get("market")
    if (
        not _plain_int(step, minimum=0)
        or type(player) is not int
        or not isinstance(farms, list)
        or not (0 <= player < len(farms))
        or not isinstance(market, dict)
    ):
        return None
    farm = farms[player]
    prices = market.get("prices")
    if not isinstance(farm, dict) or not isinstance(prices, dict):
        return None
    tiles = farm.get("tiles")
    if (
        not isinstance(tiles, list)
        or len(tiles) != BOARD_SIZE
        or any(not isinstance(row, list) or len(row) != BOARD_SIZE for row in tiles)
    ):
        return None
    for crop in ("WHEAT", "CARROT", "TOMATO"):
        if not _plain_int(prices.get(crop), minimum=0):
            return None
    return step // TURNS_PER_DAY, tiles, prices


def _current_targets(observation: Any):
    parsed = _state(observation)
    if parsed is None:
        return None
    day, tiles, prices = parsed
    targets = []
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                continue
            crop = tile.get("crop")
            if crop == "CARROT":
                # Reservation must mirror the incumbent hand, including its
                # un-clipped calendar and price-independent target decision.
                gain = _annual_gain(tile, day, crop, clip_to_episode=False)
                if gain is None:
                    return None
                if gain > 0:
                    targets.append((x, y, crop, gain, gain * prices[crop]))
                continue
            if crop == "WHEAT":
                gain = _annual_gain(tile, day, crop, clip_to_episode=True)
            elif crop == "TOMATO":
                gain = _tomato_gain(tile, day)
            else:
                continue
            if gain is None:
                return None
            if gain <= 0:
                continue
            value = gain * prices[crop]
            if value > 0:
                targets.append((x, y, crop, gain, value))
    return targets


def choose_fert_hand_target(observation: Any, pos: Any, upcoming=()):
    """Return an idle-capacity target, or None to preserve incumbent routing."""
    parsed = _state(observation)
    if parsed is None or not isinstance(pos, tuple) or len(pos) != 2:
        return None
    if (
        type(pos[0]) is not int
        or type(pos[1]) is not int
        or not (0 <= pos[0] < BOARD_SIZE)
        or not (0 <= pos[1] < BOARD_SIZE)
    ):
        return None
    day, _, _ = parsed
    targets = _current_targets(observation)
    if targets is None:
        return None

    # CARROT is incumbent r04_fert_hand work. S6 is deliberately subordinate:
    # any current positive-gain CARROT returns control to the exact baseline
    # target/fertilize path instead of reprioritizing already-proven work.
    if any(target[2] == "CARROT" for target in targets):
        return None

    # r04_fert_hand._upcoming emits authored CARROT plantings that become
    # incumbent targets on the next callback. A positive upcoming obligation
    # also reserves the hand/fertilizer for baseline; malformed look-ahead
    # fails closed rather than widening S6.
    try:
        for item in upcoming or ():
            if not isinstance(item, (tuple, list)) or len(item) < 2:
                return None
            x, y = item[0], item[1]
            gain = item[2] if len(item) >= 3 else 1
            if (
                not _plain_int(x, minimum=0)
                or not _plain_int(y, minimum=0)
                or x >= BOARD_SIZE
                or y >= BOARD_SIZE
            ):
                return None
            if not _plain_int(gain, minimum=0):
                return None
            if gain > 0:
                return None
    except Exception:
        return None

    px, py = pos
    # A day-scoped hand must be able to spend movement callbacks plus the final
    # FERTILIZE callback before EOD. This is mandatory for every S6 target: an
    # unreachable annual target is not productive idle-capacity work either.
    step = observation["step"]
    turns_left = TURNS_PER_DAY - (step % TURNS_PER_DAY)
    targets = [
        target for target in targets
        if target[2] != "CARROT"
        and abs(px - target[0]) + abs(py - target[1]) + 1 <= turns_left
    ]
    if not targets:
        return None

    def key(target):
        x, y, crop, gain, value = target
        distance = abs(px - x) + abs(py - y)
        # This branch is reachable only after r04_fert_hand has an existing hand
        # with held fertilizer. No hire/buy/pickup decision is made here.
        return (value / float(distance + 1), value, -distance, gain, -y, -x, crop)

    x, y, crop, gain, value = max(targets, key=key)
    distance = abs(px - x) + abs(py - y)
    REPORT["choices"] += 1
    REPORT["choice_by_crop"][crop] += 1
    return {
        "position": (x, y),
        "crop": crop,
        "marginal_units": gain,
        "marginal_value": value,
        "distance": distance,
        "day": day,
    }


def record_fertilize(target: Any) -> None:
    if isinstance(target, dict) and target.get("crop") in REPORT["choice_by_crop"]:
        REPORT["fertilize_requests"] += 1
