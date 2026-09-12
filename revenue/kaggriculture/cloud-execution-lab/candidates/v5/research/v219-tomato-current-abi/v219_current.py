# SPDX-License-Identifier: Apache-2.0
"""Current-ABI recovery of submitted V3.1 R03/R04 V219 tomato investment.

The submitted V3.1 score path inherited prvsiyan's always-on V219 layer before
V224/V226/V231/V233/E184.  This module ports that finite day-18..29 investment
to the current selected-action ABI without calling a producer/controller.

Current-native adaptation: the installed current controller may still choose its
last route at public step 433.  The donor qualified at step 432 against its fixed
R03 tape family; this adapter therefore qualifies at step 433, still inside the
donor's day-18 request window (hours 0..3).  The caller must provide a detached
full installed-route snapshot plus the SHA-256 authenticated by the shared
``current-route-witness`` seam.  The snapshot is re-hashed here and every later
call must retain the same digest; route drift fails closed.

State is explicit and copy-on-write.  ``apply`` never mutates the caller's state
or selected action, so runtime composition can commit state only after the action
itself is durably returned.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

LAST_STEP = 718
TURNS_PER_DAY = 24
BOARD_SIZE = 10
SHED_CAPACITY = 100
MAX_ORDERS = 10
QUALIFY_STEP = 433
PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
ANIMALS = {"GOOSE", "COW", "SHEEP"}
ANIMAL_COST = {"COW": 400, "SHEEP": 500, "GOOSE": 300}
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}


def new_state() -> dict[str, Any]:
    return {
        "last_step": -1,
        "day": -1,
        "eligible": False,
        "qualified": False,
        "route_sha256": None,
        "committed": False,
        "requested_day": None,
        "pending": None,
        "workers": {},
        "last_work": {},
        "seen_plants": [],
        "lost": [],
        "targets": [(x, y) for y in (5, 6) for x in range(5, 10)],
    }


def _identity(selected: Any, state: Any, reason: str) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    action = copy.deepcopy(selected)
    stable = copy.deepcopy(state) if isinstance(state, dict) else new_state()
    return action, stable, {"applied": False, "reason": reason}


def _plain_int(value: Any, minimum: int | None = None) -> bool:
    return type(value) is int and (minimum is None or value >= minimum)


def _strict_config(configuration: Any) -> bool:
    if not isinstance(configuration, dict):
        return False
    expected = {
        "boardSize": BOARD_SIZE,
        "turnsPerDay": TURNS_PER_DAY,
        "shedCapacity": SHED_CAPACITY,
        "maxMarketOrdersPerTurn": MAX_ORDERS,
        "farmHandCostMult": 1,
    }
    for key, value in expected.items():
        actual = configuration.get(key, value)
        if type(actual) is not int or actual != value:
            return False
    return True


def _canonical_route(route: Any) -> tuple[list[dict[str, Any]], str] | None:
    if not isinstance(route, (list, tuple)) or len(route) <= LAST_STEP:
        return None
    try:
        rendered = json.dumps(list(route), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        recovered = json.loads(rendered)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if recovered != list(route) or not isinstance(recovered, list):
        return None
    for action in recovered:
        if not isinstance(action, dict):
            return None
        if not isinstance(action.get("hands", []), list) or not isinstance(action.get("market", []), list):
            return None
        farmer = action.get("farmer", ["PASS"])
        if not isinstance(farmer, list) or not farmer or not isinstance(farmer[0], str):
            return None
    digest = hashlib.sha256(rendered.encode("ascii")).hexdigest()
    return recovered, digest


def _bind_route(route_snapshot: Any, expected_sha256: Any) -> list[dict[str, Any]] | None:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        return None
    captured = _canonical_route(route_snapshot)
    if captured is None:
        return None
    route, digest = captured
    return route if digest == expected_sha256.lower() else None


def _farm_private(observation: Any) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not isinstance(observation, dict):
        return None
    player = observation.get("player")
    step = observation.get("step")
    farms = observation.get("farms")
    private = observation.get("private")
    if type(player) is not int or player not in (0, 1) or not _plain_int(step, 0):
        return None
    if not isinstance(farms, list) or not (0 <= player < len(farms)) or not isinstance(private, dict):
        return None
    farm = farms[player]
    if not isinstance(farm, dict):
        return None
    if not isinstance(farm.get("hands"), list) or not isinstance(farm.get("tiles"), list):
        return None
    inventories = private.get("inventories")
    shed = private.get("shed")
    seeds = private.get("seeds")
    if not isinstance(inventories, list) or len(inventories) != 1 + len(farm["hands"]):
        return None
    if not isinstance(shed, dict) or not isinstance(seeds, dict):
        return None
    return farm, private


def _selected_shape(selected: Any, worker_count: int) -> bool:
    if not isinstance(selected, dict) or not isinstance(selected.get("market"), list):
        return False
    hands = selected.get("hands")
    farmer = selected.get("farmer")
    if not isinstance(hands, list) or len(hands) != worker_count - 1:
        return False
    commands = [farmer, *hands]
    return all(isinstance(c, list) and c and isinstance(c[0], str) for c in commands)


def _route_day(route: list[dict[str, Any]], day: int) -> list[dict[str, Any]]:
    start = day * TURNS_PER_DAY
    return route[start:min((day + 1) * TURNS_PER_DAY, LAST_STEP + 1)]


def _contains_native_conflict(action: dict[str, Any]) -> bool:
    for order in action.get("market", []):
        if order and order[0] == "BUY_LAND":
            return True
    commands = [action.get("farmer") or ["PASS"], *list(action.get("hands") or [])]
    return any(command == ["PLANT", "TOMATO"] for command in commands)


def _eligible(observation: dict[str, Any], route: list[dict[str, Any]]) -> bool:
    bound = _farm_private(observation)
    if bound is None:
        return False
    farm, private = bound
    market = observation.get("market")
    town = observation.get("town")
    if not isinstance(market, dict) or not isinstance(market.get("prices"), dict):
        return False
    if not isinstance(town, dict) or not isinstance(town.get("unlocked_shops"), list):
        return False
    tiles = farm["tiles"]
    if len(tiles) != BOARD_SIZE or any(not isinstance(row, list) or len(row) != BOARD_SIZE for row in tiles):
        return False
    if set(farm.get("unlocked_quadrants", [])) != {"NW", "NE", "SW"}:
        return False
    money = farm.get("money")
    tomato_price = market["prices"].get("TOMATO")
    if not _plain_int(money, 0) or money < 12000 or not _plain_int(tomato_price, 0) or tomato_price < 70:
        return False
    shops = town["unlocked_shops"]
    if sum(shop in ("PIZZA_SHOP", "FARMERS_MARKET") for shop in shops) < 3:
        return False
    if any(tiles[y][x] != "LOCKED" for y in (5, 6) for x in range(5, 10)):
        return False
    if int(private["seeds"].get("TOMATO", 0)) or int(private["shed"].get("TOMATO", 0)):
        return False
    for row in tiles:
        for tile in row:
            if isinstance(tile, dict) and tile.get("crop") == "TOMATO":
                return False
    for day in range(18, 30):
        for action in _route_day(route, day):
            if _contains_native_conflict(action):
                return False
    return True


def _fib(n: int) -> int:
    a, b = 1, 1
    for _ in range(max(0, n)):
        a, b = b, a + b
    return a


def _beside_shed(position: Any, tiles: list[Any]) -> bool:
    if not isinstance(position, (list, tuple)) or len(position) != 2:
        return False
    center = len(tiles) // 2
    return position[0] in (center - 1, center) and position[1] in (center - 1, center)


def _projected_shed(action: dict[str, Any], observation: dict[str, Any]) -> dict[str, int] | None:
    bound = _farm_private(observation)
    if bound is None:
        return None
    farm, private = bound
    positions = [farm.get("farmer"), *farm.get("hands", [])]
    inventories = private["inventories"]
    stock = {item: max(0, int(private["shed"].get(item, 0))) for item in PRODUCTS}
    for item, value in private["shed"].items():
        try:
            stock[item] = max(0, int(value))
        except (TypeError, ValueError):
            return None
    total = sum(stock.values())
    workers = [action.get("farmer") or ["PASS"], *list(action.get("hands") or [])]
    for actor in range(min(len(workers), len(positions), len(inventories))):
        if not _beside_shed(positions[actor], farm["tiles"]):
            continue
        work = workers[actor]
        if not isinstance(work, list) or not work:
            continue
        inventory = inventories[actor] if isinstance(inventories[actor], dict) else {}
        op = work[0]
        if op == "PICKUP" and len(work) >= 2 and work[1] in stock:
            quantity = max(0, int(work[2]) if len(work) >= 3 else 1)
            taken = min(stock[work[1]], quantity)
            stock[work[1]] -= taken
            total -= taken
        elif op == "DROP":
            for item, held in inventory.items():
                added = min(max(0, int(held)), max(0, SHED_CAPACITY - total))
                if added:
                    stock[item] = stock.get(item, 0) + added
                    total += added
        elif op == "PLACE" and len(work) >= 2 and work[1] not in ANIMALS:
            item = work[1]
            quantity = max(0, int(work[2]) if len(work) >= 3 else 1)
            added = min(quantity, max(0, int(inventory.get(item, 0))), max(0, SHED_CAPACITY - total))
            if added:
                stock[item] = stock.get(item, 0) + added
                total += added
    return stock


def _walk(position: tuple[int, int], target: tuple[int, int]) -> list[str] | None:
    x, y = position
    tx, ty = target
    if x != tx:
        return ["EAST" if x < tx else "WEST"]
    if y != ty:
        return ["SOUTH" if y < ty else "NORTH"]
    return None


def _home(position: tuple[int, int]) -> tuple[int, int]:
    access = ((4, 4), (5, 4), (4, 5), (5, 5))
    return min(access, key=lambda p: (abs(position[0] - p[0]) + abs(position[1] - p[1]), p))


def _request(observation: dict[str, Any], action: dict[str, Any], state: dict[str, Any], route: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
    step = observation["step"]
    day, offset = divmod(step, TURNS_PER_DAY)
    farm = observation["farms"][observation["player"]]
    market = observation["market"]
    if not state.get("committed") and day != 18:
        return action
    if state.get("requested_day") == day or offset > 3:
        return action
    planned = _route_day(route, day)
    if not planned:
        return action
    remaining = planned[offset + 1:]
    if any(order and order[0] == "HIRE" for future in remaining for order in future.get("market", [])):
        report["request_block"] = "future-native-hire"
        return action
    current_market = action.get("market", [])
    parent_hires = sum(bool(order) and order[0] == "HIRE" for order in current_market)
    expected = max((len(future.get("hands", [])) for future in planned), default=len(farm["hands"]))
    if len(farm["hands"]) + parent_hires != expected:
        report["request_block"] = "worker-cardinality"
        return action
    fertilizer = bool(day in (24, 27) and int(market["prices"].get("FERTILIZER", 0)) <= 30)
    crop_workers = 1 if day in (19, 20, 21, 22, 23, 25) and offset <= 2 else (3 if 26 <= day <= 28 else 2)
    count = crop_workers + int(fertilizer and day == 27)
    extra: list[list[Any]] = []
    if not state.get("committed"):
        extra += [["BUY_LAND"], ["BUY_SEED", "TOMATO", 10]]
    if fertilizer:
        extra.append(["BUY_PRODUCT", "FERTILIZER", 10])
    extra += [["HIRE"] for _ in range(count)]
    if len(current_market) + len(extra) > MAX_ORDERS:
        report["request_block"] = "market-capacity"
        return action

    hires_today = farm.get("hires_today")
    money = farm.get("money")
    if not _plain_int(hires_today, 0) or not _plain_int(money, 0):
        report["request_block"] = "malformed-money-hires"
        return action
    budget = sum(_fib(n) for n in range(hires_today, hires_today + parent_hires + count))
    if not state.get("committed"):
        budget += 4500
    if fertilizer:
        budget += 10 * (int(market["prices"].get("FERTILIZER", 0)) + 5)
    for order in current_market:
        if not order:
            continue
        op = order[0]
        if op == "BUY_PRODUCT" and len(order) >= 3:
            budget += int(order[2]) * (int(market["prices"].get(order[1], 0)) + 10)
        elif op == "BUY_ANIMAL" and len(order) >= 3 and order[1] in ANIMAL_COST:
            budget += int(order[2]) * ANIMAL_COST[order[1]]
        elif op == "BUY_SEED" and len(order) >= 3 and order[1] in SEED_COST:
            budget += int(order[2]) * SEED_COST[order[1]]
    if money < budget + 3000:
        report["budget_decline"] = budget + 3000 - money
        return action

    state["pending"] = {
        "step": step,
        "first_actor": expected + 1,
        "count": count,
        "crop_workers": crop_workers,
        "fertilizer": fertilizer,
    }
    state["requested_day"] = day
    if not state.get("committed"):
        state["committed"] = True
        report["commitment"] = True
    changed = copy.deepcopy(action)
    changed["market"] = copy.deepcopy(current_market) + extra
    report["hire_requests"] = count
    report["request_extra"] = copy.deepcopy(extra)
    return changed


def _worker(observation: dict[str, Any], state: dict[str, Any], actor: int, role: dict[str, Any], report: dict[str, Any]) -> list[Any]:
    step = observation["step"]
    day = step // TURNS_PER_DAY
    farm = observation["farms"][observation["player"]]
    private = observation["private"]
    if actor >= len(private["inventories"]):
        return ["PASS"]
    positions = [farm["farmer"], *farm["hands"]]
    if actor >= len(positions):
        return ["PASS"]
    pos = tuple(positions[actor])
    inv = private["inventories"][actor]
    targets = [tuple(target) for target in role["targets"]]

    previous = state["last_work"].get(actor)
    if previous and previous.get("step") == step - 1 and previous.get("command") == ["HARVEST"]:
        gained = max(0, int(inv.get("TOMATO", 0)) - int(previous.get("tomatoes", 0)))
        report["confirmed_harvest_units"] = report.get("confirmed_harvest_units", 0) + gained

    if role.get("needs_fertilizer") and not role.get("loaded"):
        home = _home(pos)
        walk = _walk(pos, home)
        if walk:
            return walk
        desired = 10 if role["kind"] == "fertilizer" else 5
        if int(inv.get("FERTILIZER", 0)) >= desired:
            role["loaded"] = True
        elif role.get("pickup_requested"):
            role["loaded"] = True
            role["fertilizer_available"] = int(inv.get("FERTILIZER", 0))
        elif int(private["shed"].get("FERTILIZER", 0)) >= desired:
            role["pickup_requested"] = True
            return ["PICKUP", "FERTILIZER", desired]
        else:
            role["loaded"] = True

    todo: list[tuple[tuple[int, int], list[Any]]] = []
    seen = {tuple(v) for v in state.get("seen_plants", [])}
    lost = {tuple(v) for v in state.get("lost", [])}
    for target in targets:
        x, y = target
        tile = farm["tiles"][y][x]
        tomato = isinstance(tile, dict) and tile.get("crop") == "TOMATO"
        if tomato and target not in seen:
            seen.add(target)
        if target in seen and not tomato and target not in lost:
            lost.add(target)
        command = None
        if role["kind"] == "fertilizer":
            if tomato and int(tile.get("fertilized_until_day", -1)) < day + 2 and int(inv.get("FERTILIZER", 0)) > 0:
                command = ["FERTILIZE"]
        elif day == 18 and not tomato:
            if tile is None and int(private["seeds"].get("TOMATO", 0)) > 0:
                command = ["PLANT", "TOMATO"]
            elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                command = ["DIG"]
        elif tomato:
            if day < 29 and not tile.get("watered_today"):
                command = ["WATER"]
            elif role.get("needs_fertilizer") and int(tile.get("fertilized_until_day", -1)) < day + 2 and int(inv.get("FERTILIZER", 0)) > 0:
                command = ["FERTILIZE"]
            elif int(tile.get("yield_units", 0)) > 0:
                command = ["HARVEST"]
        if command:
            todo.append((target, command))
    state["seen_plants"] = [list(v) for v in sorted(seen)]
    state["lost"] = [list(v) for v in sorted(lost)]

    home = _home(pos)
    distance = abs(pos[0] - home[0]) + abs(pos[1] - home[1])
    if step >= LAST_STEP - distance and int(inv.get("TOMATO", 0)):
        return _walk(pos, home) or ["PLACE", "TOMATO", int(inv.get("TOMATO", 0))]
    if todo:
        target, command = min(todo, key=lambda value: (
            abs(pos[0] - value[0][0]) + abs(pos[1] - value[0][1]), targets.index(value[0])
        ))
        return _walk(pos, target) or command
    if int(inv.get("TOMATO", 0)):
        return _walk(pos, home) or ["PLACE", "TOMATO", int(inv["TOMATO"])]
    if any(int(v) for v in inv.values() if isinstance(v, (int, float))):
        return _walk(pos, home) or ["DROP"]
    return ["PASS"]


def apply(
    observation: Any,
    selected: Any,
    configuration: Any,
    *,
    enabled: Any,
    route_snapshot: Any,
    route_sha256: Any,
    state: Any = None,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Apply one V219 current-ABI transition and return ``(action,state,report)``.

    ``route_sha256`` must come from the shared current-route witness capture.
    ``route_snapshot`` is a detached full-route value read by the composer; its
    canonical digest must match that witness.  Any mismatch returns identity.
    """
    if enabled is not True:
        return _identity(selected, state, "disabled")
    if not _strict_config(configuration):
        return _identity(selected, state, "unsupported-config")
    bound = _farm_private(observation)
    if bound is None:
        return _identity(selected, state, "malformed-observation")
    farm, _private = bound
    if not _selected_shape(selected, 1 + len(farm["hands"])):
        return _identity(selected, state, "malformed-selected")
    route = _bind_route(route_snapshot, route_sha256)
    if route is None:
        return _identity(selected, state, "route-authority")

    step = observation["step"]
    work = copy.deepcopy(state) if isinstance(state, dict) else new_state()
    if not _plain_int(work.get("last_step", -1)) or step < work.get("last_step", -1):
        work = new_state()
    report: dict[str, Any] = {"applied": False, "reason": "inactive", "step": step}

    if step == QUALIFY_STEP and not work.get("qualified"):
        work["qualified"] = True
        work["eligible"] = _eligible(observation, route)
        work["route_sha256"] = route_sha256
        report["qualified"] = True
        report["eligible"] = bool(work["eligible"])
    elif work.get("qualified") and work.get("route_sha256") != route_sha256:
        work["eligible"] = False
        report["reason"] = "route-drift"
        work["last_step"] = step
        return copy.deepcopy(selected), work, report

    day = step // TURNS_PER_DAY
    if not work.get("eligible") or day < 18:
        work["last_step"] = step
        report["reason"] = "not-eligible"
        return copy.deepcopy(selected), work, report

    if work.get("day") != day:
        work["day"] = day
        work["workers"] = {}
        work["last_work"] = {}

    pending = work.pop("pending", None)
    if pending:
        first = int(pending["first_actor"])
        count = int(pending["count"])
        if len(farm["hands"]) + 1 >= first + count and "SE" in farm.get("unlocked_quadrants", []):
            for index in range(count):
                fertilizer_worker = index == int(pending["crop_workers"])
                crop_workers = int(pending["crop_workers"])
                if fertilizer_worker:
                    targets = work["targets"]
                elif crop_workers == 1:
                    targets = work["targets"]
                elif crop_workers == 2:
                    targets = work["targets"][index * 5:index * 5 + 5]
                else:
                    target_sets = [
                        [(5, 5), (6, 5), (7, 5)],
                        [(8, 5), (9, 5), (9, 6), (8, 6)],
                        [(5, 6), (6, 6), (7, 6)],
                    ]
                    targets = target_sets[index]
                work["workers"][first + index] = {
                    "kind": "fertilizer" if fertilizer_worker else "crop",
                    "targets": copy.deepcopy(targets),
                    "needs_fertilizer": bool(pending["fertilizer"] and (day == 24 or fertilizer_worker)),
                }
            report["confirmed_workers"] = count
        else:
            report["hire_shortfall"] = count

    action = _request(observation, copy.deepcopy(selected), work, route, report)
    if work["workers"]:
        commands = [action.get("farmer") or ["PASS"], *list(action.get("hands") or [])]
        commands += [["PASS"] for _ in range(1 + len(farm["hands"]) - len(commands))]
        for actor_raw, role in list(work["workers"].items()):
            actor = int(actor_raw)
            if actor >= len(commands):
                continue
            command = _worker(observation, work, actor, role, report)
            commands[actor] = command
            work["last_work"][actor] = {
                "step": step,
                "command": copy.deepcopy(command),
                "tomatoes": int(observation["private"]["inventories"][actor].get("TOMATO", 0)),
            }
        action = copy.deepcopy(action)
        action["farmer"], action["hands"] = commands[0], commands[1:]

    market = action.get("market", [])
    if work.get("committed") and len(market) < MAX_ORDERS and not any(
        order and len(order) >= 2 and order[:2] == ["SELL", "TOMATO"] for order in market
    ):
        stock = _projected_shed(action, observation)
        quantity = 0 if stock is None else max(0, int(stock.get("TOMATO", 0)))
        if quantity:
            action = copy.deepcopy(action)
            action["market"] = copy.deepcopy(market) + [["SELL", "TOMATO", quantity]]
            report["tomato_sale_requests"] = quantity

    work["last_step"] = step
    report["applied"] = action != selected
    report["reason"] = "changed" if report["applied"] else "eligible-no-change"
    report["route_sha256"] = route_sha256
    return action, work, report
