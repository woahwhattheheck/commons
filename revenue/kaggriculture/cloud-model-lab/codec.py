"""Reversible codec between the model's emitted surface and the engine action.

The output contract IS the engine's own action object, so the codec is an
identity on well-formed output and the legality check is exact rather than
interpretive:

    {"farmer": [OP, ...], "hands": [[OP, ...], ...], "market": [[OP, ...], ...]}

Decoding is strict and REJECTS. It never repairs an invalid emission into a
plausible one and never substitutes a fallback while reporting a model decision:
a rejection is returned with its reason and counted as a rejection.
"""

import json

UNIT_OPS_0 = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP", "WATER", "HARVEST",
    "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "FEED",
    "COLLECT_FERTILIZER", "CARE",
}
UNIT_OPS_ITEM = {"PLANT", "PICKUP", "PLACE"}
MARKET_OPS_0 = {"HIRE", "BUY_LAND"}
MARKET_OPS_ITEM_N = {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}


class Rejected(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def encode_turn(action):
    """Canonical compact surface for a turn action. Deterministic key order."""
    return json.dumps(
        {
            "farmer": list(action.get("farmer", ["PASS"])),
            "hands": [list(h) for h in action.get("hands", [])],
            "market": [list(m) for m in action.get("market", [])],
        },
        separators=(",", ":"),
    )


def _first_json_object(text):
    """The first balanced {...} in the text, string/escape aware."""
    depth = 0
    start = None
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    raise Rejected("no balanced JSON object in output")


def _norm_unit(entry, where):
    if not isinstance(entry, list) or not entry:
        raise Rejected(f"{where}: not a non-empty list")
    op = entry[0]
    if not isinstance(op, str):
        raise Rejected(f"{where}: op is not a string")
    op = op.strip().upper()
    if op in UNIT_OPS_0:
        if len(entry) != 1:
            raise Rejected(f"{where}: {op} takes no arguments, got {len(entry) - 1}")
        return [op]
    if op in UNIT_OPS_ITEM:
        if len(entry) < 2 or not isinstance(entry[1], str):
            raise Rejected(f"{where}: {op} needs an item name")
        item = entry[1].strip().upper()
        if op == "PLANT":
            if len(entry) != 2:
                raise Rejected(f"{where}: PLANT takes exactly one crop")
            return ["PLANT", item]
        n = 1
        if len(entry) >= 3:
            if not isinstance(entry[2], (int, float)) or isinstance(entry[2], bool):
                raise Rejected(f"{where}: {op} count is not a number")
            n = int(entry[2])
        if len(entry) > 3:
            raise Rejected(f"{where}: {op} takes at most item and count")
        return [op, item, n]
    raise Rejected(f"{where}: unknown unit op {op!r}")


def _norm_market(entry, where):
    if not isinstance(entry, list) or not entry:
        raise Rejected(f"{where}: not a non-empty list")
    op = entry[0]
    if not isinstance(op, str):
        raise Rejected(f"{where}: op is not a string")
    op = op.strip().upper()
    if op in MARKET_OPS_0:
        if len(entry) != 1:
            raise Rejected(f"{where}: {op} takes no arguments")
        return [op]
    if op in MARKET_OPS_ITEM_N:
        if len(entry) != 3:
            raise Rejected(f"{where}: {op} needs item and count")
        if not isinstance(entry[1], str):
            raise Rejected(f"{where}: {op} item is not a string")
        if not isinstance(entry[2], (int, float)) or isinstance(entry[2], bool):
            raise Rejected(f"{where}: {op} count is not a number")
        return [op, entry[1].strip().upper(), int(entry[2])]
    raise Rejected(f"{where}: unknown market op {op!r}")


def decode_turn(text):
    """Model text -> engine action dict. Raises Rejected with a reason."""
    if not isinstance(text, str) or not text.strip():
        raise Rejected("empty output")
    blob = _first_json_object(text)
    try:
        obj = json.loads(blob)
    except Exception as exc:
        raise Rejected(f"not valid JSON: {exc}")
    if not isinstance(obj, dict):
        raise Rejected("top level is not an object")
    unknown = set(obj) - {"farmer", "hands", "market"}
    if unknown:
        raise Rejected(f"unknown top-level keys: {sorted(unknown)}")
    if "farmer" not in obj:
        raise Rejected("missing 'farmer'")
    farmer = _norm_unit(obj["farmer"], "farmer")
    hands_raw = obj.get("hands", [])
    if not isinstance(hands_raw, list):
        raise Rejected("'hands' is not a list")
    hands = [_norm_unit(h, f"hands[{i}]") for i, h in enumerate(hands_raw)]
    market_raw = obj.get("market", [])
    if not isinstance(market_raw, list):
        raise Rejected("'market' is not a list")
    market = [_norm_market(m, f"market[{i}]") for i, m in enumerate(market_raw)]
    return {"farmer": farmer, "hands": hands, "market": market}


def _in_set(entry, admissible_set):
    """Membership ignoring the count argument (the engine clamps counts, not rejects)."""
    for cand in admissible_set:
        if cand[0] != entry[0]:
            continue
        if len(cand) == 1 and len(entry) == 1:
            return True
        if len(cand) > 1 and len(entry) > 1 and cand[1] == entry[1]:
            return True
    return False


def _market_orders(adm, key):
    return [m["order"] for m in adm[key]]


def _max_n(adm, key, order):
    for m in adm[key]:
        if m["order"][0] == order[0] and m["order"][1:] == order[1:2]:
            return m["max_n"]
    return None


def legality(action, adm):
    """Three DISTINCT results for one decoded turn -- never collapsed into one score.

      violations   the engine will not act on this entry at all (a silent no-op)
      joint_blocks turn-level drops the per-unit view cannot see (the PLANT budget)
      clamped      quantities the engine will silently reduce, which is legal but lossy

    A turn with no violations and no joint_blocks is one the engine acts on in full.
    Whether it is a GOOD turn is a separate question this function does not answer.
    """
    violations, joint_blocks, clamped = [], [], []
    units = adm["units"]
    qty = adm.get("quantities", [{}] * len(units))

    entries = [(0, action["farmer"], "farmer")]
    n_hands = len(units) - 1
    if len(action["hands"]) > n_hands:
        violations.append(f"{len(action['hands'])} hand actions but {n_hands} hands exist")
    for i, h in enumerate(action["hands"][:n_hands]):
        entries.append((i + 1, h, f"hands[{i}]"))

    for idx, entry, label in entries:
        if not _in_set(entry, units[idx]):
            violations.append(f"{label} {entry} not admissible")
            continue
        if entry[0] in ("PICKUP", "PLACE") and len(entry) >= 3:
            dom = qty[idx].get("PICKUP" if entry[0] == "PICKUP" else "PLACE_to_shed", {})
            cap = dom.get(entry[1])
            if cap is not None and entry[2] > cap:
                clamped.append(f"{label} {entry[0]} {entry[1]} {entry[2]} clamps to {cap}")

    # Atomic PLANT budget, summed across farmer and hands (interpreter 920-933).
    demand = {}
    for _idx, entry, _label in entries:
        if entry[0] == "PLANT":
            demand[entry[1]] = demand.get(entry[1], 0) + 1
    budget = adm["rules"]["plant_budget"]
    for crop, n in sorted(demand.items()):
        have = budget.get(crop, 0)
        if n > have:
            joint_blocks.append(
                f"PLANT {crop} requested {n}x across units but only {have} seed(s): "
                f"the engine drops ALL {n} to PASS")

    # Market. An order can be enabled by a deposit earlier in the SAME turn, so the
    # permissive basis is the post-deposit set; which basis carried it is recorded.
    now = _market_orders(adm, "market")
    after = _market_orders(adm, "market_after_full_deposit")
    limit = adm["max_market_orders"]
    if len(action["market"]) > limit:
        violations.append(
            f"{len(action['market'])} market orders exceeds maxMarketOrdersPerTurn={limit}; "
            f"the engine silently drops the extras")
    for i, m in enumerate(action["market"][:limit]):
        if _in_set(m, now):
            cap = _max_n(adm, "market", m)
        elif _in_set(m, after):
            cap = _max_n(adm, "market_after_full_deposit", m)
            clamped.append(f"market[{i}] {m[0]} {m[1] if len(m) > 1 else ''} "
                           f"needs a same-turn deposit to fill")
        else:
            violations.append(f"market[{i}] {m} not admissible")
            continue
        if cap is not None and len(m) >= 3 and m[2] > cap:
            clamped.append(f"market[{i}] {m[0]} {m[1]} {m[2]} fills at most {cap}")

    return {"violations": violations, "joint_blocks": joint_blocks, "clamped": clamped,
            "legal": not violations and not joint_blocks}


# --------------------------------------------------------------------------
# Grammar-level output binding for constrained decoding
# --------------------------------------------------------------------------

def _alt(names):
    return "(?:" + "|".join(sorted(names)) + ")"


def turn_regex():
    """A regex over the exact turn grammar, for ResponseFormat.REGEX.

    This binds SYNTAX only -- op names, arity, nesting. Whether an op is admissible
    on this card stays a separate check, so a constrained decode cannot manufacture
    a legality result it did not earn.
    """
    from constraints import engine
    K = engine()
    items = sorted(set(K.PRODUCTS) | set(K.ANIMALS) | set(K.CROPS))
    n = "[0-9]{1,3}"
    unit = "(?:" + "|".join([
        r'\["' + _alt(UNIT_OPS_0) + r'"\]',
        r'\["PLANT","' + _alt(K.CROPS) + r'"\]',
        r'\["(?:PICKUP|PLACE)","' + _alt(items) + r'",' + n + r'\]',
    ]) + ")"
    order = "(?:" + "|".join([
        r'\["' + _alt(MARKET_OPS_0) + r'"\]',
        r'\["' + _alt(MARKET_OPS_ITEM_N) + r'","' + _alt(items) + r'",' + n + r'\]',
    ]) + ")"
    lst = lambda e: r"\[(?:" + e + r"(?:," + e + r"){0,9})?\]"
    return r'\{"farmer":' + unit + r',"hands":' + lst(unit) + r',"market":' + lst(order) + r"\}"


TIGHT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["farmer", "hands", "market"],
    "properties": {
        "farmer": {"type": "array", "minItems": 1, "maxItems": 3,
                   "items": {"type": ["string", "integer"]}},
        "hands": {"type": "array", "maxItems": 8,
                  "items": {"type": "array", "minItems": 1, "maxItems": 3,
                            "items": {"type": ["string", "integer"]}}},
        "market": {"type": "array", "maxItems": 10,
                   "items": {"type": "array", "minItems": 1, "maxItems": 3,
                             "items": {"type": ["string", "integer"]}}},
    },
}
