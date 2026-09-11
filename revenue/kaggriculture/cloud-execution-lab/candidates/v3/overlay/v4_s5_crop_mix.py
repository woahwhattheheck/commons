# SPDX-License-Identifier: Apache-2.0
"""V4 S5: late crop-mix timing experiment.

The active ``retain_wheat`` mode tests the exact late-game divergence seen in the
107953186 mirror loss: keep the day-24/25 crop rotation on WHEAT longer instead
of pivoting to CARROT immediately.

The transform is deliberately narrow and RNG-neutral for the current callback:

* it never adds, removes, or reorders market rows;
* a qualifying ``BUY_SEED CARROT q`` becomes ``BUY_SEED WHEAT q`` with the
  exact same positive integer quantity, so seed count is preserved and spend
  can only decrease under the official $20 CARROT / $10 WHEAT seed costs;
* current ``PLANT CARROT`` commands become ``PLANT WHEAT`` only when the
  pre-market private seed state proves that every original WHEAT/CARROT plant
  would have seed and that every rewritten plant also has WHEAT. Unit actions
  execute before market orders, so same-turn seed purchases are never credited;
* the market rewrite is allowed only when no later cash-spending order can be
  enabled by the saved seed cost.

The helper is source-only until it survives the paired V4 field/live gate. The
eventual installed seam must pass the live configuration; enabled operation
fails closed unless the standard 720-step / 24-turn-day contract is explicit.
"""

MODE_OFF = "off"
MODE_RETAIN_WHEAT = "retain_wheat"
MODES = (MODE_OFF, MODE_RETAIN_WHEAT)

EPISODE_STEPS = 720
TURNS_PER_DAY = 24
ACTIVE_DAYS = frozenset((24, 25))
WHEAT_SEED_COST = 10
CARROT_SEED_COST = 20

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


def _rewrite_safe_seed_row(market):
    """Return ``(index, row)`` for one quantity-preserving late seed rewrite.

    Only the final cash-spending order may be rewritten. Later SELL rows are
    harmless; malformed/unknown later rows fail closed because their cash or
    state effect is not proven.
    """
    if not isinstance(market, list):
        return None

    candidate = None
    for index, row in enumerate(market):
        if not isinstance(row, list) or not row:
            return None
        op = row[0]
        if op == "BUY_SEED" and len(row) == 3 and row[1] == "CARROT":
            quantity = row[2]
            if type(quantity) is int and quantity > 0:
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
    """Return the narrow S5 late-rotation variant of ``action``.

    The exact parent object is returned whenever a guard fails or no change is
    available. All mutation is copy-on-write.
    """
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
    if step < 0 or day != step // TURNS_PER_DAY or day not in ACTIVE_DAYS:
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

    # Preserve which current PLANT commands can execute. This is deliberately
    # conservative: all original WHEAT/CARROT plants must be seed-backed, and
    # WHEAT must also cover every proposed CARROT->WHEAT rewrite.
    rewrite_plants = (
        carrot_plants > 0
        and carrot >= carrot_plants
        and wheat >= wheat_plants + carrot_plants
    )

    market = action.get("market")
    market_rewrite = _rewrite_safe_seed_row(market)

    if not rewrite_plants and market_rewrite is None:
        return action

    changed = dict(action)

    if market_rewrite is not None:
        index, row = market_rewrite
        new_market = list(market)
        new_market[index] = row
        changed["market"] = new_market

    if rewrite_plants:
        farmer = action["farmer"]
        if _literal_plant(farmer, "CARROT"):
            changed["farmer"] = ["PLANT", "WHEAT"]

        hands = action["hands"]
        hand_indexes = [
            index for index, command in enumerate(hands)
            if _literal_plant(command, "CARROT")
        ]
        if hand_indexes:
            new_hands = list(hands)
            for index in hand_indexes:
                new_hands[index] = ["PLANT", "WHEAT"]
            changed["hands"] = new_hands

    return changed
