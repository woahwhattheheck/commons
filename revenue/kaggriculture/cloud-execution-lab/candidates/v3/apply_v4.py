"""Apply V4 key plumbing after the frozen V3.1 integration.

V3.1 source is the submitted baseline.  V4 lanes add exact-string edits in this
small follow-on layer so the V3.1 integration recipe remains an immutable receipt.
Every edit is asserted to match exactly once.
"""
import io
import json
import os

PLACE_KEY = "r04_place_delivery"
FERT_MIX_KEY = "r04_fert_mix"


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

    # F1: preserve the shipped fertilizer hand's hire/purchase decision exactly.
    # The new lane only post-processes that already-existing hand when it would PASS.
    router = _replace_once(
        router,
        "GOOSE_RESCUE = False\nPLACE_DELIVERY = False\n_TERMINAL_FERTILIZER_AGENT = None\n",
        "GOOSE_RESCUE = False\nPLACE_DELIVERY = False\nFERT_MIX = False\n"
        "_TERMINAL_FERTILIZER_AGENT = None\n",
        "R04 fert-mix flag",
    )
    router = _replace_once(
        router,
        "        return _FERT_HAND_AGENT(observation, configuration)\n"
        "    return _v3_stack(observation, configuration)\n",
        "        action = _FERT_HAND_AGENT(observation, configuration)\n"
        "        if FERT_MIX:\n"
        "            import r04_fert_mix\n"
        "            action = r04_fert_mix.apply_fert_mix(observation, action, enabled=True)\n"
        "        return action\n"
        "    return _v3_stack(observation, configuration)\n",
        "R04 fert-mix post-fert-hand seam",
    )
    router = _replace_once(
        router,
        "            place_delivery=None):\n",
        "            place_delivery=None, fert_mix=None):\n",
        "R04 fert-mix install parameter",
    )
    router = _replace_once(
        router,
        "    deliveries to capacity-bounded PLACE actions so overflow remains on the worker.\n",
        "    deliveries to capacity-bounded PLACE actions so overflow remains on the worker. fert_mix only\n"
        "    reallocates otherwise-idle work from the already-shipped fertilizer hand; it never hires.\n",
        "R04 fert-mix install docs",
    )
    router = _replace_once(
        router,
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE, PLACE_DELIVERY\n",
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE, PLACE_DELIVERY, FERT_MIX\n",
        "R04 fert-mix global",
    )
    router = _replace_once(
        router,
        "    if place_delivery is not None:\n"
        "        PLACE_DELIVERY = bool(place_delivery)\n"
        "    return v3_agent\n",
        "    if place_delivery is not None:\n"
        "        PLACE_DELIVERY = bool(place_delivery)\n"
        "    if fert_mix is not None:\n"
        "        FERT_MIX = bool(fert_mix)\n"
        "    return v3_agent\n",
        "R04 fert-mix install setter",
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
        "    r04_fert_mix: bool = False\n\n    def __post_init__(self):",
        "Features fert-mix field",
    )
    runtime = _replace_once(
        runtime,
        "                                 place_delivery=bool(self.features.r04_place_delivery))(observation, configuration)\n",
        "                                 place_delivery=bool(self.features.r04_place_delivery),\n"
        "                                 fert_mix=bool(self.features.r04_fert_mix))(observation, configuration)\n",
        "TitanAgent fert-mix install argument",
    )
    runtime = _replace_once(
        runtime,
        "                self.diagnostics['place_delivery'] = bool(self.features.r04_place_delivery)\n",
        "                self.diagnostics['place_delivery'] = bool(self.features.r04_place_delivery)\n"
        "                self.diagnostics['fert_mix'] = bool(self.features.r04_fert_mix)\n",
        "TitanAgent fert-mix diagnostics",
    )
    write("titan_runtime.py", runtime)

    cfg_path = os.path.join(src, "TITAN-CONFIG.json")
    data = json.loads(io.open(cfg_path, encoding="utf-8").read())
    assert PLACE_KEY not in data, PLACE_KEY
    assert FERT_MIX_KEY not in data, FERT_MIX_KEY
    data[PLACE_KEY] = False
    data[FERT_MIX_KEY] = False
    with io.open(cfg_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")
    return src
