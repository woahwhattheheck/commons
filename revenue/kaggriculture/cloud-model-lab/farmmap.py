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
                pens.append(((x, y), _fmt_tile(t, day)))
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
    return "\n".join(lines)
