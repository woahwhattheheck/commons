# SPDX-License-Identifier: Apache-2.0
"""V4 S2 profile for the shipped V233 sheep discovery controller.

S2 deliberately does not create a second livestock controller.  The published
V233 mechanism already owns a financed SE unlock, sheep purchase, daily grain
funding, worker confirmation, pasture construction, pickup/place, service,
harvest, fertilizer collection and credited sales.  S2 only widens that exact
3-sheep-per-worker profile from two rows to three rows when its V4 key is on.
"""
from __future__ import annotations

BASE_PROFILE = {
    "sheep": 6,
    "workers": 2,
    "rows": (5, 6),
}

SCALED_PROFILE = {
    "sheep": 9,
    "workers": 3,
    "rows": (5, 6, 7),
}


def v233_profile(enabled=False):
    """Return a fresh, internally consistent V233 investment profile."""
    source = SCALED_PROFILE if enabled else BASE_PROFILE
    profile = dict(source)
    profile["rows"] = tuple(source["rows"])
    if profile["workers"] != len(profile["rows"]):
        raise ValueError("one V233 worker row is required per worker")
    if profile["sheep"] != 3 * profile["workers"]:
        raise ValueError("V233 service proof is three sheep per worker")
    return profile


def initial_fixed_cost(profile):
    """SE land plus sheep purchase, excluding grain and HIRE costs."""
    sheep = profile["sheep"]
    if type(sheep) is not int or sheep <= 0:
        raise ValueError("positive integer sheep count required")
    # V233 eligibility requires NW+NE+SW already unlocked; the final SE land is
    # the standard fourth-quadrant purchase ($4,000). Sheep cost $500 each.
    return 4000 + 500 * sheep
