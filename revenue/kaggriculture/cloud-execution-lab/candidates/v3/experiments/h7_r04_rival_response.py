# SPDX-License-Identifier: Apache-2.0
"""H7 experiment: expose V3's existing O01 rival response on the live R04 route.

The integrated V3 tree already ships ``overlay/rival_model.py``.  Its only action edit
classifies a public-state EARLY_EXPANDER and queue-safely appends one BUY_LAND when our
farm still owns only NW, cash clears the configured floor, no land order is already
queued, and the final market queue has a free slot.

Canonical ``TitanAgent._v3_post`` applies that model on the normal controller path, but
R04 is a whole-route delegate and never reaches ``_v3_post``.  This experiment wraps the
*final* R04 callable instead of copying the model.  Running last is deliberate: ROW_ORDER,
EVENING_FLUSH, and the optional opening replacement retain first claim on market rows;
O01 may append BUY_LAND only after those R04 transforms have finished.

This file lives outside ``overlay/**`` and is not included by build_v3.py.  It is a
bench/evaluator arm only until paired competitive-margin evidence justifies production
wiring.  Disabled mode returns the exact parent output object.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

OVERLAY = Path(__file__).resolve().parents[1] / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

from rival_model import apply_rival_model  # noqa: E402

DEFAULT_EARLY_EXPANDER_STEP = 144
DEFAULT_LAND_CASH_FLOOR = 0.0


def install(
    parent: Callable[[Mapping[str, Any], Mapping[str, Any] | None], Mapping[str, Any]],
    *,
    enabled: bool = False,
    early_expander_step: int = DEFAULT_EARLY_EXPANDER_STEP,
    land_cash_floor: float = DEFAULT_LAND_CASH_FLOOR,
):
    """Wrap a fully installed R04 callable with the already-audited O01 edit.

    The wrapper intentionally executes after the parent.  Therefore existing R04 market
    construction, row ordering, evening flush, and opening semantics win before O01 checks
    the final queue capacity.  No parent output is copied in disabled mode.
    """
    previous_prices: dict[int, dict[str, Any]] = {}
    last_step: dict[int, int] = {}
    telemetry: dict[str, Any] = {
        "calls": 0,
        "changed": 0,
        "archetypes": Counter(),
        "reasons": Counter(),
    }

    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        telemetry["calls"] += 1
        if not enabled:
            telemetry["reasons"]["OFF"] += 1
            return action

        cfg = dict(configuration or {})
        cfg["g01_early_expander_step"] = int(early_expander_step)
        cfg["g01_land_cash_floor"] = float(land_cash_floor)

        player = int(observation.get("player", 0))
        step = int(observation.get("step", 0))
        if player not in last_step or step <= last_step[player]:
            previous_prices.pop(player, None)
        last_step[player] = step

        out, report = apply_rival_model(
            observation,
            action,
            previous_prices.get(player),
            cfg,
            enabled=True,
        )
        previous_prices[player] = dict((observation.get("market") or {}).get("prices") or {})
        telemetry["archetypes"][report.get("archetype", "NO_ARCHETYPE")] += 1
        telemetry["reasons"][report.get("reason", "UNKNOWN")] += 1
        telemetry["changed"] += int(bool(report.get("changed")))
        return out

    agent.telemetry = telemetry
    agent.parent = parent
    agent.h7_enabled = bool(enabled)
    return agent
