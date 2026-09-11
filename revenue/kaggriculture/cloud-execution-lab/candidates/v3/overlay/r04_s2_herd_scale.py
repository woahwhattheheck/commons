# SPDX-License-Identifier: Apache-2.0
"""V4 S2 profile for the shipped V233 sheep discovery controller.

S2 deliberately does not create a second livestock controller.  The published
V233 mechanism already owns a financed SE unlock, sheep purchase, daily grain
funding, worker confirmation, pasture construction, pickup/place, service,
harvest, fertilizer collection and credited sales.  S2 widens only the animal
surface while preserving V233's published two-worker/two-HIRE footprint, so the
native-tape hand-count synchronization is unchanged.
"""
from __future__ import annotations

BASE_TARGETS = (
    ((5, 5), (6, 5), (7, 5)),
    ((5, 6), (6, 6), (7, 6)),
)

# Two additional SE cells, one per V233 worker.  Four sheep per worker is the
# smallest useful scale probe that does not perturb V233's daily HIRE count.
SCALED_TARGETS = (
    ((5, 5), (6, 5), (7, 5), (5, 7)),
    ((5, 6), (6, 6), (7, 6), (6, 7)),
)

BASE_PROFILE = {
    "sheep": 6,
    "workers": 2,
    "targets": BASE_TARGETS,
}

SCALED_PROFILE = {
    "sheep": 8,
    "workers": 2,
    "targets": SCALED_TARGETS,
}


def v233_profile(enabled=False):
    """Return a fresh, internally consistent V233 investment profile."""
    source = SCALED_PROFILE if enabled else BASE_PROFILE
    targets = tuple(tuple(tuple(site) for site in group) for group in source["targets"])
    profile = {
        "sheep": source["sheep"],
        "workers": source["workers"],
        "targets": targets,
    }
    if profile["workers"] != len(targets):
        raise ValueError("one V233 target group is required per worker")
    sites = [site for group in targets for site in group]
    if profile["sheep"] != len(sites):
        raise ValueError("one target cell is required per sheep")
    if len(set(sites)) != len(sites):
        raise ValueError("V233 sheep target cells must be unique")
    if any(len(site) != 2 or any(type(v) is not int or not 0 <= v < 10 for v in site)
           for site in sites):
        raise ValueError("V233 sheep target cells must be strict in-board coordinates")
    return profile


def initial_fixed_cost(profile):
    """SE land plus sheep purchase, excluding grain and HIRE costs."""
    sheep = profile["sheep"]
    if type(sheep) is not int or sheep <= 0:
        raise ValueError("positive integer sheep count required")
    # V233 eligibility requires NW+NE+SW already unlocked; the final SE land is
    # the standard fourth-quadrant purchase ($4,000). Sheep cost $500 each.
    return 4000 + 500 * sheep
