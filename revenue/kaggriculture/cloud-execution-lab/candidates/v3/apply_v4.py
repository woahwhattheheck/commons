"""Apply V4 key plumbing after the frozen V3.1 integration.

V3.1 source is the submitted baseline.  V4 lanes add exact-string edits in this
small follow-on layer so the V3.1 integration recipe remains an immutable receipt.
Every edit is asserted to match exactly once.
"""
import io
import json
import os

KEYS = ("r04_place_delivery", "r04_goose_pass_rescue", "r04_s6_fert_roi")


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
        "S6_FERT_ROI = False\n"
        "_TERMINAL_FERTILIZER_AGENT = None\n",
        "R04 V4 flags",
    )
    router = _replace_once(
        router,
        "def _v3_stack(observation, configuration=None):\n"
        "    action = POLICY_AGENT(observation, configuration)\n",
        "def _v3_stack(observation, configuration=None):\n"
        "    action = POLICY_AGENT(observation, configuration)\n"
        "    if PLACE_DELIVERY:\n"
        "        import r04_place_delivery\n"
        "        action = r04_place_delivery.apply_place_delivery(observation, action, enabled=True)\n"
        "    if GOOSE_PASS_RESCUE:\n"
        "        import r04_goose_pass_rescue\n"
        "        action = r04_goose_pass_rescue.apply_goose_pass_rescue(\n"
        "            action, observation, configuration, enabled=True)\n",
        "R04 V4 stack seams",
    )
    router = _replace_once(
        router,
        "    if FERT_HAND:\n"
        "        if _FERT_HAND_AGENT is None:\n"
        "            import r04_fert_hand\n"
        "            r04_fert_hand.FERT_HAND = True\n"
        "            _FERT_HAND_AGENT = r04_fert_hand.wrap(_v3_stack, _policy_tape)\n"
        "        return _FERT_HAND_AGENT(observation, configuration)\n",
        "    if FERT_HAND:\n"
        "        import r04_fert_hand\n"
        "        r04_fert_hand.FERT_HAND = True\n"
        "        s6_enabled = False\n"
        "        if S6_FERT_ROI:\n"
        "            try:\n"
        "                import r04_s6_fert_roi\n"
        "                s6_enabled = r04_s6_fert_roi.standard_configuration(configuration)\n"
        "            except Exception:\n"
        "                s6_enabled = False\n"
        "        r04_fert_hand.S6_FERT_ROI = bool(s6_enabled)\n"
        "        if _FERT_HAND_AGENT is None:\n"
        "            _FERT_HAND_AGENT = r04_fert_hand.wrap(_v3_stack, _policy_tape)\n"
        "        return _FERT_HAND_AGENT(observation, configuration)\n",
        "R04 S6 fertilizer-ROI fert-hand propagation",
    )
    router = _replace_once(
        router,
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None):\n",
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None,\n"
        "            place_delivery=None, goose_pass_rescue=None, s6_fert_roi=None):\n",
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
        "    s6_fert_roi changes only idle target selection inside an already-hired r04_fert_hand,\n"
        "    after reserving all incumbent CARROT work already present or authored later today.\n",
        "R04 V4 install docs",
    )
    router = _replace_once(
        router,
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE\n",
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE, PLACE_DELIVERY, GOOSE_PASS_RESCUE, S6_FERT_ROI\n",
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
        "    if s6_fert_roi is not None:\n"
        "        S6_FERT_ROI = bool(s6_fert_roi)\n"
        "    return v3_agent\n",
        "R04 V4 install setters",
    )
    write("r04_full_router.py", router)

    fert_hand = read("r04_fert_hand.py")
    fert_hand = _replace_once(
        fert_hand,
        "FERT_HAND = False\nDAYS = (24, 25, 26, 27, 28)\n",
        "FERT_HAND = False\nS6_FERT_ROI = False\nDAYS = (24, 25, 26, 27, 28)\n",
        "fert-hand S6 flag",
    )
    fert_hand = _replace_once(
        fert_hand,
        "    if held <= 0:\n"
        "        return [\"PASS\"]\n"
        "    if any((t[0], t[1]) == pos for t in targets):\n",
        "    if held <= 0:\n"
        "        return [\"PASS\"]\n"
        "    s6_future_carrots = None\n"
        "    if S6_FERT_ROI:\n"
        "        try:\n"
        "            s6_future_carrots = _future_plantings(tape, step)\n"
        "        except Exception:\n"
        "            s6_future_carrots = None\n"
        "    if S6_FERT_ROI and s6_future_carrots == 0:\n"
        "        try:\n"
        "            import r04_s6_fert_roi\n"
        "            target = r04_s6_fert_roi.choose_fert_hand_target(observation, pos, upcoming)\n"
        "        except Exception:\n"
        "            target = None\n"
        "        if target is not None:\n"
        "            goal = tuple(target[\"position\"])\n"
        "            if goal == pos:\n"
        "                REPORT[\"fertilized\"] += 1\n"
        "                r04_s6_fert_roi.record_fertilize(target)\n"
        "                return [\"FERTILIZE\"]\n"
        "            return _step_toward(pos, goal, sheds)\n"
        "    if any((t[0], t[1]) == pos for t in targets):\n",
        "fert-hand S6 target selection",
    )
    write("r04_fert_hand.py", fert_hand)

    runtime = read("titan_runtime.py")
    runtime = _replace_once(
        runtime,
        "    r04_goose_rescue: bool = True\n\n    def __post_init__(self):",
        "    r04_goose_rescue: bool = True\n"
        "    r04_place_delivery: bool = False\n"
        "    r04_goose_pass_rescue: bool = False\n"
        "    r04_s6_fert_roi: bool = False\n\n    def __post_init__(self):",
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
        "                                 s6_fert_roi=bool(self.features.r04_s6_fert_roi))(observation, configuration)\n",
        "TitanAgent V4 install arguments",
    )
    runtime = _replace_once(
        runtime,
        "                self.diagnostics['goose_rescue'] = bool(self.features.r04_goose_rescue)\n",
        "                self.diagnostics['goose_rescue'] = bool(self.features.r04_goose_rescue)\n"
        "                self.diagnostics['place_delivery'] = bool(self.features.r04_place_delivery)\n"
        "                self.diagnostics['goose_pass_rescue'] = bool(self.features.r04_goose_pass_rescue)\n"
        "                self.diagnostics['s6_fert_roi'] = bool(self.features.r04_s6_fert_roi)\n",
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
