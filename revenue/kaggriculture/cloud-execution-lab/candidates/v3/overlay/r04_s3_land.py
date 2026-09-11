"""V4 lane S3 (key r04_s3_land): open the SE quadrant for work the authored tape does not route to.

The engine sells land in a fixed order, NE ($1,000), SW ($2,000), SE ($4,000). The R04 tapes buy
NE and SW and never SE, and from day 7 on every tile the tape owns is in use. With the key on, one
BUY_LAND is appended to the market after the tape owns NE and SW, so the purchase can only land on
SE. It goes out only when the farm's money covers SE plus a reserve, only when no BUY_LAND is
already queued this step, only while an order slot is free, and only up to LAST_STEP. Nothing else
in the action changes. The SE tiles start empty; the S1 operator decides what to do with them.

se_open() and se_tiles() are the read side for that operator.

Shop-unlock RNG. At each end of day the engine seeds one Random((seed*1_000_003) ^ day), draws one
rng.random() for every empty (None) tile of farm 0 and then farm 1 (weed spawn), and only then, on
days where (day + 1) % 3 == 0 and fewer than 8 shops exist, draws the town's next shop from the same
stream. LOCKED, planted, structure and WEED tiles draw nothing. Empty SE tiles at such an end of day
therefore change which shop the town unlocks for both players. The purchase is allowed only in the
first hours of a day with day % 3 == 0, which leaves three whole days before the next shop draw for
the operator to occupy all 25 SE tiles; shop_draw_tonight() and se_empty() let the operator hold SE
at zero empty tiles on every drawing night.

V219. The day-18 late-tomato program (_v219_qualifies) is itself an SE program: at step 432 it needs
exactly NW, NE and SW owned with SE rows 5-6 still LOCKED, 12,000 money, a TOMATO price of 70 and
three PIZZA_SHOP / FARMERS_MARKET among the unlocked shops, then buys SE in hours 0-3 of day 18. With
DEFER_TO_V219 on, S3 waits while those shops could still reach three by day 18 (the shops already
unlocked plus the shop nights left before it), stays out of hours 0-3 of day 18, and on day 18 buys
only in hours 4-5 when V219 has not taken SE.
"""

S3_LAND = False
SE_PRICE = 4000
RESERVE = 3000
FIRST_STEP = 0
LAST_STEP = 480          # day 20: later purchases leave too few days to work the land
BUY_HOURS = 6            # buy in hours 0-5 of an allowed day
TURNS_PER_DAY = 24
SHOP_UNLOCK_INTERVAL = 3
MAX_SHOP_INSTANCES = 8
MAX_ORDERS = 10
DEFER_TO_V219 = True
V219_DAY = 18
V219_REQUEST_HOURS = 4   # V219 requests its land in hours 0-3 of day 18
V219_SHOPS = ("PIZZA_SHOP", "FARMERS_MARKET")
V219_SHOP_COUNT = 3
_OWNED_BEFORE_SE = {"NW", "NE", "SW"}

REPORT = {"calls": 0, "buy_requests": 0, "buy_step": None, "skip_cash": 0, "skip_full": 0,
          "skip_v219": 0}


def _farm(observation):
    return observation["farms"][int(observation["player"])]


def se_tiles(board_size=10):
    """Every (x, y) of the SE quadrant, using the engine's quadrant rule (x, y >= size // 2)."""
    half = int(board_size) // 2
    return [(x, y) for y in range(half, int(board_size)) for x in range(half, int(board_size))]


def se_open(observation):
    """True when this player's farm owns the SE quadrant."""
    try:
        return "SE" in (_farm(observation).get("unlocked_quadrants") or [])
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def shop_draw_tonight(observation):
    """True when tonight's end of day draws a shop (so empty tiles tonight move the town)."""
    try:
        day = int(observation["step"]) // TURNS_PER_DAY
        shops = (observation.get("town") or {}).get("unlocked_shops") or []
    except (KeyError, TypeError, ValueError):
        return True
    return (day + 1) % SHOP_UNLOCK_INTERVAL == 0 and len(shops) < MAX_SHOP_INSTANCES


def v219_possible(observation):
    """True while V219's day-18 program could still qualify on its PIZZA_SHOP / FARMERS_MARKET count."""
    try:
        day = int(observation["step"]) // TURNS_PER_DAY
        shops = list((observation.get("town") or {}).get("unlocked_shops") or [])
    except (KeyError, TypeError, ValueError):
        return True
    if day > V219_DAY:
        return False
    have = sum(s in V219_SHOPS for s in shops)
    if day == V219_DAY:
        return have >= V219_SHOP_COUNT
    nights = sum(1 for e in range(day, V219_DAY) if (e + 1) % SHOP_UNLOCK_INTERVAL == 0)
    nights = min(nights, max(0, MAX_SHOP_INSTANCES - len(shops)))
    return have + nights >= V219_SHOP_COUNT


def se_empty(observation):
    """SE tiles of this farm that are empty (None) right now, as (x, y)."""
    try:
        tiles = _farm(observation)["tiles"]
    except (KeyError, IndexError, TypeError, ValueError):
        return []
    return [(x, y) for (x, y) in se_tiles(len(tiles)) if tiles[y][x] is None]


def apply_s3_land(observation, action):
    """Append one SE BUY_LAND when the conditions hold; otherwise return the action unchanged."""
    if not S3_LAND:
        return action
    REPORT["calls"] += 1
    try:
        step = int(observation["step"])
        farm = _farm(observation)
        owned = set(farm.get("unlocked_quadrants") or [])
        money = float(farm.get("money", 0))
    except (KeyError, IndexError, TypeError, ValueError):
        return action
    if owned != _OWNED_BEFORE_SE or not (FIRST_STEP <= step <= LAST_STEP):
        return action
    day, hour = divmod(step, TURNS_PER_DAY)
    if day % SHOP_UNLOCK_INTERVAL != 0 or hour >= BUY_HOURS:
        return action
    if DEFER_TO_V219:
        if day == V219_DAY and hour < V219_REQUEST_HOURS:
            return action
        if day < V219_DAY and v219_possible(observation):
            REPORT["skip_v219"] += 1
            return action
    if not isinstance(action, dict):
        return action
    market = action.get("market")
    if market is None:
        market = []
    if not isinstance(market, list):
        return action
    if any(o and isinstance(o, (list, tuple)) and o[0] == "BUY_LAND" for o in market):
        return action
    if money < SE_PRICE + RESERVE:
        REPORT["skip_cash"] += 1
        return action
    if len(market) >= MAX_ORDERS:
        REPORT["skip_full"] += 1
        return action
    out = dict(action)
    out["market"] = list(market) + [["BUY_LAND"]]
    REPORT["buy_requests"] += 1
    if REPORT["buy_step"] is None:
        REPORT["buy_step"] = step
    return out
