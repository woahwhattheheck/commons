"""Joint-turn constraint contract: what the engine will accept for a WHOLE turn.

The engine is the authority. Nothing here re-implements a rule: candidate ops are
enumerated over the grammar and handed to the pinned engine's own functions, and a
whole proposed turn is executed by the pinned `interpreter` itself on a deep copy.

Four interpreter facts make a per-unit probe insufficient on its own, so each is
modelled explicitly (line numbers are in the pinned kaggriculture.py):

  * 920-933  ATOMIC PLANT BUDGET. PLANT requests are summed across farmer and all
             hands. If the count for a crop exceeds that crop's seed stock, EVERY
             PLANT request for that crop that turn becomes PASS -- not just the
             surplus one. One seed and two planters is a different turn from two
             seeds and two planters.
  * 935-944  UNIT PHASE BEFORE MARKET PHASE. All unit actions resolve, then
             `_process_market` runs. A unit may DROP goods into the shed and SELL
             them in the same turn, so a market set derived only from the pre-unit
             shed is wrong. The reverse does not hold: BUY_SEED this turn cannot
             feed a PLANT this turn, because planting already happened.
  * per-unit market lockstep. Orders share one cash balance and one shed capacity
             and REPRICE after every unit, so quantities are not independent.
  * 873-882  END OF DAY, when (step+1) % turnsPerDay == 0: carried inventories drop
             to the shed and OVERFLOW IS DISCARDED, hired hands are removed and the
             farmer respawns. 960-963: terminal reward is cash only, so stock still
             held at the end scores nothing.

Constraint derivation and scoring are kept apart on purpose. This module answers
"will the engine act on this", never "is this a good move".
"""

import copy

FARMER_ARGLESS = [
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP",
    "WATER", "HARVEST", "FERTILIZE", "DIG",
    "BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
]

# Config keys a player legitimately sees. `seed` is deliberately excluded: it is
# the episode's hidden randomness and must never reach the model.
VISIBLE_CONFIG = (
    "boardSize", "startingMoney", "maxMarketOrdersPerTurn", "turnsPerDay",
    "shedCapacity", "weedSpawnChance", "townShopUnlockInterval",
    "townShopSellInterval", "townCenterSellInterval", "farmHandCostMult",
    "episodeSteps", "actTimeout", "marketParams",
)


def engine():
    from kaggle_environments.envs.kaggriculture import kaggriculture as K
    return K


def visible_config(config):
    """The player-visible configuration subset. Drops `seed` and any runner key."""
    return {k: config[k] for k in VISIBLE_CONFIG if k in config and config[k] is not None}


def _cfg(config, key, default):
    v = config.get(key, default) if isinstance(config, dict) else default
    return default if v is None else v


# --------------------------------------------------------------------------
# Marginal (single-op) admissibility -- the probe, not the whole grammar
# --------------------------------------------------------------------------

def unit_admissible(obs, config, seat, idx):
    """Ops the engine acts on for unit `idx` taken ALONE, at quantity 1.

    This is a marginal probe. It is not the playable grammar: quantities are
    exposed separately by `quantity_domains`, and the joint PLANT budget is a
    turn-level rule this per-unit view cannot express.
    """
    K = engine()
    board = int(_cfg(config, "boardSize", 10))
    tpd = int(_cfg(config, "turnsPerDay", 24))
    shed_cap = int(_cfg(config, "shedCapacity", 100))
    day = int(obs["day"])

    cands = [[op] for op in FARMER_ARGLESS]
    cands += [["PLANT", c] for c in K.CROPS]
    cands += [["PICKUP", it, 1] for it, n in obs["private"].get("shed", {}).items() if n > 0]
    invs = obs["private"].get("inventories", [])
    held = invs[idx] if idx < len(invs) else {}
    cands += [["PLACE", it, 1] for it, n in held.items() if n > 0]

    out = []
    for act in cands:
        if act == ["PASS"]:
            out.append(act)
            continue
        farm = copy.deepcopy(obs["farms"][seat])
        private = copy.deepcopy(obs["private"])
        before = (copy.deepcopy(farm), copy.deepcopy(private))
        try:
            K._apply_unit_action(farm, private, idx, list(act), board, day, tpd, shed_cap)
        except Exception:
            continue
        if (farm, private) != before:
            out.append(act)
    return sorted(out, key=lambda a: (a[0], str(a[1:])))


def quantity_domains(obs, config, seat, idx):
    """Max n the engine can actually move for each quantity-bearing unit op.

    PICKUP is bounded by shed stock; PLACE-to-shed by what the unit carries AND
    the shed's remaining room. The engine clamps rather than rejecting, so these
    are the useful upper ends of the domain, not a legality gate.
    """
    shed = obs["private"].get("shed", {})
    cap = int(_cfg(config, "shedCapacity", 100))
    room = max(0, cap - sum(shed.values()))
    invs = obs["private"].get("inventories", [])
    held = invs[idx] if idx < len(invs) else {}
    return {
        "PICKUP": {it: int(n) for it, n in shed.items() if n > 0},
        "PLACE_to_shed": {it: int(min(n, room)) for it, n in held.items() if n > 0},
        "shed_room": int(room),
    }


def _market_state(obs, config, seat, shed_override=None, money_override=None):
    farm = copy.deepcopy(obs["farms"][seat])
    private = copy.deepcopy(obs["private"])
    if shed_override is not None:
        private["shed"] = dict(shed_override)
    if money_override is not None:
        farm["money"] = money_override
    return farm, private


def market_admissible(obs, config, seat, shed=None, money=None):
    """Market orders the engine commits at least one unit of, plus a max quantity.

    `shed` / `money` let the caller ask about the POST-UNIT-PHASE balance, which is
    what the market actually sees. Max quantity is found by walking the engine's own
    per-unit lockstep (repricing each unit, sharing cash and shed room), so it is the
    engine's answer and not an estimate.
    """
    K = engine()
    shed_cap = int(_cfg(config, "shedCapacity", 100))
    board = int(_cfg(config, "boardSize", 10))
    mult = int(_cfg(config, "farmHandCostMult", K.FARM_HAND_COST_MULT))

    cands = [["HIRE"], ["BUY_LAND"]]
    cands += [["SELL", it] for it in K.PRODUCTS]
    cands += [["BUY_PRODUCT", it] for it in ("WHEAT", "FERTILIZER")]
    cands += [["BUY_SEED", c] for c in K.CROPS]
    cands += [["BUY_ANIMAL", a] for a in K.ANIMALS]

    out = []
    for order in cands:
        op = order[0]
        farm, private = _market_state(obs, config, seat, shed, money)
        if op == "HIRE":
            before = (copy.deepcopy(farm), copy.deepcopy(private))
            K._do_hire(farm, private, board, mult)
            if (farm, private) != before:
                out.append({"order": ["HIRE"], "max_n": 1})
            continue
        if op == "BUY_LAND":
            before = copy.deepcopy(farm)
            K._do_buy_land(farm, board)
            if farm != before:
                out.append({"order": ["BUY_LAND"], "max_n": 1})
            continue
        item = order[1]
        mk = copy.deepcopy(obs["market"])
        filled = 0
        while filled < 10_000:
            price = _quote(K, op, item, mk)
            if price is None:
                break
            if not K._commit_unit(op, item, price, farm, private, mk, shed_cap):
                break
            filled += 1
            K._refresh_prices(mk)
        if filled:
            out.append({"order": [op, item], "max_n": filled})
    return sorted(out, key=lambda d: (d["order"][0], str(d["order"][1:])))


def _quote(K, op, item, market):
    inv = market["inventory"]
    params = market.get("params")
    if op == "SELL":
        return K.market_price(item, inv[item], params) if item in K.PRODUCTS else None
    if op == "BUY_PRODUCT":
        return K.market_price(item, inv[item] - 1, params) if item in ("WHEAT", "FERTILIZER") else None
    if op == "BUY_SEED":
        return K.CROPS[item]["seed"] if item in K.CROPS else None
    if op == "BUY_ANIMAL":
        return K.ANIMALS[item]["cost"] if item in K.ANIMALS else None
    return None


# --------------------------------------------------------------------------
# Turn-level rules the per-unit view cannot express
# --------------------------------------------------------------------------

def turn_rules(obs, config, seat):
    """The joint-turn facts, as data. Rendered to the model verbatim, never applied for it."""
    tpd = int(_cfg(config, "turnsPerDay", 24))
    hour = int(obs["hour"])
    step = int(obs.get("step", 0))
    episode_steps = int(_cfg(config, "episodeSteps", 720))
    seeds = {k: int(v) for k, v in obs["private"].get("seeds", {}).items()}
    n_hands = len(obs["farms"][seat].get("hands", []))
    shed = obs["private"].get("shed", {})
    cap = int(_cfg(config, "shedCapacity", 100))
    carried = sum(sum(inv.values()) for inv in obs["private"].get("inventories", []))
    return {
        "units": 1 + n_hands,
        "plant_budget": seeds,
        "seed_budget_is_joint": True,
        "unit_phase_before_market": True,
        "max_market_orders": int(_cfg(config, "maxMarketOrdersPerTurn", 10)),
        "shed_room": max(0, cap - sum(shed.values())),
        "carried_units": int(carried),
        "hour": hour,
        "turns_per_day": tpd,
        "end_of_day_this_turn": (step + 1) % tpd == 0,
        "last_turn_of_episode": step >= episode_steps - 2,
    }


def admissible(obs, config, seat):
    """The full applicable-constraint set for one card."""
    n_units = 1 + len(obs["farms"][seat].get("hands", []))
    shed = obs["private"].get("shed", {})
    cap = int(_cfg(config, "shedCapacity", 100))
    # What the market would see if every carried unit were deposited this turn --
    # the engine's real upper bound on same-turn sellable stock (unit phase first).
    room = max(0, cap - sum(shed.values()))
    post = dict(shed)
    for inv in obs["private"].get("inventories", []):
        for it, n in inv.items():
            take = min(int(n), room)
            if take > 0:
                post[it] = post.get(it, 0) + take
                room -= take
    return {
        "units": [unit_admissible(obs, config, seat, i) for i in range(n_units)],
        "quantities": [quantity_domains(obs, config, seat, i) for i in range(n_units)],
        "market": market_admissible(obs, config, seat),
        "market_after_full_deposit": market_admissible(obs, config, seat, shed=post),
        "rules": turn_rules(obs, config, seat),
        "max_market_orders": int(_cfg(config, "maxMarketOrdersPerTurn", 10)),
    }


# --------------------------------------------------------------------------
# Ground truth: run the proposed turn through the pinned interpreter
# --------------------------------------------------------------------------

def evaluate_turn(obs, config, seat, action):
    """Execute `action` for `seat` with the REAL interpreter and report what happened.

    The opponent seat is given an empty private state and the engine's default PASS
    action. That is a declared counterfactual: it leaves this seat's unit phase
    untouched and makes the market quotes the solo-player quotes. It is used for
    scoring a turn, never shown to the model.

    Returns the per-op effects, the joint PLANT block, market fills, and the cash and
    shed deltas -- syntax, engine effect, and economics kept as separate fields.
    """
    K = engine()
    from kaggle_environments.utils import structify

    obs_a = copy.deepcopy(obs)
    other = 1 - seat
    obs_b = copy.deepcopy(obs)
    obs_b["player"] = other
    obs_b["private"] = {"shed": {}, "inventories": [{}], "seeds": {}}
    # farms is the shared public list; both observations must alias the same object
    # exactly as the engine does when it fans state out after each step.
    obs_b["farms"] = copy.deepcopy(obs_a["farms"])
    obs_b["market"] = copy.deepcopy(obs_a["market"])
    obs_b["town"] = copy.deepcopy(obs_a["town"])

    default = {"farmer": ["PASS"], "hands": [], "market": []}
    states = [None, None]
    states[seat] = {"observation": obs_a, "action": copy.deepcopy(action),
                    "status": "ACTIVE", "reward": 0.0}
    states[other] = {"observation": obs_b, "action": dict(default),
                     "status": "ACTIVE", "reward": 0.0}
    state = structify(states)
    env = structify({"configuration": visible_config(config), "done": False, "info": {"seed": 0}})

    before_money = float(obs["farms"][seat]["money"])
    before_shed = dict(obs["private"].get("shed", {}))
    before_carried = sum(sum(i.values()) for i in obs["private"].get("inventories", []))

    # Per-op effect: replay each unit op alone against the PRE-turn state, so a
    # no-op is attributable to that op rather than to an earlier op in the turn.
    effects = []
    board = int(_cfg(config, "boardSize", 10))
    tpd = int(_cfg(config, "turnsPerDay", 24))
    shed_cap = int(_cfg(config, "shedCapacity", 100))
    day = int(obs["day"])
    unit_actions = [action.get("farmer", ["PASS"])] + list(action.get("hands", []))
    for i, act in enumerate(unit_actions):
        farm = copy.deepcopy(obs["farms"][seat])
        private = copy.deepcopy(obs["private"])
        before = (copy.deepcopy(farm), copy.deepcopy(private))
        try:
            K._apply_unit_action(farm, private, i, list(act), board, day, tpd, shed_cap)
            changed = (farm, private) != before
        except Exception:
            changed = False
        effects.append({"unit": i, "action": list(act), "non_no_op": bool(changed)})

    # Joint PLANT budget, exactly as the interpreter computes it.
    demand = {}
    for a in unit_actions:
        if isinstance(a, list) and len(a) >= 2 and a[0] == "PLANT":
            demand[a[1]] = demand.get(a[1], 0) + 1
    seeds = obs["private"].get("seeds", {})
    blocked = sorted(c for c, n in demand.items() if n > seeds.get(c, 0))

    K.interpreter(state, env)

    # Read back from the structified state the interpreter actually mutated:
    # `structify` copies, so the pre-call dicts are stale. The interpreter reads
    # every farm from state[0].observation.farms and each private from its own seat.
    post_farms = state[0].observation.farms
    post_private = state[seat].observation.private
    after_money = float(post_farms[seat]["money"])
    after_shed = dict(post_private.get("shed", {}))
    return {
        "unit_effects": effects,
        "plant_demand": demand,
        "plant_blocked": blocked,
        "money_before": before_money,
        "money_after": after_money,
        "money_delta": after_money - before_money,
        "shed_before": before_shed,
        "shed_after": after_shed,
        "carried_before": int(before_carried),
        "carried_after": int(sum(sum(i.values()) for i in post_private.get("inventories", []))),
        "hands_after": len(post_farms[seat].get("hands", [])),
        "seeds_after": dict(post_private.get("seeds", {})),
    }


# --------------------------------------------------------------------------
# Production / survival horizon -- state exposure, not a recommendation
# --------------------------------------------------------------------------

def plant_horizon(tile, day, step, turns_per_day):
    """What the engine will do to THIS plant next. Facts only; no preference.

    Derived from `_daily_refresh_plants` and `_decay_plants`:
      * ongoing crops produce when (next_day - planted_day - first_yield_day) is a
        non-negative multiple of `interval`, for at most `max_yield` events; TOMATO
        (first 8, interval 1) therefore fires at ages 8,9,10,11 and STRAWBERRY
        (first 10, interval 2) at ages 10,12,14,16 -- four events each, then the
        plant is put on a lifespan clock and decays.
      * a plant with consecutive_unwatered >= 2 at the daily refresh becomes a WEED.
        `_new_plant` starts it at 1, so an unwatered planting day is already fatal.
      * a surviving ongoing plant still gains base yield on an unwatered day; the
        fertilizer bonus is the part that requires the day to have been watered.
    """
    K = engine()
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
        return None
    cd = K.CROPS[tile["crop"]]
    planted = tile["planted_day"]
    info = {
        "crop": tile["crop"],
        "ongoing": bool(cd["ongoing"]),
        "age_days": day - planted,
        "first_yield_day": cd["first_yield_day"],
        "yield_units": tile.get("yield_units", 0),
        "max_yield": cd["max_yield"],
        "consecutive_unwatered": tile.get("consecutive_unwatered", 0),
        "watered_today": bool(tile.get("watered_today")),
        "fertilized": tile.get("fertilized_until_day", -1) >= day,
    }
    # Dies at this day's refresh unless watered before it.
    info["dies_at_refresh_unless_watered"] = (
        not tile.get("watered_today") and tile.get("consecutive_unwatered", 0) + 1 >= 2)
    if cd["ongoing"]:
        interval = max(1, cd["interval"])
        events = []
        for nd in range(day + 1, day + 40):
            dsf = nd - planted - cd["first_yield_day"]
            if dsf < 0 or dsf % interval:
                continue
            count = dsf // interval + 1
            if count > cd["max_yield"]:
                break
            events.append({"day": nd, "event": count})
        info["remaining_production_days"] = events
        info["events_left"] = len(events)
    else:
        info["remaining_production_days"] = []
        info["max_yield_day"] = cd["max_yield_day"]
        info["watering_bonus_window_days"] = [
            (cd["max_yield_day"] + 1) // 2, cd["max_yield_day"]]
    mls = tile.get("max_lifespan_step", -1)
    info["decaying"] = mls >= 0 and step >= mls
    info["decay_starts_step"] = mls if mls >= 0 else None
    return info


def horizon(obs, config, seat):
    """Production/decay horizon for every owned plant, plus the cash-realization clock."""
    tpd = int(_cfg(config, "turnsPerDay", 24))
    day, step = int(obs["day"]), int(obs.get("step", 0))
    episode_steps = int(_cfg(config, "episodeSteps", 720))
    farm = obs["farms"][seat]
    plants = []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            h = plant_horizon(tile, day, step, tpd)
            if h:
                h["at"] = [x, y]
                plants.append(h)
    # DONE fires at step >= episodeSteps - 2, so that step is the last decision.
    last = episode_steps - 2
    return {
        "plants": plants,
        "remaining_decisions": max(0, last - step + 1),
        "last_decision_step": last,
        "turns_left_today": (tpd - int(obs["hour"])) if tpd else 0,
    }
