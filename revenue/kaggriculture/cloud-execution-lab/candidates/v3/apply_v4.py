"""Apply V4 key plumbing after the frozen V3.1 integration.

V3.1 source is the submitted baseline.  V4 lanes add exact-string edits in this
small follow-on layer so the V3.1 integration recipe remains an immutable receipt.
Every edit is asserted to match exactly once.
"""
import io
import json
import os

KEYS = ("r04_place_delivery", "r04_goose_pass_rescue", "r04_s2_herd_scale")


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

    # S2 parameterizes the shipped V233 livestock controller. OFF reproduces
    # its 6-sheep / 2-worker footprint exactly; ON buys/services two extra
    # sheep without changing the two-worker / two-HIRE native-hand footprint.
    router = _replace_once(
        router,
        "def _v233_eligible(obs,native):\n"
        "    farm=obs['farms'][obs['player']];prices=obs['market']['prices']\n"
        "    if len(farm['tiles'])!=10 or set(farm['unlocked_quadrants'])!={'NW','NE','SW'}:return False\n"
        "    if obs['town']['unlocked_shops'].count('YARN_STORE')<2 or prices['WOOL']<220 or prices['WHEAT']>45:return False\n"
        "    if any(farm['tiles'][y][x]!='LOCKED' for y in (5,6) for x in range(5,8)):return False\n",
        "def _v233_eligible(obs,native):\n"
        "    farm=obs['farms'][obs['player']];prices=obs['market']['prices'];profile=_v4_s2_profile()\n"
        "    if len(farm['tiles'])!=10 or set(farm['unlocked_quadrants'])!={'NW','NE','SW'}:return False\n"
        "    if obs['town']['unlocked_shops'].count('YARN_STORE')<2 or prices['WOOL']<220 or prices['WHEAT']>45:return False\n"
        "    if any(farm['tiles'][y][x]!='LOCKED' for targets in profile['targets'] for x,y in targets):return False\n",
        "S2 V233 eligibility targets",
    )
    router = _replace_once(
        router,
        "    initial=not state.get('committed')\n"
        "    extra=([['BUY_LAND'],['BUY_ANIMAL','SHEEP',6]] if initial else [])+[['BUY_PRODUCT','WHEAT',6],['HIRE'],['HIRE']]\n"
        "    if len(market)+len(extra)>MAX_ORDERS:return action\n"
        "    stock=projected_shed(action,FarmView(obs))\n"
        "    incoming=6+6*initial\n"
        "    budget=7000*initial+6*(int(obs['market']['prices']['WHEAT'])+10)\n"
        "    budget+=sum(_v219_fib(n) for n in range(farm['hires_today'],farm['hires_today']+parent_hires+2))\n",
        "    initial=not state.get('committed');profile=_v4_s2_profile()\n"
        "    sheep=profile['sheep'];workers=profile['workers']\n"
        "    extra=([['BUY_LAND'],['BUY_ANIMAL','SHEEP',sheep]] if initial else [])+[['BUY_PRODUCT','WHEAT',sheep]]+[['HIRE'] for _ in range(workers)]\n"
        "    if len(market)+len(extra)>MAX_ORDERS:return action\n"
        "    stock=projected_shed(action,FarmView(obs))\n"
        "    incoming=sheep+sheep*initial\n"
        "    budget=_v4_s2_initial_fixed_cost(profile)*initial+sheep*(int(obs['market']['prices']['WHEAT'])+10)\n"
        "    budget+=sum(_v219_fib(n) for n in range(farm['hires_today'],farm['hires_today']+parent_hires+workers))\n",
        "S2 V233 request profile",
    )
    router = _replace_once(
        router,
        "    state['requested_day']=day\n"
        "    state['pending']={'first':expected+1,'initial':initial}\n"
        "    _V233_REPORT['sheep_hire_requests']+=2;_V233_REPORT['sheep_feed_buy_requests']+=6\n",
        "    state['requested_day']=day\n"
        "    state['pending']={'first':expected+1,'initial':initial,'sheep':sheep,\n"
        "                      'workers':workers,'targets':tuple(tuple(site for site in group) for group in profile['targets'])}\n"
        "    _V233_REPORT['sheep_hire_requests']+=workers;_V233_REPORT['sheep_feed_buy_requests']+=sheep\n",
        "S2 V233 pending profile",
    )
    router = _replace_once(
        router,
        "    shortage=hungry-carried-stock.get('WHEAT',0)\n"
        "    if not 0<shortage<=6 or state.get('rescue_today',0)+shortage>6:return action\n",
        "    shortage=hungry-carried-stock.get('WHEAT',0)\n"
        "    rescue_cap=sum(len(targets) for targets in state['workers'].values())\n"
        "    if not 0<shortage<=rescue_cap or state.get('rescue_today',0)+shortage>rescue_cap:return action\n",
        "S2 V233 rescue cap",
    )
    router = _replace_once(
        router,
        "    pending=state.pop('pending',None)\n"
        "    if pending:\n"
        "        funded='SE' in farm['unlocked_quadrants'] and (not pending['initial'] or private['shed'].get('SHEEP',0)>=6)\n"
        "        if not funded:_V233_REPORT['sheep_purchase_shortfalls']+=1\n"
        "        elif len(farm['hands'])<pending['first']+1:_V233_REPORT['sheep_hire_shortfalls']+=1\n"
        "        else:\n"
        "            for i in range(2):state['workers'][pending['first']+i]=[(x,5+i) for x in range(5,8)]\n"
        "            _V233_REPORT['sheep_workers_confirmed']+=2\n",
        "    pending=state.pop('pending',None)\n"
        "    if pending:\n"
        "        sheep=pending.get('sheep',6);workers=pending.get('workers',2)\n"
        "        targets=tuple(tuple(site for site in group) for group in pending.get('targets',(((5,5),(6,5),(7,5)),((5,6),(6,6),(7,6)))))\n"
        "        funded=('SE' in farm['unlocked_quadrants'] and len(targets)==workers\n"
        "                and sum(len(group) for group in targets)==sheep\n"
        "                and (not pending['initial'] or private['shed'].get('SHEEP',0)>=sheep))\n"
        "        if not funded:_V233_REPORT['sheep_purchase_shortfalls']+=1\n"
        "        elif len(farm['hands'])<pending['first']+workers-1:_V233_REPORT['sheep_hire_shortfalls']+=1\n"
        "        else:\n"
        "            for i,group in enumerate(targets):state['workers'][pending['first']+i]=list(group)\n"
        "            _V233_REPORT['sheep_workers_confirmed']+=workers\n",
        "S2 V233 confirmation profile",
    )

    router = _replace_once(
        router,
        "GOOSE_RESCUE = False\n_TERMINAL_FERTILIZER_AGENT = None\n",
        "GOOSE_RESCUE = False\n"
        "PLACE_DELIVERY = False\n"
        "GOOSE_PASS_RESCUE = False\n"
        "S2_HERD_SCALE = False\n"
        "_TERMINAL_FERTILIZER_AGENT = None\n",
        "R04 V4 flags",
    )
    router = _replace_once(
        router,
        "def _v3_stack(observation, configuration=None):\n"
        "    action = POLICY_AGENT(observation, configuration)\n",
        "def _v4_s2_profile():\n"
        "    import r04_s2_herd_scale\n"
        "    return r04_s2_herd_scale.v233_profile(S2_HERD_SCALE)\n"
        "\n"
        "\n"
        "def _v4_s2_initial_fixed_cost(profile):\n"
        "    import r04_s2_herd_scale\n"
        "    return r04_s2_herd_scale.initial_fixed_cost(profile)\n"
        "\n"
        "\n"
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
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None):\n",
        "            dribble_dump=None, mirror_horizon=None, terminal_fertilizer=None, goose_rescue=None,\n"
        "            place_delivery=None, goose_pass_rescue=None, s2_herd_scale=None):\n",
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
        "    s2_herd_scale widens the existing financed V233 sheep controller from six to eight sheep\n"
        "    while preserving its two-worker/two-HIRE native hand-count footprint.\n",
        "R04 V4 install docs",
    )
    router = _replace_once(
        router,
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE\n",
        "    global MIRROR_HORIZON, TERMINAL_FERTILIZER, GOOSE_RESCUE, PLACE_DELIVERY, GOOSE_PASS_RESCUE, S2_HERD_SCALE\n",
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
        "    if s2_herd_scale is not None:\n"
        "        S2_HERD_SCALE = bool(s2_herd_scale)\n"
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
        "    r04_s2_herd_scale: bool = False\n\n    def __post_init__(self):",
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
        "                                 s2_herd_scale=bool(self.features.r04_s2_herd_scale))(observation, configuration)\n",
        "TitanAgent V4 install arguments",
    )
    runtime = _replace_once(
        runtime,
        "                self.diagnostics['goose_rescue'] = bool(self.features.r04_goose_rescue)\n",
        "                self.diagnostics['goose_rescue'] = bool(self.features.r04_goose_rescue)\n"
        "                self.diagnostics['place_delivery'] = bool(self.features.r04_place_delivery)\n"
        "                self.diagnostics['goose_pass_rescue'] = bool(self.features.r04_goose_pass_rescue)\n"
        "                self.diagnostics['s2_herd_scale'] = bool(self.features.r04_s2_herd_scale)\n",
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
