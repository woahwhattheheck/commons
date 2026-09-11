"""Apply V4 key plumbing after the frozen V3.1 integration.

V3.1 source is the submitted baseline.  V4 lanes add exact-string edits in this
small follow-on layer so the V3.1 integration recipe remains an immutable receipt.
Every edit is asserted to match exactly once.
"""
import io
import json
import os

KEYS = ("r04_place_delivery", "r04_goose_pass_rescue", "r04_b10_public_supply_order",
        "r04_bakery_yarn_route")


def _replace_once(text, old, new, label):
    count = text.count(old)
    assert count == 1, "%s: expected 1 match, found %d" % (label, count)
    return text.replace(old, new)


def apply(src):
    def read(name):
        return io.open(os.path.join(src, name), encoding="utf-8", newline="").read()

    def write(name, text):
        with io.open(os.path.join(src, name), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    router = read("r04_full_router.py")
    router = _replace_once(
        router,
        "GOOSE_RESCUE = False\n_TERMINAL_FERTILIZER_AGENT = None\n",
        "GOOSE_RESCUE = False\n"
        "PLACE_DELIVERY = False\n"
        "GOOSE_PASS_RESCUE = False\n"
        "B10_PUBLIC_SUPPLY_ORDER = False\n"
        "BAKERY_YARN_ROUTE = False\n"
        "_TERMINAL_FERTILIZER_AGENT = None\n",
        "R04 V4 flags",
    )
    router = _replace_once(
        router,
        "    def act(self, observation):\n",
        "    def act(self, observation, configuration=None):\n",
        "R04 V4 Policy configuration seam",
    )
    router = _replace_once(
        router,
        "        if step == ROUTE_STEP:\n"
        "            shops = observation[\"town\"][\"unlocked_shops\"]\n"
        "            state.plan = SHOP_PLANS.get(tuple(shops[:2]), 0)\n",
        "        if step == ROUTE_STEP:\n"
        "            shops = observation[\"town\"][\"unlocked_shops\"]\n"
        "            state.plan = SHOP_PLANS.get(tuple(shops[:2]), 0)\n"
        "            if BAKERY_YARN_ROUTE and isinstance(shops, list) and shops == [\"BAKERY\", \"YARN_STORE\"]:\n"
        "                expected = ((\"episodeSteps\", 720), (\"turnsPerDay\", 24),\n"
        "                            (\"boardSize\", 10), (\"townShopUnlockInterval\", 3),\n"
        "                            (\"shedCapacity\", 100), (\"maxMarketOrdersPerTurn\", 10))\n"
        "                standard = configuration is not None\n"
        "                for name, required in expected:\n"
        "                    if isinstance(configuration, dict):\n"
        "                        value = configuration.get(name)\n"
        "                    else:\n"
        "                        value = getattr(configuration, name, None)\n"
        "                    if type(value) is not int or value != required:\n"
        "                        standard = False\n"
        "                        break\n"
        "                if isinstance(configuration, dict):\n"
        "                    market_params = configuration.get(\"marketParams\", {})\n"
        "                else:\n"
        "                    market_params = getattr(configuration, \"marketParams\", {})\n"
        "                if standard and isinstance(market_params, dict) and not market_params:\n"
        "                    state.plan = 9\n",
        "R04 V4 bakery-yarn route seam",
    )
    router = _replace_once(
        router,
        "    return _POLICY.act(observation)\n",
        "    return _POLICY.act(observation, configuration)\n",
        "R04 V4 Policy configuration forwarding",
    )
    router = _replace_once(
        router,
        "def _v3_stack(observation, configuration=None):\n"
        "    action = POLICY_AGENT(observation, configuration)\n",
        "def _v3_stack(observation, configuration=None):\n"
        "    action = POLICY_AGENT(observation, configuration)\n"
        "    if PLACE_DELIVERY and configuration is not None:\n"
        "        import r04_place_delivery\n"
        "        action = r04_place_delivery.apply_place_delivery(\n"
        "            observation, action, enabled=True, configuration=configuration)\n"
        "    if GOOSE_PASS_RESCUE:\n"
        "        import r04_goose_pass_rescue\n"
        "        action = r04_goose_pass_rescue.apply_goose_pass_rescue(\n"
        "            action, observation, configuration, enabled=True)\n",
        "R04 V4 stack seams",
    )
    router = _replace_once(
        router,
        "def v3_agent(observation, configuration=None):\n"
        "    global SALE_HORIZON, _TERMINAL_FERTILIZER_AGENT\n"
        "    if not (MIRROR_HORIZON or TERMINAL_FERTILIZER or GOOSE_RESCUE):\n"
        "        return _v3_core(observation, configuration)\n",
        "def v3_agent(observation, configuration=None):\n"
        "    global SALE_HORIZON, _TERMINAL_FERTILIZER_AGENT\n"
        "    if not (MIRROR_HORIZON or TERMINAL_FERTILIZER or GOOSE_RESCUE or PLACE_DELIVERY or GOOSE_PASS_RESCUE or B10_PUBLIC_SUPPLY_ORDER):\n"
        "        return _v3_core(observation, configuration)\n",
        "R04 V4 outer-wrapper dispatch",
    )
    router = _replace_once(
        router,
        "    if GOOSE_RESCUE:\n"
        "        import h3c_goose_eod_cap_rescue\n"
        "        action = h3c_goose_eod_cap_rescue.apply_goose_eod_cap_rescue(action, observation, configuration,\n"
        "                                                                     enabled=True)\n"
        "    return action\n",
        "    if GOOSE_RESCUE:\n"
        "        import h3c_goose_eod_cap_rescue\n"
        "        action = h3c_goose_eod_cap_rescue.apply_goose_eod_cap_rescue(action, observation, configuration,\n"
        "                                                                     enabled=True)\n"
        "    if B10_PUBLIC_SUPPLY_ORDER:\n"
        "        import r04_b10_public_supply_order\n"
        "        if configuration is None:\n"
        "            r04_b10_public_supply_order.invalidate_public_supply_order(observation)\n"
        "        else:\n"
        "            action = r04_b10_public_supply_order.apply_public_supply_order(\n"
        "                observation, action, configuration, enabled=True)\n"
        "    return action\n",
        "R04 B10 outermost seam",
    )
    router = _replace_once(
        router,
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None):\n",
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None,\n"
        "            place_delivery=None, goose_pass_rescue=None, b10_public_supply_order=None,\n"
        "            bakery_yarn_route=None):\n",
        "R04 V4 install parameters",
    )
    router = _replace_once(
        router,
        "    mirror_horizon, terminal_fertilizer and goose_rescue switch the ASTRA lanes B11, B9 and H3c,\n"
        "    applied around the whole agent in v3_agent().\n",
        "    mirror_horizon, terminal_fertilizer and goose_rescue switch the ASTRA lanes B11, B9 and H3c,\n"
        "    applied around the whole agent in v3_agent(). place_delivery converts terminal DROP cargo\n"
        "    deliveries to capacity-bounded PLACE actions so overflow remains on the worker.\n"
        "    goose_pass_rescue banks clipping hour-23 GOOSE eggs when the authored unit action is PASS.\n"
        "    b10_public_supply_order is the outermost V4 market-order transform: it reorders only\n"
        "    existing leading non-WHEAT SELL rows after proved prior-step public rival supply.\n"
        "    bakery_yarn_route remaps only the exact BAKERY->YARN_STORE opening from tape 3 to tape 9\n"
        "    under the exact standard runtime and town-unlock contract.\n",
        "R04 V4 install docs",
    )
    router = _replace_once(
        router,
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE\n",
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE, PLACE_DELIVERY, GOOSE_PASS_RESCUE, B10_PUBLIC_SUPPLY_ORDER, BAKERY_YARN_ROUTE\n",
        "R04 V4 globals",
    )
    router = _replace_once(
        router,
        "    if goose_rescue is not None:\n"
        "        GOOSE_RESCUE = bool(goose_rescue)\n"
        "    return v3_agent\n",
        "    if goose_rescue is not None:\n"
        "        GOOSE_RESCUE = bool(goose_rescue)\n"
        "    if place_delivery is not None:\n"
        "        PLACE_DELIVERY = bool(place_delivery)\n"
        "    if goose_pass_rescue is not None:\n"
        "        GOOSE_PASS_RESCUE = bool(goose_pass_rescue)\n"
        "    if b10_public_supply_order is not None:\n"
        "        B10_PUBLIC_SUPPLY_ORDER = bool(b10_public_supply_order)\n"
        "    if bakery_yarn_route is not None:\n"
        "        BAKERY_YARN_ROUTE = bool(bakery_yarn_route)\n"
        "    return v3_agent\n",
        "R04 V4 install setters",
    )
    write("r04_full_router.py", router)

    runtime = read("titan_runtime.py")
    runtime = _replace_once(
        runtime,
        "    r04_goose_rescue: bool = True\n\n    def __post_init__(self):",
        "    r04_goose_rescue: bool = True\n"
        "    r04_place_delivery: bool = False\n"
        "    r04_goose_pass_rescue: bool = False\n"
        "    r04_b10_public_supply_order: bool = False\n"
        "    r04_bakery_yarn_route: bool = False\n\n    def __post_init__(self):",
        "Features V4 fields",
    )
    runtime = _replace_once(
        runtime,
        "                                 terminal_fertilizer=bool(self.features.r04_terminal_fertilizer),\n"
        "                                 goose_rescue=bool(self.features.r04_goose_rescue))(observation, configuration)\n",
        "                                 terminal_fertilizer=bool(self.features.r04_terminal_fertilizer),\n"
        "                                 goose_rescue=bool(self.features.r04_goose_rescue),\n"
        "                                 place_delivery=bool(self.features.r04_place_delivery),\n"
        "                                 goose_pass_rescue=bool(self.features.r04_goose_pass_rescue),\n"
        "                                 b10_public_supply_order=bool(self.features.r04_b10_public_supply_order),\n"
        "                                 bakery_yarn_route=bool(self.features.r04_bakery_yarn_route))(observation, configuration)\n",
        "TitanAgent V4 install arguments",
    )
    runtime = _replace_once(
        runtime,
        "                self.diagnostics['goose_rescue'] = bool(self.features.r04_goose_rescue)\n",
        "                self.diagnostics['goose_rescue'] = bool(self.features.r04_goose_rescue)\n"
        "                self.diagnostics['place_delivery'] = bool(self.features.r04_place_delivery)\n"
        "                self.diagnostics['goose_pass_rescue'] = bool(self.features.r04_goose_pass_rescue)\n"
        "                self.diagnostics['b10_public_supply_order'] = bool(self.features.r04_b10_public_supply_order)\n"
        "                self.diagnostics['bakery_yarn_route'] = bool(self.features.r04_bakery_yarn_route)\n",
        "TitanAgent V4 diagnostics",
    )
    write("titan_runtime.py", runtime)

    cfg_path = os.path.join(src, "TITAN-CONFIG.json")
    data = json.loads(io.open(cfg_path, encoding="utf-8").read())
    for key in KEYS:
        assert key not in data, key
        data[key] = False
    with io.open(cfg_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")
    return src
