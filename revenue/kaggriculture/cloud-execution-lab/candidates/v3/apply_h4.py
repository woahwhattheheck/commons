"""Wire reviewed H4 strawberry top-up into the deterministic V3 package, default OFF.

This runs *after* apply_v3.apply().  The OFF path deliberately keeps the existing
R04 import/call branch intact; only r04_strawberry_topup=True selects the reviewed
H4 wrapper.  H4 is subordinate to r04_sale_window: the key alone never activates a
router or changes canonical/R03 behavior.
"""
from __future__ import annotations

import io
import json
import os

KEY = "r04_strawberry_topup"

FEATURE_ANCHOR = (
    "    r04_sale_window: bool = False\n"
    "    r04_sale_horizon: int = 8\n"
)
FEATURE_REPLACEMENT = (
    "    r04_sale_window: bool = False\n"
    "    r04_strawberry_topup: bool = False\n"
    "    r04_sale_horizon: int = 8\n"
)

R04_CALL_ANCHOR = (
    "            if route == 'r04_sale_window':\n"
    "                from r04_full_router import install\n"
    "                output = install(self, int(self.features.r04_sale_horizon),\n"
    "                                 int(self.features.r04_open_roundtrip),\n"
    "                                 bool(self.features.r04_row_order),\n"
    "                                 bool(self.features.r04_evening_flush),\n"
    "                                 bool(self.features.r04_sale_fertilizer),\n"
    "                                 bool(self.features.r04_cattle_early))(observation, configuration)\n"
)
R04_CALL_REPLACEMENT = (
    "            if route == 'r04_sale_window':\n"
    "                if self.features.r04_strawberry_topup:\n"
    "                    from r04_h4_strawberry import install\n"
    "                    output = install(self, int(self.features.r04_sale_horizon),\n"
    "                                     int(self.features.r04_open_roundtrip),\n"
    "                                     bool(self.features.r04_row_order),\n"
    "                                     bool(self.features.r04_evening_flush),\n"
    "                                     bool(self.features.r04_sale_fertilizer),\n"
    "                                     bool(self.features.r04_cattle_early),\n"
    "                                     strawberry_topup=True)(observation, configuration)\n"
    "                else:\n"
    "                    from r04_full_router import install\n"
    "                    output = install(self, int(self.features.r04_sale_horizon),\n"
    "                                     int(self.features.r04_open_roundtrip),\n"
    "                                     bool(self.features.r04_row_order),\n"
    "                                     bool(self.features.r04_evening_flush),\n"
    "                                     bool(self.features.r04_sale_fertilizer),\n"
    "                                     bool(self.features.r04_cattle_early))(observation, configuration)\n"
    "                self.diagnostics['strawberry_topup'] = bool(self.features.r04_strawberry_topup)\n"
)

RELEASE_NOTE = (
    "\n### V3.1 H4 production wiring (default OFF)\n\n"
    "`r04_strawberry_topup` is package-reachable but ships `false`.  It is subordinate to "
    "`r04_sale_window`: when false, the existing R04 import/call path is retained; when true "
    "alongside R04 it selects the byte-reviewed H4 wrapper, which may top up exactly one existing "
    "STRAWBERRY SELL from already-planned future tape sells inside the normal E184 horizon.  The "
    "wrapper preserves R04 post-policy order (ROW_ORDER, EVENING_FLUSH, OPEN_ROUNDTRIP).  This "
    "wiring carries no default-on or submission authority.\n"
)

MANIFEST_KEY = {
    "default": False,
    "requires": "r04_sale_window",
    "seam": "TitanAgent._v3_r03_act selects H4 only when R04 is active and r04_strawberry_topup is true",
    "module": "r04_h4_strawberry.py",
    "effect": "top up one existing STRAWBERRY SELL from future planned tape sells; no new market row",
}
MANIFEST_LANE = {
    "id": "H4",
    "key": KEY,
    "status": "wired_default_off",
    "lineage": [
        "reviewed H4 experiment #12344/#12419",
        "H4 convergence spine #12447",
        "production wiring default-OFF successor",
    ],
    "authority": "package-reachable only; promotion/default-on requires combined exact-head gates",
}


def _replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise AssertionError("%s: expected 1 match, found %d" % (label, count))
    return text.replace(old, new)


def update_manifest(manifest):
    """Add/update the semantic H4 manifest records during a normal build."""
    keys = manifest.setdefault("keys", {})
    existing = keys.get(KEY)
    if existing not in (None, MANIFEST_KEY):
        raise AssertionError("%s manifest key drift" % KEY)
    keys[KEY] = dict(MANIFEST_KEY)

    lanes = manifest.setdefault("lanes", [])
    matches = [i for i, lane in enumerate(lanes) if lane.get("id") == "H4"]
    if len(matches) > 1:
        raise AssertionError("duplicate H4 manifest lanes")
    if matches:
        lanes[matches[0]] = dict(MANIFEST_LANE)
    else:
        lanes.append(dict(MANIFEST_LANE))
    return manifest


def require_manifest(manifest):
    if manifest.get("keys", {}).get(KEY) != MANIFEST_KEY:
        raise AssertionError("%s manifest key missing or drifted" % KEY)
    matches = [lane for lane in manifest.get("lanes", []) if lane.get("id") == "H4"]
    if matches != [MANIFEST_LANE]:
        raise AssertionError("H4 manifest lane missing or drifted")


def apply(src):
    def read(name):
        return io.open(os.path.join(src, name), encoding="utf-8", newline="").read()

    def write(name, text):
        with io.open(os.path.join(src, name), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    runtime = read("titan_runtime.py")
    runtime = _replace_once(runtime, FEATURE_ANCHOR, FEATURE_REPLACEMENT, "H4 feature field")
    runtime = _replace_once(runtime, R04_CALL_ANCHOR, R04_CALL_REPLACEMENT, "H4 R04 delegate seam")
    write("titan_runtime.py", runtime)

    cfg_path = os.path.join(src, "TITAN-CONFIG.json")
    data = json.loads(io.open(cfg_path, encoding="utf-8").read())
    if KEY in data:
        raise AssertionError("%s already exists in TITAN-CONFIG.json" % KEY)
    data[KEY] = False
    with io.open(cfg_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")

    write("TITAN-RELEASE.md", read("TITAN-RELEASE.md") + RELEASE_NOTE)
    return src
