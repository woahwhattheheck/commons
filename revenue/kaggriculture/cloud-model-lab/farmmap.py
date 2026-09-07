"""Compact but complete farm topology: everything ownable, plantable or workable.

The legality list says what one unit can do where it stands. This says what the farm
IS -- owned versus locked quadrants, every non-empty tile with its exact contents,
every empty plantable tile, the pens, the shed access tiles and the unit positions --
so a plan can be about somewhere the units are not currently standing.

Compression is by grouping only. No tile is dropped because it looked irrelevant.
"""

from constraints import engine


def _fmt_tile(tile, day):
    import prompt as P
    return P._tile_str(tile, day)


def build(obs, config, seat):
    K = engine()
    farm = obs["farms"][seat]
    tiles = farm["tiles"]
    n = len(tiles)
    day = int(obs["day"])
    access = [tuple(t) for t in K._shed_access_tiles(n)]

    empty, locked, weeds, plants, pens, other = [], [], [], [], [], []
    for y in range(n):
        for x in range(n):
            t = tiles[y][x]
            if t is None:
                empty.append((x, y))
            elif t == "LOCKED":
                locked.append((x, y))
            elif isinstance(t, dict) and t.get("kind") == "PLANT":
                plants.append(((x, y), _fmt_tile(t, day)))
            elif isinstance(t, dict) and t.get("kind") == "WEED":
                weeds.append((x, y))
            elif isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE"):
                label = _fmt_tile(t, day)
                pens.append(((x, y), label if "animal" in t else f"{t['kind']} (empty)"))
            else:
                other.append(((x, y), _fmt_tile(t, day)))

    def coords(ps, limit=None):
        s = ps if limit is None else ps[:limit]
        out = ",".join(f"({x},{y})" for x, y in s)
        if limit is not None and len(ps) > limit:
            out += f" +{len(ps) - limit} more"
        return out or "none"

    lines = [f"farm {n}x{n}, quadrants unlocked: "
             f"{', '.join(farm.get('unlocked_quadrants') or ['NW'])}; "
             f"locked tiles {len(locked)}"]
    lines.append(f"shed access tiles (DROP/PICKUP work only here): {coords(access)}")
    units = [("farmer", farm["farmer"])] + [(f"hand{i}", p) for i, p in enumerate(farm.get("hands", []))]
    lines.append("units: " + "; ".join(f"{l} at ({int(p[0])},{int(p[1])})" for l, p in units))
    lines.append(f"empty plantable tiles ({len(empty)}): {coords(empty, 24)}")
    if plants:
        lines.append("plants:")
        for (x, y), s in plants:
            lines.append(f"  ({x},{y}) {s}")
    if pens:
        lines.append("pens:")
        for (x, y), s in pens:
            lines.append(f"  ({x},{y}) {s}")
    if weeds:
        lines.append(f"weeds to DIG ({len(weeds)}): {coords(weeds, 16)}")
    if other:
        for (x, y), s in other:
            lines.append(f"  ({x},{y}) {s}")
    if locked:
        lines.append(f"locked tiles: {coords(locked, 12)}")

    # Stock that is an ANIMAL sitting in the shed cannot produce anything there. The
    # engine's install path is PICKUP at a shed access tile, walk onto an EMPTY
    # matching structure, then PLACE. Stating that path is state, not advice: the
    # model still chooses whether to take it. A bought COW sat unused in the shed for
    # a whole diagnostic segment while the seat kept building structures.
    shed = obs["private"].get("shed", {})
    stock = {a: int(n) for a, n in shed.items() if a in K.ANIMALS and n > 0}
    if stock:
        empty_pens = {}
        for (x, y), desc in pens:
            kind = desc.split()[0] if desc else ""
            if "on" not in desc:
                empty_pens.setdefault(kind, []).append((x, y))
        out = []
        for a, n in sorted(stock.items()):
            need = K.ANIMALS[a]["structure"]
            free = empty_pens.get(need, [])
            where = coords(free, 6) if free else f"none built yet (BUILD_{need} on an empty tile)"
            out.append(f"{a} x{n} needs an empty {need}: {where}")
        lines.append("ANIMALS IN THE SHED (they produce nothing there; to install: PICKUP at a "
                     "shed access tile, stand on an empty matching structure, then PLACE):")
        for o in out:
            lines.append("  " + o)
    # Installed animals produce at the daily refresh, and the care bonus needs the
    # animal FED that same day. FEED consumes 1 WHEAT carried by the unit standing on
    # it, so the WHEAT has to be in that unit's hands, not in the shed. State where
    # the wheat is and what each unit is holding; the model still chooses.
    animals_on_board = [(xy, d) for xy, d in pens if "on" in d]
    if animals_on_board:
        invs = obs["private"].get("inventories", [])
        holders = []
        for i, (label, _p) in enumerate(units):
            w = int((invs[i] if i < len(invs) else {}).get("WHEAT", 0))
            holders.append(f"{label} holds {w} WHEAT")
        shed_wheat = int(shed.get("WHEAT", 0))
        lines.append("FEEDING (an installed animal only pays the care bonus if it is FED the "
                     "same day; FEED spends 1 WHEAT from the hands of the unit standing on it):")
        lines.append("  " + "; ".join(holders))
        lines.append(f"  shed holds {shed_wheat} WHEAT"
                     + ("; PICKUP WHEAT at a shed access tile to carry it to an animal"
                        if shed_wheat else "; buy WHEAT from the market or harvest it"))
        for (x, y), d in animals_on_board:
            lines.append(f"  ({x},{y}) {d}")
    return "\n".join(lines)
