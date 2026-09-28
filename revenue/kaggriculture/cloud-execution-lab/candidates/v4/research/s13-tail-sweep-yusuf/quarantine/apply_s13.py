"""Second-stage V3 integration for the default-OFF S13 tail settlement lane.

Run only after apply_v3.apply().  This keeps the shared V3 generator untouched:
the builder first produces the established V3 runtime, then this exact-anchor
stage adds one feature key and one pre-production hook.  The shipped transform
and the current-turn projector are both source-bound before any package edit.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys

TAIL_SHA256 = "ead794d663a01967723932613fef800a0345b67daabefcf6799c812c933a6a54"

POST_UNITS_ANCHOR = '''def post_units(obs, action, config, *, shed_capacity=None):
    """Exact deterministic engine unit stage on the player's observed farm."""
    farm = detached_json_value(obs['farms'][obs['player']])
    private = detached_json_value(obs['private'])
    acts = [action.get('farmer',['PASS']), *action.get('hands',[])]
    demand = {}
    for a in acts:
        if a and a[0]=='PLANT' and len(a)>1:
            demand[a[1]]=demand.get(a[1],0)+1
    blocked={p for p,n in demand.items() if n>private['seeds'].get(p,0)}
    capacity=int(config.get('shedCapacity',100)) if shed_capacity is None else int(shed_capacity)
    for i,a in enumerate(acts):
        if a and a[0]=='PLANT' and a[1] in blocked:a=['PASS']
        m._apply_unit_action(farm,private,i,a,len(farm['tiles']),int(obs['step'])//int(config.get('turnsPerDay',24)),int(config.get('turnsPerDay',24)),capacity)
    return farm, private
'''

RELEASE_NOTE = '''

S13 tail sweep (`s13_tail_sweep`, shipped off) runs on the completed selected
action in `TitanAgent._v3_post`, immediately before `_finish_production`.  It
uses the package's pinned `scheduler.post_units` current-turn projector and the
observation's unlocked-shop product set.  The pinned transform grows only
already-executable SELL rows and, with its default consumption guard, waits
until each product is past its final applicable shop/town absorption tick.
Reserve-aware mode is deliberately not wired here: no reserve provider is part
of this integration.  Whole-game value is a paired-panel measurement, not a
proof claim; the transform's report certifies execution/funding only.
'''


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    assert count == 1, "%s: expected 1 match, found %d" % (label, count)
    return text.replace(old, new, 1)


def _read(src: str, name: str) -> str:
    return io.open(os.path.join(src, name), encoding="utf-8", newline="").read()


def _write(src: str, name: str, text: str) -> None:
    with io.open(os.path.join(src, name), "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _bind_sources(src: str) -> None:
    tail_path = os.path.join(src, "tail_settlement.py")
    with open(tail_path, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    assert digest == TAIL_SHA256, "tail_settlement.py drift: %s" % digest
    scheduler = _read(src, "scheduler.py")
    assert scheduler.count(POST_UNITS_ANCHOR) == 1, "scheduler.post_units projector drift"


def apply(src: str) -> str:
    _bind_sources(src)

    runtime = _read(src, "titan_runtime.py")
    runtime = _replace_once(
        runtime,
        "    r02_route_bank: bool = False\n\n    def __post_init__(self):",
        "    r02_route_bank: bool = False\n"
        "    # S13 tail settlement: exact funded late SELL completion, default OFF.\n"
        "    s13_tail_sweep: bool = False\n\n"
        "    def __post_init__(self):",
        "S13 feature field",
    )
    runtime = _replace_once(
        runtime,
        "                    or f.r01_shop_router or f.r02_route_bank)\n\n"
        "    def _v3_config(self):",
        "                    or f.r01_shop_router or f.r02_route_bank or f.s13_tail_sweep)\n\n"
        "    def _v3_config(self):",
        "S13 active key",
    )
    runtime = _replace_once(
        runtime,
        "                'e20_hire_guard': bool(f.e20_hire_guard),\n"
        "                'params': {'rival_dump_price_drop': float(f.rival_dump_price_drop),",
        "                'e20_hire_guard': bool(f.e20_hire_guard),\n"
        "                's13_tail_sweep': bool(f.s13_tail_sweep),\n"
        "                'params': {'rival_dump_price_drop': float(f.rival_dump_price_drop),",
        "S13 config projection",
    )
    runtime = _replace_once(
        runtime,
        "        if not (v3.get('rival_model') or v3.get('e20_hire_guard')):\n"
        "            return output\n",
        "        if not (v3.get('rival_model') or v3.get('e20_hire_guard') or v3.get('s13_tail_sweep')):\n"
        "            return output\n",
        "S13 post admission",
    )
    e20 = (
        "            if v3.get('e20_hire_guard'):\n"
        "                from e20_hire_guard import apply_hire_guard\n"
        "                output, report['e20_hire_guard'] = apply_hire_guard(obs, output, params, enabled=True)\n"
    )
    s13 = e20 + (
        "            if v3.get('s13_tail_sweep'):\n"
        "                from mechanics import SHOPS\n"
        "                from scheduler import post_units\n"
        "                from tail_settlement import compose_tail_settlement\n"
        "                unlocked = list(((obs.get('town') or {}).get('unlocked_shops') or []))\n"
        "                shop_consumed = set()\n"
        "                for shop in unlocked:\n"
        "                    shop_consumed.update(SHOPS.get(shop, ()))\n"
        "                output, report['s13_tail_sweep'] = compose_tail_settlement(\n"
        "                    obs, params, output, project_units=post_units,\n"
        "                    shop_interval=int(params.get('townShopSellInterval', 4)),\n"
        "                    town_interval=int(params.get('townCenterSellInterval', 24)),\n"
        "                    shop_consumed=shop_consumed)\n"
    )
    runtime = _replace_once(runtime, e20, s13, "S13 runtime seam")
    _write(src, "titan_runtime.py", runtime)

    cfg_path = os.path.join(src, "TITAN-CONFIG.json")
    data = json.loads(io.open(cfg_path, encoding="utf-8").read())
    assert "s13_tail_sweep" not in data, "s13_tail_sweep"
    data["s13_tail_sweep"] = False
    with io.open(cfg_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")

    _write(src, "TITAN-RELEASE.md", _read(src, "TITAN-RELEASE.md") + RELEASE_NOTE)
    return src


if __name__ == "__main__":
    print("V3 S13 edits applied to", apply(sys.argv[1]))
