"""Build each operator's emitted surface from REAL derivation-card states.

Every exemplar situation is rendered from a real captured card (mutated in the one
field the operator's gate turns on), and every exemplar output is checked
admissible by the pinned engine before it is allowed into a surface. An exemplar
therefore demonstrates an ENGINE GATE, never an invented "best move" label.

Derivation cards must come from seeds disjoint from the evaluation seeds; `build`
raises if they overlap.
"""

import copy

import constraints
import discriminate
import operators
from constraints import engine


class OverlapError(Exception):
    pass


def _situation(card, extra=""):
    """A one-line situation in the same shape the STATE block uses."""
    obs, cfg, seat = card["observation"], card["configuration"], card["seat"]
    farm = obs["farms"][seat]
    x, y = int(farm["farmer"][0]), int(farm["farmer"][1])
    import prompt as P
    tile = P._tile_str(farm["tiles"][y][x], int(obs["day"]))
    seeds = ",".join(f"{k}{v}" for k, v in sorted(obs["private"].get("seeds", {}).items()) if v) or "-"
    shed = obs["private"].get("shed", {})
    cap = int(cfg.get("shedCapacity", 100) or 100)
    inv = obs["private"].get("inventories", [{}])[0]
    carry = ",".join(f"{k}{v}" for k, v in sorted(inv.items()) if v) or "-"
    bits = [f"farmer on [{tile}]", f"seeds {seeds}", f"carrying {carry}",
            f"shed {sum(shed.values())}/{cap}"]
    if extra:
        bits.append(extra)
    return "; ".join(bits)


def _assert_admissible(card, action):
    adm = constraints.admissible(card["observation"], card["configuration"], card["seat"])
    verdict = __import__("codec").legality(action, adm)
    if not verdict["legal"]:
        raise AssertionError(f"exemplar action not admissible: {verdict}")
    return action


def _pairs_for(card):
    """The five engine gates instantiated on this derivation card."""
    return {p["name"]: p for p in discriminate.build_pairs(card)}


def build(deriv_cards, eval_cards):
    """(surfaces, provenance). Raises OverlapError if the two card sets share a seed."""
    dseeds = {c["seed"] for c in deriv_cards}
    eseeds = {c["seed"] for c in eval_cards}
    if dseeds & eseeds:
        raise OverlapError(f"derivation and evaluation seeds overlap: {sorted(dseeds & eseeds)}")

    card = deriv_cards[0]
    pairs = _pairs_for(card)
    K = engine()
    prov = {"derivation_seeds": sorted(dseeds), "evaluation_seeds": sorted(eseeds),
            "derivation_cards": [c["card_id"] for c in deriv_cards], "exemplars": {}}
    surfaces = {}

    def add(name, items):
        checked = []
        for src_card, situation, action in items:
            _assert_admissible(src_card, action)
            checked.append((situation, action))
        surfaces[name] = operators.surface(name, checked)
        prov["exemplars"][name] = [{"situation": s, "output": a} for s, a in checked]

    # ADMIT -- the output contract itself: one turn object, entries from the accepted set.
    admit_card = copy.deepcopy(card)
    adm = constraints.admissible(admit_card["observation"], admit_card["configuration"], admit_card["seat"])
    first_move = next(o for o in adm["units"][0] if o[0] in ("NORTH", "SOUTH", "EAST", "WEST"))
    add("ADMIT", [
        (admit_card, _situation(admit_card, f"accepted includes {' '.join(first_move)}"),
         {"farmer": list(first_move), "hands": [], "market": []}),
        (admit_card, _situation(admit_card, "nothing to advance the goal here"),
         {"farmer": ["PASS"], "hands": [], "market": []}),
    ])

    # STOCK -- a resource is present, or it is absent and acquired instead.
    p = pairs["seed_stock"]
    add("STOCK", [
        (p["a"], _situation(p["a"]), {"farmer": ["PLANT", "WHEAT"], "hands": [], "market": []}),
        (p["b"], _situation(p["b"]),
         {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 1]]}),
    ])

    # ONCE -- the daily flag is unconsumed, or already consumed.
    p = pairs["watered_negation"]
    alt = next(o for o in constraints.admissible(
        p["b"]["observation"], p["b"]["configuration"], p["b"]["seat"])["units"][0]
        if o[0] in ("NORTH", "SOUTH", "EAST", "WEST"))
    add("ONCE", [
        (p["a"], _situation(p["a"]), {"farmer": ["WATER"], "hands": [], "market": []}),
        (p["b"], _situation(p["b"]), {"farmer": list(alt), "hands": [], "market": []}),
    ])

    # RIPE -- the maturity deadline is met, or it is not.
    p = pairs["maturity_deadline"]
    add("RIPE", [
        (p["a"], _situation(p["a"]), {"farmer": ["HARVEST"], "hands": [], "market": []}),
        (p["b"], _situation(p["b"]), {"farmer": ["WATER"], "hands": [], "market": []}),
    ])

    # KEEP -- a plant that dies at this refresh unless watered, versus one that does not.
    K2 = engine()
    keep_card = copy.deepcopy(card)
    seat_k = keep_card["seat"]
    spots = [(x, y) for y, row in enumerate(keep_card["observation"]["farms"][seat_k]["tiles"])
             for x, t_ in enumerate(row) if t_ is None]
    kx, ky = spots[0]
    keep_card["observation"]["farms"][seat_k]["farmer"] = [kx, ky]
    day_k = int(keep_card["observation"]["day"])
    tpd_k = int(keep_card["configuration"]["turnsPerDay"])

    dying = copy.deepcopy(keep_card)
    dying["observation"]["farms"][seat_k]["tiles"][ky][kx] = K2._new_plant("WHEAT", day_k, tpd_k)
    safe = copy.deepcopy(keep_card)
    safe_tile = K2._new_plant("WHEAT", day_k, tpd_k)
    safe_tile["consecutive_unwatered"] = 0
    safe["observation"]["farms"][seat_k]["tiles"][ky][kx] = safe_tile
    safe_alt = next(o for o in constraints.admissible(
        safe["observation"], safe["configuration"], seat_k)["units"][0]
        if o[0] in ("NORTH", "SOUTH", "EAST", "WEST"))
    add("KEEP", [
        (dying, _situation(dying, "unwatered_streak1, DIES at this refresh unless watered"),
         {"farmer": ["WATER"], "hands": [], "market": []}),
        (safe, _situation(safe, "unwatered_streak0, survives this refresh either way"),
         {"farmer": list(safe_alt), "hands": [], "market": []}),
    ])

    # VENT -- the shed has room, or it is full and a sale opens it.
    p = pairs["shed_capacity"]
    add("VENT", [
        (p["a"], _situation(p["a"]),
         {"farmer": ["PASS"], "hands": [], "market": [["BUY_PRODUCT", "WHEAT", 1]]}),
        (p["b"], _situation(p["b"]),
         {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 5]]}),
    ])
    return surfaces, prov


def composed_pattern(surfaces):
    """The five gate surfaces stacked under one header (sigma1 || sigma2 ...)."""
    return "\n".join(surfaces[n] for n in operators.ORDER)


def composed_formal():
    """The eight-part specifications stacked, one per operator."""
    return "\n\n".join(operators.spec_text(n) for n in operators.ORDER)
