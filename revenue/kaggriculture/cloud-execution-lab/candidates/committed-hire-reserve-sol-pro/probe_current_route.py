# SPDX-License-Identifier: Apache-2.0
"""Repo-native structural probe; runs no game and calls no producer."""
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from scheduler import parent  # noqa: E402
from committed_hire_reserve import (  # noqa: E402
    action_fingerprint,
    protect_committed_hire_seed_boundary,
)


def main() -> int:
    evidence = json.loads((HERE / "evidence" / "episode-107130860-causal-witness.json").read_text())
    routes = parent.routes()
    route = routes[parent.MAIN]
    unit = {
        "farmer": list(route[1].get("farmer", ["PASS"])),
        "hands": [list(row) for row in route[1].get("hands", [])],
    }
    predecessor = {**unit, "market": evidence["opening_boundary"]["v1_market"]}
    candidate = {**unit, "market": evidence["opening_boundary"]["v2_market"]}
    chosen, guard = protect_committed_hire_seed_boundary(
        predecessor,
        candidate,
        route,
        1,
        {"maxMarketOrdersPerTurn": 10, "turnsPerDay": 24},
        post_unit_seeds={"MELON": 0},
        route_switch_steps=[row[0] for row in parent.DECISIONS],
    )
    report = {
        "schema": "titan.committed-hire-reserve.route-probe.v1",
        "route": parent.MAIN,
        "route_length": len(route),
        "selection_step": 1,
        "landed_route_opening_fingerprint": action_fingerprint(route[1]),
        "guard": guard,
        "chosen_is_exact_predecessor": chosen == predecessor,
        "new_games": 0,
        "producer_calls": 0,
    }
    print(json.dumps(report, sort_keys=True, indent=2))
    exact = (
        guard.get("certified") is True
        and guard.get("prefix_plant_requests") == 12
        and guard.get("hire_witness", {}).get("hire_count") == 4
        and guard.get("hire_witness", {}).get("represented_rows") == 23
        and chosen == predecessor
    )
    return 0 if exact else 1


if __name__ == "__main__":
    raise SystemExit(main())
