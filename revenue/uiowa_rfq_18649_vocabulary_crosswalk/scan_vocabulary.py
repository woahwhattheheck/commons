"""Scan the RFQ-18649 lane tree for the terms actually used in group and area columns.

Evidence, not assertion: every reported term carries the file, the column and the row
count it was observed in, so a reader can open the file and see it.

Strictly READ-ONLY. This module opens files to parse them and writes nothing.

Python 3 standard library only.
"""
import csv
import json
import os

# Column names that occupy the "which system group" and "which assessment area" slots.
# Matching is on the exact lowercased header - guessing which columns mean what is the
# same error this package exists to catch, one level up.
GROUP_COLUMNS = frozenset({
    "group", "service", "system_group", "group_code", "group_id", "team",
})
AREA_COLUMNS = frozenset({
    "area", "assessment_area", "area_code", "dimension", "assessment_dimension",
    "area_label",
})

# A cell holding several terms at once. Recorded as a compound observation rather than
# split, because splitting assumes the separator means "and" and it may not.
MULTI_SEPARATORS = ("|", ";")

MAX_TERM_LEN = 48
LANE_PREFIX = "uiowa_rfq_18649_"


def _read_rows(path):
    """Read a CSV, dropping '#' banner lines, which several lanes use."""
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        lines = [ln for ln in fh.read().splitlines() if not ln.startswith("#")]
    if not lines:
        return []
    return list(csv.DictReader(lines))


def _is_placeholder(value):
    """Template files carry <angle-bracket> placeholders. Those are not vocabulary."""
    return value.startswith("<") or value.endswith(">") or value in {"-", "n/a", "N/A"}


def scan(root, skip_lanes=()):
    """Return observations of every group/area term in the tree under `root`.

    skip_lanes lets this package exclude its own output and any lane that merely
    copies another's artifacts, so one file is not counted as two sources of truth.
    """
    observations = []
    for lane in sorted(os.listdir(root)):
        if not lane.startswith(LANE_PREFIX) or lane in skip_lanes:
            continue
        lane_path = os.path.join(root, lane)
        if not os.path.isdir(lane_path):
            continue
        for dirpath, dirnames, files in os.walk(lane_path):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for fn in sorted(files):
                if not fn.endswith(".csv"):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    rows = _read_rows(path)
                except OSError:
                    continue
                if not rows:
                    continue
                for column in rows[0].keys():
                    if column is None:
                        continue
                    slot = ("group" if column.strip().lower() in GROUP_COLUMNS
                            else "area" if column.strip().lower() in AREA_COLUMNS
                            else None)
                    if slot is None:
                        continue
                    counts = {}
                    for row in rows:
                        raw = (row.get(column) or "").strip()
                        if not raw or len(raw) > MAX_TERM_LEN or _is_placeholder(raw):
                            continue
                        counts[raw] = counts.get(raw, 0) + 1
                    for term, n in sorted(counts.items()):
                        observations.append({
                            "slot": slot,
                            "term": term,
                            "lane": lane,
                            "file": os.path.relpath(path, root).replace(os.sep, "/"),
                            "column": column,
                            "rows": n,
                            "compound": any(sep in term for sep in MULTI_SEPARATORS),
                        })
    return sorted(observations, key=lambda o: (o["slot"], o["term"], o["file"], o["column"]))


def terms_by_slot(observations):
    out = {"group": {}, "area": {}}
    for o in observations:
        entry = out[o["slot"]].setdefault(
            o["term"], {"term": o["term"], "rows": 0, "lanes": set(), "files": set(),
                        "columns": set(), "compound": o["compound"]})
        entry["rows"] += o["rows"]
        entry["lanes"].add(o["lane"])
        entry["files"].add(o["file"])
        entry["columns"].add(o["column"])
    for slot in out:
        for entry in out[slot].values():
            for key in ("lanes", "files", "columns"):
                entry[key] = sorted(entry[key])
    return out


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else ".."
    obs = scan(root)
    print(json.dumps(terms_by_slot(obs), indent=2, sort_keys=True, default=list))
