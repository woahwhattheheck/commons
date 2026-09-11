# SPDX-License-Identifier: Apache-2.0
"""V4 S5: census-bounded late crop-mix timing experiment.

The active ``retain_wheat`` mode tests the exact late-game divergence seen in the
107953186 mirror loss without turning every late CARROT decision into WHEAT.
That replay starts day 24 at 38 WHEAT tiles versus the winner's 37, then starts
day 25 at 37 versus the winner's 41.  The winning mirror keeps materially more
WHEAT through the rotation window while moving into CARROT later.

S5 therefore uses a *tile-census floor*, not a blanket crop substitution:

* day 24: preserve at least 37 observed WHEAT tiles;
* day 25: preserve at least 41 observed WHEAT tiles.

Only an observed deficit can activate the lane.  Current ``PLANT CARROT``
commands are converted in actor order only up to that deficit and only when the
pre-market seed state proves the parent WHEAT/CARROT plants and the selected
candidate WHEAT plants are seed-backed.  A qualifying ``BUY_SEED CARROT q`` may
become ``BUY_SEED WHEAT q`` only for residual deficit, with the exact same
positive integer quantity.  Under the pinned engine this preserves seed count
and lowers seed spend ($20 CARROT -> $10 WHEAT).  The seed rewrite is also vetoed
when any later cash-spending order could be enabled by the saved cash.

The transform never adds/removes/reorders market rows, never changes actor
cardinality, never uses RNG, and uses same-turn seed purchases only for future
callbacks because unit actions execute before market orders.

The helper is source-only until it survives the paired V4 field/live gate.  The
eventual installed seam must pass the live configuration; enabled operation
fails closed unless the standard 720-step / 24-turn-day / 10x10 contract is
explicit.
"""

MODE_OFF = "off"
MODE_RETAIN_WHEAT = "retain_wheat"
MODES = (MODE_OFF, MODE_RETAIN_WHEAT)

EPISODE_STEPS = 720
TURNS_PER_DAY = 24
BOARD_SIZE = 10
WHEAT_SEED_COST = 10
CARROT_SEED_COST = 20
WHEAT_TILE_FLOOR = {24: 37, 25: 41}

_CASH_SPEND_OPS = frozenset(
    ("HIRE", "BUY_LAND", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL")
)
_SAFE_TRAILING_OPS = frozenset(("SELL",))
_MISSING = object()


def _cfg_get(configuration, key):
    if isinstance(configuration, dict):
        return configuration.get(key, _MISSING)
    return getattr(configuration, key, _MISSING)


def _standard_configuration(configuration):
    if configuration is None:
        return False
    for key, expected in (
        ("episodeSteps", EPISODE_STEPS),
        ("turnsPerDay", TURNS_PER_DAY),
        ("boardSize", BOARD_SIZE),
    ):
        value = _cfg_get(configuration, key)
        if type(value) is not int or value != expected:
            return False
    return True


def _normalized_mode(mode):
    if type(mode) is not str:
        return MODE_OFF
    return mode if mode in MODES else MODE_OFF


def _literal_plant(command, crop):
    return isinstance(command, list) and command == ["PLANT", crop]


def _strict_nonnegative_seed_count(seeds, crop):
    value = seeds.get(crop, 0)
    if type(value) is not int or value < 0:
        return None
    return value


def _actor_commands(action):
    farmer = action.get("farmer")
    hands = action.get("hands")
    if not isinstance(farmer, list) or not isinstance(hands, list):
        return None
    if any(not isinstance(command, list) for command in hands):
        return None
    return [farmer, *hands]


def _own_crop_counts(observation):
    player = observation.get("player")
    farms = observation.get("farms")
    if type(player) is not int or player not in (0, 1):
        return None
    if not isinstance(farms, list) or player >= len(farms):
        return None
    farm = farms[player]
    if not isinstance(farm, dict):
        return None
    tiles = farm.get("tiles")
    if not isinstance(tiles, list) or len(tiles) != BOARD_SIZE:
        return None

    wheat = 0
    carrot = 0
    for row in tiles:
        if not isinstance(row, list) or len(row) != BOARD_SIZE:
            return None
        for tile in row:
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                continue
            crop = tile.get("crop")
            if crop == "WHEAT":
                wheat += 1
            elif crop == "CARROT":
                carrot += 1
    return wheat, carrot


def _rewrite_safe_seed_row(market, max_quantity):
    """Return one quantity-preserving CARROT->WHEAT seed-row rewrite.

    The row must fit entirely inside ``max_quantity``; S5 never splits a market
    row because that would change order count.  Only the final cash-spending
    order may be rewritten.  Later SELL rows are safe; malformed/unknown later
    rows fail closed.
    """
    if type(max_quantity) is not int or max_quantity <= 0:
        return None
    if not isinstance(market, list):
        return None

    candidate = None
    for index, row in enumerate(market):
        if not isinstance(row, list) or not row:
            return None
        op = row[0]
        if op == "BUY_SEED" and len(row) == 3 and row[1] == "CARROT":
            quantity = row[2]
            if type(quantity) is int and 0 < quantity <= max_quantity:
                candidate = (index, row)
        elif op not in _CASH_SPEND_OPS and op not in _SAFE_TRAILING_OPS:
            return None

    if candidate is None:
        return None

    index, row = candidate
    for later in market[index + 1:]:
        op = later[0]
        if op in _CASH_SPEND_OPS:
            return None
        if op not in _SAFE_TRAILING_OPS:
            return None

    changed = list(row)
    changed[1] = "WHEAT"
    return index, changed


def apply_crop_mix(
    observation,
    action,
    mode=MODE_OFF,
    configuration=None,
):
    """Return the narrow, census-bounded S5 late-rotation variant."""
    if _normalized_mode(mode) != MODE_RETAIN_WHEAT or not isinstance(action, dict):
        return action
    if not _standard_configuration(configuration):
        return action
    if not isinstance(observation, dict):
        return action

    step = observation.get("step")
    day = observation.get("day")
    if type(step) is not int or type(day) is not int:
        return action
    if step < 0 or day != step // TURNS_PER_DAY:
        return action
    floor = WHEAT_TILE_FLOOR.get(day)
    if floor is None:
        return action

    crop_counts = _own_crop_counts(observation)
    if crop_counts is None:
        return action
    wheat_tiles, _ = crop_counts
    deficit = max(0, floor - wheat_tiles)
    if deficit <= 0:
        return action

    private = observation.get("private")
    if not isinstance(private, dict):
        return action
    seeds = private.get("seeds")
    if not isinstance(seeds, dict):
        return action

    wheat = _strict_nonnegative_seed_count(seeds, "WHEAT")
    carrot = _strict_nonnegative_seed_count(seeds, "CARROT")
    if wheat is None or carrot is None:
        return action

    commands = _actor_commands(action)
    if commands is None:
        return action

    wheat_plants = sum(_literal_plant(command, "WHEAT") for command in commands)
    carrot_plants = sum(_literal_plant(command, "CARROT") for command in commands)

    # Parent crop plants must be seed-backed before S5 is allowed to claim
    # current-callback occupancy equivalence.  Candidate WHEAT uses only the
    # seed surplus beyond the parent's authored WHEAT plants.
    plant_budget = 0
    if carrot >= carrot_plants and wheat >= wheat_plants:
        plant_budget = min(
            deficit,
            carrot_plants,
            wheat - wheat_plants,
        )

    residual = deficit - plant_budget
    market = action.get("market")
    market_rewrite = _rewrite_safe_seed_row(market, residual)

    if plant_budget <= 0 and market_rewrite is None:
        return action

    changed = dict(action)

    if market_rewrite is not None:
        index, row = market_rewrite
        new_market = list(market)
        new_market[index] = row
        changed["market"] = new_market

    if plant_budget > 0:
        remaining = plant_budget
        farmer = action["farmer"]
        if remaining and _literal_plant(farmer, "CARROT"):
            changed["farmer"] = ["PLANT", "WHEAT"]
            remaining -= 1

        hands = action["hands"]
        hand_indexes = []
        for index, command in enumerate(hands):
            if remaining <= 0:
                break
            if _literal_plant(command, "CARROT"):
                hand_indexes.append(index)
                remaining -= 1
        if hand_indexes:
            new_hands = list(hands)
            for index in hand_indexes:
                new_hands[index] = ["PLANT", "WHEAT"]
            changed["hands"] = new_hands

    return changed
