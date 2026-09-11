"""Apply V4 key plumbing after the frozen V3.1 integration.

V3.1 source is the submitted baseline.  V4 lanes add exact-string edits in this
small follow-on layer so the V3.1 integration recipe remains an immutable receipt.
Every edit is asserted to match exactly once.
"""
import io
import json
import os

KEY = "r04_place_delivery"
S8_EGG_CARE_KEY = "r04_s8_egg_care"


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
        "GOOSE_RESCUE = False\nPLACE_DELIVERY = False\n_TERMINAL_FERTILIZER_AGENT = None\n",
        "R04 place-delivery flag",
    )
    router = _replace_once(
        router,
        "def _v3_stack(observation, configuration=None):\n"
        "    action = POLICY_AGENT(observation, configuration)\n",
        "def _v3_stack(observation, configuration=None):\n"
        "    action = POLICY_AGENT(observation, configuration)\n"
        "    if PLACE_DELIVERY:\n"
        "        import r04_place_delivery\n"
        "        action = r04_place_delivery.apply_place_delivery(observation, action, enabled=True)\n",
        "R04 place-delivery seam",
    )
    router = _replace_once(
        router,
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None):\n",
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None,\n"
        "            place_delivery=None):\n",
        "R04 place-delivery install parameter",
    )
    router = _replace_once(
        router,
        "    mirror_horizon, terminal_fertilizer and goose_rescue switch the ASTRA lanes B11, B9 and H3c,\n"
        "    applied around the whole agent in v3_agent().\n",
        "    mirror_horizon, terminal_fertilizer and goose_rescue switch the ASTRA lanes B11, B9 and H3c,\n"
        "    applied around the whole agent in v3_agent(). place_delivery converts terminal DROP cargo\n"
        "    deliveries to capacity-bounded PLACE actions so overflow remains on the worker.\n",
        "R04 place-delivery install docs",
    )
    router = _replace_once(
        router,
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE\n",
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE, PLACE_DELIVERY\n",
        "R04 place-delivery global",
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
        "    return v3_agent\n",
        "R04 place-delivery install setter",
    )

    # S8: resource-neutral EGG care reallocation. Apply after H3c so a clipping
    # rescue that already converted COLLECT_FERTILIZER -> HARVEST keeps priority.
    router = _replace_once(
        router,
        "GOOSE_RESCUE = False\nPLACE_DELIVERY = False\n_TERMINAL_FERTILIZER_AGENT = None\n",
        "GOOSE_RESCUE = False\nPLACE_DELIVERY = False\nS8_EGG_CARE = False\n_TERMINAL_FERTILIZER_AGENT = None\n",
        "R04 S8 egg-care flag",
    )
    router = _replace_once(
        router,
        "    if not (MIRROR_HORIZON or TERMINAL_FERTILIZER or GOOSE_RESCUE):\n",
        "    if not (MIRROR_HORIZON or TERMINAL_FERTILIZER or GOOSE_RESCUE or S8_EGG_CARE):\n",
        "R04 S8 outer-wrapper activation",
    )
    router = _replace_once(
        router,
        "    return action\n\n\ndef install(host=None, horizon=None, opening=None, row_order=None, evening_flush=None,\n",
        "    if S8_EGG_CARE:\n"
        "        import r04_s8_egg_care\n"
        "        action = r04_s8_egg_care.apply_egg_care(observation, action, configuration, enabled=True)\n"
        "    return action\n\n\ndef install(host=None, horizon=None, opening=None, row_order=None, evening_flush=None,\n",
        "R04 S8 post-H3c seam",
    )
    router = _replace_once(
        router,
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None,\n"
        "            place_delivery=None):\n",
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None,\n"
        "            place_delivery=None, s8_egg_care=None):\n",
        "R04 S8 install parameter",
    )
    router = _replace_once(
        router,
        "    deliveries to capacity-bounded PLACE actions so overflow remains on the worker.\n",
        "    deliveries to capacity-bounded PLACE actions so overflow remains on the worker.\n"
        "    s8_egg_care may trade an hour-23 goose fertilizer collection for CARE after H3c,\n"
        "    only behind its shipped-off public-price/cap guard.\n",
        "R04 S8 install docs",
    )
    router = _replace_once(
        router,
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE, PLACE_DELIVERY\n",
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE, PLACE_DELIVERY, S8_EGG_CARE\n",
        "R04 S8 global",
    )
    router = _replace_once(
        router,
        "    if place_delivery is not None:\n"
        "        PLACE_DELIVERY = bool(place_delivery)\n"
        "    return v3_agent\n",
        "    if place_delivery is not None:\n"
        "        PLACE_DELIVERY = bool(place_delivery)\n"
        "    if s8_egg_care is not None:\n"
        "        S8_EGG_CARE = bool(s8_egg_care)\n"
        "    return v3_agent\n",
        "R04 S8 install setter",
    )
    write("r04_full_router.py", router)

    runtime = read("titan_runtime.py")
    runtime = _replace_once(
        runtime,
        "    r04_goose_rescue: bool = True\n\n    def __post_init__(self):",
        "    r04_goose_rescue: bool = True\n"
        "    r04_place_delivery: bool = False\n\n    def __post_init__(self):",
        "Features place-delivery field",
    )
    runtime = _replace_once(
        runtime,
        "                                 terminal_fertilizer=bool(self.features.r04_terminal_fertilizer),\n"
        "                                 goose_rescue=bool(self.features.r04_goose_rescue))(observation, configuration)\n",
        "                                 terminal_fertilizer=bool(self.features.r04_terminal_fertilizer),\n"
        "                                 goose_rescue=bool(self.features.r04_goose_rescue),\n"
        "                                 place_delivery=bool(self.features.r04_place_delivery))(observation, configuration)\n",
        "TitanAgent place-delivery install argument",
    )
    runtime = _replace_once(
        runtime,
        "                self.diagnostics['goose_rescue'] = bool(self.features.r04_goose_rescue)\n",
        "                self.diagnostics['goose_rescue'] = bool(self.features.r04_goose_rescue)\n"
        "                self.diagnostics['place_delivery'] = bool(self.features.r04_place_delivery)\n",
        "TitanAgent place-delivery diagnostics",
    )

    runtime = _replace_once(
        runtime,
        "    r04_place_delivery: bool = False\n\n    def __post_init__(self):",
        "    r04_place_delivery: bool = False\n"
        "    r04_s8_egg_care: bool = False\n\n    def __post_init__(self):",
        "Features S8 egg-care field",
    )
    runtime = _replace_once(
        runtime,
        "                                 goose_rescue=bool(self.features.r04_goose_rescue),\n"
        "                                 place_delivery=bool(self.features.r04_place_delivery))(observation, configuration)\n",
        "                                 goose_rescue=bool(self.features.r04_goose_rescue),\n"
        "                                 place_delivery=bool(self.features.r04_place_delivery),\n"
        "                                 s8_egg_care=bool(self.features.r04_s8_egg_care))(observation, configuration)\n",
        "TitanAgent S8 egg-care install argument",
    )
    runtime = _replace_once(
        runtime,
        "                self.diagnostics['place_delivery'] = bool(self.features.r04_place_delivery)\n",
        "                self.diagnostics['place_delivery'] = bool(self.features.r04_place_delivery)\n"
        "                self.diagnostics['s8_egg_care'] = bool(self.features.r04_s8_egg_care)\n",
        "TitanAgent S8 egg-care diagnostics",
    )
    write("titan_runtime.py", runtime)

    cfg_path = os.path.join(src, "TITAN-CONFIG.json")
    data = json.loads(io.open(cfg_path, encoding="utf-8").read())
    assert KEY not in data, KEY
    data[KEY] = False
    assert S8_EGG_CARE_KEY not in data, S8_EGG_CARE_KEY
    data[S8_EGG_CARE_KEY] = False
    with io.open(cfg_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")
    return src
